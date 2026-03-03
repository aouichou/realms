"""Tests for app.services.save_service — save, load, auto_save, list, delete."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

from app.services.save_service import SaveService
from tests.factories import make_character, make_session, make_user

# ── helpers ───────────────────────────────────────────────────────────────


def _mock_redis():
    """Create a mock redis with get/setex/delete methods."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock(return_value=1)
    return redis


def _mock_session_service(redis=None):
    """Create a mock session_service with redis and get_session_state."""
    ss = AsyncMock()
    ss.redis = redis
    ss.get_session_state = AsyncMock(return_value={"turn": 5, "location": "Tavern"})
    return ss


# ── save_game ─────────────────────────────────────────────────────────────


async def test_save_game_happy_path(db_session):
    """Should save game data to Redis and return save dict."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    redis = _mock_redis()
    ss = _mock_session_service(redis)

    with patch("app.services.save_service.session_service", ss):
        result = await SaveService.save_game(db_session, session.id, save_name="MySave")

    assert result["save_name"] == "MySave"
    assert result["session_id"] == str(session.id)
    assert result["character_name"] == char.name
    redis.setex.assert_called_once()


async def test_save_game_auto_name(db_session):
    """Should auto-generate a save name when not provided."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    redis = _mock_redis()
    ss = _mock_session_service(redis)

    with patch("app.services.save_service.session_service", ss):
        result = await SaveService.save_game(db_session, session.id)

    assert result["save_name"].startswith("Auto-save")


async def test_save_game_session_not_found(db_session):
    """Should raise ValueError if session doesn't exist."""
    redis = _mock_redis()
    ss = _mock_session_service(redis)

    import pytest

    with patch("app.services.save_service.session_service", ss):
        with pytest.raises(ValueError, match="not found"):
            await SaveService.save_game(db_session, uuid.uuid4())


async def test_save_game_duplicate_name_no_overwrite(db_session):
    """Should raise ValueError for duplicate save name without overwrite."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    existing_save = json.dumps({"save_name": "MySave"})
    redis = _mock_redis()
    redis.get.return_value = existing_save
    ss = _mock_session_service(redis)

    import pytest

    with patch("app.services.save_service.session_service", ss):
        with pytest.raises(ValueError, match="already exists"):
            await SaveService.save_game(db_session, session.id, save_name="MySave", overwrite=False)


async def test_save_game_overwrite_allowed(db_session):
    """Should allow overwrite even with duplicate name."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    existing_save = json.dumps({"save_name": "MySave"})
    redis = _mock_redis()
    redis.get.return_value = existing_save
    ss = _mock_session_service(redis)

    with patch("app.services.save_service.session_service", ss):
        result = await SaveService.save_game(
            db_session, session.id, save_name="MySave", overwrite=True
        )

    assert result["save_name"] == "MySave"


