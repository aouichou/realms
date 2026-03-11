"""
Rate Limiting Middleware
Protects API from abuse with configurable rate limits.

Uses Redis sorted sets (sliding window) as primary storage,
with an in-memory fallback when Redis is unavailable.
"""

import time
from collections import defaultdict
from typing import Callable, Dict, Tuple

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.logger import get_logger
from app.observability.metrics import metrics as app_metrics
from app.services.redis_service import session_service

logger = get_logger(__name__)


# Endpoint-specific rate limits (requests per minute)
ENDPOINT_RATE_LIMITS = {
    "/api/v1/auth/login": {"requests_per_minute": 5, "description": "login attempts"},
    "/api/v1/auth/register": {"requests_per_minute": 3, "description": "registration attempts"},
    "/api/v1/auth/refresh": {"requests_per_minute": 10, "description": "token refreshes"},
    "/api/v1/image/generate": {"requests_per_hour": 5, "description": "image generations"},
    "/api/v1/adventure/start": {"requests_per_hour": 10, "description": "adventure starts"},
}

# Redis key prefixes
_RATELIMIT_PREFIX = "ratelimit:"
_BLOCKED_PREFIX = "ratelimit:blocked:"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with multiple strategies.

    Features:
    - IP-based rate limiting
    - User-based rate limiting (for authenticated requests)
    - Configurable limits per endpoint
    - Sliding window algorithm (Redis sorted sets or in-memory)
    - DDoS protection with automatic blocking
    - Automatic fallback to in-memory when Redis is unavailable
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_threshold: int = 20,
        block_duration: int = 300,  # 5 minutes
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_threshold = burst_threshold
        self.block_duration = block_duration

        # In-memory fallback storage
        self.request_counts: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Dict[str, float] = {}

        # Periodic cleanup counter for in-memory fallback
        self._mem_request_counter = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_redis(self):
        """Return the shared Redis client or None."""
        return session_service.redis

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier (IP or user ID)"""
        user_id = request.state.__dict__.get("user_id")
        if user_id:
            return f"user:{user_id}"

        if request.client:
            return request.client.host

        return "unknown"

    # ------------------------------------------------------------------
    # Redis-backed helpers
    # ------------------------------------------------------------------

    async def _redis_record_request(self, r, identifier: str, endpoint: str) -> None:
        """Record a request timestamp in the appropriate Redis sorted sets."""
        now = time.time()
        member = f"{now}"

        # Global key
        global_key = f"{_RATELIMIT_PREFIX}{identifier}:global"
        await r.zadd(global_key, {member: now})
        await r.expire(global_key, 3600)

        # Endpoint-specific key (if applicable)
        if endpoint in ENDPOINT_RATE_LIMITS:
            ep_key = f"{_RATELIMIT_PREFIX}{identifier}:{endpoint}"
            await r.zadd(ep_key, {member: now})
            await r.expire(ep_key, 3600)

    async def _redis_is_blocked(self, r, identifier: str) -> bool:
        """Check if the identifier is blocked in Redis."""
        key = f"{_BLOCKED_PREFIX}{identifier}"
        return await r.exists(key) > 0

    async def _redis_block(self, r, identifier: str) -> None:
        """Block an identifier in Redis with TTL."""
        key = f"{_BLOCKED_PREFIX}{identifier}"
        await r.set(key, "1", ex=self.block_duration)

    async def _redis_check_rate_limit(
        self, r, identifier: str, endpoint: str
    ) -> Tuple[bool, str, int]:
        """
        Check rate limits using Redis sorted sets (sliding window).

        Returns:
            (allowed, reason, retry_after_seconds)
        """
        now = time.time()
        global_key = f"{_RATELIMIT_PREFIX}{identifier}:global"

        # Clean entries older than 1 hour from the global set
        await r.zremrangebyscore(global_key, "-inf", now - 3600)

        # --- Burst protection (last 10 seconds) ---
        burst_count = await r.zcount(global_key, now - 10, "+inf")
        if burst_count >= self.burst_threshold:
            await self._redis_block(r, identifier)
            logger.warning(
                f"Client {identifier} blocked for burst violation: {burst_count} requests in 10s"
            )
            return False, "burst_protection", self.block_duration

        # --- Endpoint-specific limits ---
        if endpoint in ENDPOINT_RATE_LIMITS:
            limits = ENDPOINT_RATE_LIMITS[endpoint]
            ep_key = f"{_RATELIMIT_PREFIX}{identifier}:{endpoint}"

            # Clean old entries from endpoint set
            await r.zremrangebyscore(ep_key, "-inf", now - 3600)

            if "requests_per_minute" in limits:
                ep_minute_count = await r.zcount(ep_key, now - 60, "+inf")
                if ep_minute_count >= limits["requests_per_minute"]:
                    # Estimate retry_after from oldest entry in the window
                    oldest = await r.zrangebyscore(ep_key, now - 60, "+inf", start=0, num=1)
                    retry_after = 60 - (now - float(oldest[0])) if oldest else 60
                    logger.warning(
                        f"Endpoint rate limit exceeded for {identifier} on {endpoint}: "
                        f"{ep_minute_count}/{limits['requests_per_minute']} {limits['description']}"
                    )
                    return (
                        False,
                        f"endpoint_limit_{limits['description']}",
                        max(1, int(retry_after)),
                    )

            if "requests_per_hour" in limits:
                ep_hour_count = await r.zcount(ep_key, now - 3600, "+inf")
                if ep_hour_count >= limits["requests_per_hour"]:
                    oldest = await r.zrangebyscore(ep_key, now - 3600, "+inf", start=0, num=1)
                    retry_after = 3600 - (now - float(oldest[0])) if oldest else 3600
                    logger.warning(
                        f"Endpoint hourly limit exceeded for {identifier} on {endpoint}: "
                        f"{ep_hour_count}/{limits['requests_per_hour']} {limits['description']}"
                    )
                    return (
                        False,
                        f"endpoint_limit_hour_{limits['description']}",
                        max(1, int(retry_after)),
                    )

        # --- Global per-minute limit ---
        minute_count = await r.zcount(global_key, now - 60, "+inf")
        if minute_count >= self.requests_per_minute:
            oldest = await r.zrangebyscore(global_key, now - 60, "+inf", start=0, num=1)
            retry_after = 60 - (now - float(oldest[0])) if oldest else 60
            return False, "rate_limit_minute", max(1, int(retry_after))

        # --- Global per-hour limit ---
        hour_count = await r.zcount(global_key, now - 3600, "+inf")
        if hour_count >= self.requests_per_hour:
            oldest = await r.zrangebyscore(global_key, now - 3600, "+inf", start=0, num=1)
            retry_after = 3600 - (now - float(oldest[0])) if oldest else 3600
            return False, "rate_limit_hour", max(1, int(retry_after))

        return True, "allowed", 0

    async def _redis_get_counts(self, r, identifier: str) -> Tuple[int, int]:
        """Return (minute_count, hour_count) from Redis."""
        now = time.time()
        global_key = f"{_RATELIMIT_PREFIX}{identifier}:global"
        minute_count = await r.zcount(global_key, now - 60, "+inf")
        hour_count = await r.zcount(global_key, now - 3600, "+inf")
        return minute_count, hour_count

    # ------------------------------------------------------------------
    # In-memory fallback helpers
    # ------------------------------------------------------------------

    def _mem_cleanup(self) -> None:
        """Periodic cleanup of in-memory data (every 100 requests)."""
        self._mem_request_counter += 1
        if self._mem_request_counter % 100 != 0:
            return

        now = time.time()
        # Remove request timestamps older than 1 hour
        stale_keys = []
        for ident, timestamps in self.request_counts.items():
            self.request_counts[ident] = [ts for ts in timestamps if now - ts < 3600]
            if not self.request_counts[ident]:
                stale_keys.append(ident)
        for k in stale_keys:
            del self.request_counts[k]

        # Remove expired blocks
        expired = [ip for ip, t in self.blocked_ips.items() if now - t >= self.block_duration]
        for ip in expired:
            del self.blocked_ips[ip]

    def _mem_is_blocked(self, identifier: str) -> bool:
        """Check if client is currently blocked (in-memory)."""
        if identifier in self.blocked_ips:
            block_time = self.blocked_ips[identifier]
            if time.time() - block_time < self.block_duration:
                return True
            else:
                del self.blocked_ips[identifier]
        return False

    def _mem_check_rate_limit(self, identifier: str, endpoint: str = "") -> Tuple[bool, str, int]:
        """
        Check rate limits using in-memory storage.

        Returns:
            (allowed, reason, retry_after_seconds)
        """
        now = time.time()

        # Clean old requests (older than 1 hour)
        self.request_counts[identifier] = [
            ts for ts in self.request_counts[identifier] if now - ts < 3600
        ]

        request_times = self.request_counts[identifier]

        # Burst protection (requests in last 10 seconds)
        recent_requests = [ts for ts in request_times if now - ts < 10]
        if len(recent_requests) >= self.burst_threshold:
            self.blocked_ips[identifier] = now
            logger.warning(
                f"Client {identifier} blocked for burst violation: "
                f"{len(recent_requests)} requests in 10s"
            )
            return False, "burst_protection", self.block_duration

        # Endpoint-specific rate limits
        if endpoint in ENDPOINT_RATE_LIMITS:
            limits = ENDPOINT_RATE_LIMITS[endpoint]

            if "requests_per_minute" in limits:
                minute_requests = [ts for ts in request_times if now - ts < 60]
                if len(minute_requests) >= limits["requests_per_minute"]:
                    retry_after = 60 - (now - minute_requests[0])
                    logger.warning(
                        f"Endpoint rate limit exceeded for {identifier} on {endpoint}: "
                        f"{len(minute_requests)}/{limits['requests_per_minute']} {limits['description']}"
                    )
                    return (
                        False,
                        f"endpoint_limit_{limits['description']}",
                        max(1, int(retry_after)),
                    )

            if "requests_per_hour" in limits:
                hour_requests = request_times
                if len(hour_requests) >= limits["requests_per_hour"]:
                    retry_after = 3600 - (now - hour_requests[0])
                    logger.warning(
                        f"Endpoint hourly limit exceeded for {identifier} on {endpoint}: "
                        f"{len(hour_requests)}/{limits['requests_per_hour']} {limits['description']}"
                    )
                    return (
                        False,
                        f"endpoint_limit_hour_{limits['description']}",
                        max(1, int(retry_after)),
                    )

        # Global per-minute limit
        minute_requests = [ts for ts in request_times if now - ts < 60]
        if len(minute_requests) >= self.requests_per_minute:
            retry_after = 60 - (now - minute_requests[0])
            return False, "rate_limit_minute", max(1, int(retry_after))

        # Global per-hour limit
        hour_requests = request_times
        if len(hour_requests) >= self.requests_per_hour:
            retry_after = 3600 - (now - hour_requests[0])
            return False, "rate_limit_hour", max(1, int(retry_after))

        return True, "allowed", 0

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        identifier = self._get_client_identifier(request)
        endpoint = request.url.path

        r = self._get_redis()
        use_redis = r is not None

        # ------------------------------------------------------------------
        # Try Redis, fall back to in-memory on any connection error
        # ------------------------------------------------------------------
        if use_redis:
            try:
                # Check if blocked
                if await self._redis_is_blocked(r, identifier):
                    logger.warning(f"Blocked client attempted request: {identifier}")
                    client_type = "user" if identifier.startswith("user:") else "ip"
                    app_metrics.record_rate_limit_violation(client_type, blocked=True)
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": "TooManyRequests",
                            "message": "You have been temporarily blocked due to excessive requests",
                            "retry_after": self.block_duration,
                        },
                        headers={"Retry-After": str(self.block_duration)},
                    )

                # Check rate limits
                allowed, reason, retry_after = await self._redis_check_rate_limit(
                    r, identifier, endpoint
                )

                if not allowed:
                    logger.warning(
                        f"Rate limit exceeded for {identifier}: {reason}",
                        extra={
                            "identifier": identifier,
                            "reason": reason,
                            "path": endpoint,
                            "method": request.method,
                        },
                    )
                    client_type = "user" if identifier.startswith("user:") else "ip"
                    app_metrics.record_rate_limit_violation(client_type, blocked="burst" in reason)
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": "TooManyRequests",
                            "message": f"Rate limit exceeded: {reason.replace('_', ' ')}",
                            "retry_after": retry_after,
                        },
                        headers={"Retry-After": str(retry_after)},
                    )

                # Record this request
                await self._redis_record_request(r, identifier, endpoint)

                # Process request
                response = await call_next(request)

                # Add rate limit headers
                minute_count, hour_count = await self._redis_get_counts(r, identifier)
                response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
                response.headers["X-RateLimit-Remaining-Minute"] = str(
                    max(0, self.requests_per_minute - minute_count)
                )
                response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
                response.headers["X-RateLimit-Remaining-Hour"] = str(
                    max(0, self.requests_per_hour - hour_count)
                )

                return response

            except (ConnectionError, TimeoutError, OSError) as exc:
                logger.warning(
                    f"Redis unavailable for rate limiting, falling back to in-memory: {exc}"
                )
                # Fall through to in-memory path below

        # ------------------------------------------------------------------
        # In-memory fallback
        # ------------------------------------------------------------------
        self._mem_cleanup()

        if self._mem_is_blocked(identifier):
            logger.warning(f"Blocked client attempted request: {identifier}")
            client_type = "user" if identifier.startswith("user:") else "ip"
            app_metrics.record_rate_limit_violation(client_type, blocked=True)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "TooManyRequests",
                    "message": "You have been temporarily blocked due to excessive requests",
                    "retry_after": self.block_duration,
                },
                headers={"Retry-After": str(self.block_duration)},
            )

        allowed, reason, retry_after = self._mem_check_rate_limit(identifier, endpoint)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier}: {reason}",
                extra={
                    "identifier": identifier,
                    "reason": reason,
                    "path": endpoint,
                    "method": request.method,
                },
            )
            client_type = "user" if identifier.startswith("user:") else "ip"
            app_metrics.record_rate_limit_violation(client_type, blocked="burst" in reason)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "TooManyRequests",
                    "message": f"Rate limit exceeded: {reason.replace('_', ' ')}",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        self.request_counts[identifier].append(time.time())

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        identifier_requests = self.request_counts[identifier]
        minute_count = len([ts for ts in identifier_requests if time.time() - ts < 60])
        hour_count = len(identifier_requests)

        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            max(0, self.requests_per_minute - minute_count)
        )
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            max(0, self.requests_per_hour - hour_count)
        )

        return response
