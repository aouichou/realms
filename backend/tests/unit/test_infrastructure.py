"""Tests for provider_init, embedding_service, adventure schemas, random_pool, character_service."""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# Adventure Schema
# ============================================================================


class TestAdventureSchemas:
    def test_scene_structure(self):
        from app.schemas.adventure import SceneStructure

        scene = SceneStructure(
            scene_number=1,
            title="The Dark Cave",
            description="A foreboding entrance",
        )
        assert scene.scene_number == 1
        assert scene.encounters == []
        assert scene.npcs == []
        assert scene.loot == []

    def test_scene_structure_with_data(self):
        from app.schemas.adventure import SceneStructure

        scene = SceneStructure(
            scene_number=2,
            title="Battle",
            description="Combat begins",
            encounters=["goblin_ambush"],
            npcs=[{"name": "Goblin Chief"}],
            loot=[{"name": "Gold", "amount": 50}],
        )
        assert len(scene.encounters) == 1
        assert scene.npcs[0]["name"] == "Goblin Chief"

    def test_adventure_create(self):
        from app.schemas.adventure import AdventureCreate

        ac = AdventureCreate(
            character_id=uuid.uuid4(),
            setting="haunted_castle",
            goal="rescue_mission",
            tone="epic_heroic",
        )
        assert ac.setting == "haunted_castle"

    def test_adventure_response(self):
        from datetime import datetime

        from app.schemas.adventure import AdventureResponse

        ar = AdventureResponse(
            id=uuid.uuid4(),
            character_id=uuid.uuid4(),
            setting="forest",
            goal="explore",
            tone="mysterious",
            title="Into the Woods",
            description="A mystical journey",
            scenes=[],
            is_completed=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert ar.title == "Into the Woods"
        assert ar.is_completed is False

    def test_adventure_update(self):
        from app.schemas.adventure import AdventureUpdate

        au = AdventureUpdate()
        assert au.title is None
        assert au.is_completed is None

        au2 = AdventureUpdate(title="New Title", is_completed=True)
        assert au2.title == "New Title"
        assert au2.is_completed is True


# ============================================================================
# EmbeddingService
# ============================================================================


class TestEmbeddingService:
    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"})
    @patch("app.services.embedding_service.Mistral")
    def test_init(self, mock_mistral_cls):
        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService()
        assert svc.model == "mistral-embed"
        mock_mistral_cls.assert_called_once_with(api_key="test-key")

    def test_init_no_api_key(self):
        from app.services.embedding_service import EmbeddingService

        with patch.dict(os.environ, {}, clear=True):
            # Remove MISTRAL_API_KEY if set
            os.environ.pop("MISTRAL_API_KEY", None)
            with pytest.raises(ValueError, match="MISTRAL_API_KEY"):
                EmbeddingService()

    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"})
    @patch("app.services.embedding_service.Mistral")
    async def test_generate_embedding_success(self, mock_mistral_cls):
        from app.services.embedding_service import EmbeddingService

        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1024
        mock_response = MagicMock()
        mock_response.data = [mock_embedding]

        mock_client.embeddings.create = MagicMock(return_value=mock_response)
        mock_mistral_cls.return_value = mock_client

        svc = EmbeddingService()

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_response):
            result = await svc.generate_embedding("test text")
            assert result == [0.1] * 1024

    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"})
    @patch("app.services.embedding_service.Mistral")
    async def test_generate_embedding_failure(self, mock_mistral_cls):
        from app.services.embedding_service import EmbeddingService

        mock_client = MagicMock()
        mock_mistral_cls.return_value = mock_client

        svc = EmbeddingService()

        with patch(
            "asyncio.to_thread", new_callable=AsyncMock, side_effect=RuntimeError("API down")
        ):
            result = await svc.generate_embedding("test text")
            assert result is None

    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"})
    @patch("app.services.embedding_service.Mistral")
    async def test_generate_embeddings_batch_success(self, mock_mistral_cls):
        from app.services.embedding_service import EmbeddingService

        mock_client = MagicMock()
        mock_e1 = MagicMock()
        mock_e1.embedding = [0.1] * 1024
        mock_e2 = MagicMock()
        mock_e2.embedding = [0.2] * 1024
        mock_response = MagicMock()
        mock_response.data = [mock_e1, mock_e2]

        mock_mistral_cls.return_value = mock_client

        svc = EmbeddingService()

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_response):
            result = await svc.generate_embeddings_batch(["text1", "text2"])
            assert len(result) == 2
            assert result[0] == [0.1] * 1024

    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"})
    @patch("app.services.embedding_service.Mistral")
    async def test_generate_embeddings_batch_failure(self, mock_mistral_cls):
        from app.services.embedding_service import EmbeddingService

        mock_client = MagicMock()
        mock_mistral_cls.return_value = mock_client

        svc = EmbeddingService()

        with patch("asyncio.to_thread", new_callable=AsyncMock, side_effect=RuntimeError("fail")):
            result = await svc.generate_embeddings_batch(["a", "b", "c"])
            assert result == [None, None, None]


