"""
Tests for the Mistral AI provider.

Unlike the OpenAI-compatible providers, MistralProvider uses the ``mistralai``
client (sync, wrapped with ``asyncio.to_thread``) and has rate-limit cooldown,
streaming, tracing, and metric recording logic.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_provider import (
    ProviderStatus,
    ProviderUnavailableError,
    RateLimitError,
)
from app.services.mistral_provider import MistralProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_KWARGS = {
    "api_key": "test-key",
    "model": "mistral-small-latest",
}


def _make_provider(**overrides):
    """Create a MistralProvider and replace its client with a MagicMock."""
    provider = MistralProvider(**{**DEFAULT_KWARGS, **overrides})
    provider.client = MagicMock()
    # Reset timestamps so rate-limit wait is a no-op
    provider.last_request_time = 0.0
    return provider


def _mock_response(content="Generated text", usage=True):
    """Build a mock ChatCompletionResponse."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    if usage:
        resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    else:
        resp.usage = None
    return resp


# Common patches applied to every test that calls generate_* methods.
_TRACE_PATCH = "app.services.mistral_provider.trace_llm_call"
_METRICS_PATCH = "app.services.mistral_provider.metrics"


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestInit:
    def test_default_attributes(self):
        provider = MistralProvider(api_key="k", model="m")
        assert provider.name == "mistral"
        assert provider.model == "m"
        assert provider.max_tokens == 2048
        assert provider.temperature == 0.7
        assert provider.rate_limit == 1.0
        assert provider.rate_limit_cooldown == 60
        assert provider.priority == 2
        assert provider._status == ProviderStatus.AVAILABLE
        assert provider._last_usage is None

    def test_custom_params(self):
        provider = MistralProvider(
            api_key="k",
            model="mistral-large-latest",
            max_tokens=4096,
            temperature=0.9,
            rate_limit=5.0,
            priority=1,
            rate_limit_cooldown=120,
        )
        assert provider.max_tokens == 4096
        assert provider.temperature == 0.9
        assert provider.rate_limit == 5.0
        assert provider.rate_limit_cooldown == 120


# ---------------------------------------------------------------------------
# _wait_for_rate_limit
# ---------------------------------------------------------------------------


class TestWaitForRateLimit:
    async def test_no_wait_on_first_call(self):
        provider = _make_provider()
        provider.rate_limit = 1.0
        provider.last_request_time = 0.0

        start = time.time()
        await provider._wait_for_rate_limit()
        elapsed = time.time() - start

        # Should not wait at all (last_request_time=0 is far in the past)
        assert elapsed < 0.1

    async def test_waits_when_called_too_fast(self):
        provider = _make_provider(rate_limit=10.0)  # 10 req/s → 0.1s interval
        provider.last_request_time = time.time()

        start = time.time()
        await provider._wait_for_rate_limit()
        elapsed = time.time() - start

        assert elapsed >= 0.05  # Should have waited ~0.1s


# ---------------------------------------------------------------------------
# generate_narration
# ---------------------------------------------------------------------------


