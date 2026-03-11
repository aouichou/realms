"""Tests for rate-limit middleware (in-memory path)."""

import time
from unittest.mock import MagicMock

from app.middleware.rate_limit import ENDPOINT_RATE_LIMITS, RateLimitMiddleware


def _make_middleware(**kwargs) -> RateLimitMiddleware:
    """Instantiate RateLimitMiddleware with defaults suitable for testing."""
    defaults = {
        "app": None,
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "burst_threshold": 20,
        "block_duration": 300,
    }
    defaults.update(kwargs)
    return RateLimitMiddleware(**defaults)


def _fake_request(host: str = "1.2.3.4", forwarded_for: str | None = None, user_id=None):
    """Build a minimal mock request for _get_client_identifier."""
    request = MagicMock()
    request.client.host = host

    headers = {}
    if forwarded_for:
        headers["X-Forwarded-For"] = forwarded_for
    request.headers.get = lambda key, default=None: headers.get(key, default)

    state_dict = {}
    if user_id:
        state_dict["user_id"] = user_id
    request.state.__dict__ = state_dict

    return request


# ---------------------------------------------------------------------------
# _get_client_identifier
# ---------------------------------------------------------------------------


class TestGetClientIdentifier:
    def test_returns_client_host(self):
        mw = _make_middleware()
        req = _fake_request(host="10.0.0.1")
        assert mw._get_client_identifier(req) == "10.0.0.1"

    def test_ignores_x_forwarded_for(self):
        """X-Forwarded-For is no longer trusted (H1 security fix)."""
        mw = _make_middleware()
        req = _fake_request(host="10.0.0.1", forwarded_for="203.0.113.50, 70.41.3.18")
        assert mw._get_client_identifier(req) == "10.0.0.1"

    def test_prefers_user_id(self):
        mw = _make_middleware()
        req = _fake_request(host="10.0.0.1", user_id="user-abc")
        assert mw._get_client_identifier(req) == "user:user-abc"


# ---------------------------------------------------------------------------
# _mem_is_blocked
# ---------------------------------------------------------------------------


class TestMemIsBlocked:
    def test_unknown_identifier_not_blocked(self):
        mw = _make_middleware()
        assert mw._mem_is_blocked("ip:1.2.3.4") is False

    def test_recently_blocked_ip(self):
        mw = _make_middleware(block_duration=300)
        mw.blocked_ips["ip:1.2.3.4"] = time.time()
        assert mw._mem_is_blocked("ip:1.2.3.4") is True

    def test_expired_block(self):
        mw = _make_middleware(block_duration=300)
        mw.blocked_ips["ip:1.2.3.4"] = time.time() - 400  # expired
        assert mw._mem_is_blocked("ip:1.2.3.4") is False


# ---------------------------------------------------------------------------
# _mem_check_rate_limit
# ---------------------------------------------------------------------------


class TestMemCheckRateLimit:
    def test_allows_normal_traffic(self):
        mw = _make_middleware()
        allowed, reason, retry = mw._mem_check_rate_limit("ip:1.2.3.4", "/api/v1/test")
        assert allowed is True
        assert reason == "allowed"

    def test_blocks_burst(self):
        mw = _make_middleware(burst_threshold=5)
        now = time.time()
        mw.request_counts["ip:1.2.3.4"] = [now - i * 0.1 for i in range(5)]
        allowed, reason, retry = mw._mem_check_rate_limit("ip:1.2.3.4", "/api/v1/test")
        assert allowed is False
        assert reason == "burst_protection"
        assert retry == mw.block_duration

    def test_blocks_per_minute_overflow(self):
        mw = _make_middleware(requests_per_minute=5, burst_threshold=100)
        now = time.time()
        # 5 requests in the last 30 seconds (well within 60s window)
        mw.request_counts["ip:1.2.3.4"] = [now - i * 5 for i in range(5)]
        allowed, reason, retry = mw._mem_check_rate_limit("ip:1.2.3.4", "/api/v1/test")
        assert allowed is False
        assert reason == "rate_limit_minute"

    def test_blocks_endpoint_login_limit(self):
        mw = _make_middleware(burst_threshold=100, requests_per_minute=100)
        now = time.time()
        login_limit = ENDPOINT_RATE_LIMITS["/api/v1/auth/login"]["requests_per_minute"]
        mw.request_counts["ip:1.2.3.4"] = [now - i * 2 for i in range(login_limit)]
        allowed, reason, retry = mw._mem_check_rate_limit("ip:1.2.3.4", "/api/v1/auth/login")
        assert allowed is False
        assert "login" in reason

    def test_allows_within_endpoint_limit(self):
        mw = _make_middleware(burst_threshold=100, requests_per_minute=100)
        now = time.time()
        login_limit = ENDPOINT_RATE_LIMITS["/api/v1/auth/login"]["requests_per_minute"]
        mw.request_counts["ip:1.2.3.4"] = [now - i * 2 for i in range(login_limit - 1)]
        allowed, reason, retry = mw._mem_check_rate_limit("ip:1.2.3.4", "/api/v1/auth/login")
        assert allowed is True

    def test_blocks_per_hour_overflow(self):
        mw = _make_middleware(
            requests_per_minute=10000,
            requests_per_hour=5,
            burst_threshold=10000,
        )
        now = time.time()
        # 5 requests spread over last 30 minutes
        mw.request_counts["ip:1.2.3.4"] = [now - i * 360 for i in range(5)]
        allowed, reason, retry = mw._mem_check_rate_limit("ip:1.2.3.4", "/api/v1/test")
        assert allowed is False
        assert reason == "rate_limit_hour"


# ---------------------------------------------------------------------------
# _mem_cleanup
# ---------------------------------------------------------------------------


class TestMemCleanup:
    def test_removes_old_entries(self):
        mw = _make_middleware()
        old_ts = time.time() - 7200  # 2 hours ago
        mw.request_counts["ip:old"] = [old_ts]
        mw.request_counts["ip:new"] = [time.time()]

        # Force cleanup to run (counter must be multiple of 100)
        mw._mem_request_counter = 99
        mw._mem_cleanup()

        assert "ip:old" not in mw.request_counts
        assert "ip:new" in mw.request_counts

    def test_removes_expired_blocks(self):
        mw = _make_middleware(block_duration=300)
        mw.blocked_ips["ip:expired"] = time.time() - 400
        mw.blocked_ips["ip:active"] = time.time()

        mw._mem_request_counter = 99
        mw._mem_cleanup()

        assert "ip:expired" not in mw.blocked_ips
        assert "ip:active" in mw.blocked_ips

    def test_cleanup_only_runs_every_100(self):
        mw = _make_middleware()
        old_ts = time.time() - 7200
        mw.request_counts["ip:old"] = [old_ts]

        mw._mem_request_counter = 50
        mw._mem_cleanup()

        # Should NOT have cleaned up (counter 51 is not multiple of 100)
        assert "ip:old" in mw.request_counts
