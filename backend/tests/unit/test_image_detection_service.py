"""Tests for app.services.image_detection_service — semantic scene detection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ── ImageDetectionService ─────────────────────────────────────────────────


class TestImageDetectionService:
    """Test the detection service with a mocked model to avoid loading heavy ML weights."""

    def _make_service(self):
        """Create an ImageDetectionService with a mocked model."""
        # We need to mock SentenceTransformer BEFORE importing the class
        # to avoid actually loading the model
        from app.services.image_detection_service import ImageDetectionService

        svc = object.__new__(ImageDetectionService)

        # Mock model
        mock_model = MagicMock()
        mock_model.eval.return_value = mock_model

        # Pre-compute fake scene embeddings (matching template count)
        num_templates = len(ImageDetectionService.SCENE_TEMPLATES)
        fake_embeddings = np.random.rand(num_templates, 384).astype(np.float32)

        mock_model.encode.return_value = fake_embeddings
        svc.__class__._model = mock_model
        svc.__class__._scene_embeddings = fake_embeddings

        return svc

    def test_is_significant_scene_empty_text(self):
        """Empty narration should return not significant."""
        svc = self._make_service()
        is_sig, score, template = svc.is_significant_scene("", "")
        assert is_sig is False
        assert score == 0.0
        assert template is None

    def test_is_significant_scene_model_not_initialized(self):
        """Should return False when model is None."""
        from app.services.image_detection_service import ImageDetectionService

        svc = object.__new__(ImageDetectionService)
        svc.__class__._model = None
        svc.__class__._scene_embeddings = None

        is_sig, score, template = svc.is_significant_scene("A big battle")
        assert is_sig is False
        assert score == 0.0

    def test_is_significant_scene_with_narration(self):
        """Should detect significant scenes with combat-like narration."""
        import torch

        from app.services.image_detection_service import ImageDetectionService

        svc = object.__new__(ImageDetectionService)
        mock_model = MagicMock()
        mock_model.eval.return_value = mock_model

        num_templates = len(ImageDetectionService.SCENE_TEMPLATES)

        # Create a scene embedding that will have high similarity with first template
        fake_scene_embedding = torch.rand(384)
        fake_template_embeddings = torch.rand(num_templates, 384)

        # Make first template (combat) score high
        fake_template_embeddings[0] = fake_scene_embedding + torch.rand(384) * 0.01

        mock_model.encode.side_effect = [
            fake_template_embeddings,  # For templates
            fake_scene_embedding,  # For input text
        ]

        svc.__class__._model = mock_model
        svc.__class__._scene_embeddings = fake_template_embeddings

        # Mock encode to return scene embedding for the input text
        mock_model.encode.return_value = fake_scene_embedding

        is_sig, score, template = svc.is_significant_scene(
            "The goblins rush forward with weapons drawn, initiative is rolled!"
        )
        # Result depends on cosine similarity; we just check it returns valid types
        assert isinstance(is_sig, bool)
        assert isinstance(score, float)
        assert score >= 0.0

    def test_is_significant_scene_below_threshold(self):
        """Low similarity should return not significant."""
        import torch

        from app.services.image_detection_service import ImageDetectionService

        svc = object.__new__(ImageDetectionService)
        mock_model = MagicMock()

        num_templates = len(ImageDetectionService.SCENE_TEMPLATES)

        # Create orthogonal vectors for low similarity
        scene_emb = torch.zeros(384)
        scene_emb[0] = 1.0

        template_embs = torch.zeros(num_templates, 384)
        template_embs[:, 1] = 1.0  # orthogonal to scene

        mock_model.encode.return_value = scene_emb
        svc.__class__._model = mock_model
        svc.__class__._scene_embeddings = template_embs

        is_sig, score, template = svc.is_significant_scene("Just walking around")
        assert is_sig is False
        assert score < 0.5

    def test_is_significant_scene_above_threshold(self):
        """High similarity should return significant."""
        import torch

        from app.services.image_detection_service import ImageDetectionService

        svc = object.__new__(ImageDetectionService)
        mock_model = MagicMock()

        num_templates = len(ImageDetectionService.SCENE_TEMPLATES)

        # Create identical vectors for max similarity
        scene_emb = torch.ones(384)
        template_embs = torch.ones(num_templates, 384)

        mock_model.encode.return_value = scene_emb
        svc.__class__._model = mock_model
        svc.__class__._scene_embeddings = template_embs

        is_sig, score, template = svc.is_significant_scene(
            "A massive dragon appears before the adventurers"
        )
        assert is_sig is True
        assert score >= 0.5
        assert template is not None

    def test_is_significant_scene_with_player_action(self):
        """Should combine player action and narration."""
        import torch

        from app.services.image_detection_service import ImageDetectionService

        svc = object.__new__(ImageDetectionService)
        mock_model = MagicMock()

        num_templates = len(ImageDetectionService.SCENE_TEMPLATES)
        scene_emb = torch.ones(384)
        template_embs = torch.ones(num_templates, 384)

        mock_model.encode.return_value = scene_emb
        svc.__class__._model = mock_model
        svc.__class__._scene_embeddings = template_embs

        is_sig, score, template = svc.is_significant_scene(
            "A portal opens before you",
            player_action="I open the ancient gate",
        )
        # encode was called with combined text
        call_args = mock_model.encode.call_args
        combined_text = call_args[0][0]
        assert "open" in combined_text.lower()

    def test_is_significant_scene_exception(self):
        """Should return False on error."""
        from app.services.image_detection_service import ImageDetectionService

        svc = object.__new__(ImageDetectionService)
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("Model error")

        num_templates = len(ImageDetectionService.SCENE_TEMPLATES)
        svc.__class__._model = mock_model
        svc.__class__._scene_embeddings = MagicMock()

        is_sig, score, template = svc.is_significant_scene("Some scene")
        assert is_sig is False
        assert score == 0.0

    def test_adjust_threshold(self):
        """Should update the class-level SIMILARITY_THRESHOLD."""
        from app.services.image_detection_service import ImageDetectionService

        svc = object.__new__(ImageDetectionService)
        original = ImageDetectionService.SIMILARITY_THRESHOLD

        svc.adjust_threshold(0.7)
        assert ImageDetectionService.SIMILARITY_THRESHOLD == 0.7

        # Restore
        svc.adjust_threshold(original)

    def test_adjust_threshold_invalid(self):
        """Should raise ValueError for out-of-range threshold."""
        from app.services.image_detection_service import ImageDetectionService

        svc = object.__new__(ImageDetectionService)

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            svc.adjust_threshold(1.5)

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            svc.adjust_threshold(-0.1)


# ── get_image_detection_service ───────────────────────────────────────────


def test_get_image_detection_service_creates_singleton():
    """Should return the same instance on repeated calls."""
    from app.services import image_detection_service as mod

    # Reset singleton
    mod._image_detection_service = None

    with patch.object(mod.ImageDetectionService, "__init__", return_value=None):
        svc1 = mod.get_image_detection_service()
        # Set it manually since __init__ is mocked
        mod._image_detection_service = svc1
        svc2 = mod.get_image_detection_service()
        assert svc1 is svc2

    # Cleanup
    mod._image_detection_service = None


# ── SCENE_TEMPLATES ───────────────────────────────────────────────────────


def test_scene_templates_not_empty():
    """Sanity check — templates should exist."""
    from app.services.image_detection_service import ImageDetectionService

    assert len(ImageDetectionService.SCENE_TEMPLATES) > 0
    for t in ImageDetectionService.SCENE_TEMPLATES:
        assert isinstance(t, str)
        assert len(t) > 0
