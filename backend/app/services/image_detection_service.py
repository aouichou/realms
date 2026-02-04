"""
Semantic image detection service using sentence embeddings.

This service uses multilingual sentence transformers to detect significant
scenes that warrant image generation, working across languages without
explicit keyword matching.
"""

import os
from typing import Optional, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sentence_transformers import util as st_util

from app.observability.logger import get_logger

logger = get_logger(__name__)


class ImageDetectionService:
    """
    Detect significant D&D scenes using semantic similarity.

    Works in any language (French, English, etc.) without keyword matching.
    Uses lightweight multilingual sentence embeddings for fast inference.
    """

    # Multilingual model: supports 50+ languages, ~420MB
    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    SIMILARITY_THRESHOLD = 0.5  # Balanced threshold for significant scenes only

    # OPTIMIZATION: Threads for CPU inference (adjust based on container resources)
    # Default to 2 threads for typical container limits, or use all cores if available
    CPU_THREADS = int(os.getenv("TORCH_NUM_THREADS", "2"))

    # Scene type templates - describe what we want to generate images for
    SCENE_TEMPLATES = [
        # Combat scenes
        "A combat encounter begins with enemies attacking",
        "A battle starts with weapons drawn and initiative rolled",
        "Enemies emerge and attack the adventurers",
        # New locations
        "The adventurers enter a new location or building",
        "Arriving at a significant place like a tavern, temple, or dungeon",
        "Stepping into a chamber, throne room, or important area",
        # Investigation & Discovery
        "Investigating clues, tracks, or examining an abandoned cart or scene",
        "Discovering mysterious tracks, footprints, or signs of passage",
        "Examining a crime scene, wreckage, or suspicious area",
        "Finding a hidden note, message, or important clue",
        # Boss encounters / Important NPCs
        "A dragon or powerful enemy appears before the party",
        "An important character emerges or is discovered",
        "A towering boss creature looms over the adventurers",
        # Dramatic moments
        "A magical explosion or portal opens",
        "An ancient artifact or treasure hoard is discovered",
        "A dramatic revelation or important event unfolds",
        # Quest milestones
        "The party achieves a major quest objective",
        "A significant story event or turning point occurs",
    ]

    _instance: Optional["ImageDetectionService"] = None
    _model: Optional[SentenceTransformer] = None
    _scene_embeddings: Optional[Union[torch.Tensor, np.ndarray]] = None

    def __new__(cls):
        """Singleton pattern for model reuse."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize (lazy loading - model loads on first use)."""
        if self._model is None:
            # Apply PyTorch optimizations for Docker/CPU
            self._apply_torch_optimizations()

            logger.info(f"Loading sentence transformer model: {self.MODEL_NAME}")
            logger.info(f"Torch CPU threads: {self.CPU_THREADS}")
            try:
                self._model = SentenceTransformer(self.MODEL_NAME)

                # Set to evaluation mode for inference
                self._model = self._model.eval()

                # Pre-compute scene template embeddings
                self._scene_embeddings = self._model.encode(
                    self.SCENE_TEMPLATES,
                    convert_to_tensor=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,  # OPTIMIZATION: Normalize for faster cosine
                )
                logger.info(
                    f"Model loaded successfully. "
                    f"Pre-computed {len(self.SCENE_TEMPLATES)} scene embeddings."
                )
            except Exception as e:
                logger.error(f"Failed to load sentence transformer model: {e}")
                raise

    def _apply_torch_optimizations(self):
        """Apply PyTorch optimizations for CPU inference in containers."""
        # Force CPU usage (even if CUDA is somehow detected)
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

        # Set optimal number of threads for container environment
        torch.set_num_threads(self.CPU_THREADS)

        # Disable gradient computation - we only do inference
        torch.set_grad_enabled(False)

        # Set memory allocator to be more efficient for inference workloads
        os.environ["OMP_NUM_THREADS"] = str(self.CPU_THREADS)
        os.environ["MKL_NUM_THREADS"] = str(self.CPU_THREADS)

        logger.debug(f"Applied torch optimizations: {self.CPU_THREADS} threads, gradients disabled")

    def is_significant_scene(
        self, narration: str, player_action: str = ""
    ) -> tuple[bool, float, Optional[str]]:
        """
        Determine if scene warrants image generation using semantic similarity.

        Args:
            narration: DM's narration text
            player_action: Player's action text

        Returns:
            Tuple of (is_significant, max_similarity, matched_template)
            - is_significant: True if image should be generated
            - max_similarity: Highest similarity score (0-1)
            - matched_template: The scene template that matched best
        """
        if self._model is None or self._scene_embeddings is None:
            logger.error("Model not initialized")
            return False, 0.0, None

        # Combine narration and player action for context
        combined_text = f"{player_action} {narration}".strip()

        if not combined_text:
            return False, 0.0, None

        try:
            # OPTIMIZATION: Use inference mode context manager (faster than torch.no_grad())
            with torch.inference_mode():
                # Encode the scene text
                scene_embedding = self._model.encode(
                    combined_text,
                    convert_to_tensor=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,  # OPTIMIZATION: Consistent normalization
                )

                # Compute cosine similarity with all scene templates
                similarities = st_util.cos_sim(scene_embedding, self._scene_embeddings)[0]

                # Find best match
                max_similarity = float(similarities.max())
                best_match_idx = int(similarities.argmax())
                matched_template = self.SCENE_TEMPLATES[best_match_idx]

                is_significant = max_similarity >= self.SIMILARITY_THRESHOLD

                # Log all attempts for debugging
                logger.info(
                    f"Image detection: similarity={max_similarity:.3f}, "
                    f"threshold={self.SIMILARITY_THRESHOLD}, "
                    f"significant={is_significant}, "
                    f"template='{matched_template}'"
                )

                # Detailed logging
                if is_significant:
                    logger.info(
                        f"✓ Significant scene detected! "
                        f"Similarity: {max_similarity:.3f} | "
                        f"Template: '{matched_template}' | "
                        f"Text preview: '{combined_text[:100]}...'"
                    )
                else:
                    logger.debug(
                        f"✗ Scene not significant. "
                        f"Max similarity: {max_similarity:.3f} "
                        f"(threshold: {self.SIMILARITY_THRESHOLD})"
                    )

                return is_significant, max_similarity, matched_template

        except Exception as e:
            logger.error(f"Error computing scene significance: {e}", exc_info=True)
            return False, 0.0, None

    def adjust_threshold(self, new_threshold: float) -> None:
        """
        Adjust the similarity threshold for image generation.

        Args:
            new_threshold: New threshold (0.0-1.0).
                          Lower = more images, Higher = fewer images
        """
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")

        old_threshold = self.SIMILARITY_THRESHOLD
        self.__class__.SIMILARITY_THRESHOLD = new_threshold
        logger.info(f"Adjusted similarity threshold: {old_threshold:.2f} → {new_threshold:.2f}")


# Global singleton instance
_image_detection_service: Optional[ImageDetectionService] = None


def get_image_detection_service() -> ImageDetectionService:
    """Get or create the image detection service singleton."""
    global _image_detection_service
    if _image_detection_service is None:
        _image_detection_service = ImageDetectionService()
    return _image_detection_service
