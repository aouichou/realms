"""
Tests for the MistralClient wrapper (``app.services.mistral_client``).

This is a separate client class from MistralProvider, used in other parts of
the codebase. It wraps the ``mistralai.Mistral`` SDK with rate limiting,
tracing, metrics, streaming, and a global singleton.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.mistral_client import (
    MistralAPIError,
    MistralClient,
    RateLimitError,
    get_mistral_client,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SETTINGS_PATCH = "app.services.mistral_client.settings"
_TRACE_PATCH = "app.services.mistral_client.trace_llm_call"
_METRICS_PATCH = "app.services.mistral_client.metrics"


def _make_client():
    """Create a MistralClient with mocked settings and replace the SDK client."""
    with patch(_SETTINGS_PATCH) as mock_settings:
        mock_settings.mistral_api_key = "test-key"
        mock_settings.mistral_model = "mistral-small-latest"
        mock_settings.mistral_max_tokens = 2048
        mock_settings.mistral_temperature = 0.7
        mock_settings.rate_limit_per_second = 100  # high limit → no wait in tests

        client = MistralClient()

    client.client = MagicMock()
    client.last_request_time = 0.0
    return client


def _mock_response(content="Generated text", usage=True):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    if usage:
        resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    else:
        resp.usage = None
    return resp


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestInit:
    @patch(_SETTINGS_PATCH)
    def test_reads_settings(self, mock_settings):
        mock_settings.mistral_api_key = "my-key"
        mock_settings.mistral_model = "mistral-large-latest"
        mock_settings.mistral_max_tokens = 4096
        mock_settings.mistral_temperature = 0.5
        mock_settings.rate_limit_per_second = 2

        client = MistralClient()

        assert client.model == "mistral-large-latest"
        assert client.max_tokens == 4096
        assert client.temperature == 0.5
        assert client.rate_limit == 2


# ---------------------------------------------------------------------------
# _wait_for_rate_limit
# ---------------------------------------------------------------------------


class TestWaitForRateLimit:
    async def test_no_wait_on_first_call(self):
        client = _make_client()
        client.last_request_time = 0.0

        start = time.time()
        await client._wait_for_rate_limit()
        elapsed = time.time() - start

        assert elapsed < 0.1

    async def test_enforces_minimum_interval(self):
        client = _make_client()
        client.rate_limit = 10.0  # 0.1s interval
        client.last_request_time = time.time()

        start = time.time()
        await client._wait_for_rate_limit()
        elapsed = time.time() - start

        assert elapsed >= 0.05


# ---------------------------------------------------------------------------
# chat_completion
# ---------------------------------------------------------------------------


class TestChatCompletion:
    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_success(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_client()
        mock_resp = _mock_response("Hello")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            result = await client.chat_completion([{"role": "user", "content": "Hi"}])

        assert result is mock_resp
        mock_thread.assert_awaited_once()

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_uses_default_model(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_client()
        mock_resp = _mock_response("ok")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            await client.chat_completion([{"role": "user", "content": "x"}])

        # The model passed to asyncio.to_thread should be the default
        call_kwargs = mock_thread.call_args
        # model is passed as a keyword arg to the underlying function
        assert "mistral-small-latest" in str(call_kwargs)

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_custom_params(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_client()
        mock_resp = _mock_response("ok")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            await client.chat_completion(
                [{"role": "user", "content": "x"}],
                model="mistral-large-latest",
                temperature=0.1,
                max_tokens=100,
            )

        call_str = str(mock_thread.call_args)
        assert "mistral-large-latest" in call_str

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_records_metrics_on_success(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_client()
        mock_resp = _mock_response("ok")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_resp
            await client.chat_completion([{"role": "user", "content": "x"}])

        mock_metrics.record_llm_request.assert_called_once()
        call_kwargs = mock_metrics.record_llm_request.call_args.kwargs
        assert call_kwargs["status"] == "success"

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_rate_limit_error(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_client()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("rate limit exceeded 429")
            with pytest.raises(RateLimitError):
                await client.chat_completion([{"role": "user", "content": "x"}])

        mock_metrics.record_llm_request.assert_called_once()
        call_kwargs = mock_metrics.record_llm_request.call_args.kwargs
        assert call_kwargs["status"] == "error"

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_generic_api_error(self, mock_trace_cls, mock_metrics):
        mock_span = MagicMock()
        mock_trace_cls.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_trace_cls.return_value.__exit__ = MagicMock(return_value=False)

        client = _make_client()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("connection timeout")
            with pytest.raises(MistralAPIError, match="Failed to get completion"):
                await client.chat_completion([{"role": "user", "content": "x"}])


# ---------------------------------------------------------------------------
# chat_completion_stream
# ---------------------------------------------------------------------------


class TestChatCompletionStream:
    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_success(self, mock_trace_cls, mock_metrics):
        client = _make_client()

        chunk1 = MagicMock()
        chunk1.data.choices = [MagicMock()]
        chunk1.data.choices[0].delta.content = "Hello"

        chunk2 = MagicMock()
        chunk2.data.choices = [MagicMock()]
        chunk2.data.choices[0].delta.content = " world"

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = [chunk1, chunk2]
            chunks = []
            async for c in client.chat_completion_stream([{"role": "user", "content": "Hi"}]):
                chunks.append(c)

        assert chunks == ["Hello", " world"]

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_non_string_content_converted(self, mock_trace_cls, mock_metrics):
        client = _make_client()

        chunk = MagicMock()
        chunk.data.choices = [MagicMock()]
        chunk.data.choices[0].delta.content = 42  # non-string

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = [chunk]
            chunks = []
            async for c in client.chat_completion_stream([{"role": "user", "content": "x"}]):
                chunks.append(c)

        assert chunks == ["42"]

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_rate_limit_error(self, mock_trace_cls, mock_metrics):
        client = _make_client()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("429 rate limit")
            with pytest.raises(RateLimitError):
                async for _ in client.chat_completion_stream([{"role": "user", "content": "x"}]):
                    pass

    @patch(_METRICS_PATCH)
    @patch(_TRACE_PATCH)
    async def test_generic_error(self, mock_trace_cls, mock_metrics):
        client = _make_client()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("network error")
            with pytest.raises(MistralAPIError, match="Failed to stream"):
                async for _ in client.chat_completion_stream([{"role": "user", "content": "x"}]):
                    pass


# ---------------------------------------------------------------------------
# get_token_count
# ---------------------------------------------------------------------------


class TestGetTokenCount:
    def test_basic_estimation(self):
        client = _make_client()
        messages = [{"role": "user", "content": "Hello world!!"}]  # 13 chars
        assert client.get_token_count(messages) == 13 // 4

    def test_multiple_messages(self):
        client = _make_client()
        messages = [
            {"role": "user", "content": "Hello"},  # 5 chars
            {"role": "assistant", "content": "Hi there"},  # 8 chars
        ]
        assert client.get_token_count(messages) == (5 + 8) // 4

    def test_empty_messages(self):
        client = _make_client()
        assert client.get_token_count([]) == 0

    def test_missing_content_key(self):
        client = _make_client()
        messages = [{"role": "user"}]
        assert client.get_token_count(messages) == 0


# ---------------------------------------------------------------------------
# get_available_models
# ---------------------------------------------------------------------------


class TestGetAvailableModels:
    def test_returns_known_models(self):
        client = _make_client()
        models = client.get_available_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "mistral-small-latest" in models
        assert "mistral-large-latest" in models

    def test_returns_list_of_strings(self):
        client = _make_client()
        models = client.get_available_models()
        assert all(isinstance(m, str) for m in models)


# ---------------------------------------------------------------------------
# get_model_info
# ---------------------------------------------------------------------------


class TestGetModelInfo:
    def test_returns_config_dict(self):
        client = _make_client()
        info = client.get_model_info()

        assert info["model"] == "mistral-small-latest"
        assert info["max_tokens"] == 2048
        assert info["temperature"] == 0.7
        assert "rate_limit" in info


# ---------------------------------------------------------------------------
# get_mistral_client (singleton)
# ---------------------------------------------------------------------------


class TestGetMistralClient:
    @patch(_SETTINGS_PATCH)
    def test_creates_singleton(self, mock_settings):
        mock_settings.mistral_api_key = "key"
        mock_settings.mistral_model = "m"
        mock_settings.mistral_max_tokens = 2048
        mock_settings.mistral_temperature = 0.7
        mock_settings.rate_limit_per_second = 1

        # Reset global
        import app.services.mistral_client as mc

        mc._mistral_client = None

        client1 = get_mistral_client()
        client2 = get_mistral_client()

        assert client1 is client2

        # Clean up
        mc._mistral_client = None

    @patch(_SETTINGS_PATCH)
    def test_returns_mistral_client_instance(self, mock_settings):
        mock_settings.mistral_api_key = "key"
        mock_settings.mistral_model = "m"
        mock_settings.mistral_max_tokens = 2048
        mock_settings.mistral_temperature = 0.7
        mock_settings.rate_limit_per_second = 1

        import app.services.mistral_client as mc

        mc._mistral_client = None

        client = get_mistral_client()
        assert isinstance(client, MistralClient)

        mc._mistral_client = None


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_rate_limit_is_api_error(self):
        assert issubclass(RateLimitError, MistralAPIError)

    def test_mistral_api_error_is_exception(self):
        assert issubclass(MistralAPIError, Exception)
