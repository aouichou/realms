"""
Adaptive Narration Service (RL-145)
Uses semantic similarity to generate natural narrations when AI returns empty content.
Reuses sentence-transformer model from ImageDetectionService.
"""

from typing import Dict, Optional

import numpy as np
import torch

from app.observability.logger import get_logger
from app.services.image_detection_service import ImageDetectionService

logger = get_logger(__name__)


class AdaptiveNarrationService:
    """
    Generate contextual narrations using semantic similarity.

    When AI returns empty content with tool calls, this service:
    1. Analyzes the tool call context (ability, description, action)
    2. Finds semantically similar narrative templates
    3. Generates natural, varied narration

    Example:
        Input: request_player_roll(Survival, 15, "checking for footprints")
        Output: "You carefully examine the ground, looking for any signs of tracks."
        (Instead of: "You focus on checking for footprints.")
    """

    # Narrative templates organized by action type
    # Each template has placeholders that can be filled with tool context
    NARRATIVE_TEMPLATES = {
        # Investigation & Perception
        "investigation": [
            "You carefully examine {target}, searching for clues.",
            "You inspect {target} closely, looking for any details.",
            "Your eyes scan {target}, trying to make sense of what you see.",
            "You study {target} with keen attention to detail.",
            "You investigate {target}, piecing together what happened.",
        ],
        "perception": [
            "You scan the area around {target}, alert for any signs.",
            "Your senses heighten as you watch {target} carefully.",
            "You observe {target}, taking in every detail.",
            "You look around {target}, searching for anything unusual.",
            "Your attention focuses on {target}, ready to react.",
        ],
        "tracking": [
            "You examine the ground near {target}, looking for tracks.",
            "You search {target} for signs of passage.",
            "You carefully study {target}, trying to follow the trail.",
            "You inspect {target}, looking for footprints or marks.",
            "You analyze {target}, tracking the path ahead.",
        ],
        # Physical actions
        "stealth": [
            "You move silently toward {target}, careful not to be noticed.",
            "You creep closer to {target}, staying in the shadows.",
            "You approach {target} quietly, minimizing any sound.",
            "You sneak toward {target}, keeping low and quiet.",
            "You move stealthily near {target}, avoiding detection.",
        ],
        "athletic": [
            "You prepare to test your strength at {target}.",
            "You ready yourself for the physical challenge of {target}.",
            "You brace yourself as you attempt {target}.",
            "You gather your energy to tackle {target}.",
            "You focus your physical prowess on {target}.",
        ],
        # Social interactions
        "persuasion": [
            "You speak to {target} with conviction and charm.",
            "You attempt to convince {target}, choosing your words carefully.",
            "You engage {target} with persuasive reasoning.",
            "You try to win over {target} through diplomacy.",
            "You address {target}, making your case eloquently.",
        ],
        "deception": [
            "You weave a careful story for {target}.",
            "You attempt to mislead {target} with careful words.",
            "You maintain a neutral expression as you speak to {target}.",
            "You craft a believable lie for {target}.",
            "You try to deceive {target} without revealing your intent.",
        ],
        # Knowledge & Arcana
        "arcana": [
            "You focus on the magical energies around {target}.",
            "You attempt to understand the arcane nature of {target}.",
            "You analyze {target} through your knowledge of magic.",
            "You study the mystical aspects of {target}.",
            "You examine {target} with your arcane expertise.",
        ],
        "nature": [
            "You draw on your knowledge of nature to understand {target}.",
            "You examine {target} through the lens of the natural world.",
            "You observe {target}, recalling what you know about wilderness.",
            "You study {target} using your understanding of nature.",
            "You analyze {target} with your knowledge of flora and fauna.",
        ],
        # Combat-related
        "combat_ready": [
            "You ready yourself for what comes next.",
            "You prepare for the challenge ahead.",
            "Your hand moves to your weapon as you assess the situation.",
            "You stand ready, alert and prepared.",
            "You take a defensive stance, ready to act.",
        ],
        # Generic fallbacks
        "generic": [
            "You focus on {target}.",
            "You attempt {target}.",
            "You prepare for {target}.",
            "You concentrate on {target}.",
            "You ready yourself.",
        ],
    }

    # Keywords for semantic matching to action types
    ACTION_TYPE_KEYWORDS = {
        "investigation": [
            "examine",
            "inspect",
            "search",
            "look at",
            "check",
            "investigate",
            "study",
            "analyze",
            "clues",
            "evidence",
        ],
        "perception": [
            "watch",
            "observe",
            "scan",
            "spot",
            "notice",
            "see",
            "hear",
            "sense",
            "alert",
            "lookout",
        ],
        "tracking": ["track", "follow", "trail", "footprints", "marks", "signs", "passage", "path"],
        "stealth": ["sneak", "hide", "quiet", "silent", "stealth", "shadows", "creep", "unnoticed"],
        "athletic": ["climb", "jump", "swim", "lift", "push", "strength", "athletics", "physical"],
        "persuasion": ["convince", "persuade", "charm", "diplomacy", "negotiate", "talk", "reason"],
        "deception": ["lie", "deceive", "mislead", "trick", "bluff", "fake"],
        "arcana": ["magic", "arcane", "spell", "mystical", "enchantment", "magical", "rune"],
        "nature": ["nature", "animal", "plant", "wilderness", "forest", "natural", "beast"],
        "combat_ready": ["attack", "fight", "battle", "defend", "combat", "weapon"],
    }

    def __init__(self):
        """Initialize with embedding model."""
        self.embedding_service: Optional[ImageDetectionService] = None
        self._initialize_model()

        # Pre-compute embeddings for action type keywords
        self._action_embeddings: Dict[str, np.ndarray] = {}
        self._precompute_action_embeddings()

    def _initialize_model(self):
        """Initialize the sentence transformer model."""
        try:
            self.embedding_service = ImageDetectionService()
            logger.info("RL-145: Initialized adaptive narration with embedding model")
        except Exception as e:
            logger.error(f"RL-145: Error initializing embedding model: {e}")

    def _precompute_action_embeddings(self):
        """Pre-compute embeddings for action type keywords."""
        if not self.embedding_service or not self.embedding_service._model:
            return

        try:
            with torch.inference_mode():
                for action_type, keywords in self.ACTION_TYPE_KEYWORDS.items():
                    # Combine keywords into a single string for embedding
                    keyword_text = " ".join(keywords)
                    embedding = self.embedding_service._model.encode(
                        keyword_text,
                        convert_to_tensor=True,
                        show_progress_bar=False,
                        normalize_embeddings=True,
                    )
                    self._action_embeddings[action_type] = embedding.cpu().numpy()

            logger.info(
                f"RL-145: Pre-computed embeddings for {len(self._action_embeddings)} action types"
            )
        except Exception as e:
            logger.error(f"RL-145: Error pre-computing action embeddings: {e}")

    def _get_action_type(self, description: str, ability: str) -> str:
        """
        Determine action type using semantic similarity.

        Args:
            description: Tool description (e.g., "checking for footprints")
            ability: Ability/skill name (e.g., "Survival", "Perception")

        Returns:
            Action type key (e.g., "tracking", "perception", "generic")
        """
        if not self.embedding_service or not self.embedding_service._model:
            return "generic"

        # Combine description and ability for better context
        query_text = f"{ability} {description}".lower()

        try:
            with torch.inference_mode():
                query_embedding = (
                    self.embedding_service._model.encode(
                        query_text,
                        convert_to_tensor=True,
                        show_progress_bar=False,
                        normalize_embeddings=True,
                    )
                    .cpu()
                    .numpy()
                )

            # Find most similar action type
            best_match = "generic"
            best_similarity = 0.0

            for action_type, action_embedding in self._action_embeddings.items():
                similarity = float(np.dot(query_embedding, action_embedding))
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = action_type

            logger.debug(
                f"RL-145: Action type '{best_match}' matched with "
                f"similarity {best_similarity:.3f} for '{query_text}'"
            )

            return best_match

        except Exception as e:
            logger.error(f"RL-145: Error determining action type: {e}")
            return "generic"

    def generate_narration(
        self, tool_name: str, tool_args: Dict, player_action: Optional[str] = None
    ) -> str:
        """
        Generate contextual narration for a tool call.

        Args:
            tool_name: Name of the tool (e.g., "request_player_roll")
            tool_args: Tool arguments dict
            player_action: Optional player action text for context

        Returns:
            Natural narrative text

        Example:
            Input:
                tool_name="request_player_roll"
                tool_args={"ability_or_skill": "Survival", "description": "tracking footprints"}
            Output:
                "You examine the ground near the path, looking for tracks."
        """
        if tool_name != "request_player_roll":
            # For non-roll tools, return simple generic narration
            return "You take action."

        # Extract context from tool arguments
        ability = tool_args.get("ability_or_skill", "")
        description = tool_args.get("description", "")

        # Clean description to work with templates
        # Remove gerunds that conflict with template verbs
        cleaned_desc = self._clean_description_for_template(description)

        # Determine what the target is (what player is acting on)
        target = cleaned_desc if cleaned_desc else f"using {ability}"

        # Get semantic action type
        action_type = self._get_action_type(description, ability)

        # Get appropriate templates
        templates = self.NARRATIVE_TEMPLATES.get(action_type, self.NARRATIVE_TEMPLATES["generic"])

        # Use first template and fill in target
        # In future: could use embedding similarity to pick best template variant
        import random

        template = random.choice(templates)

        # Fill in the template
        if "{target}" in template:
            narration = template.replace("{target}", target)
        else:
            narration = template

        logger.info(
            f"RL-145: Generated adaptive narration (action_type={action_type}): "
            f"'{narration[:100]}...'"
        )

        return narration

    @staticmethod
    def _clean_description_for_template(description: str) -> str:
        """
        Clean description to work with narrative templates.

        Removes gerunds (-ing verbs) at the start since templates already have action verbs.

        Examples:
            "examining the signpost" -> "the signpost"
            "checking for footprints" -> "for footprints"
            "searching the ground for traps" -> "the ground for traps"

        Args:
            description: Raw description from tool args

        Returns:
            Cleaned description suitable for template insertion
        """
        import re

        if not description:
            return description

        # Pattern to match common gerunds at the start
        # Examples: "examining", "checking", "searching", "looking", "scanning", etc.
        gerund_pattern = r"^(examining|checking|searching|looking|scanning|investigating|inspecting|studying|watching|observing|analyzing|tracking|following|moving|climbing|hiding|sneaking|approaching|attempting|trying|deciphering|interpreting|reading|understanding|identifying|recognizing|discovering|finding|locating|detecting|spotting|noticing|sensing)\s+"

        # Remove the gerund
        cleaned = re.sub(gerund_pattern, "", description, flags=re.IGNORECASE)

        # If we removed a gerund and the result starts with an article, keep it
        # If it starts with a preposition ("for", "at", "on"), keep it
        # Otherwise, add "the" if it makes sense
        if cleaned != description and cleaned:
            # Check if it starts with common articles or prepositions
            if not re.match(
                r"^(the|a|an|for|at|on|in|through|around|over|under|to|from)\s",
                cleaned,
                re.IGNORECASE,
            ):
                # Try to intelligently add "the" if the text seems like it needs it
                # e.g., "signpost" -> "the signpost", but "footprints" -> "footprints"
                if re.match(r"^[a-z]+\s+(for|at|on|in)", cleaned, re.IGNORECASE):
                    # e.g., "ground for traps" -> "the ground for traps"
                    cleaned = f"the {cleaned}"
                elif re.match(r"^[a-z]+(s)?\s*$", cleaned, re.IGNORECASE):
                    # Single word or phrase
                    cleaned = f"the {cleaned}"

        return cleaned or description  # Fallback to original if cleaning failed


# Singleton instance
_adaptive_narration_instance: Optional[AdaptiveNarrationService] = None


def get_adaptive_narration_service() -> AdaptiveNarrationService:
    """Get or create singleton AdaptiveNarrationService instance."""
    global _adaptive_narration_instance
    if _adaptive_narration_instance is None:
        _adaptive_narration_instance = AdaptiveNarrationService()
    return _adaptive_narration_instance
