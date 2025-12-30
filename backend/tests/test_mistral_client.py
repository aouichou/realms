"""
Tests for Mistral API client
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.mistral_client import (
    MistralClient,
    MistralAPIError,
    RateLimitError,
    get_mistral_client
)


@pytest.fixture
def mistral_client():
    """Create a Mistral client instance for testing"""
    with patch('app.services.mistral_client.Mistral'):
        client = MistralClient()
        return client


@pytest.mark.asyncio
async def test_rate_limiting(mistral_client):
    """Test that rate limiting works correctly"""
    import time
    
    # Record start time
    start_time = time.time()
    
    # Make two requests (should enforce rate limit)
    await mistral_client._wait_for_rate_limit()
    await mistral_client._wait_for_rate_limit()
    
    # Check that at least 1 second passed (rate limit is 1 req/sec)
    elapsed = time.time() - start_time
    assert elapsed >= 1.0, "Rate limiting did not enforce delay"


@pytest.mark.asyncio
async def test_chat_completion_success(mistral_client):
    """Test successful chat completion"""
    # Mock response
    mock_response = Mock()
    mock_response.usage.total_tokens = 50
    
    mistral_client.client.chat.complete = Mock(return_value=mock_response)
    
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = mock_response
        
        response = await mistral_client.chat_completion(messages)
        
        assert response == mock_response
        mock_thread.assert_called_once()


@pytest.mark.asyncio
async def test_chat_completion_rate_limit_error(mistral_client):
    """Test rate limit error handling"""
    mistral_client.client.chat.complete = Mock(
        side_effect=Exception("429 Rate limit exceeded")
    )
    
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("429 Rate limit exceeded")
        
        with pytest.raises(RateLimitError):
            await mistral_client.chat_completion(messages)


@pytest.mark.asyncio
async def test_chat_completion_generic_error(mistral_client):
    """Test generic API error handling"""
    mistral_client.client.chat.complete = Mock(
        side_effect=Exception("Network error")
    )
    
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("Network error")
        
        with pytest.raises(MistralAPIError):
            await mistral_client.chat_completion(messages)


def test_get_token_count(mistral_client):
    """Test token count estimation"""
    messages = [
        {"role": "user", "content": "Hello, how are you?"},  # ~20 chars
        {"role": "assistant", "content": "I'm doing well!"}  # ~16 chars
    ]
    
    # Total ~36 chars, roughly 9 tokens
    estimated = mistral_client.get_token_count(messages)
    assert estimated > 0
    assert estimated < 20  # Should be reasonable estimate


def test_get_available_models(mistral_client):
    """Test that available models are returned"""
    models = mistral_client.get_available_models()
    
    assert isinstance(models, list)
    assert len(models) > 0
    assert "mistral-small-latest" in models


def test_get_model_info(mistral_client):
    """Test model info retrieval"""
    info = mistral_client.get_model_info()
    
    assert "model" in info
    assert "max_tokens" in info
    assert "temperature" in info
    assert "rate_limit" in info


def test_get_mistral_client_singleton():
    """Test that get_mistral_client returns singleton"""
    with patch('app.services.mistral_client.Mistral'):
        client1 = get_mistral_client()
        client2 = get_mistral_client()
        
        assert client1 is client2, "Should return same instance"


@pytest.mark.asyncio
async def test_streaming_chat_completion(mistral_client):
    """Test streaming chat completion"""
    # Mock streaming response
    mock_chunk1 = Mock()
    mock_chunk1.data.choices = [Mock()]
    mock_chunk1.data.choices[0].delta.content = "Hello "
    
    mock_chunk2 = Mock()
    mock_chunk2.data.choices = [Mock()]
    mock_chunk2.data.choices[0].delta.content = "World"
    
    mock_stream = [mock_chunk1, mock_chunk2]
    
    messages = [{"role": "user", "content": "Say hello"}]
    
    with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = mock_stream
        
        chunks = []
        async for chunk in mistral_client.chat_completion_stream(messages):
            chunks.append(chunk)
        
        assert chunks == ["Hello ", "World"]