# ============================================================================
# TrueRandomPool
# ============================================================================


class TestTrueRandomPool:
    @patch("app.services.random_pool.settings")
    async def test_disabled_uses_pseudorandom(self, mock_settings):
        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = False
        mock_settings.random_pool_size = 100
        mock_settings.random_pool_min_threshold = 10

        pool = TrueRandomPool()
        result = await pool.get_random_int(1, 20)
        assert 1 <= result <= 20

    @patch("app.services.random_pool.settings")
    async def test_enabled_uses_pool(self, mock_settings):
        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = True
        mock_settings.random_pool_size = 100
        mock_settings.random_pool_min_threshold = 10

        pool = TrueRandomPool()
        pool.pool = [500000, 123456, 789012]  # Pre-fill pool

        result = await pool.get_random_int(1, 20)
        assert 1 <= result <= 20
        assert len(pool.pool) == 2  # One consumed

    @patch("app.services.random_pool.settings")
    async def test_empty_pool_fallback(self, mock_settings):
        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = True
        mock_settings.random_pool_size = 100
        mock_settings.random_pool_min_threshold = 0  # Don't trigger refill
        mock_settings.random_org_url = "https://www.random.org/integers/"
        mock_settings.random_pool_timeout = 5

        pool = TrueRandomPool()
        pool.pool = []  # Empty pool

        result = await pool.get_random_int(1, 6)
        assert 1 <= result <= 6

    @patch("app.services.random_pool.settings")
    async def test_get_pool_status(self, mock_settings):
        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = True
        mock_settings.random_pool_size = 100
        mock_settings.random_pool_min_threshold = 10

        pool = TrueRandomPool()
        pool.pool = [1, 2, 3]
        status = await pool.get_pool_status()
        assert status["enabled"] is True
        assert status["pool_size"] == 3
        assert status["min_threshold"] == 10

    @patch("app.services.random_pool.httpx.AsyncClient")
    @patch("app.services.random_pool.settings")
    async def test_refill_pool_success(self, mock_settings, mock_client_cls):
        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = True
        mock_settings.random_pool_size = 5
        mock_settings.random_pool_min_threshold = 10
        mock_settings.random_org_url = "https://www.random.org/integers/"
        mock_settings.random_pool_timeout = 5

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "100\n200\n300\n400\n500\n"
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        pool = TrueRandomPool()
        pool.pool = []
        await pool._refill_pool()
        assert len(pool.pool) == 5
        assert pool.api_available is True

    @patch("app.services.random_pool.httpx.AsyncClient")
    @patch("app.services.random_pool.settings")
    async def test_refill_pool_503(self, mock_settings, mock_client_cls):
        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = True
        mock_settings.random_pool_size = 5
        mock_settings.random_pool_min_threshold = 10
        mock_settings.random_org_url = "https://www.random.org/integers/"
        mock_settings.random_pool_timeout = 5

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        pool = TrueRandomPool()
        await pool._refill_pool()
        assert pool.api_available is False

    @patch("app.services.random_pool.httpx.AsyncClient")
    @patch("app.services.random_pool.settings")
    async def test_refill_pool_unexpected_status(self, mock_settings, mock_client_cls):
        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = True
        mock_settings.random_pool_size = 5
        mock_settings.random_pool_min_threshold = 10
        mock_settings.random_org_url = "https://www.random.org/integers/"
        mock_settings.random_pool_timeout = 5

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        pool = TrueRandomPool()
        await pool._refill_pool()
        assert pool.api_available is False

    @patch("app.services.random_pool.httpx.AsyncClient")
    @patch("app.services.random_pool.settings")
    async def test_refill_pool_timeout(self, mock_settings, mock_client_cls):
        import httpx

        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = True
        mock_settings.random_pool_size = 5
        mock_settings.random_pool_min_threshold = 10
        mock_settings.random_org_url = "https://www.random.org/integers/"
        mock_settings.random_pool_timeout = 5

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client_cls.return_value = mock_client

        pool = TrueRandomPool()
        await pool._refill_pool()
        assert pool.api_available is False

    @patch("app.services.random_pool.httpx.AsyncClient")
    @patch("app.services.random_pool.settings")
    async def test_refill_pool_generic_error(self, mock_settings, mock_client_cls):
        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = True
        mock_settings.random_pool_size = 5
        mock_settings.random_pool_min_threshold = 10
        mock_settings.random_org_url = "https://www.random.org/integers/"
        mock_settings.random_pool_timeout = 5

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=RuntimeError("network fail"))
        mock_client_cls.return_value = mock_client

        pool = TrueRandomPool()
        await pool._refill_pool()
        assert pool.api_available is False

    @patch("app.services.random_pool.settings")
    async def test_refill_skips_if_already_refilling(self, mock_settings):
        from app.services.random_pool import TrueRandomPool

        mock_settings.use_true_randomness = True
        mock_settings.random_pool_size = 100
        mock_settings.random_pool_min_threshold = 10

        pool = TrueRandomPool()
        pool.is_refilling = True
        old_pool_size = len(pool.pool)
        await pool._refill_pool()
        assert len(pool.pool) == old_pool_size  # unchanged


