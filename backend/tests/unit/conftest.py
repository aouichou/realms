"""
Unit-test conftest — fixtures for isolated, fast tests.

CRITICAL IMPLEMENTATION NOTES
------------------------------
* The app creates its SQLAlchemy engine at *module import time* inside
  ``app.db.base``::

      engine = create_async_engine(settings.database_url, ...)
      async_session = async_sessionmaker(engine, ...)

  So we MUST set ``DATABASE_URL`` before any app import (done in the root
  conftest via ``os.environ.setdefault``).

* We create our own test engine + session and override the ``get_db``
  dependency so every unit test operates on an in-memory SQLite database.

* ``ActiveEffect`` is defined in ``app.schemas.effects`` (not
  ``app.db.models``). It inherits from ``Base``, so we import it here to
  ensure its table is created by ``Base.metadata.create_all``.

* ``AdventureMemory`` uses ``ARRAY(String)`` columns (tags,
  npcs_involved, locations, items_involved) and a ``Vector(1024)``
  embedding column. SQLite doesn't support ARRAY natively, but
  SQLAlchemy's ``ARRAY`` type from ``sqlalchemy.dialects.postgresql``
  won't auto-create on SQLite. We render the DDL manually, falling back
  to ``TEXT`` for unsupported column types, so table creation succeeds.

* The ``client`` fixture uses ``httpx.ASGITransport`` which does NOT
  execute ASGI lifespan events, avoiding Redis / ML-model startup.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# ── Ensure ActiveEffect table is included in Base.metadata ─────────────
import app.schemas.effects  # noqa: F401
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base, get_db
from app.db.models import User

# ---------------------------------------------------------------------------
# Engine & session factory (session-scoped — created once per test run)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create a single async engine for the whole test session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db_tables(db_engine):
    """Create all tables once, before any test runs.

    SQLite doesn't support PostgreSQL-specific types (ARRAY, Vector, JSONB).
    We compile the DDL and fall back gracefully for those columns:
    SQLAlchemy will render them as best it can or skip constraints.

    We register a ``before_create`` listener that rewrites JSONB columns
    to JSON so SQLite can handle them.
    """
    from sqlalchemy import JSON
    from sqlalchemy.dialects.postgresql import JSONB

    # Monkey-patch JSONB to compile as JSON on SQLite
    from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

    if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):

        def _visit_jsonb(self, type_, **kw):
            return "JSON"

        SQLiteTypeCompiler.visit_JSONB = _visit_jsonb

    if not hasattr(SQLiteTypeCompiler, "visit_ARRAY"):

        def _visit_array(self, type_, **kw):
            return "TEXT"

        SQLiteTypeCompiler.visit_ARRAY = _visit_array

    # Handle pgvector's Vector type
    try:
        from pgvector.sqlalchemy import Vector  # noqa: F401

        if not hasattr(SQLiteTypeCompiler, "visit_VECTOR"):

            def _visit_vector(self, type_, **kw):
                return "TEXT"

            SQLiteTypeCompiler.visit_VECTOR = _visit_vector
    except ImportError:
        pass

    # ── UUID bind-processor fix for SQLite ────────────────────────────
    # The PostgreSQL ``UUID(as_uuid=True)`` column type has a bind
    # processor that calls ``value.hex`` — expecting a ``uuid.UUID``
    # object.  Some service functions (e.g. ``get_user_by_id``) pass a
    # plain *string* extracted from the JWT ``sub`` claim.  On
    # PostgreSQL this is handled natively, but on SQLite the processor
    # crashes with ``AttributeError: 'str' object has no attribute
    # 'hex'``.  We monkey-patch the processor to coerce strings first.
    from sqlalchemy.sql import sqltypes as _sqltypes

    _orig_uuid_bp = _sqltypes.Uuid.bind_processor

    def _patched_uuid_bp(self, dialect):
        orig_process = _orig_uuid_bp(self, dialect)
        if orig_process is None:
            return None

        def _process(value):
            if value is not None and isinstance(value, str):
                value = uuid.UUID(value)
            return orig_process(value)

        return _process

    _sqltypes.Uuid.bind_processor = _patched_uuid_bp

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Per-test database session (function-scoped, rolled back after each test)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Yield an ``AsyncSession`` that is rolled back after the test."""
    async_session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_factory() as session:
        # Start a savepoint so we can roll back after the test
        # without affecting other tests.
        async with session.begin():
            yield session
            # Rollback any changes made during the test
            await session.rollback()


# ---------------------------------------------------------------------------
# HTTP test client (function-scoped, no lifespan)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """HTTPX async client wired to the FastAPI app.

    * Overrides ``get_db`` to use the test ``db_session``.
    * Uses ``ASGITransport`` which skips ASGI lifespan events, so Redis,
      AI providers, and ML models are never initialised.
    """
    from app.main import app

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Authenticated user helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def auth_user(db_session: AsyncSession):
    """Create a real ``User`` row and return ``(user, headers_dict)``.

    The headers dict contains a valid ``Authorization: Bearer <jwt>``
    header ready to pass to ``client.get(..., headers=headers)``.
    """
    user = User(
        id=uuid.uuid4(),
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        password_hash=get_password_hash("TestPassword123!"),
        is_guest=False,
        is_active=True,
        is_verified=False,
        preferred_language="en",
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


@pytest_asyncio.fixture(scope="function")
async def auth_headers(auth_user):
    """Convenience fixture — returns only the auth headers dict."""
    _user, headers = auth_user
    return headers


# ---------------------------------------------------------------------------
# Mock Redis
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def mock_redis(monkeypatch):
    """Patch ``session_service`` with an ``AsyncMock`` so tests never hit Redis."""
    mock_ss = AsyncMock()
    mock_ss.is_token_revoked = AsyncMock(return_value=False)
    mock_ss.get_session = AsyncMock(return_value=None)
    mock_ss.set_session = AsyncMock(return_value=True)
    mock_ss.connect = AsyncMock()
    mock_ss.disconnect = AsyncMock()

    monkeypatch.setattr("app.services.redis_service.session_service", mock_ss)
    return mock_ss
