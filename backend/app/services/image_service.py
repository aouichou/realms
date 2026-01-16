"""Scene Image Generation Service using Mistral AI Agents"""

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Optional

from mistralai import Mistral
from mistralai.models import ToolFileChunk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.generated_image import GeneratedImage
from app.services.redis_service import session_service

logger = logging.getLogger(__name__)

# Initialize Mistral client
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None

# Configuration
IMAGE_CACHE_TTL = 60 * 60 * 24  # 24 hours
MEDIA_ROOT = Path("media/images/generated")
MAX_IMAGES_PER_HOUR = int(os.getenv("IMAGE_GENERATION_MAX_PER_HOUR", "10"))
ENABLE_IMAGE_GENERATION = os.getenv("ENABLE_IMAGE_GENERATION", "true").lower() == "true"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Rate limiting storage
_image_generation_calls = []


def rate_limit(max_per_hour: int = MAX_IMAGES_PER_HOUR):
    """Decorator to limit image generation rate"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not ENABLE_IMAGE_GENERATION:
                logger.info("Image generation disabled via environment variable")
                return None

            now = time.time()
            hour_ago = now - 3600

            # Clean old calls
            global _image_generation_calls
            _image_generation_calls = [t for t in _image_generation_calls if t > hour_ago]

            if len(_image_generation_calls) >= max_per_hour:
                logger.warning(f"Image generation rate limit hit: {max_per_hour}/hour")
                return None

            _image_generation_calls.append(now)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class ImageService:
    """Service for generating scene images using Mistral AI Agents"""

    def __init__(self):
        self.client = client
        self.agent_id: Optional[str] = None
        if self.client and ENABLE_IMAGE_GENERATION:
            self._initialize_agent()

        # Ensure media directory exists
        MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    def _initialize_agent(self):
        """Create or retrieve the D&D Scene Illustrator agent"""
        try:
            # Check if we have a persistent agent ID in env
            persistent_agent_id = os.getenv("MISTRAL_IMAGE_AGENT_ID")
            if persistent_agent_id:
                self.agent_id = persistent_agent_id
                logger.info(f"Using persistent image agent: {persistent_agent_id}")
                return

            # Create new agent
            if not self.client:
                logger.error("Cannot create agent: Mistral client not initialized")
                return

            agent = self.client.beta.agents.create(
                model="mistral-medium-latest",  # Required for image generation
                name="D&D Scene Illustrator",
                description="Generates vivid fantasy scene images for D&D adventures",
                instructions=(
                    "Generate cinematic, fantasy-themed images based on D&D scene descriptions. "
                    "Focus on atmosphere, dramatic lighting, and epic composition. "
                    "Style: Fantasy art with detailed environments, medieval fantasy aesthetic. "
                    "Avoid modern elements. Emphasize adventure, mystery, and epicness."
                ),
                tools=[{"type": "image_generation"}],
            )
            self.agent_id = agent.id
            logger.info(f"Image generation agent created: {agent.id}")
            logger.info(
                "💡 TIP: Set MISTRAL_IMAGE_AGENT_ID=%s in .env to reuse this agent", agent.id
            )

        except Exception as e:
            logger.error(f"Failed to initialize image agent: {e}")
            self.agent_id = None

    @staticmethod
    def _generate_hash(text: str) -> str:
        """Generate MD5 hash from text"""
        return hashlib.md5(text.encode()).hexdigest()

    @staticmethod
    def _normalize_description(description: str) -> str:
        """Normalize scene description for better matching"""
        # Remove extra whitespace, lowercase, remove punctuation at end
        normalized = " ".join(description.lower().strip().split())
        return normalized.rstrip(".,!?;:")

    @rate_limit(max_per_hour=MAX_IMAGES_PER_HOUR)
    async def generate_scene_image(
        self,
        scene_description: str,
        db: AsyncSession,
        use_cache: bool = True,
        character_description: Optional[str] = None,
    ) -> Optional[str]:
        """Generate scene image using Mistral Agent API with smart reuse

        Args:
            scene_description: Description of the scene to visualize
            db: Database session
            use_cache: Whether to check for existing images
            character_description: Optional character context (e.g., "Gandalf, Human Wizard")

        Returns:
            str: URL path to image (/media/images/generated/{hash}.png) or None
        """
        if not self.client or not self.agent_id:
            logger.warning("Image generation not available (agent not initialized)")
            return None

        # Normalize and hash description
        normalized_desc = self._normalize_description(scene_description)
        desc_hash = self._generate_hash(normalized_desc)

        # Check database for existing image
        if use_cache:
            result = await db.execute(
                select(GeneratedImage).filter(GeneratedImage.description_hash == desc_hash)
            )
            existing_image = result.scalar_one_or_none()

            if existing_image:
                # Update reuse stats
                existing_image.reuse_count += 1  # type: ignore[assignment]
                existing_image.last_used_at = datetime.now(timezone.utc)  # type: ignore[assignment]
                await db.commit()

                # Convert relative path to full URL
                full_url = f"{API_BASE_URL}{existing_image.image_path}"

                logger.info(
                    f"Reusing existing image (hash={desc_hash}, reuse_count={existing_image.reuse_count})"
                )
                return full_url

        try:
            # Build enhanced prompt
            image_prompt = self._build_image_prompt(scene_description, character_description)

            logger.info(f"Generating new image for scene (hash={desc_hash})")

            # Start conversation with agent
            response = self.client.beta.conversations.start(
                agent_id=self.agent_id, inputs=image_prompt
            )

            logger.info("Agent response received")
            logger.info(
                f"Response has outputs: {hasattr(response, 'outputs') and len(response.outputs) > 0 if hasattr(response, 'outputs') else False}"
            )

            # Extract and save image
            image_url = await self._process_agent_response(response, desc_hash, db, normalized_desc)

            return image_url

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None

    def _build_image_prompt(
        self, scene_description: str, character_description: Optional[str] = None
    ) -> str:
        """Enhance scene description for better image generation"""
        # Extract key scene elements (first 2-3 sentences)
        sentences = scene_description.split(". ")
        core_scene = ". ".join(sentences[: min(3, len(sentences))])

        # Remove dialogue
        core_scene = core_scene.replace('"', "")

        # Build character context if provided
        character_context = ""
        if character_description:
            character_context = f"\n\nMain Character: {character_description}"

        prompt = f"""Generate a cinematic D&D fantasy scene image:

