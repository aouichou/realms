"""Tests for adaptive_narration_service, message_summarizer, summarization_service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# AdaptiveNarrationService
# ============================================================================


@pytest.fixture(autouse=True)
def _patch_image_detection(monkeypatch):
    """Prevent real model loading."""
    monkeypatch.setattr(
        "app.services.adaptive_narration_service.ImageDetectionService",
        MagicMock,
    )


def _make_narration_service():
    from app.services.adaptive_narration_service import AdaptiveNarrationService

    svc = AdaptiveNarrationService.__new__(AdaptiveNarrationService)
    svc.embedding_service = None
    svc._action_embeddings = {}
    return svc


class TestAdaptiveNarrationGenerate:
    def test_non_roll_tool_returns_generic(self):
        svc = _make_narration_service()
        assert svc.generate_narration("give_item", {}) == "You take action."

    def test_roll_without_embedding_service(self):
        svc = _make_narration_service()
        result = svc.generate_narration(
            "request_player_roll",
            {"ability_or_skill": "Perception", "description": "scanning the room"},
        )
        # Without embedding service, falls back to "generic" action type
        assert isinstance(result, str)
        assert len(result) > 0

    def test_saving_throw_returns_save_template(self):
        svc = _make_narration_service()
        result = svc.generate_narration(
            "request_player_roll",
            {
                "ability_or_skill": "Wisdom",
                "description": "resist charm",
                "roll_type": "saving_throw",
            },
        )
        # Should pick from save templates
        assert isinstance(result, str)
        assert len(result) > 5

    def test_get_action_type_no_model(self):
        svc = _make_narration_service()
        assert svc._get_action_type("search the room", "Investigation") == "generic"


class TestCleanDescription:
    def test_removes_gerund(self):
        from app.services.adaptive_narration_service import AdaptiveNarrationService

        assert "the signpost" in AdaptiveNarrationService._clean_description_for_template(
            "examining the signpost"
        )

    def test_keeps_preposition(self):
        from app.services.adaptive_narration_service import AdaptiveNarrationService

        result = AdaptiveNarrationService._clean_description_for_template("checking for footprints")
        assert "for footprints" in result

    def test_empty_input(self):
        from app.services.adaptive_narration_service import AdaptiveNarrationService

        assert AdaptiveNarrationService._clean_description_for_template("") == ""

    def test_no_gerund(self):
        from app.services.adaptive_narration_service import AdaptiveNarrationService

        result = AdaptiveNarrationService._clean_description_for_template("the old bridge")
        assert result == "the old bridge"


# ============================================================================
# MessageSummarizer
# ============================================================================


class TestMessageSummarizer:
    def _make_messages(self, count: int):
        msgs = [{"role": "system", "content": "You are a DM."}]
        for i in range(count - 1):
            role = "user" if i % 2 == 0 else "assistant"
            msgs.append({"role": role, "content": f"Message {i}"})
        return msgs

    async def test_no_summarization_below_threshold(self):
        from app.services.message_summarizer import MessageSummarizer

        ms = MessageSummarizer()
        msgs = self._make_messages(5)
        result = await ms.summarize_if_needed(msgs)
        assert result == msgs  # unchanged

    @patch("app.services.message_summarizer.TokenCounter")
    @patch("app.services.message_summarizer.provider_selector")
    async def test_no_summarization_under_token_limit(self, mock_prov, mock_tc):
        from app.services.message_summarizer import MessageSummarizer

        mock_tc.count_message_tokens = MagicMock(return_value=5000)
        mock_tc.count_tokens = MagicMock(return_value=0)

        ms = MessageSummarizer()
        ms.token_counter = mock_tc
        msgs = self._make_messages(25)
        result = await ms.summarize_if_needed(msgs)
        assert result == msgs

    @patch("app.services.message_summarizer.TokenCounter")
    @patch("app.services.message_summarizer.provider_selector")
    async def test_summarization_when_over_limit(self, mock_prov, mock_tc):
        from app.services.message_summarizer import MessageSummarizer

        mock_tc.count_message_tokens = MagicMock(return_value=30000)
        mock_tc.count_tokens = MagicMock(return_value=0)
        mock_tc.truncate_to_fit = MagicMock(side_effect=lambda m, _: m[-5:])

        mock_prov.generate_chat = AsyncMock(return_value="Summary of events")

        ms = MessageSummarizer()
        ms.provider = mock_prov
        ms.token_counter = mock_tc

        msgs = self._make_messages(25)
        result = await ms.summarize_if_needed(msgs)
        # Should be: system msg + summary msg + recent messages
        assert len(result) < len(msgs)
        assert result[0]["role"] == "system"
        assert "SUMMARY" in result[1]["content"]

    def test_format_messages(self):
        from app.services.message_summarizer import MessageSummarizer

        ms = MessageSummarizer()
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        formatted = ms._format_messages(msgs)
        assert "Player: [MSG]hello[/MSG]" in formatted
        assert "DM: world" in formatted  # DM messages not wrapped
        assert "sys" not in formatted  # system skipped

    def test_fallback_summary(self):
        from app.services.message_summarizer import MessageSummarizer

        ms = MessageSummarizer()
        msgs = [
            {"role": "user", "content": "attack"},
            {"role": "assistant", "content": "you strike"},
        ]
        result = ms._fallback_summary(msgs)
        assert "Player took 1 actions" in result
        assert "DM provided 1 responses" in result

    def test_fallback_summary_empty(self):
        from app.services.message_summarizer import MessageSummarizer

        ms = MessageSummarizer()
        assert ms._fallback_summary([]) == "Earlier conversation"


# ============================================================================
# SummarizationService
# ============================================================================


class TestSummarizationService:
    def test_should_summarize_below_threshold(self):
        from app.services.summarization_service import SummarizationService

        assert SummarizationService.should_summarize(5) is False

    def test_should_summarize_above_threshold(self):
        from app.services.summarization_service import SummarizationService

        assert SummarizationService.should_summarize(15) is True

    def test_should_summarize_custom_threshold(self):
        from app.services.summarization_service import SummarizationService

        assert SummarizationService.should_summarize(5, threshold=3) is True
        assert SummarizationService.should_summarize(2, threshold=3) is False

    def test_format_messages_as_summary_empty(self):
        from app.services.summarization_service import SummarizationService

        assert SummarizationService._format_messages_as_summary([]) == "No conversation history."

    def test_format_messages_as_summary(self):
        from app.services.summarization_service import SummarizationService

        msgs = [
            {"role": "user", "content": "I attack"},
            {"role": "assistant", "content": "You swing your sword"},
        ]
        result = SummarizationService._format_messages_as_summary(msgs)
        assert "Player: I attack" in result
        assert "DM: You swing your sword" in result

    def test_format_truncates_long_messages(self):
        from app.services.summarization_service import SummarizationService

        msgs = [{"role": "user", "content": "x" * 200}]
        result = SummarizationService._format_messages_as_summary(msgs)
        assert "..." in result

    @patch("app.services.summarization_service.get_mistral_client")
    async def test_summarize_conversation_empty(self, mock_client_fn):
        from app.services.summarization_service import SummarizationService

        result = await SummarizationService.summarize_conversation([])
        assert result == "No conversation history yet."

    @patch("app.services.summarization_service.get_mistral_client")
    async def test_summarize_short_conversation(self, mock_client_fn):
        from app.services.summarization_service import SummarizationService

        msgs = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = await SummarizationService.summarize_conversation(msgs)
        assert "RECENT EVENTS" in result

    @patch("app.services.summarization_service.get_mistral_client")
    async def test_summarize_conversation_success(self, mock_client_fn):
        from app.services.summarization_service import SummarizationService

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Battle summary here"
        mock_client.chat_completion = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client

        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        result = await SummarizationService.summarize_conversation(msgs, "Gandalf")
        assert result == "Battle summary here"

    @patch("app.services.summarization_service.get_mistral_client")
    async def test_summarize_conversation_error_fallback(self, mock_client_fn):
        from app.services.summarization_service import SummarizationService

        mock_client = MagicMock()
        mock_client.chat_completion = AsyncMock(side_effect=RuntimeError("fail"))
        mock_client_fn.return_value = mock_client

        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        result = await SummarizationService.summarize_conversation(msgs)
        assert "RECENT EVENTS" in result

    @patch("app.services.summarization_service.get_mistral_client")
    async def test_get_summarized_context_short(self, mock_client_fn):
        from app.services.summarization_service import SummarizationService

        msgs = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
        summary, recent = await SummarizationService.get_summarized_context(msgs)
        assert summary == ""
        assert recent == msgs

    @patch("app.services.summarization_service.get_mistral_client")
    async def test_get_summarized_context_splits(self, mock_client_fn):
        from app.services.summarization_service import SummarizationService

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary text"
        mock_client.chat_completion = AsyncMock(return_value=mock_response)
        mock_client_fn.return_value = mock_client

        msgs = [{"role": "user", "content": f"msg {i}"} for i in range(15)]
        summary, recent = await SummarizationService.get_summarized_context(msgs, keep_recent=3)
        assert summary == "Summary text"
        assert len(recent) == 3