# ============================================================================
# Provider Init
# ============================================================================


class TestProviderInit:
    @patch("app.services.provider_init.create_provider", new_callable=AsyncMock)
    @patch("app.services.provider_init.provider_selector")
    @patch("app.services.provider_init.settings")
    async def test_initialize_no_providers(self, mock_settings, mock_sel, mock_create):
        from app.services.provider_init import initialize_providers

        mock_settings.mistral_enabled = False
        mock_settings.ai_providers_config = {
            "groq": {"enabled": False, "priority": 1, "model": "m", "api_key": "k"},
        }
        count = await initialize_providers()
        assert count == 0

    @patch("app.services.provider_init.create_provider", new_callable=AsyncMock)
    @patch("app.services.provider_init.provider_selector")
    @patch("app.services.provider_init.settings")
    async def test_initialize_one_provider(self, mock_settings, mock_sel, mock_create):
        from app.services.provider_init import initialize_providers

        mock_settings.mistral_enabled = True
        mock_settings.ai_providers_config = {
            "groq": {"enabled": True, "priority": 1, "model": "llama", "api_key": "key"},
        }
        mock_provider = MagicMock()
        mock_create.return_value = mock_provider

        count = await initialize_providers()
        assert count == 1
        mock_sel.register_provider.assert_called_once_with(mock_provider)

    @patch("app.services.provider_init.create_provider", new_callable=AsyncMock)
    @patch("app.services.provider_init.provider_selector")
    @patch("app.services.provider_init.settings")
    async def test_initialize_provider_failure(self, mock_settings, mock_sel, mock_create):
        from app.services.provider_init import initialize_providers

        mock_settings.mistral_enabled = False
        mock_settings.ai_providers_config = {
            "groq": {"enabled": True, "priority": 1, "model": "llama", "api_key": "key"},
        }
        mock_create.side_effect = RuntimeError("init failed")

        count = await initialize_providers()
        assert count == 0


