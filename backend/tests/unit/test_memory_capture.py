"""Tests for MemoryCaptureService — memory_capture.py"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

from app.services.memory_capture import MemoryCaptureService

SESSION_ID = uuid.uuid4()


def _mock_db():
    return AsyncMock()


# ---------------------------------------------------------------------------
# capture_combat_event
# ---------------------------------------------------------------------------


class TestCaptureCombatEvent:
    async def test_victory_auto_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_combat_event(
                db=db,
                session_id=SESSION_ID,
                combatant_names=["Goblin", "Orc"],
                outcome="victory",
                details="The party won the fight.",
            )
            mock_store.assert_awaited_once()
            call_kwargs = mock_store.call_args.kwargs
            assert call_kwargs["importance"] == 7
            assert "Combat:" in call_kwargs["content"]
            assert call_kwargs["npcs_involved"] == ["Goblin", "Orc"]

    async def test_defeat_auto_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_combat_event(
                db=db,
                session_id=SESSION_ID,
                combatant_names=["Dragon"],
                outcome="defeat",
                details="The dragon annihilated the party.",
            )
            assert mock_store.call_args.kwargs["importance"] == 9

    async def test_boss_auto_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_combat_event(
                db=db,
                session_id=SESSION_ID,
                combatant_names=["Boss Goblin"],
                outcome="victory",
                details="Defeated the boss goblin in the cave.",
            )
            assert mock_store.call_args.kwargs["importance"] == 9

    async def test_default_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_combat_event(
                db=db,
                session_id=SESSION_ID,
                combatant_names=["Rat"],
                outcome="fled",
                details="The party ran from a rat.",
            )
            assert mock_store.call_args.kwargs["importance"] == 6

    async def test_explicit_importance_override(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_combat_event(
                db=db,
                session_id=SESSION_ID,
                combatant_names=["Rat"],
                outcome="victory",
                details="Won.",
                importance=3,
            )
            assert mock_store.call_args.kwargs["importance"] == 3

    async def test_exception_is_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db down"),
        ):
            # Should not raise
            await MemoryCaptureService.capture_combat_event(
                db=db,
                session_id=SESSION_ID,
                combatant_names=[],
                outcome="victory",
                details="ok",
            )


# ---------------------------------------------------------------------------
# capture_dialogue
# ---------------------------------------------------------------------------


class TestCaptureDialogue:
    async def test_quest_dialogue_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_dialogue(
                db=db,
                session_id=SESSION_ID,
                npc_name="Elara",
                dialogue="I have a quest for you.",
            )
            assert mock_store.call_args.kwargs["importance"] == 6
            assert "Elara" in mock_store.call_args.kwargs["npcs_involved"]

    async def test_normal_dialogue_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_dialogue(
                db=db,
                session_id=SESSION_ID,
                npc_name="Barkeep",
                dialogue="Hello, traveler.",
            )
            assert mock_store.call_args.kwargs["importance"] == 4

    async def test_explicit_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_dialogue(
                db=db,
                session_id=SESSION_ID,
                npc_name="NPC",
                dialogue="hello",
                importance=10,
            )
            assert mock_store.call_args.kwargs["importance"] == 10

    async def test_exception_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=Exception("oops"),
        ):
            await MemoryCaptureService.capture_dialogue(
                db=db, session_id=SESSION_ID, npc_name="X", dialogue="Y"
            )


# ---------------------------------------------------------------------------
# capture_summary
# ---------------------------------------------------------------------------


class TestCaptureSummary:
    async def test_default_importance_and_tags(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_summary(
                db=db,
                session_id=SESSION_ID,
                summary="The party met Gandalf and explored the Dark Forest.",
                message_count=15,
            )
            kw = mock_store.call_args.kwargs
            assert kw["importance"] == 8
            assert "summary" in kw["tags"]
            assert "messages_15" in kw["tags"]

    async def test_entity_extraction(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_summary(
                db=db,
                session_id=SESSION_ID,
                summary="Gandalf said the quest is important. They arrived at Dark Forest Cave. They found a Magic Sword.",
                message_count=10,
            )
            kw = mock_store.call_args.kwargs
            assert len(kw["npcs_involved"]) > 0
            # locations/items may be extracted
            assert isinstance(kw["locations"], list)
            assert isinstance(kw["items_involved"], list)

    async def test_exception_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=Exception("boom"),
        ):
            await MemoryCaptureService.capture_summary(
                db=db, session_id=SESSION_ID, summary="x", message_count=1
            )


# ---------------------------------------------------------------------------
# _extract_npcs / _extract_locations / _extract_items
# ---------------------------------------------------------------------------


class TestEntityExtraction:
    def test_extract_npcs_dialogue(self):
        text = "Gandalf said the ring must be destroyed. Elara replied with concern."
        npcs = MemoryCaptureService._extract_npcs(text)
        assert "Gandalf" in npcs
        assert "Elara" in npcs

    def test_extract_npcs_meeting(self):
        text = "The party met Thorin near the mountain."
        npcs = MemoryCaptureService._extract_npcs(text)
        assert "Thorin" in npcs

    def test_extract_npcs_max_ten(self):
        # Build text with many NPC mentions
        names = [f"Name{chr(65 + i)}" for i in range(15)]
        text = " ".join(f"{n} said hi." for n in names)
        npcs = MemoryCaptureService._extract_npcs(text)
        assert len(npcs) <= 10

    def test_extract_npcs_dedup(self):
        text = "Gandalf said hello. Gandalf replied goodbye."
        npcs = MemoryCaptureService._extract_npcs(text)
        assert npcs.count("Gandalf") == 1

    def test_extract_locations(self):
        text = "They arrived at Dark Forest and entered the Crystal Cave."
        locs = MemoryCaptureService._extract_locations(text)
        assert len(locs) >= 1

    def test_extract_locations_max_eight(self):
        places = [f"Place{chr(65 + i)}" for i in range(12)]
        text = " ".join(f"Arrived at {p} Town." for p in places)
        locs = MemoryCaptureService._extract_locations(text)
        assert len(locs) <= 8

    def test_extract_items(self):
        text = "They found a Magic Sword and acquired the Silver Ring."
        items = MemoryCaptureService._extract_items(text)
        assert len(items) >= 1

    def test_extract_items_max_ten(self):
        things = [f"Thing{chr(65 + i)}" for i in range(12)]
        text = " ".join(f"found a {t} Sword." for t in things)
        items = MemoryCaptureService._extract_items(text)
        assert len(items) <= 10


# ---------------------------------------------------------------------------
# capture_discovery
# ---------------------------------------------------------------------------


class TestCaptureDiscovery:
    async def test_legendary_discovery(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_discovery(
                db=db,
                session_id=SESSION_ID,
                discovery_type="treasure",
                details="Found a legendary artifact.",
                location="Old Temple",
                items=["Artifact"],
            )
            kw = mock_store.call_args.kwargs
            assert kw["importance"] == 8
            assert kw["locations"] == ["Old Temple"]
            assert kw["items_involved"] == ["Artifact"]

    async def test_secret_discovery(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_discovery(
                db=db,
                session_id=SESSION_ID,
                discovery_type="secret",
                details="Hidden room found.",
            )
            assert mock_store.call_args.kwargs["importance"] == 8

    async def test_treasure_discovery(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_discovery(
                db=db,
                session_id=SESSION_ID,
                discovery_type="treasure",
                details="Found gold coins.",
            )
            assert mock_store.call_args.kwargs["importance"] == 7

    async def test_generic_discovery(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_discovery(
                db=db,
                session_id=SESSION_ID,
                discovery_type="clue",
                details="Found a clue.",
            )
            assert mock_store.call_args.kwargs["importance"] == 6

    async def test_exception_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            await MemoryCaptureService.capture_discovery(
                db=db, session_id=SESSION_ID, discovery_type="x", details="y"
            )


# ---------------------------------------------------------------------------
# capture_quest_milestone
# ---------------------------------------------------------------------------


class TestCaptureQuestMilestone:
    async def test_milestone(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_quest_milestone(
                db=db,
                session_id=SESSION_ID,
                quest_title="Save the Village",
                milestone="started",
                details="The quest has begun.",
            )
            kw = mock_store.call_args.kwargs
            assert kw["importance"] == 8
            assert "Save the Village" in kw["tags"]
            assert "started" in kw["tags"]

    async def test_exception_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            await MemoryCaptureService.capture_quest_milestone(
                db=db, session_id=SESSION_ID, quest_title="Q", milestone="m", details="d"
            )


# ---------------------------------------------------------------------------
# capture_decision
# ---------------------------------------------------------------------------


class TestCaptureDecision:
    async def test_without_consequences(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_decision(
                db=db,
                session_id=SESSION_ID,
                decision="Spare the goblin.",
            )
            kw = mock_store.call_args.kwargs
            assert kw["importance"] == 7
            assert "Decision:" in kw["content"]
            assert "Consequences" not in kw["content"]

    async def test_with_consequences(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_decision(
                db=db,
                session_id=SESSION_ID,
                decision="Spare the goblin.",
                consequences="The goblin revealed a shortcut.",
            )
            assert "Consequences" in mock_store.call_args.kwargs["content"]

    async def test_exception_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            await MemoryCaptureService.capture_decision(db=db, session_id=SESSION_ID, decision="x")


# ---------------------------------------------------------------------------
# capture_npc_interaction
# ---------------------------------------------------------------------------


class TestCaptureNpcInteraction:
    async def test_betrayed_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_npc_interaction(
                db=db,
                session_id=SESSION_ID,
                npc_name="Vizier",
                interaction_type="betrayed",
                details="The Vizier betrayed the party.",
            )
            assert mock_store.call_args.kwargs["importance"] == 8

    async def test_met_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_npc_interaction(
                db=db,
                session_id=SESSION_ID,
                npc_name="Merchant",
                interaction_type="met",
                details="Met the merchant.",
            )
            assert mock_store.call_args.kwargs["importance"] == 5

    async def test_generic_importance(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_npc_interaction(
                db=db,
                session_id=SESSION_ID,
                npc_name="Guard",
                interaction_type="questioned",
                details="Asked the guard about events.",
            )
            assert mock_store.call_args.kwargs["importance"] == 6

    async def test_exception_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            await MemoryCaptureService.capture_npc_interaction(
                db=db, session_id=SESSION_ID, npc_name="X", interaction_type="met", details="d"
            )


# ---------------------------------------------------------------------------
# capture_location_visit
# ---------------------------------------------------------------------------


class TestCaptureLocationVisit:
    async def test_location_visit(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_location_visit(
                db=db,
                session_id=SESSION_ID,
                location_name="Dark Forest",
                details="The party entered the Dark Forest.",
            )
            kw = mock_store.call_args.kwargs
            assert kw["importance"] == 5
            assert kw["locations"] == ["Dark Forest"]

    async def test_exception_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            await MemoryCaptureService.capture_location_visit(
                db=db, session_id=SESSION_ID, location_name="X", details="d"
            )


# ---------------------------------------------------------------------------
# capture_loot
# ---------------------------------------------------------------------------


class TestCaptureLoot:
    async def test_legendary_loot(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_loot(
                db=db,
                session_id=SESSION_ID,
                items=["Legendary Sword", "Gold"],
                source="Dragon hoard",
            )
            assert mock_store.call_args.kwargs["importance"] == 7

    async def test_normal_loot(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_loot(
                db=db,
                session_id=SESSION_ID,
                items=["Gold coins"],
                source="Chest",
            )
            assert mock_store.call_args.kwargs["importance"] == 5

    async def test_exception_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            await MemoryCaptureService.capture_loot(
                db=db, session_id=SESSION_ID, items=["x"], source="s"
            )


# ---------------------------------------------------------------------------
# capture_spell_cast
# ---------------------------------------------------------------------------


class TestCaptureSpellCast:
    async def test_high_level_spell(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_spell_cast(
                db=db,
                session_id=SESSION_ID,
                spell_name="Wish",
                spell_level=9,
                target="self",
                outcome="Success",
            )
            kw = mock_store.call_args.kwargs
            assert kw["importance"] == 8
            assert "Wish" in kw["content"]
            assert "self" in kw["content"]
            assert "Success" in kw["content"]

    async def test_mid_level_spell(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_spell_cast(
                db=db, session_id=SESSION_ID, spell_name="Fireball", spell_level=5
            )
            assert mock_store.call_args.kwargs["importance"] == 7

    async def test_low_level_spell(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_spell_cast(
                db=db, session_id=SESSION_ID, spell_name="Magic Missile", spell_level=1
            )
            assert mock_store.call_args.kwargs["importance"] == 5

    async def test_level_3_spell(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_spell_cast(
                db=db, session_id=SESSION_ID, spell_name="Counterspell", spell_level=3
            )
            assert mock_store.call_args.kwargs["importance"] == 6

    async def test_no_target_no_outcome(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory", new_callable=AsyncMock
        ) as mock_store:
            await MemoryCaptureService.capture_spell_cast(
                db=db, session_id=SESSION_ID, spell_name="Shield", spell_level=1
            )
            content = mock_store.call_args.kwargs["content"]
            assert "on" not in content.split("level")[1] if "level" in content else True

    async def test_exception_swallowed(self):
        db = _mock_db()
        with patch(
            "app.services.memory_capture.MemoryService.store_memory",
            new_callable=AsyncMock,
            side_effect=Exception("err"),
        ):
            await MemoryCaptureService.capture_spell_cast(
                db=db, session_id=SESSION_ID, spell_name="X", spell_level=1
            )
