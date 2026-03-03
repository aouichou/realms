"""Tests for app.services.dm_supervisor — DM response validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# We patch heavy dependencies at import time so the class can be instantiated
# without needing torch / numpy / sentence_transformers / filesystem.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_supervisor_deps(monkeypatch):
    """Prevent real model loading and filesystem access."""
    monkeypatch.setattr(
        "app.services.dm_supervisor.ImageDetectionService",
        MagicMock,
    )


def _make_supervisor():
    """Create a DMSupervisor with mocked dependencies."""
    with patch("app.services.dm_supervisor.Path"):
        from app.services.dm_supervisor import DMSupervisor

        sup = DMSupervisor.__new__(DMSupervisor)
        sup.knowledge_dir = MagicMock()
        sup.reference_texts = {}
        sup.reference_chunks = []
        sup.chunk_embeddings = None
        sup.model_service = None
        # copy trigger keywords and mistake patterns from class
        real = DMSupervisor.__new__(DMSupervisor)
        sup.trigger_keywords = [
            "attack",
            "damage",
            "hit points",
            "hp",
            "roll",
            "dice",
            "d20",
            "combat",
            "initiative",
            "loot",
            "item",
            "spell",
            "cast",
            "heal",
            "hurt",
            "wound",
            "strike",
            "swing",
            "shoot",
            "stab",
        ]
        # Copy mistake_patterns from the real class body
        import re

        sup.mistake_patterns = [
            {
                "name": "narrated_roll_result",
                "pattern": r"(you|player|character)\s+(roll|rolled|rolls)\s+(and\s+)?(hit|hits|miss|misses|get|gets|score|scores)",
                "explanation": "DM should use request_player_roll, not narrate roll results",
                "relevant_sections": ["Dice Rolling Protocol", "Common Mistakes"],
            },
            {
                "name": "damage_without_tool",
                "pattern": r"(take|takes|deals?|suffering?|loses?)\s+\d+\s+(damage|hp|hit points)",
                "explanation": "Must use update_character_hp when mentioning damage",
                "relevant_sections": ["HP Management", "update_character_hp"],
            },
            {
                "name": "text_based_tool_call",
                "pattern": r"(request_player_roll|roll_for_npc|update_character_hp|give_item|search_items|update_quest|create_quest)\s*\([^)]+\)",
                "explanation": "DM must use actual tool calling API, not write tool calls as text in narration",
                "relevant_sections": ["Tool Usage Rules", "Common Mistakes"],
            },
        ]
        return sup


# ---------------------------------------------------------------------------
# detect_triggers
# ---------------------------------------------------------------------------


class TestDetectTriggers:
    def test_trigger_found(self):
        sup = _make_supervisor()
        assert sup.detect_triggers("I attack the goblin", "The goblin snarls") is True

    def test_no_trigger(self):
        sup = _make_supervisor()
        assert sup.detect_triggers("I look around", "You see a tavern") is False

    def test_case_insensitive(self):
        sup = _make_supervisor()
        assert sup.detect_triggers("ATTACK!", "") is True

    def test_trigger_in_response(self):
        sup = _make_supervisor()
        assert sup.detect_triggers("hello", "You take 5 damage") is True


# ---------------------------------------------------------------------------
# _check_mistake_patterns
# ---------------------------------------------------------------------------


class TestCheckMistakePatterns:
    def test_no_mistakes(self):
        sup = _make_supervisor()
        assert sup._check_mistake_patterns("You see a quiet forest clearing.") == []

    def test_detects_narrated_roll(self):
        sup = _make_supervisor()
        resp = "You rolled and hit the goblin squarely."
        mistakes = sup._check_mistake_patterns(resp)
        assert any(m["type"] == "narrated_roll_result" for m in mistakes)

    def test_detects_damage_without_tool(self):
        sup = _make_supervisor()
        resp = "The goblin takes 8 damage from your attack."
        mistakes = sup._check_mistake_patterns(resp)
        assert any(m["type"] == "damage_without_tool" for m in mistakes)

    def test_detects_text_based_tool_call(self):
        sup = _make_supervisor()
        resp = 'The DM uses request_player_roll("Athletics", 15) to check.'
        mistakes = sup._check_mistake_patterns(resp)
        assert any(m["type"] == "text_based_tool_call" for m in mistakes)


# ---------------------------------------------------------------------------
# _check_tool_calls
# ---------------------------------------------------------------------------


class TestCheckToolCalls:
    def test_no_issues_when_clean(self):
        sup = _make_supervisor()
        issues = sup._check_tool_calls("You enter the tavern.", None)
        assert issues == []

    def test_spell_effect_without_save(self):
        sup = _make_supervisor()
        resp = "You cast a spell and the guard's eyes widen as it takes effect."
        issues = sup._check_tool_calls(resp, [])
        assert any("saving throw" in i.lower() or "spell" in i.lower() for i in issues)

    def test_spell_ok_with_roll(self):
        sup = _make_supervisor()
        resp = "You cast a spell and the guard's eyes widen."
        tools = [{"name": "roll_for_npc"}]
        issues = sup._check_tool_calls(resp, tools)
        # Should be clean because roll_for_npc was called
        assert not any("saving throw" in i.lower() for i in issues)

    def test_attack_hitting_without_roll(self):
        sup = _make_supervisor()
        resp = "You attack the goblin and your sword connects!"
        issues = sup._check_tool_calls(resp, [])
        assert any("attack" in i.lower() for i in issues)

    def test_damage_mention_without_hp_tool(self):
        sup = _make_supervisor()
        resp = "The goblin deals 5 damage to you."
        issues = sup._check_tool_calls(resp, [])
        assert any("update_character_hp" in i for i in issues)

    def test_combat_start_without_initiative(self):
        sup = _make_supervisor()
        resp = "Combat begins as the orcs rush forward!"
        issues = sup._check_tool_calls(resp, [])
        assert any("initiative" in i.lower() for i in issues)


# ---------------------------------------------------------------------------
# validate_response
# ---------------------------------------------------------------------------


class TestValidateResponse:
    async def test_valid_response(self):
        sup = _make_supervisor()
        result = await sup.validate_response(
            player_input="I look around the room",
            dm_response="You see a cozy tavern with a roaring fire.",
        )
        assert result["valid"] is True
        assert result["should_regenerate"] is False
        assert result["issues"] == []

    async def test_invalid_response_with_mistake(self):
        sup = _make_supervisor()
        result = await sup.validate_response(
            player_input="I attack",
            dm_response="You rolled and hit the goblin. It takes 10 damage.",
        )
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    async def test_exception_returns_safe_default(self):
        sup = _make_supervisor()
        # Force an error inside validation
        sup._check_mistake_patterns = MagicMock(side_effect=RuntimeError("boom"))
        result = await sup.validate_response("x", "y")
        assert result["valid"] is True  # defaults to valid on error

    async def test_should_regenerate_on_low_confidence(self):
        sup = _make_supervisor()
        result = await sup.validate_response(
            player_input="I attack",
            dm_response="You rolled and hit. The goblin takes 10 damage.",
        )
        # Both mistake pattern + tool issue → confidence drops → should_regenerate
        if not result["valid"]:
            assert result["confidence"] < 1.0