class TestCreateProvider:
    @patch("app.services.provider_init.QwenProvider")
    async def test_create_qwen(self, mock_cls):
        from app.services.provider_init import create_provider

        mock_cls.return_value = MagicMock()
        result = await create_provider("qwen", {"api_key": "k", "model": "m", "priority": 1})
        assert result is not None
        mock_cls.assert_called_once()

    @patch("app.services.provider_init.MistralProvider")
    async def test_create_mistral(self, mock_cls):
        from app.services.provider_init import create_provider

        mock_cls.return_value = MagicMock()
        result = await create_provider("mistral", {"api_key": "k", "model": "m", "priority": 1})
        assert result is not None

    @patch("app.services.provider_init.GroqProvider")
    async def test_create_groq(self, mock_cls):
        from app.services.provider_init import create_provider

        mock_cls.return_value = MagicMock()
        result = await create_provider("groq", {"api_key": "k", "model": "m", "priority": 1})
        assert result is not None

    @patch("app.services.provider_init.CerebrasProvider")
    async def test_create_cerebras(self, mock_cls):
        from app.services.provider_init import create_provider

        mock_cls.return_value = MagicMock()
        result = await create_provider("cerebras", {"api_key": "k", "model": "m", "priority": 1})
        assert result is not None

    @patch("app.services.provider_init.TogetherProvider")
    async def test_create_together(self, mock_cls):
        from app.services.provider_init import create_provider

        mock_cls.return_value = MagicMock()
        result = await create_provider("together", {"api_key": "k", "model": "m", "priority": 1})
        assert result is not None

    @patch("app.services.provider_init.SambanovaProvider")
    async def test_create_sambanova(self, mock_cls):
        from app.services.provider_init import create_provider

        mock_cls.return_value = MagicMock()
        result = await create_provider("sambanova", {"api_key": "k", "model": "m", "priority": 1})
        assert result is not None

    async def test_create_unknown(self):
        from app.services.provider_init import create_provider

        result = await create_provider(
            "unknown_provider", {"api_key": "k", "model": "m", "priority": 1}
        )
        assert result is None

    async def test_create_error(self):
        from app.services.provider_init import create_provider

        with patch("app.services.provider_init.QwenProvider", side_effect=RuntimeError("boom")):
            result = await create_provider("qwen", {"api_key": "k", "model": "m", "priority": 1})
            assert result is None


class TestGetProviderStatus:
    @patch("app.services.provider_init.provider_selector")
    async def test_get_status(self, mock_sel):
        from app.services.provider_init import get_provider_status

        mock_p = MagicMock()
        mock_p.name = "groq"
        mock_p.priority = 1
        mock_p._status.value = "available"
        mock_p.get_last_error.return_value = None
        mock_sel.providers = [mock_p]
        mock_sel.get_stats.return_value = {"groq": {"requests": 5}}
        mock_sel.get_current_provider.return_value = mock_p

        status = await get_provider_status()
        assert status["current_provider"] == "groq"
        assert len(status["providers"]) == 1

    @patch("app.services.provider_init.provider_selector")
    async def test_get_status_no_current(self, mock_sel):
        from app.services.provider_init import get_provider_status

        mock_sel.providers = []
        mock_sel.get_stats.return_value = {}
        mock_sel.get_current_provider.return_value = None

        status = await get_provider_status()
        assert status["current_provider"] is None


# ============================================================================
# CharacterService — uncovered lines
# ============================================================================