async def test_save_game_no_redis(db_session):
    """Should still return save_data even without Redis (just won't persist to Redis)."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    ss = _mock_session_service(redis=None)

    with patch("app.services.save_service.session_service", ss):
        result = await SaveService.save_game(db_session, session.id, save_name="NoRedis")

    assert result["save_name"] == "NoRedis"


async def test_save_game_no_character(db_session):
    """Should handle missing character gracefully (name = 'Unknown')."""
    user = make_user()
    fake_char_id = uuid.uuid4()
    session = make_session(user=user, character_id=fake_char_id)
    db_session.add_all([user, session])
    await db_session.flush()

    redis = _mock_redis()
    ss = _mock_session_service(redis)

    with patch("app.services.save_service.session_service", ss):
        result = await SaveService.save_game(db_session, session.id, save_name="NoChar")

    assert result["character_name"] == "Unknown"


# ── load_game ─────────────────────────────────────────────────────────────


async def test_load_game_found(db_session):
    """Should return parsed save data from Redis."""
    save_data = {"save_name": "Test", "session_id": "abc"}
    redis = _mock_redis()
    redis.get.return_value = json.dumps(save_data)

    with patch("app.services.save_service.session_service") as mock_ss:
        mock_ss.redis = redis
        result = await SaveService.load_game(db_session, uuid.uuid4())

    assert result == save_data


async def test_load_game_not_found(db_session):
    """Should return None when no save exists."""
    redis = _mock_redis()
    redis.get.return_value = None

    with patch("app.services.save_service.session_service") as mock_ss:
        mock_ss.redis = redis
        result = await SaveService.load_game(db_session, uuid.uuid4())

    assert result is None


async def test_load_game_no_redis(db_session):
    """Should return None when Redis is not available."""
    with patch("app.services.save_service.session_service") as mock_ss:
        mock_ss.redis = None
        result = await SaveService.load_game(db_session, uuid.uuid4())

    assert result is None


# ── auto_save ─────────────────────────────────────────────────────────────


async def test_auto_save(db_session):
    """auto_save delegates to save_game with auto-generated name."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    redis = _mock_redis()
    ss = _mock_session_service(redis)

    with patch("app.services.save_service.session_service", ss):
        result = await SaveService.auto_save(db_session, session.id)

    assert result["save_name"].startswith("Auto-save")


# ── list_saves ────────────────────────────────────────────────────────────


async def test_list_saves_with_saves(db_session):
    """Should return saves sorted by timestamp (newest first)."""
    user = make_user()
    char = make_character(user=user)
    s1 = make_session(user=user, character=char)
    s2 = make_session(user=user, character=char)
    db_session.add_all([user, char, s1, s2])
    await db_session.flush()

    save1 = json.dumps({"save_name": "Old", "timestamp": "2025-01-01T00:00:00"})
    save2 = json.dumps({"save_name": "New", "timestamp": "2025-06-01T00:00:00"})

    redis = _mock_redis()

    async def _get_side_effect(key):
        if str(s1.id) in key:
            return save1
        if str(s2.id) in key:
            return save2
        return None

    redis.get = AsyncMock(side_effect=_get_side_effect)

    with patch("app.services.save_service.session_service") as mock_ss:
        mock_ss.redis = redis
        result = await SaveService.list_saves(db_session, user.id)

    assert len(result) == 2
    assert result[0]["save_name"] == "New"  # newest first


async def test_list_saves_no_saves(db_session):
    """Should return empty list when no saves exist."""
    user = make_user()
    db_session.add(user)
    await db_session.flush()

    redis = _mock_redis()
    with patch("app.services.save_service.session_service") as mock_ss:
        mock_ss.redis = redis
        result = await SaveService.list_saves(db_session, user.id)

    assert result == []


async def test_list_saves_no_redis(db_session):
    """Should return empty list when Redis is unavailable."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    with patch("app.services.save_service.session_service") as mock_ss:
        mock_ss.redis = None
        result = await SaveService.list_saves(db_session, user.id)

    assert result == []


# ── delete_save ───────────────────────────────────────────────────────────


async def test_delete_save_success(db_session):
    """Should return True when save is deleted."""
    redis = _mock_redis()
    redis.delete.return_value = 1

    with patch("app.services.save_service.session_service") as mock_ss:
        mock_ss.redis = redis
        result = await SaveService.delete_save(db_session, uuid.uuid4())

    assert result is True


async def test_delete_save_not_found(db_session):
    """Should return False when save doesn't exist."""
    redis = _mock_redis()
    redis.delete.return_value = 0

    with patch("app.services.save_service.session_service") as mock_ss:
        mock_ss.redis = redis
        result = await SaveService.delete_save(db_session, uuid.uuid4())

    assert result is False


async def test_delete_save_no_redis(db_session):
    """Should return False when Redis is unavailable."""
    with patch("app.services.save_service.session_service") as mock_ss:
        mock_ss.redis = None
        result = await SaveService.delete_save(db_session, uuid.uuid4())

    assert result is False
