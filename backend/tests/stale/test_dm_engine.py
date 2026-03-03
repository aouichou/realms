"""
Tests for DM Engine
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.dm_engine import DMEngine, get_dm_engine


@pytest.fixture
def dm_engine():
    """Create DM Engine instance for testing"""
    with patch('app.services.dm_engine.get_mistral_client'):
        engine = DMEngine()
        return engine


def test_format_character_context(dm_engine):
    """Test character context formatting"""
    character = {
        "name": "Thorin",
        "race": "Dwarf",
        "class": "Fighter",
        "level": 3,
        "background": "Soldier"
    }
    
    context = dm_engine._format_character_context(character)
    
    assert "Thorin" in context
    assert "Dwarf" in context
    assert "Fighter" in context
    assert "Level: 3" in context


def test_format_game_state(dm_engine):
    """Test game state formatting"""
    state = {
        "location": "Dark Cave",
        "time_of_day": "Night",
        "weather": "Stormy",
        "party_members": ["Thorin", "Elara"],
        "active_quest": "Find the Lost Artifact"
    }
    
    formatted = dm_engine._format_game_state(state)
    
    assert "Dark Cave" in formatted
    assert "Night" in formatted
    assert "Stormy" in formatted
    assert "Thorin" in formatted


def test_build_messages_basic(dm_engine):
    """Test basic message building"""
    messages = dm_engine._build_messages("I look around")
    
    assert len(messages) >= 2  # System + user
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "I look around"


def test_build_messages_with_context(dm_engine):
    """Test message building with character and game context"""
    character = {"name": "Thorin", "class": "Fighter"}
    game_state = {"location": "Tavern"}
    history = [
        {"role": "user", "content": "I enter the tavern"},
        {"role": "assistant", "content": "You push open the heavy oak door..."}
    ]
    
    messages = dm_engine._build_messages(
        "I order a drink",
        conversation_history=history,
        character_context=character,
        game_state=game_state
    )
    
    # Should have system, character context, game state, history, and current message
    assert len(messages) > 4
    assert any("Thorin" in str(msg) for msg in messages)
    assert any("Tavern" in str(msg) for msg in messages)


@pytest.mark.asyncio
async def test_narrate_success(dm_engine):
    """Test successful narration generation"""
    # Mock Mistral client response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "You see a dark corridor ahead."
    mock_response.usage.total_tokens = 50
    
    dm_engine.mistral_client.chat_completion = AsyncMock(return_value=mock_response)
    
    result = await dm_engine.narrate("I look down the corridor")
    
    assert result["narration"] == "You see a dark corridor ahead."
    assert result["tokens_used"] == 50
    assert "timestamp" in result
    assert "model" in result


@pytest.mark.asyncio
async def test_narrate_with_character(dm_engine):
    """Test narration with character context"""
    character = {"name": "Elara", "class": "Wizard"}
    
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Elara, you sense magic nearby."
    mock_response.usage.total_tokens = 30
    
    dm_engine.mistral_client.chat_completion = AsyncMock(return_value=mock_response)
    
    result = await dm_engine.narrate(
        "I cast detect magic",
        character_context=character
    )
    
    assert "Elara" in result["narration"]


@pytest.mark.asyncio
async def test_start_adventure(dm_engine):
    """Test adventure opening generation"""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "You stand at the entrance of an ancient dungeon..."
    mock_response.usage.total_tokens = 75
    
    dm_engine.mistral_client.chat_completion = AsyncMock(return_value=mock_response)
    
    result = await dm_engine.start_adventure(
        setting="mysterious ruins",
        character_context={"name": "Thorin"}
    )
    
    assert "narration" in result
    assert len(result["narration"]) > 0


@pytest.mark.asyncio
async def test_narrate_stream(dm_engine):
    """Test streaming narration"""
    async def mock_stream(messages):
        chunks = ["You ", "enter ", "the ", "dungeon."]
        for chunk in chunks:
            yield chunk
    
    dm_engine.mistral_client.chat_completion_stream = mock_stream
    
    chunks = []
    async for chunk in dm_engine.narrate_stream("I enter"):
        chunks.append(chunk)
    
    assert chunks == ["You ", "enter ", "the ", "dungeon."]


@pytest.mark.asyncio
async def test_start_adventure_stream(dm_engine):
    """Test streaming adventure opening"""
    async def mock_stream(messages):
        yield "The "
        yield "adventure "
        yield "begins!"
    
    dm_engine.mistral_client.chat_completion_stream = mock_stream
    
    chunks = []
    async for chunk in dm_engine.start_adventure_stream():
        chunks.append(chunk)
    
    assert len(chunks) == 3
    assert "".join(chunks) == "The adventure begins!"


def test_system_prompt_content(dm_engine):
    """Test that system prompt includes critical instructions"""
    prompt = DMEngine.SYSTEM_PROMPT
    
    # Check for critical instructions
    assert "Dungeon Master" in prompt
    assert "Never say" in prompt or "NEVER include" in prompt
    assert "Would you like" in prompt  # As example of what NOT to say
    assert "vivid" in prompt or "description" in prompt
    assert "D&D" in prompt or "5e" in prompt


def test_get_dm_engine_singleton():
    """Test that get_dm_engine returns singleton"""
    with patch('app.services.dm_engine.get_mistral_client'):
        engine1 = get_dm_engine()
        engine2 = get_dm_engine()
        
        assert engine1 is engine2
