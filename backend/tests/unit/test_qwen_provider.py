"""
Tests for the Qwen (Alibaba Cloud DashScope) provider.

Same OpenAI-compatible structure as groq/cerebras/sambanova/together,
plus additional set_model/get_model/get_available_models methods.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIError
from openai import RateLimitError as OpenAIRateLimitError

from app.services.ai_provider import (
    ProviderStatus,
    ProviderUnavailableError,
    RateLimitError,
)
from app.services.qwen_provider import QwenProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_KWARGS = {"api_key": "test-key", "model": "qwen-max"}


def _make_provider(**overrides):
    provider = QwenProvider(**{**DEFAULT_KWARGS, **overrides})
    provider.client = MagicMock()
    provider.client.chat.completions.create = AsyncMock()
    return provider


def _mock_response(content="Generated text"):
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    return resp


def _mock_openai_rate_limit_error():
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "rate limit"}}
    return OpenAIRateLimitError(
        message="Rate limit exceeded",
        response=mock_response,
        body={"error": {"message": "rate limit"}},
    )


def _mock_api_error():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "server error"}}
    return APIError(
        message="Internal server error",
        request=MagicMock(),
        body={"error": {"message": "server error"}},
    )


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestInit:
    def test_default_attributes(self):
        provider = QwenProvider(api_key="k", model="qwen-max")
        assert provider.name == "qwen"
        assert provider.model == "qwen-max"
        assert provider.default_max_tokens == 2048
        assert provider.default_temperature == 0.6
        assert provider.priority == 1
        assert provider._status == ProviderStatus.AVAILABLE

    def test_custom_params(self):
        provider = QwenProvider(
            api_key="k",
            model="qwen-turbo",
            max_tokens=4096,
            temperature=0.9,
            priority=5,
        )
        assert provider.default_max_tokens == 4096
        assert provider.default_temperature == 0.9
        assert provider.priority == 5


# ---------------------------------------------------------------------------
# generate_narration
# ---------------------------------------------------------------------------


class TestGenerateNarration:
    async def test_success(self):
        provider = _make_provider()
        provider.client.chat.completions.create.return_value = _mock_response("Once upon a time")

        result = await provider.generate_narration("Tell a story")

        assert result == "Once upon a time"
        call_kwargs = provider.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["messages"] == [{"role": "user", "content": "Tell a story"}]

    async def test_passes_custom_params(self):
        provider = _make_provider()
        provider.client.chat.completions.create.return_value = _mock_response("ok")

        await provider.generate_narration("p", max_tokens=100, temperature=0.2)

        call_kwargs = provider.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 100
        assert call_kwargs["temperature"] == 0.2


# ---------------------------------------------------------------------------
# generate_chat
# ---------------------------------------------------------------------------


class TestGenerateChat:
    async def test_success(self):
        provider = _make_provider()
        provider.client.chat.completions.create.return_value = _mock_response("Hello adventurer")

        result = await provider.generate_chat([{"role": "user", "content": "Hi"}])

        assert result == "Hello adventurer"
        assert provider._status == ProviderStatus.AVAILABLE

    async def test_defaults_when_none(self):
        provider = _make_provider()
        provider.client.chat.completions.create.return_value = _mock_response("ok")

        await provider.generate_chat([{"role": "user", "content": "x"}])

        call_kwargs = provider.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.6

    async def test_rate_limit_error(self):
        provider = _make_provider()
        provider.client.chat.completions.create.side_effect = _mock_openai_rate_limit_error()

        with pytest.raises(RateLimitError):
            await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.RATE_LIMITED

    async def test_rate_limit_retry_after_is_none_by_default(self):
        """Qwen uses getattr(e, 'retry_after', None) without a fallback."""
        provider = _make_provider()
        provider.client.chat.completions.create.side_effect = _mock_openai_rate_limit_error()

        with pytest.raises(RateLimitError) as exc_info:
            await provider.generate_chat([{"role": "user", "content": "x"}])

        # Qwen doesn't set a default retry_after — it passes the raw value
        assert exc_info.value.retry_after is None

    async def test_api_error(self):
        provider = _make_provider()
        provider.client.chat.completions.create.side_effect = _mock_api_error()

        with pytest.raises(ProviderUnavailableError):
            await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.ERROR

    async def test_generic_exception(self):
        provider = _make_provider()
        provider.client.chat.completions.create.side_effect = RuntimeError("boom")

        with pytest.raises(ProviderUnavailableError, match="boom"):
            await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.ERROR

    async def test_empty_response(self):
        provider = _make_provider()
        provider.client.chat.completions.create.return_value = _mock_response(None)

        with pytest.raises(ProviderUnavailableError, match="empty response"):
            await provider.generate_chat([{"role": "user", "content": "x"}])

    async def test_empty_string_response(self):
        provider = _make_provider()
        provider.client.chat.completions.create.return_value = _mock_response("")

        with pytest.raises(ProviderUnavailableError, match="empty response"):
            await provider.generate_chat([{"role": "user", "content": "x"}])

    async def test_passes_extra_kwargs(self):
        provider = _make_provider()
        provider.client.chat.completions.create.return_value = _mock_response("ok")

        await provider.generate_chat(
            [{"role": "user", "content": "x"}], tools=[{"type": "function"}]
        )

        call_kwargs = provider.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["tools"] == [{"type": "function"}]


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------


class TestIsAvailable:
    async def test_available_by_default(self):
        provider = QwenProvider(api_key="k", model="m")
        assert await provider.is_available() is True

    async def test_unavailable_treated_as_available(self):
        provider = QwenProvider(api_key="k", model="m")
        provider.set_status(ProviderStatus.UNAVAILABLE)
        assert await provider.is_available() is True

    async def test_rate_limited_not_available(self):
        provider = QwenProvider(api_key="k", model="m")
        provider.set_status(ProviderStatus.RATE_LIMITED)
        assert await provider.is_available() is False

    async def test_error_not_available(self):
        provider = QwenProvider(api_key="k", model="m")
        provider.set_status(ProviderStatus.ERROR)
        assert await provider.is_available() is False


# ---------------------------------------------------------------------------
# set_model / get_model
# ---------------------------------------------------------------------------


class TestModelManagement:
    def test_set_model(self):
        provider = QwenProvider(api_key="k", model="qwen-max")
        provider.set_model("qwen-turbo")
        assert provider.model == "qwen-turbo"

    def test_get_model(self):
        provider = QwenProvider(api_key="k", model="qwen-plus")
        assert provider.get_model() == "qwen-plus"

    def test_set_model_updates_get_model(self):
        provider = QwenProvider(api_key="k", model="qwen-max")
        provider.set_model("qwen-plus")
        assert provider.get_model() == "qwen-plus"


# ---------------------------------------------------------------------------
# get_available_models
# ---------------------------------------------------------------------------


class TestGetAvailableModels:
    @patch("app.services.qwen_provider.get_model_discovery_service")
    async def test_delegates_to_discovery_service(self, mock_get_svc):
        mock_svc = MagicMock()
        mock_svc.discover_models = AsyncMock(return_value=["qwen-max", "qwen-turbo", "qwen-plus"])
        mock_get_svc.return_value = mock_svc

        provider = QwenProvider(api_key="k", model="qwen-max")
        models = await provider.get_available_models()

        assert models == ["qwen-max", "qwen-turbo", "qwen-plus"]
        mock_svc.discover_models.assert_awaited_once_with("qwen")


# ---------------------------------------------------------------------------
# Status management
# ---------------------------------------------------------------------------


class TestStatus:
    def test_set_status_with_error(self):
        provider = QwenProvider(api_key="k", model="m")
        provider.set_status(ProviderStatus.ERROR, "oops")
        assert provider._status == ProviderStatus.ERROR
        assert provider.get_last_error() == "oops"

    async def test_successful_call_resets_status(self):
        provider = _make_provider()
        provider.set_status(ProviderStatus.ERROR, "old")
        provider.client.chat.completions.create.return_value = _mock_response("ok")

        await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.AVAILABLE
