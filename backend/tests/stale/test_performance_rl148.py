"""
Performance test for RL-148: Response Time Investigation

Test actual DM response times to identify performance bottleneck.
"""

import time

import pytest

from app.services.dm_engine import DMEngine


@pytest.mark.asyncio
async def test_dm_response_timing():
    """
    Measure DM response time with different scenarios.

    This test helps identify:
    1. Baseline response time
    2. Impact of conversation history length
    3. Impact of memory context
    """
    dm_engine = DMEngine()

    # Test 1: Simple action, no history
    print("\n=== Test 1: Simple action, no history ===")
    start_time = time.time()
    result1 = await dm_engine.narrate(
        user_action="I look around the room",
        conversation_history=None,
        character_context={"name": "TestHero", "level": 1, "class": "Fighter"},
    )
    duration1 = time.time() - start_time
    print(f"Duration: {duration1:.2f}s")
    print(f"Response length: {len(result1['response'])} chars")
    print(f"Response: {result1['response'][:100]}...")

    # Test 2: With short conversation history (5 messages)
    print("\n=== Test 2: With short conversation history (5 messages) ===")
    short_history = [
        {"role": "user", "content": "I enter the dungeon"},
        {"role": "assistant", "content": "You step into a dark corridor..."},
        {"role": "user", "content": "I light a torch"},
        {"role": "assistant", "content": "The flickering light reveals..."},
        {"role": "user", "content": "I move forward cautiously"},
    ]
    start_time = time.time()
    result2 = await dm_engine.narrate(
        user_action="I look around the room",
        conversation_history=short_history,
        character_context={"name": "TestHero", "level": 1, "class": "Fighter"},
    )
    duration2 = time.time() - start_time
    print(f"Duration: {duration2:.2f}s")
    print(f"Response length: {len(result2['response'])} chars")

    # Test 3: With long conversation history (20 messages)
    print("\n=== Test 3: With long conversation history (20 messages) ===")
    long_history = []
    for i in range(10):
        long_history.append({"role": "user", "content": f"User message {i}"})
        long_history.append({"role": "assistant", "content": f"DM response {i}" * 20})
    start_time = time.time()
    result3 = await dm_engine.narrate(
        user_action="I look around the room",
        conversation_history=long_history,
        character_context={"name": "TestHero", "level": 1, "class": "Fighter"},
    )
    duration3 = time.time() - start_time
    print(f"Duration: {duration3:.2f}s")
    print(f"Response length: {len(result3['response'])} chars")

    # Test 4: With memory context (simulates vector DB results)
    print("\n=== Test 4: With memory context ===")
    memory_context = (
        """
    Past memories:
    - You previously fought a goblin in this dungeon
    - You found a magic sword in the armory
    - The wizard warned you about traps
    """
        * 5
    )  # Make it longer
    start_time = time.time()
    result4 = await dm_engine.narrate(
        user_action="I look around the room",
        conversation_history=short_history,
        character_context={"name": "TestHero", "level": 1, "class": "Fighter"},
        memory_context=memory_context,
    )
    duration4 = time.time() - start_time
    print(f"Duration: {duration4:.2f}s")
    print(f"Response length: {len(result4['response'])} chars")

    # Summary
    print("\n=== PERFORMANCE SUMMARY ===")
    print(f"No history:          {duration1:.2f}s")
    print(f"Short history (5):   {duration2:.2f}s (+{duration2 - duration1:.2f}s)")
    print(f"Long history (20):   {duration3:.2f}s (+{duration3 - duration1:.2f}s)")
    print(f"With memory context: {duration4:.2f}s (+{duration4 - duration2:.2f}s from short)")

    # Assertions (expected < 5 seconds per requirement)
    assert duration1 < 5.0, f"Simple narration took {duration1:.2f}s > 5s"
    assert duration2 < 7.0, f"With short history took {duration2:.2f}s > 7s"
    assert duration3 < 10.0, f"With long history took {duration3:.2f}s > 10s"


@pytest.mark.asyncio
async def test_token_counting():
    """
    Measure token counts to understand context window usage.
    """
    from app.services.token_counter import TokenCounter

    counter = TokenCounter()

    # Simple message
    simple = "I look around the room"
    simple_tokens = counter.count(simple)
    print(f"\nSimple action: {simple_tokens} tokens")

    # Long conversation
    long_conversation = [
        {"role": "user", "content": "Message " * 50},
        {"role": "assistant", "content": "Response " * 100},
    ] * 10
    long_tokens = sum(counter.count(msg["content"]) for msg in long_conversation)
    print(f"Long conversation: {long_tokens} tokens")

    # Memory context
    memory = "Past memory " * 200
    memory_tokens = counter.count(memory)
    print(f"Memory context: {memory_tokens} tokens")

    # Total context
    total = simple_tokens + long_tokens + memory_tokens
    print(f"\nTotal context: {total} tokens")
    print(f"Percentage of 32k limit: {total / 32000 * 100:.1f}%")


@pytest.mark.asyncio
async def test_provider_timing():
    """
    Compare timing across different provider methods.
    """
    from app.services.provider_selector import provider_selector

    messages = [{"role": "user", "content": "Tell me a short story about a brave knight"}]

    print("\n=== Testing Provider Response Time ===")
    start_time = time.time()
    response = await provider_selector.generate_chat(
        messages=messages,
        max_tokens=200,
        temperature=0.7,
    )
    duration = time.time() - start_time

    print(
        f"Provider: {provider_selector.current_provider.name if provider_selector.current_provider else 'Unknown'}"
    )
    print(f"Duration: {duration:.2f}s")
    print(f"Response length: {len(response)} chars")
    print(f"Chars per second: {len(response) / duration:.1f}")

    assert duration < 5.0, f"Provider response took {duration:.2f}s > 5s"


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_dm_response_timing())
    asyncio.run(test_token_counting())
    asyncio.run(test_provider_timing())