{core_scene}{character_context}

Style Requirements:
- Epic fantasy art with dramatic lighting
- Medieval fantasy aesthetic (no modern elements)
- Detailed environment and atmosphere
- Immersive and atmospheric mood
- High detail, cinematic composition
- Evoke sense of adventure and mystery"""

        return prompt

    async def _process_agent_response(
        self, response, desc_hash: str, db: AsyncSession, description: str
    ) -> Optional[str]:
        """Extract image file from agent response and save it"""
        try:
            logger.info(
                f"Processing agent response, outputs count: {len(response.outputs) if hasattr(response, 'outputs') else 0}"
            )

            # Find the image file in response
            if not hasattr(response, "outputs") or not response.outputs:
                logger.warning("Response has no outputs")
                return None

            last_output = response.outputs[-1]
            logger.info(
                f"Last output type: {type(last_output)}, has content: {hasattr(last_output, 'content')}"
            )

            if not hasattr(last_output, "content"):
                logger.warning("Last output has no content")
                return None

            for i, chunk in enumerate(last_output.content):
                logger.info(
                    f"Chunk {i}: type={type(chunk)}, is_tool_file={isinstance(chunk, ToolFileChunk)}"
                )
                if isinstance(chunk, ToolFileChunk):
                    # Download image bytes
                    if not self.client:
                        logger.error("Cannot download file: Mistral client not initialized")
                        continue
                    file_bytes = self.client.files.download(file_id=chunk.file_id).read()

                    # Save to filesystem
                    filename = f"{desc_hash}.png"
                    filepath = MEDIA_ROOT / filename
                    relative_path = f"/media/images/generated/{filename}"
                    full_url = f"{API_BASE_URL}{relative_path}"

                    with open(filepath, "wb") as f:
                        f.write(file_bytes)

                    logger.info(f"Image saved: {filepath} ({len(file_bytes)} bytes)")

                    # Save to database (store relative path for flexibility)
                    generated_image = GeneratedImage(
                        description_hash=desc_hash,
                        description_text=description,
                        image_path=relative_path,
                        model_used="mistral-medium-latest",
                        reuse_count=0,
                    )
                    db.add(generated_image)
                    await db.commit()

                    # Cache in Redis (store full URL)
                    if session_service.redis:
                        cache_key = f"scene_image:{desc_hash}"
                        await session_service.redis.setex(  # type: ignore[misc]
                            cache_key, IMAGE_CACHE_TTL, full_url
                        )

                    return full_url

            logger.warning("No image file found in agent response")
            return None

        except Exception as e:
            logger.error(f"Failed to process agent response: {e}")
            return None


# Global instance
image_service = ImageService()
