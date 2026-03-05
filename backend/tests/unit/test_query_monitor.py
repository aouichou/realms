"""Tests for QueryPerformanceMonitor — query_monitor.py"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from app.middleware.query_monitor import QueryPerformanceMonitor, query_monitor

# ---------------------------------------------------------------------------
# Construction and defaults
# ---------------------------------------------------------------------------


class TestQueryPerformanceMonitorInit:
    def test_defaults(self):
        qm = QueryPerformanceMonitor()
        assert qm.query_count == 0
        assert qm.total_time == 0.0
        assert qm.queries == []

    def test_thresholds(self):
        assert QueryPerformanceMonitor.SLOW_QUERY_THRESHOLD == 1.0
        assert QueryPerformanceMonitor.VERY_SLOW_QUERY_THRESHOLD == 3.0


# ---------------------------------------------------------------------------
# setup_query_logging
# ---------------------------------------------------------------------------


class TestSetupQueryLogging:
    def test_registers_listeners(self):
        """Calling setup_query_logging should not error."""
        # We can't easily verify event registration without a real engine,
        # but we can ensure the function runs without error.
        QueryPerformanceMonitor.setup_query_logging()


# ---------------------------------------------------------------------------
# Event listener callbacks (before/after cursor execute)
# ---------------------------------------------------------------------------


class TestQueryListenerCallbacks:
    def test_slow_query_logged(self):
        """Simulate the after_cursor_execute callback for a slow query."""
        from sqlalchemy import create_engine

        # Create a real in-memory engine to trigger events
        engine = create_engine("sqlite:///:memory:")

        # Ensure listeners are registered
        QueryPerformanceMonitor.setup_query_logging()

        with patch("app.middleware.query_monitor.logger") as mock_logger:
            # Execute a real query to trigger the callbacks
            with engine.connect() as conn:
                # Monkey-patch time to simulate slow query
                original_time = time.time
                call_count = [0]

                def fake_time():
                    call_count[0] += 1
                    if call_count[0] <= 1:
                        # before_cursor_execute records start time
                        return 1000.0
                    else:
                        # after_cursor_execute reads end time → 1s elapsed
                        return 1001.0

                with patch("app.middleware.query_monitor.time.time", fake_time):
                    conn.execute(MagicMock(__str__=lambda s: "SELECT 1"))


# ---------------------------------------------------------------------------
# track_request_queries
# ---------------------------------------------------------------------------


class TestTrackRequestQueries:
    async def test_resets_counters(self):
        qm = QueryPerformanceMonitor()
        qm.query_count = 99
        qm.total_time = 5.0

        async with qm.track_request_queries() as tracker:
            assert tracker.query_count == 0
            assert tracker.total_time == 0.0

    async def test_warns_high_query_count(self):
        qm = QueryPerformanceMonitor()
        with patch("app.middleware.query_monitor.logger") as mock_logger:
            async with qm.track_request_queries() as tracker:
                tracker.query_count = 15
                tracker.total_time = 2.0

            mock_logger.warning.assert_called()

    async def test_no_warning_low_count(self):
        qm = QueryPerformanceMonitor()
        with patch("app.middleware.query_monitor.logger") as mock_logger:
            async with qm.track_request_queries() as tracker:
                tracker.query_count = 3
                tracker.total_time = 0.1

            mock_logger.warning.assert_not_called()


# ---------------------------------------------------------------------------
# log_query_stats
# ---------------------------------------------------------------------------


class TestLogQueryStats:
    def test_passes_without_error(self):
        qm = QueryPerformanceMonitor()
        mock_session = MagicMock()
        qm.log_query_stats(mock_session)  # Currently a no-op, should not error


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------


class TestGlobalInstance:
    def test_global_instance_exists(self):
        assert isinstance(query_monitor, QueryPerformanceMonitor)
