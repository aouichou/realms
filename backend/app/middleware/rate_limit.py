"""
Rate Limiting Middleware
Protects API from abuse with configurable rate limits
"""

import time
from collections import defaultdict
from typing import Callable, Dict, Tuple

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with multiple strategies.

    Features:
    - IP-based rate limiting
    - User-based rate limiting (for authenticated requests)
    - Configurable limits per endpoint
    - Sliding window algorithm
    - DDoS protection with automatic blocking
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

        # Storage for rate limit tracking
        self.request_counts: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Dict[str, float] = {}

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier (IP or user ID)"""
        # Try to get user from auth token
        user_id = request.state.__dict__.get("user_id")
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        if request.client:
            # Check X-Forwarded-For header for proxied requests
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            return request.client.host

        return "unknown"

    def _is_blocked(self, identifier: str) -> bool:
        """Check if client is currently blocked"""
        if identifier in self.blocked_ips:
            block_time = self.blocked_ips[identifier]
            if time.time() - block_time < self.block_duration:
                return True
            else:
                # Unblock after duration expires
                del self.blocked_ips[identifier]
        return False

    def _check_rate_limit(self, identifier: str) -> Tuple[bool, str, int]:
        """
        Check if request should be allowed.

        Returns:
            (allowed, reason, retry_after_seconds)
        """
        now = time.time()

        # Clean old requests (older than 1 hour)
        self.request_counts[identifier] = [
            ts for ts in self.request_counts[identifier] if now - ts < 3600
        ]

        request_times = self.request_counts[identifier]

        # Check burst protection (requests in last 10 seconds)
        recent_requests = [ts for ts in request_times if now - ts < 10]
        if len(recent_requests) >= self.burst_threshold:
            # Block this client
            self.blocked_ips[identifier] = now
            logger.warning(
                f"Client {identifier} blocked for burst violation: "
                f"{len(recent_requests)} requests in 10s"
            )
            return False, "burst_protection", self.block_duration

        # Check per-minute limit
        minute_requests = [ts for ts in request_times if now - ts < 60]
        if len(minute_requests) >= self.requests_per_minute:
            retry_after = 60 - (now - minute_requests[0])
            return False, "rate_limit_minute", int(retry_after)

        # Check per-hour limit
        hour_requests = request_times
        if len(hour_requests) >= self.requests_per_hour:
            retry_after = 3600 - (now - hour_requests[0])
            return False, "rate_limit_hour", int(retry_after)

        return True, "allowed", 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        identifier = self._get_client_identifier(request)

        # Check if client is blocked
        if self._is_blocked(identifier):
            logger.warning(f"Blocked client attempted request: {identifier}")
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
        allowed, reason, retry_after = self._check_rate_limit(identifier)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier}: {reason}",
                extra={
                    "identifier": identifier,
                    "reason": reason,
                    "path": request.url.path,
                    "method": request.method,
                },
            )

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
