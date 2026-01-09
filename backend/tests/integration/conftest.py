"""
Integration Test Fixtures
Provides shared fixtures for integration testing
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.db.base import Base, get_db
from app.db.models import Character, User
from app.main import app

# Test database URL (use separate test database)
TEST_DATABASE_URL = (
    "postgresql+asyncpg://realms_user:realms_password@localhost:5432/mistral_realms_test"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    # Create test engine
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def auth_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database dependency override"""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$test_hashed_password",
        is_guest=False,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_character(test_db: AsyncSession, test_user: User) -> Character:
    """Create test character"""
    character = Character(
        user_id=test_user.id,
        name="Test Character",
        race="human",
        character_class="fighter",
        level=1,
        strength=16,
        dexterity=14,
        constitution=15,
        intelligence=10,
        wisdom=12,
        charisma=8,
        max_hp=15,
        current_hp=15,
    )
    test_db.add(character)
    await test_db.commit()
    await test_db.refresh(character)
    return character
