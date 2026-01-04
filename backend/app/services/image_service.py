"""Scene Image Generation Service using Pixtral"""
import hashlib
import os
from typing import Optional

from mistralai import Mistral

from app.services.redis_service import session_service

# Initialize Mistral client
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None

# Cache TTL: 24 hours
IMAGE_CACHE_TTL = 60 * 60 * 24


class ImageService:
    """Service for generating scene images with Pixtral"""
    
    @staticmethod
    def _generate_cache_key(scene_description: str) -> str:
        """Generate cache key from scene description"""
        # Hash the description for consistent caching
        hash_obj = hashlib.md5(scene_description.encode())
        return f"scene_image:{hash_obj.hexdigest()}"
    
    @staticmethod
    async def generate_scene_image(
        scene_description: str,
        use_cache: bool = True
    ) -> Optional[str]:
        """Generate scene image using Pixtral
        
        Args:
            scene_description: Description of the scene to visualize
            use_cache: Whether to use Redis cache
            
        Returns:
            str: Base64-encoded image data or None if generation fails
        """
        if not client:
            return None
        
        # Check cache first
        if use_cache:
            cache_key = ImageService._generate_cache_key(scene_description)
            cached_image = await session_service.redis.get(cache_key)
            if cached_image:
                return cached_image.decode() if isinstance(cached_image, bytes) else cached_image
        
        try:
            # Call Pixtral API (Note: Actual Pixtral API integration would go here)
            # For now, return placeholder since Pixtral API details are not fully available
            # In production, this would call: client.images.generate(model="pixtral", prompt=scene_description)
            
            # Placeholder response
            image_data = None
            
            # Cache the result
            if use_cache and image_data:
                cache_key = ImageService._generate_cache_key(scene_description)
                await session_service.redis.setex(
                    cache_key,
                    IMAGE_CACHE_TTL,
                    image_data
                )
            
            return image_data
            
        except Exception as e:
            print(f"Error generating scene image: {e}")
            return None
    
    @staticmethod
    def extract_scene_from_narration(narration: str) -> str:
        """Extract scene description from narration text
        
        Args:
            narration: Full narration text
            
        Returns:
            str: Cleaned scene description for image generation
        """
        # Extract first 2-3 sentences that describe the scene
        sentences = narration.split(". ")
        scene = ". ".join(sentences[:min(3, len(sentences))])
        
        # Clean up dialogue and player actions
        scene = scene.replace('"', '')
        
        # Add D&D fantasy art style
        scene_prompt = f"Fantasy D&D scene: {scene}. Epic medieval fantasy art style, detailed environment, cinematic lighting."
        
        return scene_prompt
