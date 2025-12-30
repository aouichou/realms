"""
Integration tests for Mistral API
These tests make real API calls and require a valid API key
Run with: pytest tests/test_integration.py --integration
"""
import pytest
from app.services.mistral_client import get_mistral_client, RateLimitError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_mistral_api_call():
    """Test real API call to Mistral"""
    client = get_mistral_client()
    
    messages = [
        {"role": "user", "content": "Say 'Hello, adventurer!' in a fantasy style."}
    ]
    
    response = await client.chat_completion(messages)
    
    assert response is not None
    assert response.choices is not None
    assert len(response.choices) > 0
    assert response.choices[0].message.content is not None
    
    print(f"\n✅ Mistral API Response: {response.choices[0].message.content}")
    print(f"   Tokens used: {response.usage.total_tokens}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_mistral_streaming():
    """Test real streaming API call to Mistral"""
    client = get_mistral_client()
    
    messages = [
        {"role": "user", "content": "Count from 1 to 5."}
    ]
    
    chunks = []
    async for chunk in client.chat_completion_stream(messages):
        chunks.append(chunk)
        print(chunk, end="", flush=True)
    
    print()  # New line after streaming
    
    assert len(chunks) > 0
    full_response = "".join(chunks)
    assert len(full_response) > 0
    
    print(f"\n✅ Streaming completed: {len(chunks)} chunks received")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_estimation():
    """Test token count estimation"""
    client = get_mistral_client()
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there! How can I help you?"}
    ]
    
    estimated = client.get_token_count(messages)
    
    print(f"\n✅ Estimated tokens: {estimated}")
    assert estimated > 0
