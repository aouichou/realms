"""Tests for quest endpoints (/api/v1/quests).

These endpoints use sync SQLAlchemy Session (db.query pattern).
A dedicated sync engine/session is used instead of the async db_session.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.db.models import CharacterQuest, QuestState
from tests.factories import make_character, make_quest, make_quest_objective, make_user

# ---------------------------------------------------------------------------
# Sync engine/session fixtures for sync ORM endpoints
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _sync_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sync_db(_sync_engine):
    connection = _sync_engine.connect()
    transaction = connection.begin()
    SyncSession = sessionmaker(bind=connection, expire_on_commit=False)
    session = SyncSession()

    original_commit = session.commit
    session.commit = session.flush
    yield session
    session.commit = original_commit
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _strip_middleware():
    from app.main import app
    from app.middleware.csrf import CSRFProtectionMiddleware
    from app.middleware.https import HTTPSEnforcementMiddleware
    from app.middleware.rate_limit import RateLimitMiddleware

    original = app.user_middleware[:]
    app.user_middleware = [
        m
        for m in app.user_middleware
        if m.cls not in (CSRFProtectionMiddleware, RateLimitMiddleware, HTTPSEnforcementMiddleware)
    ]
    app.middleware_stack = app.build_middleware_stack()
    yield
    app.user_middleware = original
    app.middleware_stack = app.build_middleware_stack()


@pytest_asyncio.fixture
async def sync_client(sync_db):
    from app.db.models import User
    from app.main import app
    from app.middleware.auth import get_current_active_user

    def _get_sync_db():
        yield sync_db

    auth_user = User(
        id=uuid.uuid4(),
        username=f"syncuser_{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        is_guest=False,
        is_active=True,
    )
    sync_db.add(auth_user)
    sync_db.flush()

    async def _mock_auth():
        return auth_user

    app.dependency_overrides[get_db] = _get_sync_db
    app.dependency_overrides[get_current_active_user] = _mock_auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


BASE = "/api/v1/quests"


# ===========================================================================
# POST /api/v1/quests — create_quest
# ===========================================================================


async def test_create_quest(sync_client, sync_db):
    body = {
        "title": "Find the Dragon",
        "description": "Locate the ancient dragon in the mountain cave.",
        "rewards": {"xp": 500, "gold": 100, "items": []},
        "objectives": [
            {"description": "Talk to the village elder", "order": 0},
            {"description": "Travel to the mountain", "order": 1},
        ],
    }
    resp = await sync_client.post(BASE, json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Find the Dragon"
    assert data["state"] == "not_started"
    assert len(data["objectives"]) == 2
    assert data["progress"] == "0/2 objectives"


async def test_create_quest_missing_objectives(sync_client):
    body = {
        "title": "No Objectives",
        "description": "Quest without objectives",
        "rewards": {"xp": 0, "gold": 0, "items": []},
        "objectives": [],
    }
    resp = await sync_client.post(BASE, json=body)
    assert resp.status_code == 422


# ===========================================================================
# POST /api/v1/quests/{quest_id}/accept
# ===========================================================================


async def test_accept_quest(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    quest = make_quest()
    obj = make_quest_objective(quest=quest)
    sync_db.add_all([user, char, quest, obj])
    sync_db.flush()

    resp = await sync_client.post(f"{BASE}/{quest.id}/accept", json={"character_id": str(char.id)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Quest accepted"


async def test_accept_quest_not_found(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    sync_db.add_all([user, char])
    sync_db.flush()

    resp = await sync_client.post(
        f"{BASE}/{uuid.uuid4()}/accept", json={"character_id": str(char.id)}
    )
    assert resp.status_code == 404


async def test_accept_quest_character_not_found(sync_client, sync_db):
    quest = make_quest()
    obj = make_quest_objective(quest=quest)
    sync_db.add_all([quest, obj])
    sync_db.flush()

    resp = await sync_client.post(
        f"{BASE}/{quest.id}/accept", json={"character_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


async def test_accept_quest_already_accepted(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    quest = make_quest()
    obj = make_quest_objective(quest=quest)
    sync_db.add_all([user, char, quest, obj])
    sync_db.flush()

    cq = CharacterQuest(character_id=char.id, quest_id=quest.id)
    sync_db.add(cq)
    sync_db.flush()

    resp = await sync_client.post(f"{BASE}/{quest.id}/accept", json={"character_id": str(char.id)})
    assert resp.status_code == 400
    assert "already accepted" in resp.json()["detail"].lower()


# ===========================================================================
# GET /api/v1/quests/character/{character_id}
# ===========================================================================


async def test_get_character_quests(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    quest = make_quest()
    obj = make_quest_objective(quest=quest)
    sync_db.add_all([user, char, quest, obj])
    sync_db.flush()

    cq = CharacterQuest(character_id=char.id, quest_id=quest.id)
    sync_db.add(cq)
    sync_db.flush()

    resp = await sync_client.get(f"{BASE}/character/{char.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == quest.title


async def test_get_character_quests_empty(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    sync_db.add_all([user, char])
    sync_db.flush()

    resp = await sync_client.get(f"{BASE}/character/{char.id}")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_character_quests_not_found(sync_client, sync_db):
    resp = await sync_client.get(f"{BASE}/character/{uuid.uuid4()}")
    assert resp.status_code == 404


# ===========================================================================
# PATCH /api/v1/quests/{quest_id}/objectives/{objective_id}/complete
# ===========================================================================


async def test_complete_objective(sync_client, sync_db):
    quest = make_quest()
    obj = make_quest_objective(quest=quest)
    sync_db.add_all([quest, obj])
    sync_db.flush()

    resp = await sync_client.patch(f"{BASE}/{quest.id}/objectives/{obj.id}/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Objective completed"
    assert data["all_objectives_complete"] is True


async def test_complete_objective_not_all_done(sync_client, sync_db):
    quest = make_quest()
    obj1 = make_quest_objective(quest=quest, order=0)
    obj2 = make_quest_objective(quest=quest, order=1)
    sync_db.add_all([quest, obj1, obj2])
    sync_db.flush()

    resp = await sync_client.patch(f"{BASE}/{quest.id}/objectives/{obj1.id}/complete")
    assert resp.status_code == 200
    data = resp.json()
    assert data["all_objectives_complete"] is False


async def test_complete_objective_already_completed(sync_client, sync_db):
    quest = make_quest()
    obj = make_quest_objective(quest=quest, is_completed=True)
    sync_db.add_all([quest, obj])
    sync_db.flush()

    resp = await sync_client.patch(f"{BASE}/{quest.id}/objectives/{obj.id}/complete")
    assert resp.status_code == 400
    assert "already completed" in resp.json()["detail"].lower()


async def test_complete_objective_quest_not_found(sync_client, sync_db):
    resp = await sync_client.patch(f"{BASE}/{uuid.uuid4()}/objectives/{uuid.uuid4()}/complete")
    assert resp.status_code == 404


async def test_complete_objective_not_found(sync_client, sync_db):
    quest = make_quest()
    sync_db.add(quest)
    sync_db.flush()

    resp = await sync_client.patch(f"{BASE}/{quest.id}/objectives/{uuid.uuid4()}/complete")
    assert resp.status_code == 404


# ===========================================================================
# POST /api/v1/quests/{quest_id}/complete
# ===========================================================================


async def test_complete_quest(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user, experience_points=0, gold=0)
    quest = make_quest(rewards={"xp": 100, "gold": 50, "items": ["Magic Ring"]})
    sync_db.add_all([user, char, quest])
    sync_db.flush()

    cq = CharacterQuest(character_id=char.id, quest_id=quest.id)
    sync_db.add(cq)
    sync_db.flush()

    resp = await sync_client.post(
        f"{BASE}/{quest.id}/complete", params={"character_id": str(char.id)}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Quest completed!"
    assert "100 XP" in data["rewards_granted"]
    assert "50 gold" in data["rewards_granted"]
    assert "Magic Ring" in data["rewards_granted"]


async def test_complete_quest_not_found(sync_client, sync_db):
    resp = await sync_client.post(
        f"{BASE}/{uuid.uuid4()}/complete", params={"character_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


async def test_complete_quest_already_completed(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    quest = make_quest(state=QuestState.COMPLETED)
    sync_db.add_all([user, char, quest])
    sync_db.flush()

    cq = CharacterQuest(character_id=char.id, quest_id=quest.id)
    sync_db.add(cq)
    sync_db.flush()

    resp = await sync_client.post(
        f"{BASE}/{quest.id}/complete", params={"character_id": str(char.id)}
    )
    assert resp.status_code == 400


# ===========================================================================
# POST /api/v1/quests/{quest_id}/fail
# ===========================================================================


async def test_fail_quest(sync_client, sync_db):
    quest = make_quest(state=QuestState.IN_PROGRESS)
    sync_db.add(quest)
    sync_db.flush()

    resp = await sync_client.post(f"{BASE}/{quest.id}/fail")
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Quest failed"


async def test_fail_quest_not_found(sync_client, sync_db):
    resp = await sync_client.post(f"{BASE}/{uuid.uuid4()}/fail")
    assert resp.status_code == 404


async def test_fail_quest_already_completed(sync_client, sync_db):
    quest = make_quest(state=QuestState.COMPLETED)
    sync_db.add(quest)
    sync_db.flush()

    resp = await sync_client.post(f"{BASE}/{quest.id}/fail")
    assert resp.status_code == 400
