"""Embedding generation service for vector memory"""

import os
from typing import List

from mistralai import Mistral

from app.observability.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Mistral AI"""

    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")

        self.client = Mistral(api_key=api_key)
        # Mistral embedding model
        self.model = "mistral-embed"

    async def generate_embedding(self, text: str) -> List[float] | None:
        """Generate embedding for a single text

        Args:
            text: Text to embed

        Returns:
            List of 1024 floats (Mistral embedding dimension) or None on failure
        """
        try:
            import asyncio

            # Wrap synchronous Mistral API call in asyncio.to_thread for proper async
            embeddings_response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.model,
                inputs=[text],
            )

            # Extract embedding from response
            if embeddings_response.data and len(embeddings_response.data) > 0:
                return embeddings_response.data[0].embedding

            raise ValueError("No embedding returned from Mistral API")

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float] | None]:
        """Generate embeddings for multiple texts in batch

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (may contain None for failures)
        """
        try:
            import asyncio

            # Wrap synchronous Mistral API call in asyncio.to_thread for proper async
            embeddings_response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.model,
                inputs=texts,
            )

            # Extract embeddings
            return [data.embedding for data in embeddings_response.data]

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)


# Singleton instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
