"""Tests for app.services.tool_executor — tool dispatch and handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.tool_executor import (
    _execute_companion_share_knowledge,
    _execute_companion_suggest_action,
    _execute_consume_spell_slot,
    _execute_generate_treasure_hoard,
    _execute_get_creature_stats,
    _execute_get_monster_loot,
    _execute_give_item,
    _execute_introduce_companion,
    _execute_list_available_tools,
    _execute_request_player_roll,
    _execute_roll_for_npc,
    _execute_search_items,
    _execute_search_memories,
    _execute_search_monsters,
    _execute_search_spells,
    _execute_update_character_hp,
    execute_tool,
)
from tests.factories import (
    make_character,
    make_companion,
    make_creature,
    make_item_catalog_entry,
    make_spell,
    make_user,
)

# ═══════════════════════════════════════════════════════════════════
# execute_tool dispatcher
# ═══════════════════════════════════════════════════════════════════


class TestExecuteToolDispatcher:
    async def test_unknown_tool_returns_error(self):
        user = make_user()
        char = make_character(user=user)
        result = await execute_tool("nonexistent_tool", {}, char, AsyncMock())
        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    async def test_dispatches_request_player_roll(self):
        user = make_user()
        char = make_character(user=user)
        args = {
            "roll_type": "ability_check",
            "ability_or_skill": "Perception",
            "dc": 15,
        }
        result = await execute_tool("request_player_roll", args, char, AsyncMock())
        assert result["success"] is True
        assert "roll_request" in result

    async def test_dispatches_list_available_tools(self):
        user = make_user()
        char = make_character(user=user)
        result = await execute_tool("list_available_tools", {}, char, AsyncMock())
        assert result["success"] is True
        assert "tools" in result

    async def test_tool_execution_exception(self):
        """When a handler raises, dispatcher catches and returns error."""
        user = make_user()
        char = make_character(user=user)
        with patch(
            "app.services.tool_executor._execute_request_player_roll",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            result = await execute_tool("request_player_roll", {}, char, AsyncMock())
        assert result["success"] is False
        assert "boom" in result["error"]


# ═══════════════════════════════════════════════════════════════════
# _execute_request_player_roll
# ═══════════════════════════════════════════════════════════════════


class TestRequestPlayerRoll:
    async def test_basic_roll(self):
        user = make_user()
        char = make_character(user=user)
        args = {
            "roll_type": "ability_check",
            "ability_or_skill": "Stealth",
            "dc": 14,
            "description": "sneaking past guard",
        }
        result = await _execute_request_player_roll(args, char)
        assert result["success"] is True
        rr = result["roll_request"]
        assert rr["type"] == "ability_check"
        assert rr["ability_or_skill"] == "Stealth"
        assert rr["dc"] == 14
        assert rr["description"] == "sneaking past guard"

    async def test_advantage_disadvantage(self):
        user = make_user()
        char = make_character(user=user)
        args = {
            "roll_type": "saving_throw",
            "ability_or_skill": "Dexterity",
            "dc": 15,
            "advantage": True,
            "disadvantage": False,
        }
        result = await _execute_request_player_roll(args, char)
        assert result["roll_request"]["advantage"] is True
        assert result["roll_request"]["disadvantage"] is False

    async def test_missing_args_uses_defaults(self):
        user = make_user()
        char = make_character(user=user)
        result = await _execute_request_player_roll({}, char)
        assert result["success"] is True
        assert result["roll_request"]["advantage"] is False


# ═══════════════════════════════════════════════════════════════════
# _execute_update_character_hp
# ═══════════════════════════════════════════════════════════════════


class TestUpdateCharacterHP:
    async def test_damage(self):
        char = MagicMock()
        char.current_hp = 20
        char.max_hp = 20
        char.name = "TestHero"
        db = AsyncMock()

        result = await _execute_update_character_hp(
            {"amount": -5, "reason": "goblin attack"}, char, db
        )
        assert result["success"] is True
        assert result["character_update"]["hp"]["new"] == 15

    async def test_healing(self):
        char = MagicMock()
        char.current_hp = 10
        char.max_hp = 20
        char.name = "TestHero"
        db = AsyncMock()

        result = await _execute_update_character_hp(
            {"amount": 5, "reason": "healing potion"}, char, db
        )
        assert result["success"] is True
        assert result["character_update"]["hp"]["new"] == 15

    async def test_healing_capped_at_max(self):
        char = MagicMock()
        char.current_hp = 18
        char.max_hp = 20
        char.name = "TestHero"
        db = AsyncMock()

        result = await _execute_update_character_hp({"amount": 10}, char, db)
        assert result["character_update"]["hp"]["new"] == 20

    async def test_damage_floors_at_zero(self):
        char = MagicMock()
        char.current_hp = 3
        char.max_hp = 20
        char.name = "TestHero"
        db = AsyncMock()

        result = await _execute_update_character_hp({"amount": -10}, char, db)
        assert result["character_update"]["hp"]["new"] == 0


# ═══════════════════════════════════════════════════════════════════
# _execute_consume_spell_slot
# ═══════════════════════════════════════════════════════════════════


class TestConsumeSpellSlot:
    async def test_consume_slot(self, db_session):
        user = make_user()
        char = make_character(
            user=user,
            spell_slots={"level_1": {"total": 3, "remaining": 2}},
        )
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_consume_spell_slot(
            {"spell_level": 1, "spell_name": "Magic Missile"}, char, db_session
        )
        assert result["success"] is True
        assert result["character_update"]["spell_slots"]["remaining"] == 1

    async def test_no_slots_remaining(self, db_session):
        user = make_user()
        char = make_character(
            user=user,
            spell_slots={"level_1": {"total": 2, "remaining": 0}},
        )
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_consume_spell_slot(
            {"spell_level": 1, "spell_name": "Shield"}, char, db_session
        )
        assert result["success"] is False

    async def test_invalid_spell_level(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_consume_spell_slot({"spell_level": 0}, char, db_session)
        assert result["success"] is False

    async def test_no_slot_key_for_level(self, db_session):
        user = make_user()
        char = make_character(
            user=user,
            spell_slots={"level_1": {"total": 2, "remaining": 1}},
        )
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_consume_spell_slot(
            {"spell_level": 3, "spell_name": "Fireball"}, char, db_session
        )
        assert result["success"] is False


# ═══════════════════════════════════════════════════════════════════
# _execute_get_creature_stats
# ═══════════════════════════════════════════════════════════════════


class TestGetCreatureStats:
    async def test_exact_match(self, db_session):
        creature = make_creature(name="Goblin")
        db_session.add(creature)
        await db_session.flush()

        result = await _execute_get_creature_stats({"creature_name": "Goblin"}, db_session)
        assert result["success"] is True
        assert result["creature_name"] == "Goblin"

    async def test_case_insensitive(self, db_session):
        creature = make_creature(name="Dragon")
        db_session.add(creature)
        await db_session.flush()

        result = await _execute_get_creature_stats({"creature_name": "dragon"}, db_session)
        assert result["success"] is True

    async def test_fuzzy_match(self, db_session):
        creature = make_creature(name="Ancient Red Dragon")
        db_session.add(creature)
        await db_session.flush()

        result = await _execute_get_creature_stats({"creature_name": "Red Dragon"}, db_session)
        assert result["success"] is True
        assert "Red Dragon" in result["creature_name"]

    async def test_not_found(self, db_session):
        result = await _execute_get_creature_stats({"creature_name": "Balrog"}, db_session)
        assert result["success"] is False


# ═══════════════════════════════════════════════════════════════════
# _execute_roll_for_npc
# ═══════════════════════════════════════════════════════════════════


class TestRollForNPC:
    async def test_basic_roll(self):
        result = await _execute_roll_for_npc(
            {
                "npc_name": "Goblin",
                "roll_type": "attack",
                "dice_expression": "d20+4",
            },
            AsyncMock(),
        )
        assert result["success"] is True
        assert result["npc_name"] == "Goblin"
        assert isinstance(result["result"], int)
        assert result["modifier"] == 4

    async def test_multiple_dice(self):
        result = await _execute_roll_for_npc(
            {
                "npc_name": "Orc",
                "roll_type": "damage",
                "dice_expression": "2d6+3",
            },
            AsyncMock(),
        )
        assert result["success"] is True
        assert len(result["rolls"]) == 2
        assert result["modifier"] == 3

    async def test_with_target(self):
        result = await _execute_roll_for_npc(
            {
                "npc_name": "Skeleton",
                "roll_type": "attack",
                "dice_expression": "d20",
                "target_name": "Gandalf",
                "context": "melee attack",
            },
            AsyncMock(),
        )
        assert result["success"] is True
        assert result["target_name"] == "Gandalf"

    async def test_invalid_dice_expression(self):
        result = await _execute_roll_for_npc(
            {
                "npc_name": "Goblin",
                "roll_type": "attack",
                "dice_expression": "invalid",
            },
            AsyncMock(),
        )
        assert result["success"] is False


# ═══════════════════════════════════════════════════════════════════
# _execute_introduce_companion
# ═══════════════════════════════════════════════════════════════════


class TestIntroduceCompanion:
    async def test_create_companion(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Xylophonic Sentinel")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        # Monkeypatch commit and refresh to avoid closing the test transaction
        original_commit = db_session.commit
        original_refresh = db_session.refresh
        db_session.commit = AsyncMock()
        db_session.refresh = AsyncMock()
        try:
            result = await _execute_introduce_companion(
                {
                    "name": "Elara",
                    "creature_name": "Xylophonic Sentinel",
                    "personality": "Brave and loyal",
                },
                char,
                db_session,
            )
            assert result["success"] is True
            assert "Elara" in result["message"]
        finally:
            db_session.commit = original_commit
            db_session.refresh = original_refresh

    async def test_creature_not_found(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_introduce_companion(
            {
                "name": "Ghost",
                "creature_name": "NonexistentCreature",
                "personality": "Mysterious",
            },
            char,
            db_session,
        )
        assert result["success"] is False


# ═══════════════════════════════════════════════════════════════════
# _execute_give_item
# ═══════════════════════════════════════════════════════════════════


class TestGiveItem:
    async def test_give_item_from_catalog_hits_model_bug(self, db_session):
        """The _execute_give_item function passes category= to Item() but
        Item model uses item_type (ItemType enum). This is a known production
        bug — the call raises TypeError. We test the actual behavior."""
        user = make_user()
        char = make_character(user=user)
        catalog = make_item_catalog_entry(name="Healing Potion", category="consumable")
        db_session.add_all([user, char, catalog])
        await db_session.flush()

        # The function will find the catalog entry but fail when creating Item
        # because Item doesn't have a 'category' field.
        with pytest.raises(TypeError, match="category"):
            await _execute_give_item(
                {"item_name": "Healing Potion", "quantity": 2, "reason": "quest reward"},
                char,
                db_session,
            )

    async def test_item_not_found(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_give_item(
            {"item_name": "NonexistentItem"},
            char,
            db_session,
        )
        assert result["success"] is False

    async def test_missing_item_name(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_give_item({}, char, db_session)
        assert result["success"] is False


# ═══════════════════════════════════════════════════════════════════
# _execute_list_available_tools
# ═══════════════════════════════════════════════════════════════════


class TestListAvailableTools:
    async def test_lists_tools(self):
        result = await _execute_list_available_tools({})
        assert result["success"] is True
        assert isinstance(result["tools"], list)
        assert len(result["tools"]) > 0
        # Each tool should have name and description
        for tool in result["tools"]:
            assert "name" in tool
            assert "description" in tool


# ═══════════════════════════════════════════════════════════════════
# _execute_search_items (exact matching path)
# ═══════════════════════════════════════════════════════════════════


class TestSearchItems:
    async def test_search_finds_items(self, db_session):
        cat = make_item_catalog_entry(name="Longsword", category="weapon", rarity="common")
        db_session.add(cat)
        await db_session.flush()

        result = await _execute_search_items({"query": "Longsword"}, db_session)
        assert result["success"] is True
        assert len(result["items"]) >= 1

    async def test_search_no_results(self, db_session):
        result = await _execute_search_items({"query": "ZzzNonexistent999"}, db_session)
        assert result["success"] is True
        assert len(result["items"]) == 0

    async def test_search_missing_query(self, db_session):
        result = await _execute_search_items({}, db_session)
        assert result["success"] is False

    async def test_search_with_category_filter(self, db_session):
        cat = make_item_catalog_entry(name="Shield", category="armor", rarity="common")
        db_session.add(cat)
        await db_session.flush()

        result = await _execute_search_items({"query": "Shield", "category": "armor"}, db_session)
        assert result["success"] is True


# ═══════════════════════════════════════════════════════════════════
# _execute_search_monsters (exact matching path)
# ═══════════════════════════════════════════════════════════════════


class TestSearchMonsters:
    async def test_search_finds_creature(self, db_session):
        creature = make_creature(name="Goblin", creature_type="humanoid")
        db_session.add(creature)
        await db_session.flush()

        result = await _execute_search_monsters({"query": "Goblin"}, db_session)
        assert result["success"] is True
        assert len(result["creatures"]) >= 1

    async def test_search_no_results(self, db_session):
        result = await _execute_search_monsters({"query": "zzNonexistent"}, db_session)
        assert result["success"] is True
        assert len(result["creatures"]) == 0

    async def test_search_missing_query(self, db_session):
        result = await _execute_search_monsters({}, db_session)
        assert result["success"] is False

    async def test_search_with_creature_type_filter(self, db_session):
        creature = make_creature(name="Skeleton", creature_type="undead")
        db_session.add(creature)
        await db_session.flush()

        result = await _execute_search_monsters(
            {"query": "Skeleton", "creature_type": "undead"}, db_session
        )
        assert result["success"] is True


# ═══════════════════════════════════════════════════════════════════
# _execute_search_spells (exact matching path)
# ═══════════════════════════════════════════════════════════════════


class TestSearchSpells:
    async def test_search_finds_spell(self, db_session):
        spell = make_spell(name="Fireball", description="A bright streak of fire")
        db_session.add(spell)
        await db_session.flush()

        result = await _execute_search_spells({"query": "Fireball"}, db_session)
        assert result["success"] is True
        assert len(result["spells"]) >= 1

    async def test_search_no_results(self, db_session):
        result = await _execute_search_spells({"query": "zzNonexistent"}, db_session)
        assert result["success"] is True
        assert len(result["spells"]) == 0

    async def test_search_missing_query(self, db_session):
        result = await _execute_search_spells({}, db_session)
        assert result["success"] is False

    async def test_search_with_level_filter(self, db_session):
        spell = make_spell(name="Fire Bolt", level=0, description="A beam of fire")
        db_session.add(spell)
        await db_session.flush()

        result = await _execute_search_spells({"query": "Fire", "spell_level": 0}, db_session)
        assert result["success"] is True


# ═══════════════════════════════════════════════════════════════════
# _execute_companion_suggest_action
# ═══════════════════════════════════════════════════════════════════


class TestCompanionSuggestAction:
    async def test_suggest_action(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Elf Scout")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature, name="Elara")
        db_session.add(companion)
        await db_session.flush()

        result = await _execute_companion_suggest_action(
            {
                "companion_name": "Elara",
                "suggestion": "We should flank the enemy",
                "urgency": "high",
            },
            char,
            db_session,
        )
        assert result["success"] is True
        assert "flank" in result["message"]

    async def test_missing_args(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_companion_suggest_action(
            {"companion_name": None, "suggestion": None},
            char,
            db_session,
        )
        assert result["success"] is False

    async def test_companion_not_found(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_companion_suggest_action(
            {"companion_name": "NonexistentCompanion", "suggestion": "Hello"},
            char,
            db_session,
        )
        assert result["success"] is False


# ═══════════════════════════════════════════════════════════════════
# _execute_companion_share_knowledge
# ═══════════════════════════════════════════════════════════════════


class TestCompanionShareKnowledge:
    async def test_share_knowledge(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Sage")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature, name="Merlin")
        db_session.add(companion)
        await db_session.flush()

        result = await _execute_companion_share_knowledge(
            {
                "companion_name": "Merlin",
                "topic": "Dragons",
                "information": "Dragons are weak to cold iron.",
                "reliability": "confident",
            },
            char,
            db_session,
        )
        assert result["success"] is True
        assert "Dragons" in result["message"]

    async def test_missing_args(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()

        result = await _execute_companion_share_knowledge(
            {"companion_name": None, "topic": None, "information": None},
            char,
            db_session,
        )
        assert result["success"] is False


# ═══════════════════════════════════════════════════════════════════
# _execute_search_memories
# ═══════════════════════════════════════════════════════════════════


class TestSearchMemories:
    async def test_missing_query(self):
        user = make_user()
        char = make_character(user=user)
        result = await _execute_search_memories({}, char, AsyncMock())
        assert result["success"] is False

    async def test_search_with_mock_service(self):
        user = make_user()
        char = make_character(user=user)

        mock_service = MagicMock()
        mock_service.search_memories = AsyncMock(
            return_value=[{"content": "Fought a dragon", "importance": 8}]
        )

        with patch(
            "app.services.semantic_search_service.get_semantic_search_service",
            return_value=mock_service,
        ):
            result = await _execute_search_memories({"query": "dragon"}, char, AsyncMock())
        assert result["success"] is True
        assert len(result["memories"]) == 1

    async def test_search_no_results(self):
        user = make_user()
        char = make_character(user=user)

        mock_service = MagicMock()
        mock_service.search_memories = AsyncMock(return_value=[])

        with patch(
            "app.services.semantic_search_service.get_semantic_search_service",
            return_value=mock_service,
        ):
            result = await _execute_search_memories({"query": "nothing"}, char, AsyncMock())
        assert result["success"] is True
        assert len(result["memories"]) == 0

    async def test_search_error(self):
        user = make_user()
        char = make_character(user=user)

        mock_service = MagicMock()
        mock_service.search_memories = AsyncMock(side_effect=Exception("boom"))

        with patch(
            "app.services.semantic_search_service.get_semantic_search_service",
            return_value=mock_service,
        ):
            result = await _execute_search_memories({"query": "dragon"}, char, AsyncMock())
        assert result["success"] is False


# ═══════════════════════════════════════════════════════════════════
# _execute_get_monster_loot
# ═══════════════════════════════════════════════════════════════════


class TestGetMonsterLoot:
    async def test_missing_monster_name(self):
        result = await _execute_get_monster_loot({}, AsyncMock())
        assert result["success"] is False

    async def test_loot_found(self):
        mock_linker = MagicMock()
        mock_linker.get_monster_equipment = AsyncMock(
            return_value=[
                {
                    "name": "Rusty Sword",
                    "rarity": "common",
                    "damage_dice": "1d6",
                    "damage_type": "slashing",
                }
            ]
        )

        with patch("app.services.content_linker.get_content_linker", return_value=mock_linker):
            result = await _execute_get_monster_loot({"monster_name": "Goblin"}, AsyncMock())
        assert result["success"] is True
        assert len(result["items"]) == 1

    async def test_no_loot(self):
        mock_linker = MagicMock()
        mock_linker.get_monster_equipment = AsyncMock(return_value=[])

        with patch("app.services.content_linker.get_content_linker", return_value=mock_linker):
            result = await _execute_get_monster_loot({"monster_name": "Goblin"}, AsyncMock())
        assert result["success"] is True
        assert len(result["items"]) == 0


# ═══════════════════════════════════════════════════════════════════
# _execute_generate_treasure_hoard
# ═══════════════════════════════════════════════════════════════════


class TestGenerateTreasureHoard:
    async def test_missing_cr(self):
        result = await _execute_generate_treasure_hoard({}, AsyncMock())
        assert result["success"] is False

    async def test_invalid_cr(self):
        result = await _execute_generate_treasure_hoard(
            {"challenge_rating": "not_a_number"}, AsyncMock()
        )
        assert result["success"] is False

    async def test_treasure_generated(self):
        mock_linker = MagicMock()
        mock_linker.generate_loot_table = AsyncMock(
            return_value=[{"name": "Gold Ring", "rarity": "uncommon", "value_gp": 50}]
        )

        with patch("app.services.content_linker.get_content_linker", return_value=mock_linker):
            result = await _execute_generate_treasure_hoard({"challenge_rating": 5}, AsyncMock())
        assert result["success"] is True
        assert len(result["items"]) == 1

    async def test_no_treasure(self):
        mock_linker = MagicMock()
        mock_linker.generate_loot_table = AsyncMock(return_value=[])

        with patch("app.services.content_linker.get_content_linker", return_value=mock_linker):
            result = await _execute_generate_treasure_hoard({"challenge_rating": 1}, AsyncMock())
        assert result["success"] is True
        assert len(result["items"]) == 0

    async def test_rarity_descriptors(self):
        """Different CRs should produce different rarity descriptors."""
        mock_linker = MagicMock()
        mock_linker.generate_loot_table = AsyncMock(
            return_value=[{"name": "Gem", "rarity": "rare", "value_gp": 200}]
        )

        with patch("app.services.content_linker.get_content_linker", return_value=mock_linker):
            for cr, expected in [
                (1, "common"),
                (5, "uncommon"),
                (12, "rare"),
                (18, "very rare"),
                (22, "legendary"),
            ]:
                result = await _execute_generate_treasure_hoard(
                    {"challenge_rating": cr}, AsyncMock()
                )
                assert result["rarity_level"] == expected, f"CR {cr} expected {expected}"
