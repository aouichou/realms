"""Tests for app.services.provider_selector — provider selection & failover."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_provider import (
    AIProvider,
    ProviderStatus,
    ProviderUnavailableError,
    RateLimitError,
)
from app.services.provider_selector import ProviderSelector

# ---------------------------------------------------------------------------
# Helpers — lightweight mock provider
# ---------------------------------------------------------------------------


def _make_provider(name: str = "test", priority: int = 1, available: bool = True) -> MagicMock:
    """Return a MagicMock that satisfies the AIProvider interface."""
    p = MagicMock(spec=AIProvider)
    p.name = name
    p.priority = priority
    p._status = ProviderStatus.AVAILABLE if available else ProviderStatus.UNAVAILABLE
    p.is_available = AsyncMock(return_value=available)
    p.generate_narration = AsyncMock(return_value="narration from " + name)
    p.generate_chat = AsyncMock(return_value="chat from " + name)
    p.generate_chat_stream = AsyncMock()
    p.get_last_error = MagicMock(return_value=None)
    return p


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegisterProvider:
    def test_register_adds_provider(self):
        sel = ProviderSelector()
        p = _make_provider("alpha", priority=2)
        sel.register_provider(p)
        assert len(sel.providers) == 1
        assert sel.providers[0].name == "alpha"

    def test_register_sorts_by_priority(self):
        sel = ProviderSelector()
        sel.register_provider(_make_provider("low", priority=5))
        sel.register_provider(_make_provider("high", priority=1))
        sel.register_provider(_make_provider("mid", priority=3))
        assert [p.name for p in sel.providers] == ["high", "mid", "low"]

    def test_register_initialises_stats(self):
        sel = ProviderSelector()
        sel.register_provider(_make_provider("p1"))
        stats = sel.provider_stats["p1"]
        assert stats["requests"] == 0
        assert stats["successes"] == 0
        assert stats["failures"] == 0
        assert stats["context_transfers"] == 0


# ---------------------------------------------------------------------------
# select_provider
# ---------------------------------------------------------------------------


class TestSelectProvider:
    async def test_no_providers_raises(self):
        sel = ProviderSelector()
        with pytest.raises(ProviderUnavailableError):
            await sel.select_provider()

    async def test_selects_highest_priority(self):
        sel = ProviderSelector()
        sel.register_provider(_make_provider("low", priority=5))
        sel.register_provider(_make_provider("high", priority=1))
        p = await sel.select_provider()
        assert p.name == "high"

    async def test_falls_back_when_first_unavailable(self):
        sel = ProviderSelector()
        sel.register_provider(_make_provider("primary", priority=1, available=False))
        sel.register_provider(_make_provider("fallback", priority=2, available=True))
        p = await sel.select_provider()
        assert p.name == "fallback"

    async def test_all_unavailable_raises(self):
        sel = ProviderSelector()
        sel.register_provider(_make_provider("a", available=False))
        sel.register_provider(_make_provider("b", priority=2, available=False))
        with pytest.raises(ProviderUnavailableError):
            await sel.select_provider()

    async def test_tracks_switch(self):
        sel = ProviderSelector()
        p1 = _make_provider("first", priority=1)
        p2 = _make_provider("second", priority=2)
        sel.register_provider(p1)
        sel.register_provider(p2)

        # First selection — no switch yet
        await sel.select_provider()
        assert sel.current_provider.name == "first"

        # Make first unavailable, select again
        p1.is_available = AsyncMock(return_value=False)
        await sel.select_provider()
        assert sel.current_provider.name == "second"
        assert sel.last_provider_name == "first"
        assert sel.provider_stats["second"]["switches_to"] == 1


# ---------------------------------------------------------------------------
# generate_narration — failover & context transfer
# ---------------------------------------------------------------------------


class TestGenerateNarration:
    async def test_success(self):
        sel = ProviderSelector()
        sel.register_provider(_make_provider("ok"))
        result = await sel.generate_narration("prompt", 100, 0.7)
        assert "narration" in result

    async def test_failover_on_rate_limit(self):
        sel = ProviderSelector()
        bad = _make_provider("bad", priority=1)
        bad.generate_narration = AsyncMock(side_effect=RateLimitError("limit"))
        good = _make_provider("good", priority=2)
        sel.register_provider(bad)
        sel.register_provider(good)

        result = await sel.generate_narration("prompt", 100, 0.7)
        assert "narration from good" in result
        assert sel.provider_stats["bad"]["failures"] == 1
        assert sel.provider_stats["good"]["successes"] == 1

    async def test_failover_on_unavailable(self):
        sel = ProviderSelector()
        bad = _make_provider("bad", priority=1)
        bad.generate_narration = AsyncMock(side_effect=ProviderUnavailableError("down"))
        good = _make_provider("good", priority=2)
        sel.register_provider(bad)
        sel.register_provider(good)

        result = await sel.generate_narration("prompt", 100, 0.7)
        assert "good" in result

    async def test_failover_on_generic_exception(self):
        sel = ProviderSelector()
        bad = _make_provider("bad", priority=1)
        bad.generate_narration = AsyncMock(side_effect=RuntimeError("boom"))
        good = _make_provider("good", priority=2)
        sel.register_provider(bad)
        sel.register_provider(good)

        result = await sel.generate_narration("prompt", 100, 0.7)
        assert "good" in result

    async def test_all_fail_raises(self):
        sel = ProviderSelector()
        bad = _make_provider("only")
        bad.generate_narration = AsyncMock(side_effect=RuntimeError("boom"))
        sel.register_provider(bad)

        with pytest.raises(ProviderUnavailableError, match="All AI providers failed"):
            await sel.generate_narration("prompt", 100, 0.7)

    @patch("app.services.provider_selector.ContextTransferService")
    async def test_context_transfer_on_switch(self, mock_ctx_cls):
        """When provider switches mid-session, context transfer fires."""
        mock_ctx = mock_ctx_cls.return_value
        mock_ctx.generate_session_summary = AsyncMock(return_value="SUMMARY")

        sel = ProviderSelector()
        sel.context_transfer_service = mock_ctx

        # Create an "old" provider that is now unavailable
        old_p = _make_provider("old_provider")
        old_p.is_available = AsyncMock(return_value=False)
        sel.register_provider(old_p)

        # Current provider is the old one (simulates prior usage)
        sel.current_provider = old_p

        p = _make_provider("p1")
        sel.register_provider(p)

        db = AsyncMock()
        sid = uuid.uuid4()
        char = MagicMock()

        result = await sel.generate_narration(
            "prompt", 100, 0.7, db=db, session_id=sid, character=char
        )
        mock_ctx.generate_session_summary.assert_awaited_once()
        # Enhanced prompt should include the summary prefix
        call_kwargs = p.generate_narration.call_args
        assert "SUMMARY" in call_kwargs.kwargs.get(
            "prompt", call_kwargs.args[0] if call_kwargs.args else ""
        )


# ---------------------------------------------------------------------------
# generate_chat
# ---------------------------------------------------------------------------


class TestGenerateChat:
    async def test_success(self):
        sel = ProviderSelector()
        sel.register_provider(_make_provider("c1"))
        result = await sel.generate_chat([{"role": "user", "content": "hi"}], 100, 0.7)
        assert "chat" in result

    async def test_failover(self):
        sel = ProviderSelector()
        bad = _make_provider("bad", priority=1)
        bad.generate_chat = AsyncMock(side_effect=RateLimitError("nope"))
        good = _make_provider("good", priority=2)
        sel.register_provider(bad)
        sel.register_provider(good)

        result = await sel.generate_chat([{"role": "user", "content": "hi"}], 100, 0.7)
        assert "good" in result

    async def test_all_fail_raises(self):
        sel = ProviderSelector()
        bad = _make_provider("only")
        bad.generate_chat = AsyncMock(side_effect=RuntimeError("boom"))
        sel.register_provider(bad)

        with pytest.raises(ProviderUnavailableError):
            await sel.generate_chat([], 100, 0.7)


# ---------------------------------------------------------------------------
# generate_chat_stream
# ---------------------------------------------------------------------------


class TestGenerateChatStream:
    async def test_stream_success(self):
        sel = ProviderSelector()
        p = _make_provider("stream", priority=1)

        async def _fake_stream(**kwargs):
            for chunk in ["Hello", " world"]:
                yield chunk

        p.generate_chat_stream = _fake_stream
        sel.register_provider(p)

        chunks = []
        async for c in sel.generate_chat_stream([{"role": "user", "content": "hi"}], 100, 0.7):
            chunks.append(c)
        assert chunks == ["Hello", " world"]

    async def test_stream_failover(self):
        sel = ProviderSelector()
        bad = _make_provider("bad", priority=1)

        async def _fail_stream(**kwargs):
            raise RateLimitError("nope")
            yield  # make it a generator  # noqa: E501

        bad.generate_chat_stream = _fail_stream
        good = _make_provider("good", priority=2)

        async def _ok_stream(**kwargs):
            yield "ok"

        good.generate_chat_stream = _ok_stream
        sel.register_provider(bad)
        sel.register_provider(good)

        chunks = []
        async for c in sel.generate_chat_stream([], 100, 0.7):
            chunks.append(c)
        assert chunks == ["ok"]


# ---------------------------------------------------------------------------
# get_stats / get_current_provider
# ---------------------------------------------------------------------------


class TestStatsAndInfo:
    def test_get_stats_returns_dict(self):
        sel = ProviderSelector()
        sel.register_provider(_make_provider("x"))
        assert "x" in sel.get_stats()

    async def test_get_current_provider_initially_none(self):
        sel = ProviderSelector()
        assert sel.get_current_provider() is None

    async def test_get_current_provider_after_select(self):
        sel = ProviderSelector()
        sel.register_provider(_make_provider("prov"))
        await sel.select_provider()
        assert sel.get_current_provider().name == "prov"