class TestGenerateNarration:
    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_success(self, mock_trace_cls, mock_metrics):
        # Make trace_llm_call context manager return a mock span
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response("A dragon appeared")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            result = await provider.generate_narration("Describe a dragon")

        assert result == "A dragon appeared"
        assert provider._status == ProviderStatus.AVAILABLE
        mock_metrics.record_llm_request.assert_called_once()

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_records_usage(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response("text", usage=True)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            await provider.generate_narration("prompt")

        assert provider._last_usage == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
        mock_span.set_usage.assert_called_once_with(
            prompt_tokens=10, completion_tokens=20, total_tokens=30
        )

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_no_usage(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response("text", usage=False)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            await provider.generate_narration("prompt")

        assert provider._last_usage is None

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_empty_response_raises(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response(None)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            with pytest.raises(ProviderUnavailableError):
                await provider.generate_narration("prompt")

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_list_content_extracted(self, mock_trace_cls, mock_metrics):
        """v2: list content is handled by extract_text_content, not rejected."""
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response("text")
        mock_resp.choices[0].message.content = ["chunk1", "chunk2"]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            result = await provider.generate_narration("prompt")

        assert result == "chunk1chunk2"

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_model_override_via_kwargs(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response("ok")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            await provider.generate_narration("prompt", model="mistral-large-latest")

        call_args = mock_thread.call_args
        assert call_args.kwargs.get("model") == "mistral-large-latest" or (
            len(call_args.args) > 2 and "mistral-large-latest" in str(call_args)
        )


# ---------------------------------------------------------------------------
# generate_narration — error handling
# ---------------------------------------------------------------------------


class TestGenerateNarrationErrors:
    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_rate_limit_by_message(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("rate_limit exceeded")
            with pytest.raises(RateLimitError):
                await provider.generate_narration("prompt")

        assert provider._status == ProviderStatus.RATE_LIMITED
        assert provider.rate_limited_at > 0

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_rate_limit_by_429(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("status 429 too many requests")
            with pytest.raises(RateLimitError):
                await provider.generate_narration("prompt")

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_rate_limit_retry_after(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider(rate_limit_cooldown=120)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("rate_limit error")
            with pytest.raises(RateLimitError) as exc_info:
                await provider.generate_narration("prompt")

        assert exc_info.value.retry_after == 120

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_generic_error(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("connection timeout")
            with pytest.raises(ProviderUnavailableError, match="connection timeout"):
                await provider.generate_narration("prompt")

        assert provider._status == ProviderStatus.ERROR
        mock_metrics.record_llm_request.assert_called_once()


# ---------------------------------------------------------------------------
# generate_chat
# ---------------------------------------------------------------------------


class TestGenerateChat:
    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_success(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response("Chat response")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            result = await provider.generate_chat([{"role": "user", "content": "Hello"}])

        assert result == "Chat response"
        assert provider._status == ProviderStatus.AVAILABLE

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_records_usage(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response("ok")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._last_usage == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_empty_response_raises(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response(None)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            with pytest.raises(ProviderUnavailableError):
                await provider.generate_chat([{"role": "user", "content": "x"}])

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_rate_limit_error(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("429 rate_limit")
            with pytest.raises(RateLimitError):
                await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.RATE_LIMITED

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_generic_error(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("network failure")
            with pytest.raises(ProviderUnavailableError, match="network failure"):
                await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.ERROR


# ---------------------------------------------------------------------------
# generate_chat_stream
# ---------------------------------------------------------------------------


class TestGenerateChatStream:
    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_success(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()

        # Build fake stream events
        event1 = MagicMock()
        event1.data.choices = [MagicMock()]
        event1.data.choices[0].delta.content = "Hello "
        event1.data.usage = None

        event2 = MagicMock()
        event2.data.choices = [MagicMock()]
        event2.data.choices[0].delta.content = "world"
        event2.data.usage = None

        event3 = MagicMock()
        event3.data.choices = []
        event3.data.usage = MagicMock(prompt_tokens=5, completion_tokens=2, total_tokens=7)

        provider.client.chat.stream.return_value = [event1, event2, event3]

        chunks = []
        async for chunk in provider.generate_chat_stream([{"role": "user", "content": "Hi"}]):
            chunks.append(chunk)

        assert chunks == ["Hello ", "world"]
        assert provider._status == ProviderStatus.AVAILABLE

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_records_usage_from_last_chunk(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()

        event = MagicMock()
        event.data.choices = [MagicMock()]
        event.data.choices[0].delta.content = "token"
        event.data.usage = MagicMock(prompt_tokens=8, completion_tokens=1, total_tokens=9)

        provider.client.chat.stream.return_value = [event]

        async for _ in provider.generate_chat_stream([{"role": "user", "content": "x"}]):
            pass

        assert provider._last_usage == {
            "prompt_tokens": 8,
            "completion_tokens": 1,
            "total_tokens": 9,
        }

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_rate_limit_error_in_stream(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        provider.client.chat.stream.side_effect = Exception("429 rate limited")

        with pytest.raises(RateLimitError):
            async for _ in provider.generate_chat_stream([{"role": "user", "content": "x"}]):
                pass

        assert provider._status == ProviderStatus.RATE_LIMITED

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_generic_error_in_stream(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        provider.client.chat.stream.side_effect = Exception("connection dropped")

        with pytest.raises(ProviderUnavailableError, match="connection dropped"):
            async for _ in provider.generate_chat_stream([{"role": "user", "content": "x"}]):
                pass

        assert provider._status == ProviderStatus.ERROR


# ---------------------------------------------------------------------------
# is_available (with cooldown logic)
# ---------------------------------------------------------------------------


class TestIsAvailable:
    async def test_available_by_default(self):
        provider = _make_provider()
        assert await provider.is_available() is True

    async def test_error_not_available(self):
        provider = _make_provider()
        provider.set_status(ProviderStatus.ERROR)
        assert await provider.is_available() is False

    async def test_rate_limited_not_available(self):
        provider = _make_provider()
        provider.set_status(ProviderStatus.RATE_LIMITED)
        provider.rate_limited_at = time.time()
        assert await provider.is_available() is False

    async def test_rate_limited_becomes_available_after_cooldown(self):
        provider = _make_provider(rate_limit_cooldown=1)
        provider.set_status(ProviderStatus.RATE_LIMITED)
        # Pretend rate limit happened 2 seconds ago
        provider.rate_limited_at = time.time() - 2

        available = await provider.is_available()

        assert available is True
        assert provider._status == ProviderStatus.AVAILABLE
        assert provider.rate_limited_at == 0.0

    async def test_rate_limited_still_in_cooldown(self):
        provider = _make_provider(rate_limit_cooldown=3600)
        provider.set_status(ProviderStatus.RATE_LIMITED)
        provider.rate_limited_at = time.time()

        assert await provider.is_available() is False

    async def test_rate_limited_without_timestamp(self):
        """rate_limited_at == 0 should be treated as unavailable."""
        provider = _make_provider()
        provider.set_status(ProviderStatus.RATE_LIMITED)
        provider.rate_limited_at = 0.0

        assert await provider.is_available() is False

    async def test_unavailable_status_not_available(self):
        """Unlike OpenAI-compatible providers, Mistral only returns True for AVAILABLE."""
        provider = _make_provider()
        provider.set_status(ProviderStatus.UNAVAILABLE)
        assert await provider.is_available() is False


# ---------------------------------------------------------------------------
# get_last_usage
# ---------------------------------------------------------------------------


class TestGetLastUsage:
    def test_none_initially(self):
        provider = _make_provider()
        assert provider.get_last_usage() is None

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_populated_after_call(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response("text", usage=True)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            await provider.generate_narration("prompt")

        usage = provider.get_last_usage()
        assert usage is not None
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 20
        assert usage["total_tokens"] == 30

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_none_when_no_usage_in_response(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        provider = _make_provider()
        mock_resp = _mock_response("text", usage=False)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            await provider.generate_narration("prompt")

        assert provider.get_last_usage() is None


# ---------------------------------------------------------------------------
# Status management
# ---------------------------------------------------------------------------


class TestStatusManagement:
    def test_set_status_with_error(self):
        provider = _make_provider()
        provider.set_status(ProviderStatus.ERROR, "boom")
        assert provider._status == ProviderStatus.ERROR
        assert provider.get_last_error() == "boom"

    async def test_get_status(self):
        provider = _make_provider()
        assert await provider.get_status() == ProviderStatus.AVAILABLE

    def test_repr(self):
        provider = _make_provider()
        r = repr(provider)
        assert "MistralProvider" in r
        assert "mistral" in r
