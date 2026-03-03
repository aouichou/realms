"""Tests for ContentLinker — content_linker.py"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.services.content_linker import ContentLinker, get_content_linker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_linker() -> ContentLinker:
    return ContentLinker()


def _mock_db_with_result(scalars=None, scalar_one=None):
    """Return an AsyncMock db session with pre-configured execute result."""
    db = AsyncMock()
    result = MagicMock()
    if scalar_one is not None:
        result.scalar_one_or_none.return_value = scalar_one
    if scalars is not None:
        result.scalars.return_value.all.return_value = scalars
    db.execute.return_value = result
    return db


# ---------------------------------------------------------------------------
# _get_rarity_for_cr
# ---------------------------------------------------------------------------


class TestGetRarityForCR:
    def test_common(self):
        linker = _make_linker()
        assert linker._get_rarity_for_cr(0) == "common"
        assert linker._get_rarity_for_cr(2) == "common"
        assert linker._get_rarity_for_cr(4) == "common"

    def test_uncommon(self):
        linker = _make_linker()
        assert linker._get_rarity_for_cr(5) == "uncommon"
        assert linker._get_rarity_for_cr(10) == "uncommon"

    def test_rare(self):
        linker = _make_linker()
        assert linker._get_rarity_for_cr(11) == "rare"
        assert linker._get_rarity_for_cr(16) == "rare"

    def test_very_rare(self):
        linker = _make_linker()
        assert linker._get_rarity_for_cr(17) == "very rare"
        assert linker._get_rarity_for_cr(20) == "very rare"

    def test_legendary(self):
        linker = _make_linker()
        assert linker._get_rarity_for_cr(21) == "legendary"
        assert linker._get_rarity_for_cr(30) == "legendary"

    def test_out_of_range_defaults_common(self):
        linker = _make_linker()
        assert linker._get_rarity_for_cr(999) == "common"


# ---------------------------------------------------------------------------
# get_monster_equipment
# ---------------------------------------------------------------------------


class TestGetMonsterEquipment:
    async def test_monster_not_found(self):
        linker = _make_linker()
        db = _mock_db_with_result(scalar_one=None)
        result = await linker.get_monster_equipment("Unknown", db)
        assert result == []

    async def test_returns_items(self):
        linker = _make_linker()

        monster = MagicMock()
        monster.name = "Goblin"
        monster.challenge_rating = "1"
        monster.id = 1

        item = MagicMock()
        item.id = 10
        item.name = "Scimitar"
        item.category = "weapon"
        item.rarity = "common"
        item.damage_dice = "1d6"
        item.damage_type = "slashing"
        item.ac_base = None
        item.ac_bonus = None
        item.description = "A curved sword"

        # First execute returns monster, second returns items
        db = AsyncMock()
        monster_result = MagicMock()
        monster_result.scalar_one_or_none.return_value = monster
        item_result = MagicMock()
        item_result.scalars.return_value.all.return_value = [item]
        db.execute.side_effect = [monster_result, item_result]

        result = await linker.get_monster_equipment("Goblin", db)
        assert len(result) == 1
        assert result[0]["name"] == "Scimitar"
        assert result[0]["category"] == "weapon"

    async def test_exception_returns_empty(self):
        linker = _make_linker()
        db = AsyncMock()
        db.execute.side_effect = Exception("db error")
        result = await linker.get_monster_equipment("Goblin", db)
        assert result == []

    async def test_monster_no_cr(self):
        linker = _make_linker()

        monster = MagicMock()
        monster.name = "Blob"
        monster.challenge_rating = None
        monster.id = 2

        db = AsyncMock()
        monster_result = MagicMock()
        monster_result.scalar_one_or_none.return_value = monster
        item_result = MagicMock()
        item_result.scalars.return_value.all.return_value = []
        db.execute.side_effect = [monster_result, item_result]

        result = await linker.get_monster_equipment("Blob", db)
        assert result == []


# ---------------------------------------------------------------------------
# generate_loot_table
# ---------------------------------------------------------------------------


class TestGenerateLootTable:
    async def test_generates_loot(self):
        linker = _make_linker()

        item = MagicMock()
        item.id = 5
        item.name = "Health Potion"
        item.category = "potion"
        item.rarity = "common"
        item.description = "Restores HP"
        item.damage_dice = None
        item.damage_type = None
        item.ac_base = None
        item.ac_bonus = None
        item.value_gp = 50

        db = _mock_db_with_result(scalars=[item])
        result = await linker.generate_loot_table(3.0, db, num_items=2)
        assert len(result) == 1
        assert result[0]["name"] == "Health Potion"

    async def test_caps_at_ten(self):
        linker = _make_linker()
        db = _mock_db_with_result(scalars=[])
        # Requesting 20 items should be capped to 10
        result = await linker.generate_loot_table(5.0, db, num_items=20)
        # No items in DB, so empty, but no error
        assert result == []

    async def test_without_consumables(self):
        linker = _make_linker()
        db = _mock_db_with_result(scalars=[])
        result = await linker.generate_loot_table(5.0, db, num_items=3, include_consumables=False)
        assert result == []

    async def test_exception_returns_empty(self):
        linker = _make_linker()
        db = AsyncMock()
        db.execute.side_effect = Exception("db error")
        result = await linker.generate_loot_table(5.0, db)
        assert result == []

    async def test_long_description_truncated(self):
        linker = _make_linker()

        item = MagicMock()
        item.id = 6
        item.name = "Tome"
        item.category = "wondrous_item"
        item.rarity = "rare"
        item.description = "A" * 300
        item.damage_dice = None
        item.damage_type = None
        item.ac_base = None
        item.ac_bonus = None
        item.value_gp = 500

        db = _mock_db_with_result(scalars=[item])
        result = await linker.generate_loot_table(12.0, db)
        assert result[0]["description"].endswith("...")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestContentLinkerSingleton:
    def test_get_content_linker_returns_same(self):
        import app.services.content_linker as mod

        mod._content_linker_instance = None
        linker1 = get_content_linker()
        linker2 = get_content_linker()
        assert linker1 is linker2
        mod._content_linker_instance = None
