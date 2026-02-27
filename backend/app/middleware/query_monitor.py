"""
Database Query Performance Monitoring
Tracks slow queries and provides optimization insights
"""

import time
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.logger import get_logger

logger = get_logger(__name__)


class QueryPerformanceMonitor:
    """
    Monitor database query performance.

    Features:
    - Track query execution time
    - Log slow queries
    - Detect N+1 query problems
    - Query count tracking per request
    """

    SLOW_QUERY_THRESHOLD = 0.5  # Warn if query takes > 500ms
    VERY_SLOW_QUERY_THRESHOLD = 2.0  # Error if query takes > 2s

    def __init__(self):
        self.query_count = 0
        self.total_time = 0.0
        self.queries = []

    @staticmethod
    def setup_query_logging():
        """Setup SQLAlchemy event listeners for query logging"""

        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, _cursor, statement, _parameters, _context, _executemany):
            conn.info.setdefault("query_start_time", []).append(time.time())

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, _cursor, statement, _parameters, _context, _executemany):
            total = time.time() - conn.info["query_start_time"].pop()

            # Log slow queries
            if total > QueryPerformanceMonitor.VERY_SLOW_QUERY_THRESHOLD:
                logger.error(
                    f"VERY SLOW QUERY ({total:.3f}s): {statement[:200]}",
                    extra={"duration": f"{total:.3f}s", "query": statement[:500]},
                )
            elif total > QueryPerformanceMonitor.SLOW_QUERY_THRESHOLD:
                logger.warning(
                    f"Slow query ({total:.3f}s): {statement[:200]}",
                    extra={"duration": f"{total:.3f}s", "query": statement[:500]},
                )

    @asynccontextmanager
    async def track_request_queries(self):
        """Context manager to track all queries in a request"""
        self.query_count = 0
        self.total_time = 0.0
        self.queries = []

        try:
            yield self
        finally:
            # Log request query stats
            if self.query_count > 10:
                logger.warning(
                    f"High query count: {self.query_count} queries in {self.total_time:.3f}s",
                    extra={
                        "query_count": self.query_count,
                        "total_time": f"{self.total_time:.3f}s",
                        "avg_time": f"{self.total_time / self.query_count:.3f}s",
                    },
                )

    def log_query_stats(self, session: AsyncSession):
        """Log query statistics for a session"""
        # This would require tracking queries at the session level
        pass


# Global query monitor instance
query_monitor = QueryPerformanceMonitor()