class TestCharacterServiceCalculations:
    def test_calculate_hp_max_level_1_fighter(self):
        from app.services.character_service import CharacterService

        hp = CharacterService.calculate_hp_max("Fighter", 14, 1)
        # Fighter: d10, CON 14 → mod +2, level 1 → 10 + 2 = 12
        assert hp == 12

    def test_calculate_hp_max_level_5_wizard(self):
        from app.services.character_service import CharacterService

        hp = CharacterService.calculate_hp_max("Wizard", 12, 5)
        # Wizard: d6, CON 12 → mod +1, level 1 = 6+1=7, levels 2-5: 4*(4+1) = 20, total = 27
        assert hp == 7 + 4 * (4 + 1)

    def test_calculate_hp_max_unknown_class(self):
        from app.services.character_service import CharacterService

        hp = CharacterService.calculate_hp_max("Unknown", 10, 1)
        # Falls back to d8, CON mod 0
        assert hp == 8

    def test_calculate_ability_modifier(self):
        from app.services.character_service import CharacterService

        assert CharacterService.calculate_ability_modifier(10) == 0
        assert CharacterService.calculate_ability_modifier(8) == -1
        assert CharacterService.calculate_ability_modifier(16) == 3
        assert CharacterService.calculate_ability_modifier(1) == -5
        assert CharacterService.calculate_ability_modifier(20) == 5

    def test_calculate_proficiency_bonus(self):
        from app.services.character_service import CharacterService

        assert CharacterService.calculate_proficiency_bonus(1) == 2
        assert CharacterService.calculate_proficiency_bonus(4) == 2
        assert CharacterService.calculate_proficiency_bonus(5) == 3
        assert CharacterService.calculate_proficiency_bonus(9) == 4
        assert CharacterService.calculate_proficiency_bonus(13) == 5
        assert CharacterService.calculate_proficiency_bonus(17) == 6
        assert CharacterService.calculate_proficiency_bonus(20) == 6

    async def test_get_character_not_found(self, db_session):
        from app.services.character_service import CharacterService

        result = await CharacterService.get_character(db_session, uuid.uuid4())
        assert result is None

    async def test_update_character_not_found(self, db_session):
        from app.schemas.character import CharacterUpdate
        from app.services.character_service import CharacterService

        result = await CharacterService.update_character(
            db_session, uuid.uuid4(), CharacterUpdate(name="X")
        )
        assert result is None

    async def test_delete_character_not_found(self, db_session):
        from app.services.character_service import CharacterService

        result = await CharacterService.delete_character(db_session, uuid.uuid4())
        assert result is False

    async def test_calculate_character_stats_not_found(self, db_session):
        from app.services.character_service import CharacterService

        result = await CharacterService.calculate_character_stats(db_session, uuid.uuid4())
        assert result is None

    async def test_calculate_character_stats_basic(self, db_session):
        """Create a character and verify stats calculation."""
        from app.services.character_service import CharacterService
        from tests.factories import make_character, make_user

        user = make_user()
        db_session.add(user)
        await db_session.flush()

        char = make_character(user=user)
        db_session.add(char)
        await db_session.flush()

        stats = await CharacterService.calculate_character_stats(db_session, char.id)
        assert stats is not None
        assert "strength" in stats
        assert "armor_class" in stats
        assert "proficiency_bonus" in stats
        assert "skills" in stats
        assert "saving_throws" in stats
        assert stats["proficiency_bonus"] == 2  # level 1

    async def test_get_user_characters(self, db_session):
        from app.services.character_service import CharacterService
        from tests.factories import make_character, make_user

        user = make_user()
        db_session.add(user)
        await db_session.flush()

        c1 = make_character(user=user, name="Char1")
        c2 = make_character(user=user, name="Char2")
        db_session.add_all([c1, c2])
        await db_session.flush()

        chars, total = await CharacterService.get_user_characters(db_session, user.id)
        assert total == 2
        assert len(chars) == 2

    async def test_delete_character_soft_delete(self, db_session):
        from app.services.character_service import CharacterService
        from tests.factories import make_character, make_user

        user = make_user()
        db_session.add(user)
        await db_session.flush()

        char = make_character(user=user)
        db_session.add(char)
        await db_session.flush()

        # Patch commit so session stays usable inside test transaction
        db_session.commit = db_session.flush
        result = await CharacterService.delete_character(db_session, char.id)
        assert result is True

        # After soft delete the character should have deleted_at set
        await db_session.refresh(char)
        assert char.deleted_at is not None
