"""
Tests for OpenAI-compatible providers: Groq, Cerebras, SambaNova, Together.

All four providers share the same structure (AsyncOpenAI client), so we use
pytest.mark.parametrize to run the same test logic against each provider class.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import APIError
from openai import RateLimitError as OpenAIRateLimitError

from app.services.ai_provider import (
    ProviderStatus,
    ProviderUnavailableError,
    RateLimitError,
)
from app.services.cerebras_provider import CerebrasProvider
from app.services.groq_provider import GroqProvider
from app.services.sambanova_provider import SambanovaProvider
from app.services.together_provider import TogetherProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROVIDERS = [
    pytest.param(
        GroqProvider,
        {"api_key": "test-key", "model": "llama-3-70b"},
        "groq",
        3600,  # default retry_after
        id="groq",
    ),
    pytest.param(
        CerebrasProvider,
        {"api_key": "test-key", "model": "llama-3-70b"},
        "cerebras",
        60,
        id="cerebras",
    ),
    pytest.param(
        SambanovaProvider,
        {"api_key": "test-key", "model": "llama-3-70b"},
        "sambanova",
        60,
        id="sambanova",
    ),
    pytest.param(
        TogetherProvider,
        {"api_key": "test-key", "model": "llama-3-70b"},
        "together",
        3600,
        id="together",
    ),
]


def _make_provider(cls, kwargs):
    """Instantiate a provider and replace its real client with a mock."""
    provider = cls(**kwargs)
    provider.client = MagicMock()
    provider.client.chat.completions.create = AsyncMock()
    return provider


def _mock_response(content: str = "Generated text"):
    """Build a mock ChatCompletion response."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    return resp


def _mock_openai_rate_limit_error():
    """Create a mock OpenAI RateLimitError."""
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
    """Create a mock OpenAI APIError."""
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
# Tests
# ---------------------------------------------------------------------------


class TestInit:
    @pytest.mark.parametrize("cls,kwargs,expected_name,_retry", PROVIDERS)
    def test_attributes(self, cls, kwargs, expected_name, _retry):
        provider = cls(**kwargs)
        assert provider.name == expected_name
        assert provider.model == kwargs["model"]
        assert provider.default_max_tokens == 2048
        assert provider.default_temperature == 0.7
        assert provider._status == ProviderStatus.AVAILABLE

    @pytest.mark.parametrize("cls,kwargs,expected_name,_retry", PROVIDERS)
    def test_custom_priority(self, cls, kwargs, expected_name, _retry):
        provider = cls(**{**kwargs, "priority": 10})
        assert provider.priority == 10

    @pytest.mark.parametrize("cls,kwargs,expected_name,_retry", PROVIDERS)
    def test_custom_max_tokens_temperature(self, cls, kwargs, expected_name, _retry):
        provider = cls(**{**kwargs, "max_tokens": 4096, "temperature": 0.9})
        assert provider.default_max_tokens == 4096
        assert provider.default_temperature == 0.9


class TestGenerateNarration:
    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_success(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.return_value = _mock_response("Once upon a time")

        result = await provider.generate_narration("Tell a story")

        assert result == "Once upon a time"
        provider.client.chat.completions.create.assert_awaited_once()
        call_kwargs = provider.client.chat.completions.create.call_args
        assert call_kwargs.kwargs["messages"] == [{"role": "user", "content": "Tell a story"}]

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_custom_params(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.return_value = _mock_response("ok")

        await provider.generate_narration("prompt", max_tokens=100, temperature=0.2)

        call_kwargs = provider.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 100
        assert call_kwargs["temperature"] == 0.2


class TestGenerateChat:
    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_success(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.return_value = _mock_response("Hello adventurer")
        messages = [{"role": "user", "content": "Hi"}]

        result = await provider.generate_chat(messages)

        assert result == "Hello adventurer"
        assert provider._status == ProviderStatus.AVAILABLE

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_uses_defaults_when_none(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.return_value = _mock_response("ok")

        await provider.generate_chat([{"role": "user", "content": "x"}])

        call_kwargs = provider.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == provider.default_max_tokens
        assert call_kwargs["temperature"] == provider.default_temperature

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_rate_limit_error(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.side_effect = _mock_openai_rate_limit_error()

        with pytest.raises(RateLimitError):
            await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.RATE_LIMITED

    @pytest.mark.parametrize("cls,kwargs,_name,default_retry", PROVIDERS)
    async def test_rate_limit_default_retry_after(self, cls, kwargs, _name, default_retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.side_effect = _mock_openai_rate_limit_error()

        with pytest.raises(RateLimitError) as exc_info:
            await provider.generate_chat([{"role": "user", "content": "x"}])

        assert exc_info.value.retry_after == default_retry

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_api_error(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.side_effect = _mock_api_error()

        with pytest.raises(ProviderUnavailableError):
            await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.ERROR

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_generic_exception(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.side_effect = RuntimeError("something broke")

        with pytest.raises(ProviderUnavailableError, match="something broke"):
            await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.ERROR
        assert provider._last_error is not None

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_empty_response(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.return_value = _mock_response(None)

        with pytest.raises(ProviderUnavailableError, match="empty response"):
            await provider.generate_chat([{"role": "user", "content": "x"}])

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_empty_string_response(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.return_value = _mock_response("")

        with pytest.raises(ProviderUnavailableError, match="empty response"):
            await provider.generate_chat([{"role": "user", "content": "x"}])

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_passes_extra_kwargs(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.client.chat.completions.create.return_value = _mock_response("ok")

        await provider.generate_chat(
            [{"role": "user", "content": "x"}],
            tools=[{"type": "function"}],
        )

        call_kwargs = provider.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["tools"] == [{"type": "function"}]


class TestIsAvailable:
    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_available_by_default(self, cls, kwargs, _name, _retry):
        provider = cls(**kwargs)
        assert await provider.is_available() is True

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_unavailable_status_is_treated_as_available(self, cls, kwargs, _name, _retry):
        provider = cls(**kwargs)
        provider.set_status(ProviderStatus.UNAVAILABLE)
        assert await provider.is_available() is True

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_rate_limited_not_available(self, cls, kwargs, _name, _retry):
        provider = cls(**kwargs)
        provider.set_status(ProviderStatus.RATE_LIMITED)
        assert await provider.is_available() is False

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_error_not_available(self, cls, kwargs, _name, _retry):
        provider = cls(**kwargs)
        provider.set_status(ProviderStatus.ERROR)
        assert await provider.is_available() is False


class TestStatusManagement:
    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    def test_set_status_with_error(self, cls, kwargs, _name, _retry):
        provider = cls(**kwargs)
        provider.set_status(ProviderStatus.ERROR, "something went wrong")
        assert provider._status == ProviderStatus.ERROR
        assert provider.get_last_error() == "something went wrong"

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_get_status(self, cls, kwargs, _name, _retry):
        provider = cls(**kwargs)
        assert await provider.get_status() == ProviderStatus.AVAILABLE

    @pytest.mark.parametrize("cls,kwargs,_name,_retry", PROVIDERS)
    async def test_successful_call_resets_status(self, cls, kwargs, _name, _retry):
        provider = _make_provider(cls, kwargs)
        provider.set_status(ProviderStatus.ERROR, "old error")
        provider.client.chat.completions.create.return_value = _mock_response("ok")

        await provider.generate_chat([{"role": "user", "content": "x"}])

        assert provider._status == ProviderStatus.AVAILABLE
