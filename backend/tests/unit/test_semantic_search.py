"""Tests for SemanticSearchService — semantic_search_service.py"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

from app.services.semantic_search_service import SemanticSearchService, get_semantic_search_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service() -> SemanticSearchService:
    """Create a SemanticSearchService with mocked embedding model."""
    with patch.object(SemanticSearchService, "_initialize_model"):
        svc = SemanticSearchService()
    svc.embedding_service = MagicMock()
    svc.embedding_service._model = MagicMock()
    return svc


def _fake_embedding(dim: int = 384) -> np.ndarray:
    """Return a normalised random embedding."""
    vec = np.random.randn(dim).astype(np.float32)
    return vec / np.linalg.norm(vec)


# ---------------------------------------------------------------------------
# _generate_embedding
# ---------------------------------------------------------------------------


class TestGenerateEmbedding:
    def test_returns_none_when_no_service(self):
        with patch.object(SemanticSearchService, "_initialize_model"):
            svc = SemanticSearchService()
        svc.embedding_service = None
        assert svc._generate_embedding("hello") is None

    def test_returns_none_when_no_model(self):
        with patch.object(SemanticSearchService, "_initialize_model"):
            svc = SemanticSearchService()
        svc.embedding_service = MagicMock()
        svc.embedding_service._model = None
        assert svc._generate_embedding("hello") is None

    def test_returns_embedding(self):
        svc = _make_service()
        fake = _fake_embedding()
        # model.encode returns a tensor-like that has .cpu().numpy()
        tensor_mock = MagicMock()
        tensor_mock.cpu.return_value.numpy.return_value = fake
        svc.embedding_service._model.encode.return_value = tensor_mock

        result = svc._generate_embedding("hello")
        assert result is not None
        np.testing.assert_array_equal(result, fake)

    def test_exception_returns_none(self):
        svc = _make_service()
        svc.embedding_service._model.encode.side_effect = RuntimeError("boom")
        assert svc._generate_embedding("hello") is None


# ---------------------------------------------------------------------------
# _calculate_similarity
# ---------------------------------------------------------------------------


class TestCalculateSimilarity:
    def test_similarity_of_identical(self):
        svc = _make_service()
        emb = _fake_embedding()
        tensor_mock = MagicMock()
        tensor_mock.cpu.return_value.numpy.return_value = emb
        svc.embedding_service._model.encode.return_value = tensor_mock

        sim = svc._calculate_similarity(emb, "same text")
        # dot product of normalised vector with itself ≈ 1.0
        assert sim > 0.99

    def test_returns_zero_when_embedding_fails(self):
        svc = _make_service()
        svc.embedding_service._model.encode.side_effect = RuntimeError("fail")
        sim = svc._calculate_similarity(_fake_embedding(), "text")
        assert sim == 0.0


# ---------------------------------------------------------------------------
# search_items
# ---------------------------------------------------------------------------


class TestSearchItems:
    async def test_empty_on_no_embedding(self):
        svc = _make_service()
        svc.embedding_service = None  # Force _generate_embedding to return None
        db = AsyncMock()
        result = await svc.search_items("healing potion", db)
        assert result == []

    async def test_returns_scored_items(self):
        svc = _make_service()
        emb = _fake_embedding()
        tensor_mock = MagicMock()
        tensor_mock.cpu.return_value.numpy.return_value = emb
        svc.embedding_service._model.encode.return_value = tensor_mock

        # Mock DB result
        item = MagicMock()
        item.id = 1
        item.name = "Potion of Healing"
        item.category = "potion"
        item.item_type = "potion_of_healing"
        item.rarity = "common"
        item.description = "Heals 2d4+2 HP"
        item.damage_type = None
        item.cost_gp = 50

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [item]
        db.execute.return_value = result_mock

        results = await svc.search_items("healing potion", db, similarity_threshold=0.0)
        assert len(results) >= 1
        assert results[0]["name"] == "Potion of Healing"
        assert "similarity" in results[0]

    async def test_filters_below_threshold(self):
        svc = _make_service()
        emb = _fake_embedding()
        tensor_mock = MagicMock()
        tensor_mock.cpu.return_value.numpy.return_value = emb
        svc.embedding_service._model.encode.return_value = tensor_mock

        # Make similarity always return low value by using orthogonal vectors
        def _low_sim_embed(text, **kwargs):
            # Return a very different vector each time
            v = _fake_embedding()
            v[0] = -emb[0]  # Make somewhat orthogonal
            mock = MagicMock()
            mock.cpu.return_value.numpy.return_value = v * 0.01
            return mock

        svc.embedding_service._model.encode.side_effect = _low_sim_embed

        item = MagicMock()
        item.id = 1
        item.name = "X"
        item.category = "weapon"
        item.item_type = "sword"
        item.rarity = "common"
        item.description = "A sword"
        item.damage_type = "slashing"
        item.cost_gp = 10

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [item]
        db.execute.return_value = result_mock

        # Need the first call (for query) to return emb, subsequent for items
        call_count = [0]
        original_gen = svc._generate_embedding

        def _gen(text):
            call_count[0] += 1
            if call_count[0] == 1:
                return emb
            return emb * 0.0  # zero vector → zero similarity

        svc._generate_embedding = _gen

        results = await svc.search_items("healing", db, similarity_threshold=0.5)
        assert len(results) == 0


# ---------------------------------------------------------------------------
# search_monsters
# ---------------------------------------------------------------------------


class TestSearchMonsters:
    async def test_empty_on_no_embedding(self):
        svc = _make_service()
        svc.embedding_service = None
        db = AsyncMock()
        result = await svc.search_monsters("undead", db)
        assert result == []

    async def test_returns_scored_creatures(self):
        svc = _make_service()
        emb = _fake_embedding()
        tensor_mock = MagicMock()
        tensor_mock.cpu.return_value.numpy.return_value = emb
        svc.embedding_service._model.encode.return_value = tensor_mock

        creature = MagicMock()
        creature.id = 1
        creature.name = "Zombie"
        creature.creature_type = "undead"
        creature.size = "Medium"
        creature.alignment = "neutral evil"
        creature.traits = "Undead Fortitude."
        creature.actions = "Slam."
        creature.cr = "1/4"
        creature.ac = 8
        creature.hp = 22

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [creature]
        db.execute.return_value = result_mock

        results = await svc.search_monsters("undead", db, similarity_threshold=0.0)
        assert len(results) >= 1
        assert results[0]["name"] == "Zombie"


# ---------------------------------------------------------------------------
# search_spells
# ---------------------------------------------------------------------------


class TestSearchSpells:
    async def test_empty_on_no_embedding(self):
        svc = _make_service()
        svc.embedding_service = None
        db = AsyncMock()
        result = await svc.search_spells("fire", db)
        assert result == []

    async def test_returns_scored_spells(self):
        svc = _make_service()
        emb = _fake_embedding()
        tensor_mock = MagicMock()
        tensor_mock.cpu.return_value.numpy.return_value = emb
        svc.embedding_service._model.encode.return_value = tensor_mock

        spell = MagicMock()
        spell.id = "abc-123"
        spell.name = "Fireball"
        spell.level = 3
        spell.school = "evocation"
        spell.casting_time = "1 action"
        spell.range = "150 feet"
        spell.duration = "Instantaneous"
        spell.description = "A bright streak flashes"
        spell.damage_type = "fire"
        spell.is_concentration = False

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [spell]
        db.execute.return_value = result_mock

        results = await svc.search_spells("fire damage", db, similarity_threshold=0.0)
        assert len(results) >= 1
        assert results[0]["name"] == "Fireball"
        assert results[0]["damage_type"] == "fire"


# ---------------------------------------------------------------------------
# search_memories
# ---------------------------------------------------------------------------


class TestSearchMemories:
    async def test_empty_when_no_model(self):
        svc = _make_service()
        svc.embedding_service._model = None
        db = AsyncMock()
        result = await svc.search_memories("dragon", db, character_id=1)
        assert result == []

    async def test_empty_when_empty_query(self):
        svc = _make_service()
        db = AsyncMock()
        result = await svc.search_memories("", db, character_id=1)
        assert result == []

    async def test_empty_when_whitespace_query(self):
        svc = _make_service()
        db = AsyncMock()
        result = await svc.search_memories("   ", db, character_id=1)
        assert result == []

    async def test_returns_empty_on_embedding_failure(self):
        svc = _make_service()
        svc.embedding_service._model.encode.side_effect = RuntimeError("fail")
        db = AsyncMock()
        result = await svc.search_memories("dragon", db, character_id=1)
        assert result == []


# ---------------------------------------------------------------------------
# get_semantic_search_service singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_returns_instance(self):
        import app.services.semantic_search_service as mod

        mod._semantic_search_instance = None
        with patch.object(SemanticSearchService, "_initialize_model"):
            svc = get_semantic_search_service()
            assert isinstance(svc, SemanticSearchService)
            # Second call returns same instance
            svc2 = get_semantic_search_service()
            assert svc is svc2
            # Cleanup
            mod._semantic_search_instance = None
