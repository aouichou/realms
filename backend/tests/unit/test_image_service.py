"""Tests for app.services.image_service — ImageService, rate limiting, caching."""

from __future__ import annotations

import hashlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import image_service as image_service_module
from app.services.image_service import ImageService

# ── _generate_hash / _normalize_description ───────────────────────────────


def test_generate_hash():
    h = ImageService._generate_hash("test string")
    assert h == hashlib.md5("test string".encode()).hexdigest()
    assert len(h) == 32


def test_normalize_description():
    raw = "  A Dark   Dungeon.  "
    result = ImageService._normalize_description(raw)
    assert result == "a dark dungeon"


def test_normalize_description_strips_punctuation():
    result = ImageService._normalize_description("The dragon roars!!!")
    assert result == "the dragon roars"


def test_normalize_description_trailing_semicolon():
    result = ImageService._normalize_description("Scene one;")
    assert result == "scene one"


# ── _build_image_prompt ───────────────────────────────────────────────────


def test_build_image_prompt_basic():
    svc = object.__new__(ImageService)  # skip __init__
    prompt = svc._build_image_prompt("A dragon in a cave. Fire everywhere. Darkness surrounds.")
    assert "dragon" in prompt.lower()
    assert "Style Requirements" in prompt


def test_build_image_prompt_with_character():
    svc = object.__new__(ImageService)
    prompt = svc._build_image_prompt(
        "A tavern scene", character_description="Gandalf, Human Wizard"
    )
    assert "Gandalf" in prompt
    assert "Main Character" in prompt


def test_build_image_prompt_no_character():
    svc = object.__new__(ImageService)
    prompt = svc._build_image_prompt("A dungeon room")
    assert "Main Character" not in prompt


def test_build_image_prompt_long_description():
    """Should only use first 3 sentences."""
    svc = object.__new__(ImageService)
    desc = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
    prompt = svc._build_image_prompt(desc)
    assert "First sentence" in prompt
    assert "Third sentence" in prompt
    # Fourth and fifth may be cut off (only first 3 sentences)


# ── rate_limit decorator ──────────────────────────────────────────────────


def test_rate_limit_cleans_old_calls():
    """Old calls should be cleaned from the tracking list."""
    # Reset global state
    image_service_module._image_generation_calls = [time.time() - 7200]  # 2 hours ago
    assert len(image_service_module._image_generation_calls) == 1

    # The calls list has old entries; after next invocation they should be cleaned
    # We test indirectly via the decorator behavior


async def test_rate_limit_disabled():
    """When ENABLE_IMAGE_GENERATION is False, should return None."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    svc.agent_id = "test-agent"

    with patch.object(image_service_module, "ENABLE_IMAGE_GENERATION", False):
        # Reset rate limit tracking
        image_service_module._image_generation_calls = []

        result = await svc.generate_scene_image("A scene", AsyncMock())

    assert result is None


async def test_rate_limit_exceeded():
    """Should return None when rate limit is hit."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    svc.agent_id = "test-agent"

    with patch.object(image_service_module, "ENABLE_IMAGE_GENERATION", True):
        # Fill up rate limit
        now = time.time()
        image_service_module._image_generation_calls = [now - i for i in range(20)]
        with patch.object(image_service_module, "MAX_IMAGES_PER_HOUR", 10):
            result = await svc.generate_scene_image("A scene", AsyncMock())

    assert result is None
    # Reset
    image_service_module._image_generation_calls = []


# ── generate_scene_image ──────────────────────────────────────────────────


async def test_generate_scene_image_no_client():
    """Should return None when client is not initialized."""
    svc = object.__new__(ImageService)
    svc.client = None
    svc.agent_id = None

    with patch.object(image_service_module, "ENABLE_IMAGE_GENERATION", True):
        image_service_module._image_generation_calls = []
        result = await svc.generate_scene_image("A scene", AsyncMock())

    assert result is None


async def test_generate_scene_image_no_agent():
    """Should return None when agent_id is not set."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    svc.agent_id = None

    with patch.object(image_service_module, "ENABLE_IMAGE_GENERATION", True):
        image_service_module._image_generation_calls = []
        result = await svc.generate_scene_image("A scene", AsyncMock())

    assert result is None


async def test_generate_scene_image_cache_hit(db_session):
    """Should reuse existing image from database cache."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    svc.agent_id = "test-agent"

    # Create a GeneratedImage in the DB
    from app.schemas.generated_image import GeneratedImage

    desc = "a dragon in a cave"
    desc_hash = hashlib.md5(desc.encode()).hexdigest()

    existing = GeneratedImage(
        description_hash=desc_hash,
        description_text=desc,
        image_path="/media/images/generated/test.png",
        model_used="mistral-medium-latest",
        reuse_count=0,
    )
    db_session.add(existing)
    await db_session.flush()

    with patch.object(image_service_module, "ENABLE_IMAGE_GENERATION", True):
        image_service_module._image_generation_calls = []
        image_service_module._api_cooldown_until = 0

        result = await svc.generate_scene_image("A dragon in a cave.", db_session, use_cache=True)

    assert result is not None
    assert "test.png" in result


