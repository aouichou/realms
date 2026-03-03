"""Tests for context_transfer and context_window_manager."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.context_transfer import ContextTransferService
from app.services.context_window_manager import ContextWindowManager

# ============================================================================
# ContextTransferService
# ============================================================================


class TestCompressConversationHistory:
    async def test_short_list_unchanged(self):
        msgs = [{"role": "user", "content": f"m{i}"} for i in range(5)]
        result = await ContextTransferService.compress_conversation_history(msgs, max_messages=10)
        assert result == msgs

    async def test_keeps_system_and_recent(self):
        msgs = [{"role": "system", "content": "sys"}] + [
            {"role": "user", "content": f"m{i}"} for i in range(15)
        ]
        result = await ContextTransferService.compress_conversation_history(msgs, max_messages=5)
        assert len(result) == 5
        assert result[0]["role"] == "system"

    async def test_no_system_message(self):
        msgs = [{"role": "user", "content": f"m{i}"} for i in range(15)]
        result = await ContextTransferService.compress_conversation_history(msgs, max_messages=5)
        assert len(result) == 5


class TestFormatContextTransfer:
    def test_formats_recent_turns(self):
        summary = "ADVENTURE SUMMARY: You fought a dragon."
        messages = [
            {"role": "user", "content": "I attack"},
            {"role": "assistant", "content": "You swing your sword"},
            {"role": "user", "content": "I dodge"},
            {"role": "assistant", "content": "You leap aside"},
        ]
        result = ContextTransferService.format_context_transfer(summary, messages)
        assert "ADVENTURE SUMMARY" in result
        assert "CONVERSATION CONTEXT" in result
        assert "PLAYER:" in result
        assert "DM:" in result

    def test_empty_messages(self):
        result = ContextTransferService.format_context_transfer("summary", [])
        assert "summary" in result


class TestFormatCharacterDetails:
    async def test_formats_character(self):
        char = MagicMock()
        char.name = "Gandalf"
        char.level = 5
        char.race = "Human"
        char.class_name = "Wizard"
        char.personality = "Mysterious"
        char.current_hp = 30
        char.max_hp = 40
        char.strength = 10
        char.dexterity = 14
        char.constitution = 12
        char.intelligence = 18
        char.wisdom = 16
        char.charisma = 12

        result = await ContextTransferService._format_character_details(char)
        assert "Gandalf" in result
        assert "Level 5" in result
        assert "STR 10" in result
        assert "INT 18" in result
        assert "Mysterious" in result


class TestFormatSessionContext:
    async def test_with_location(self):
        session = MagicMock()
        session.current_location = "Dark Forest"
        result = await ContextTransferService._format_session_context(session)
        assert "Dark Forest" in result

    async def test_without_location(self):
        session = MagicMock()
        session.current_location = None
        result = await ContextTransferService._format_session_context(session)
        assert "CURRENT SESSION" in result


class TestFormatRecentEvents:
    async def test_formats_memories(self):
        mem = MagicMock()
        mem.event_type.value = "combat"
        mem.content = "Battle with goblins"
        mem.npcs_involved = ["Goblin Chief"]

        result = await ContextTransferService._format_recent_events([mem])
        assert "Battle with goblins" in result
        assert "Goblin Chief" in result


class TestGenerateSessionSummary:
    @patch("app.services.context_transfer.MemoryService")
    async def test_summary_generation(self, mock_mem_svc):
        mock_mem_svc.get_recent_memories = AsyncMock(return_value=[])

        db = AsyncMock()
        # Mock the session query
        mock_result = MagicMock()
        session_obj = MagicMock()
        session_obj.current_location = "Tavern"
        mock_result.scalar_one_or_none.return_value = session_obj
        db.execute = AsyncMock(return_value=mock_result)

        char = MagicMock()
        char.name = "Frodo"
        char.level = 1
        char.race = "Halfling"
        char.class_name = "Rogue"
        char.personality = None
        char.current_hp = 8
        char.max_hp = 8
        char.strength = 8
        char.dexterity = 16
        char.constitution = 12
        char.intelligence = 10
        char.wisdom = 14
        char.charisma = 10

        result = await ContextTransferService.generate_session_summary(
            db=db, session_id=uuid.uuid4(), character=char
        )
        assert "ADVENTURE SUMMARY" in result
        assert "Frodo" in result

    @patch("app.services.context_transfer.MemoryService")
    async def test_summary_error_fallback(self, mock_mem_svc):
        mock_mem_svc.get_recent_memories = AsyncMock(side_effect=RuntimeError("db err"))

        db = AsyncMock()
        char = MagicMock()

        result = await ContextTransferService.generate_session_summary(
            db=db, session_id=uuid.uuid4(), character=char
        )
        assert "ADVENTURE SUMMARY" in result


# ============================================================================
# ContextWindowManager
# ============================================================================


class TestContextWindowManagerCountTokens:
    def test_count_empty(self):
        mgr = ContextWindowManager()
        assert mgr.count_tokens("") == 0

    def test_count_nonempty(self):
        mgr = ContextWindowManager()
        count = mgr.count_tokens("Hello world")
        assert count > 0

    def test_count_messages_tokens(self):
        mgr = ContextWindowManager()
        msgs = [
            {"role": "system", "content": "You are a DM."},
            {"role": "user", "content": "I look around."},
        ]
        total = mgr.count_messages_tokens(msgs)
        assert total > 0

    def test_fallback_counting(self):
        mgr = ContextWindowManager()
        mgr.encoder = None  # force fallback
        assert mgr.count_tokens("abcdefgh") == 2  # 8 chars / 4


class TestPruneMessages:
    def test_no_pruning_needed(self):
        mgr = ContextWindowManager()
        msgs = [{"role": "user", "content": "hi"}]
        pruned, removed = mgr.prune_messages(msgs, max_tokens=99999)
        assert pruned == msgs
        assert removed == 0

    def test_empty_messages(self):
        mgr = ContextWindowManager()
        pruned, removed = mgr.prune_messages([])
        assert pruned == []
        assert removed == 0

    def test_prunes_middle_messages(self):
        mgr = ContextWindowManager()
        msgs = [{"role": "system", "content": "sys"}]
        # Add many messages to exceed a small token limit
        for i in range(50):
            msgs.append({"role": "user", "content": f"Message number {i} " * 20})

        pruned, removed = mgr.prune_messages(msgs, max_tokens=500, keep_recent=3)
        assert len(pruned) < len(msgs)
        assert removed > 0
        assert pruned[0]["role"] == "system"
        # Last 3 should be preserved
        assert pruned[-1] == msgs[-1]
        assert pruned[-2] == msgs[-2]
        assert pruned[-3] == msgs[-3]

    def test_emergency_pruning(self):
        """When system + recent exceed limit, keep only system + last."""
        mgr = ContextWindowManager()
        msgs = [
            {"role": "system", "content": "x" * 10000},
            {"role": "user", "content": "y" * 10000},
            {"role": "user", "content": "z" * 10000},
        ]
        pruned, removed = mgr.prune_messages(msgs, max_tokens=50, keep_recent=2)
        # Should fallback to emergency mode: system + last message
        assert len(pruned) <= 3


class TestContextStats:
    def test_stats_structure(self):
        mgr = ContextWindowManager()
        msgs = [{"role": "user", "content": "hello"}]
        stats = mgr.get_context_stats(msgs)
        assert "total_tokens" in stats
        assert "max_tokens" in stats
        assert "remaining_tokens" in stats
        assert "usage_percent" in stats
        assert "message_count" in stats
        assert stats["message_count"] == 1

    def test_system_message_count(self):
        mgr = ContextWindowManager()
        msgs = [
            {"role": "system", "content": "a"},
            {"role": "system", "content": "b"},
            {"role": "user", "content": "c"},
        ]
        stats = mgr.get_context_stats(msgs)
        assert stats["system_message_count"] == 2
