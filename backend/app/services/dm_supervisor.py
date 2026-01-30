"""
DM Agentic Supervisor - RL-140
Validates DM responses against reference knowledge using semantic retrieval.
Implements trigger-based validation with silent regeneration on rule violations.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch

from app.services.image_detection_service import ImageDetectionService

logger = logging.getLogger(__name__)


class DMSupervisor:
    """
    Agentic supervisor that validates DM responses against D&D 5e rules.

    Design:
    - Trigger-based: Only validates when specific keywords detected (performance)
    - Silent regeneration: User never sees validation errors (immersion)
    - Semantic retrieval: Finds relevant rule sections from reference files
    - Comprehensive: Checks multiple common mistake patterns
    """

    def __init__(self):
        """Initialize supervisor with reference knowledge and embedding model."""
        self.knowledge_dir = Path(__file__).parent.parent / "dm_knowledge"
        self.reference_texts: Dict[str, str] = {}
        self.reference_chunks: List[Dict] = []
        self.chunk_embeddings: Optional[np.ndarray] = None
        self.model_service: Optional[ImageDetectionService] = None

        # Trigger keywords that indicate validation should run
        self.trigger_keywords = [
            "attack",
            "damage",
            "hit points",
            "hp",
            "roll",
            "dice",
            "d20",
            "combat",
            "initiative",
            "loot",
            "item",
            "spell",
            "cast",
            "heal",
            "hurt",
            "wound",
            "strike",
            "swing",
            "shoot",
            "stab",
        ]

        # Common mistake patterns to detect
        self.mistake_patterns = [
            {
                "name": "narrated_roll_result",
                "pattern": r"(you|player|character)\s+(roll|rolled|rolls)\s+(and\s+)?(hit|hits|miss|misses|get|gets|score|scores)",
                "explanation": "DM should use request_player_roll, not narrate roll results",
                "relevant_sections": ["Dice Rolling Protocol", "Common Mistakes"],
            },
            {
                "name": "narrated_npc_roll",
                "pattern": r"(goblin|monster|enemy|guard|bandit|creature|it|he|she|they)\s+(roll|rolled|rolls|hit|hits|deal|deals|attack|attacks)\s+(and|for|you)",
                "explanation": "DM should use roll_for_npc, not narrate NPC rolls",
                "relevant_sections": ["Dice Rolling Protocol", "roll_for_npc"],
            },
            {
                "name": "damage_without_tool",
                "pattern": r"(take|takes|deals?|suffering?|loses?)\s+\d+\s+(damage|hp|hit points)",
                "explanation": "Must use update_character_hp when mentioning damage",
                "relevant_sections": ["HP Management", "update_character_hp"],
            },
            {
                "name": "specific_roll_number",
                "pattern": r"(roll|rolled|rolls|score|scores|get|gets)\s+(a\s+)?\d{1,2}(\s+|$)",
                "explanation": "DM should not narrate specific roll numbers without using tools",
                "relevant_sections": ["Dice Rolling Protocol", "Tool Usage Rules"],
            },
        ]

        self._load_reference_knowledge()
        self._initialize_model()
        self._chunk_and_embed_references()

    def _load_reference_knowledge(self):
        """Load all markdown files from dm_knowledge directory."""
        try:
            for md_file in self.knowledge_dir.glob("*.md"):
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.reference_texts[md_file.stem] = content
                    logger.info(f"RL-140: Loaded {md_file.name} ({len(content)} chars)")
        except Exception as e:
            logger.error(f"RL-140: Error loading reference knowledge: {e}")

    def _initialize_model(self):
        """Initialize the sentence transformer model for embeddings."""
        try:
            self.model_service = ImageDetectionService()
            logger.info("RL-140: Initialized embedding model for semantic retrieval")
        except Exception as e:
            logger.error(f"RL-140: Error initializing model: {e}")

    def _chunk_and_embed_references(self):
        """Split reference texts into chunks and create embeddings."""
        try:
            chunks = []

            for file_name, content in self.reference_texts.items():
                # Split into sections (by headers)
                sections = re.split(r"\n##\s+", content)

                for i, section in enumerate(sections):
                    if not section.strip():
                        continue

                    # Extract section title
                    lines = section.split("\n", 1)
                    title = lines[0].strip("#").strip() if lines else f"Section {i}"
                    section_content = lines[1] if len(lines) > 1 else section

                    # Further split large sections into smaller chunks
                    paragraphs = section_content.split("\n\n")
                    current_chunk = []
                    current_length = 0

                    for para in paragraphs:
                        para_length = len(para)

                        # If adding this paragraph exceeds 1000 chars, save current chunk
                        if current_length + para_length > 1000 and current_chunk:
                            chunk_text = "\n\n".join(current_chunk)
                            chunks.append(
                                {
                                    "file": file_name,
                                    "section": title,
                                    "text": chunk_text,
                                    "preview": chunk_text[:200] + "..."
                                    if len(chunk_text) > 200
                                    else chunk_text,
                                }
                            )
                            current_chunk = []
                            current_length = 0

                        current_chunk.append(para)
                        current_length += para_length

                    # Save remaining chunk
                    if current_chunk:
                        chunk_text = "\n\n".join(current_chunk)
                        chunks.append(
                            {
                                "file": file_name,
                                "section": title,
                                "text": chunk_text,
                                "preview": chunk_text[:200] + "..."
                                if len(chunk_text) > 200
                                else chunk_text,
                            }
                        )

            self.reference_chunks = chunks
            logger.info(f"RL-140: Created {len(chunks)} reference chunks")

            # Generate embeddings for all chunks
            if self.model_service and self.model_service._model and chunks:
                chunk_texts = [c["text"] for c in chunks]
                embeddings = []

                with torch.inference_mode():
                    for text in chunk_texts:
                        embedding = self.model_service._model.encode(
                            text, convert_to_tensor=True, show_progress_bar=False
                        )
                        embeddings.append(embedding.cpu().numpy())

                self.chunk_embeddings = np.array(embeddings)
                logger.info(f"RL-140: Generated embeddings for {len(embeddings)} chunks")

        except Exception as e:
            logger.error(f"RL-140: Error chunking and embedding references: {e}")

    def detect_triggers(self, player_input: str, dm_response: str) -> bool:
        """
        Check if validation should run based on trigger keywords.

        Args:
            player_input: What the player said/did
            dm_response: DM's generated response

        Returns:
            True if triggers detected, False otherwise
        """
        combined_text = (player_input + " " + dm_response).lower()

        for keyword in self.trigger_keywords:
            if keyword in combined_text:
                logger.debug(f"RL-140: Trigger detected: '{keyword}'")
                return True

        return False

    def _get_relevant_sections(self, context: str, top_k: int = 3) -> List[Dict]:
        """
        Semantic retrieval of relevant rule sections.

        Args:
            context: Text to find relevant rules for (player input + DM response)
            top_k: Number of most relevant chunks to return

        Returns:
            List of relevant chunk dictionaries with similarity scores
        """
        if not self.model_service or self.chunk_embeddings is None:
            return []

        try:
            # Generate embedding for context
            if not self.model_service or not self.model_service._model:
                return []

            with torch.inference_mode():
                query_embedding = (
                    self.model_service._model.encode(
                        context, convert_to_tensor=True, show_progress_bar=False
                    )
                    .cpu()
                    .numpy()
                )

            # Calculate cosine similarity with all chunks
            similarities = []
            for i, chunk_emb in enumerate(self.chunk_embeddings):
                # Cosine similarity
                similarity = np.dot(query_embedding, chunk_emb) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_emb)
                )
                similarities.append((i, similarity))

            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Get top K
            relevant_chunks = []
            for idx, similarity in similarities[:top_k]:
                chunk = self.reference_chunks[idx].copy()
                chunk["similarity"] = float(similarity)
                relevant_chunks.append(chunk)

            return relevant_chunks

        except Exception as e:
            logger.error(f"RL-140: Error in semantic retrieval: {e}")
            return []

    def _check_tool_calls(self, dm_response: str, tool_calls: Optional[List[Dict]]) -> List[str]:
        """
        Check if appropriate tools were called given the response content.

        Args:
            dm_response: The DM's generated response
            tool_calls: List of tool calls made (if any)

        Returns:
            List of issues found (empty if valid)
        """
        issues = []
        tool_names = [tc.get("name") for tc in (tool_calls or [])]
        response_lower = dm_response.lower()

        # Check for damage mentions without update_character_hp
        if any(
            word in response_lower for word in ["damage", "hp", "hit points", "hurt", "wounded"]
        ):
            if "update_character_hp" not in tool_names:
                # Only flag if specific damage numbers mentioned
                if re.search(r"\d+\s+(damage|hp)", response_lower):
                    issues.append("Mentioned damage/HP change but didn't call update_character_hp")

        # Check for roll mentions without appropriate roll tools
        if any(word in response_lower for word in ["roll", "rolled", "dice", "d20"]):
            if "request_player_roll" not in tool_names and "roll_for_npc" not in tool_names:
                # Check if it's actually narrating a roll result (bad) or just mentioning rolling (ok)
                if re.search(
                    r"(you|player|character|goblin|monster|enemy)\s+(roll|rolled)", response_lower
                ):
                    issues.append(
                        "Mentioned rolling but didn't call request_player_roll or roll_for_npc"
                    )

        # Check for loot mentions without give_item
        if any(word in response_lower for word in ["loot", "treasure", "find", "discover"]):
            if "item" in response_lower or "gold" in response_lower or "potion" in response_lower:
                if "give_item" not in tool_names and "search_items" not in tool_names:
                    # Only flag if specific items mentioned
                    if re.search(r"(healing potion|sword|armor|gold pieces|item)", response_lower):
                        issues.append(
                            "Mentioned specific loot but didn't call search_items or give_item"
                        )

        return issues

    def _check_mistake_patterns(self, dm_response: str) -> List[Dict]:
        """
        Check response against known mistake patterns.

        Args:
            dm_response: The DM's generated response

        Returns:
            List of detected mistakes with explanations
        """
        detected = []

        for mistake in self.mistake_patterns:
            if re.search(mistake["pattern"], dm_response, re.IGNORECASE):
                detected.append(
                    {
                        "type": mistake["name"],
                        "explanation": mistake["explanation"],
                        "relevant_sections": mistake["relevant_sections"],
                    }
                )
                logger.debug(f"RL-140: Detected mistake pattern: {mistake['name']}")

        return detected

    async def validate_response(
        self, player_input: str, dm_response: str, tool_calls: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Validate DM response against rules.

        Args:
            player_input: What the player said/did
            dm_response: DM's generated response
            tool_calls: List of tool calls made (if any)

        Returns:
            Validation result dictionary:
            {
                "valid": bool,
                "confidence": float (0-1),
                "issues": List[str],
                "mistakes": List[Dict],
                "relevant_rules": List[str],
                "should_regenerate": bool
            }
        """
        try:
            # Build context for semantic retrieval
            context = f"Player: {player_input}\nDM: {dm_response}"

            # Check for mistake patterns
            detected_mistakes = self._check_mistake_patterns(dm_response)

            # Check tool usage
            tool_issues = self._check_tool_calls(dm_response, tool_calls)

            # Get relevant rule sections
            relevant_chunks = self._get_relevant_sections(context, top_k=3)

            # Determine if response is valid
            has_mistakes = len(detected_mistakes) > 0
            has_tool_issues = len(tool_issues) > 0
            is_valid = not (has_mistakes or has_tool_issues)

            # Calculate confidence (lower = more certain there's an issue)
            confidence = 1.0
            if has_mistakes:
                confidence -= 0.4
            if has_tool_issues:
                confidence -= 0.3
            # Adjust based on how well context matches rules
            if relevant_chunks and relevant_chunks[0]["similarity"] > 0.7:
                confidence -= 0.2  # High similarity suggests rule relevance

            confidence = max(0.0, min(1.0, confidence))

            # Compile all issues
            all_issues = tool_issues + [m["explanation"] for m in detected_mistakes]

            # Extract relevant rule text
            relevant_rules = []
            for chunk in relevant_chunks:
                relevant_rules.append(f"## {chunk['section']} ({chunk['file']})\n{chunk['text']}")

            # Determine if should regenerate (only if confidence of mistake is high)
            should_regenerate = not is_valid and confidence < 0.7

            result = {
                "valid": is_valid,
                "confidence": confidence,
                "issues": all_issues,
                "mistakes": detected_mistakes,
                "relevant_rules": relevant_rules,
                "should_regenerate": should_regenerate,
            }

            if not is_valid:
                logger.warning(f"RL-140: Validation failed. Issues: {all_issues}")

            return result

        except Exception as e:
            logger.error(f"RL-140: Error during validation: {e}")
            # On error, default to valid (don't block)
            return {
                "valid": True,
                "confidence": 1.0,
                "issues": [],
                "mistakes": [],
                "relevant_rules": [],
                "should_regenerate": False,
            }


# Singleton instance
_supervisor_instance: Optional[DMSupervisor] = None


def get_dm_supervisor() -> DMSupervisor:
    """Get or create singleton DMSupervisor instance."""
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = DMSupervisor()
    return _supervisor_instance