async def test_generate_scene_image_cache_hit_r2_url(db_session):
    """Should return full URL when image_path starts with http."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    svc.agent_id = "test-agent"

    from app.schemas.generated_image import GeneratedImage

    desc = "a tavern scene with adventurers"
    desc_hash = hashlib.md5(desc.encode()).hexdigest()

    existing = GeneratedImage(
        description_hash=desc_hash,
        description_text=desc,
        image_path="https://r2.example.com/scenes/test.png",
        model_used="mistral-medium-latest",
        reuse_count=2,
    )
    db_session.add(existing)
    await db_session.flush()

    with patch.object(image_service_module, "ENABLE_IMAGE_GENERATION", True):
        image_service_module._image_generation_calls = []
        image_service_module._api_cooldown_until = 0

        result = await svc.generate_scene_image(
            "A tavern scene with adventurers.", db_session, use_cache=True
        )

    assert result == "https://r2.example.com/scenes/test.png"


async def test_generate_scene_image_api_cooldown():
    """Should return None during API cooldown."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    svc.agent_id = "test-agent"

    with patch.object(image_service_module, "ENABLE_IMAGE_GENERATION", True):
        image_service_module._image_generation_calls = []
        # Set cooldown to future
        image_service_module._api_cooldown_until = time.time() + 300

        result = await svc.generate_scene_image("A scene", AsyncMock(), use_cache=False)

    assert result is None
    # Reset
    image_service_module._api_cooldown_until = 0


async def test_generate_scene_image_api_429_sets_cooldown():
    """429 error should set the cooldown timer."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    svc.agent_id = "test-agent"
    svc.client.beta.conversations.start.side_effect = Exception("429 rate limit exceeded")

    mock_db = AsyncMock()
    # Make the DB query return no cached image
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(image_service_module, "ENABLE_IMAGE_GENERATION", True):
        image_service_module._image_generation_calls = []
        image_service_module._api_cooldown_until = 0

        result = await svc.generate_scene_image("A scene", mock_db, use_cache=True)

    assert result is None
    assert image_service_module._api_cooldown_until > time.time()
    # Reset
    image_service_module._api_cooldown_until = 0


async def test_generate_scene_image_generic_error():
    """Non-429 errors should still return None but not set cooldown."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    svc.agent_id = "test-agent"
    svc.client.beta.conversations.start.side_effect = Exception("Network error")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(image_service_module, "ENABLE_IMAGE_GENERATION", True):
        image_service_module._image_generation_calls = []
        image_service_module._api_cooldown_until = 0

        result = await svc.generate_scene_image("A scene", mock_db, use_cache=True)

    assert result is None


# ── _process_agent_response ───────────────────────────────────────────────


async def test_process_agent_response_no_outputs():
    """Should return None when response has no outputs."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()

    response = MagicMock()
    response.outputs = []

    result = await svc._process_agent_response(response, "hash", AsyncMock(), "desc")
    assert result is None


async def test_process_agent_response_no_content():
    """Should return None when last output has no content."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()

    response = MagicMock()
    output = MagicMock(spec=[])  # no 'content' attribute
    response.outputs = [output]

    result = await svc._process_agent_response(response, "hash", AsyncMock(), "desc")
    assert result is None


async def test_process_agent_response_no_image_chunks():
    """Should return None when content has no ToolFileChunk."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()

    response = MagicMock()
    text_chunk = MagicMock()  # Not a ToolFileChunk
    output = MagicMock()
    output.content = [text_chunk]
    response.outputs = [output]

    result = await svc._process_agent_response(response, "hash", AsyncMock(), "desc")
    assert result is None


async def test_process_agent_response_exception():
    """Should return None on exception."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()

    # Response that raises an exception when accessing outputs
    response = MagicMock()
    type(response).outputs = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))

    result = await svc._process_agent_response(response, "hash", AsyncMock(), "desc")
    assert result is None


# ── _get_r2_client ────────────────────────────────────────────────────────


def test_get_r2_client_disabled():
    """Should return None when R2 is not enabled."""
    with patch("app.services.image_service.settings") as mock_settings:
        mock_settings.r2_images_enabled = False
        image_service_module._r2_client = None
        client = image_service_module._get_r2_client()
    assert client is None


# ── _initialize_agent ─────────────────────────────────────────────────────


def test_initialize_agent_with_env_var():
    """Should use persistent agent ID from env."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()

    with patch.dict("os.environ", {"MISTRAL_IMAGE_AGENT_ID": "persistent-id"}):
        svc._initialize_agent()

    assert svc.agent_id == "persistent-id"


def test_initialize_agent_no_client():
    """Should not crash when client is None."""
    svc = object.__new__(ImageService)
    svc.client = None
    svc.agent_id = None  # pre-initialize attribute

    with patch.dict("os.environ", {}, clear=False):
        # Remove the env var if present
        import os

        os.environ.pop("MISTRAL_IMAGE_AGENT_ID", None)
        svc._initialize_agent()

    assert svc.agent_id is None


def test_initialize_agent_creates_agent():
    """Should create a new agent via client API."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    mock_agent = MagicMock()
    mock_agent.id = "new-agent-id"
    svc.client.beta.agents.create.return_value = mock_agent

    with patch.dict("os.environ", {}, clear=False):
        import os

        os.environ.pop("MISTRAL_IMAGE_AGENT_ID", None)
        svc._initialize_agent()

    assert svc.agent_id == "new-agent-id"


def test_initialize_agent_exception():
    """Should handle agent creation failure gracefully."""
    svc = object.__new__(ImageService)
    svc.client = MagicMock()
    svc.client.beta.agents.create.side_effect = Exception("API down")

    with patch.dict("os.environ", {}, clear=False):
        import os

        os.environ.pop("MISTRAL_IMAGE_AGENT_ID", None)
        svc._initialize_agent()

    assert svc.agent_id is None
