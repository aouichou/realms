"""
Companion AI service for generating companion NPC responses.
Uses Google Gemini to provide distinct personality from DM.
"""

import random
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.character import Character
from app.db.models.companion import Companion
from app.observability.logger import get_logger
from app.observability.metrics import metrics
from app.observability.tracing import get_tracer, trace_async
from app.services.gemini_service import GeminiService

logger = get_logger(__name__)


class CompanionService:
    """
    AI service for companion NPCs.

    Handles companion personality, decision-making, and responses
    using Google Gemini (separate from DM's Mistral).
    """

    def __init__(self, gemini_service: GeminiService):
        """
        Initialize companion AI service.

        Args:
            gemini_service: Configured GeminiService instance
        """
        self.gemini_service = gemini_service
        logger.info("CompanionService initialized with Google Gemini")

    @trace_async("companion.generate_response")
    async def generate_companion_response(
        self,
        companion: Companion,
        player_action: str,
        dm_narration: str,
        recent_context: list[dict[str, Any]],
        character: Character,
    ) -> str:
        """
        Generate companion's response to current situation.

        Args:
            companion: Companion model instance
            player_action: Player's recent action/message
            dm_narration: DM's recent narration
            recent_context: Recent conversation messages for context
            character: Player character for relationship context

        Returns:
            Companion's response as text
        """
        start_time = time.time()
        tracer = get_tracer()

        logger.info(f"Generating response for companion '{companion.name}'")

        # Build companion personality prompt
        prompt = self._build_companion_prompt(
            companion=companion,
            player_action=player_action,
            dm_narration=dm_narration,
            recent_context=recent_context,
            character=character,
        )

        try:
            # Generate response using Gemini with tracing
            with tracer.start_as_current_span("companion.gemini_call") as span:
                span.set_attribute("companion.name", companion.name)
                span.set_attribute("companion.personality", companion.personality)
                span.set_attribute("companion.loyalty", companion.loyalty or 50)  # type: ignore[arg-type]

                response = await self.gemini_service.generate_narration(
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.8,
                )

                span.set_attribute("response.length", len(response))

            # Add to companion's conversation memory
            companion.add_conversation_memory("dm", dm_narration)
            companion.add_conversation_memory("player", player_action)
            companion.add_conversation_memory("companion", response)

            # Record metrics
            duration = time.time() - start_time
            if hasattr(metrics, 'companion_responses_total'):
                metrics.companion_responses_total.labels(
                    companion_name=companion.name, status="success"
                ).inc()
                metrics.companion_response_duration_seconds.labels(
                    companion_name=companion.name
                ).observe(duration)

            logger.info(f"Companion '{companion.name}' responded: {response[:100]}...")
            return response

        except Exception as e:
            duration = time.time() - start_time

            # Record error metrics
            if hasattr(metrics, 'companion_responses_total'):
                metrics.companion_responses_total.labels(
                    companion_name=companion.name, status="error"
                ).inc()

            logger.error(f"Failed to generate companion response: {e}")
            return self._get_fallback_response(companion)

    def _build_companion_prompt(
        self,
        companion: Companion,
        player_action: str,
        dm_narration: str,
        recent_context: list[dict[str, Any]],
        character: Character,
    ) -> str:
        """Build the prompt for companion AI."""
        # SQLAlchemy attributes accessed at runtime - type ignore for static analysis
        str_mod = companion.get_stat_modifier(companion.strength)  # type: ignore[arg-type]
        dex_mod = companion.get_stat_modifier(companion.dexterity)  # type: ignore[arg-type]
        int_mod = companion.get_stat_modifier(companion.intelligence)  # type: ignore[arg-type]
        wis_mod = companion.get_stat_modifier(companion.wisdom)  # type: ignore[arg-type]
        cha_mod = companion.get_stat_modifier(companion.charisma)  # type: ignore[arg-type]

        abilities_desc = []
        if str_mod >= 3:
            abilities_desc.append("very strong")
        if dex_mod >= 3:
            abilities_desc.append("very agile")
        if int_mod >= 3:
            abilities_desc.append("highly intelligent")
        if wis_mod >= 3:
            abilities_desc.append("very wise")
        if cha_mod >= 3:
            abilities_desc.append("very charismatic")

        abilities_text = ", ".join(abilities_desc) if abilities_desc else "of average abilities"

        # Loyalty-based behavior modifiers - cast Column to int for type checking
        loyalty: int = companion.loyalty or 50  # type: ignore[assignment]
        loyalty_behavior = self._get_loyalty_behavior(loyalty)

        context_text = ""
        if recent_context:
            recent_messages = recent_context[-10:]
            context_lines = []
            for msg in recent_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]
                if role == "assistant":
                    context_lines.append(f"DM: {content}")
                elif role == "user":
                    context_lines.append(f"{character.name}: {content}")
            context_text = "\n".join(context_lines)

        prompt = f"""You are {companion.name}, a {companion.creature_name} companion.

**YOUR PERSONALITY:**
{companion.personality}

**YOUR GOALS:**
{companion.goals or "To assist your companion on their journey"}

**YOUR BACKGROUND:**
{companion.background or f"A {companion.creature_name} who has joined the party"}

**YOUR ABILITIES:**
You are {abilities_text}.
- Current HP: {companion.hp}/{companion.max_hp}
- Armor Class: {companion.ac}

**YOUR RELATIONSHIP WITH {character.name}:**
Status: {companion.relationship_status.replace("_", " ").title()}
Loyalty: {loyalty}/100

{loyalty_behavior}

**RECENT CONVERSATION:**
{context_text if context_text else "(No recent context)"}

**CURRENT SITUATION:**
DM narration: {dm_narration}

{character.name}'s action: {player_action}

**YOUR RESPONSE:**
Respond in character as {companion.name}. Your response should:
- Reflect your personality ({companion.personality})
- Consider your loyalty level ({loyalty}/100) and behavior: {self._get_loyalty_descriptor(loyalty)}  # type: ignore[arg-type]
- Be aware of your current state (HP: {companion.hp}/{companion.max_hp})
- Stay true to your goals: {companion.goals or "helping your companion"}
- Be 1-3 sentences, natural and conversational
- DO NOT narrate the scene - only speak as yourself
- DO NOT speak for {character.name} or describe their actions

Speak now as {companion.name}:"""

        return prompt

    def _get_loyalty_behavior(self, loyalty: int) -> str:
        """Get loyalty-based behavior guidelines."""
        if loyalty >= 80:
            return """**BEHAVIOR GUIDANCE (High Loyalty):**
You are deeply devoted to your companion. You:
- Offer protective and supportive comments
- Volunteer for dangerous tasks willingly
- Express genuine care and concern
- May occasionally show affection or admiration"""

        elif loyalty >= 60:
            return """**BEHAVIOR GUIDANCE (Good Loyalty):**
You are cooperative and helpful. You:
- Readily assist when asked
- Offer practical suggestions
- Maintain a professional but friendly demeanor
- Show respect for your companion's decisions"""

        elif loyalty >= 40:
            return """**BEHAVIOR GUIDANCE (Neutral Loyalty):**
You are pragmatic and businesslike. You:
- Fulfill your obligations but nothing more
- Speak matter-of-factly
- May express mild skepticism
- Keep emotional distance"""

        elif loyalty >= 20:
            return """**BEHAVIOR GUIDANCE (Low Loyalty):**
You are hesitant and questioning. You:
- May challenge or question decisions
- Express concerns openly
- Show reluctance for dangerous tasks
- Maintain a guarded or cautious tone"""

        else:
            return """**BEHAVIOR GUIDANCE (Very Low Loyalty):**
You are reluctant and possibly defiant. You:
- May openly disagree or argue
- Show frustration or resentment
- Consider your own interests first
- Might hint at leaving or refusing tasks"""

    def _get_loyalty_descriptor(self, loyalty: int) -> str:
        """Get a short descriptor for loyalty level."""
        if loyalty >= 80:
            return "devoted and protective"
        elif loyalty >= 60:
            return "cooperative and helpful"
        elif loyalty >= 40:
            return "neutral and pragmatic"
        elif loyalty >= 20:
            return "hesitant and questioning"
        else:
            return "reluctant and defiant"

    def _get_fallback_response(self, companion: Companion) -> str:
        """Generate a fallback response if AI generation fails."""
        personality_lower = companion.personality.lower()

        if "brave" in personality_lower or "bold" in personality_lower:
            return f"{companion.name} nods firmly, ready for whatever comes next."
        elif "cautious" in personality_lower or "careful" in personality_lower:
            return f"{companion.name} looks around warily, staying alert."
        elif "friendly" in personality_lower or "loyal" in personality_lower:
            return f"{companion.name} stays close, offering a reassuring presence."
        elif "curious" in personality_lower:
            return f"{companion.name} watches with keen interest."
        else:
            return f"{companion.name} remains at your side."

    @trace_async("companion.should_respond")
    async def should_companion_respond(
        self,
        companion: Companion,
        player_action: str,
        dm_narration: str,
        combat_active: bool = False,
    ) -> bool:
        """Determine if companion should speak in current situation."""
        tracer = get_tracer()

        with tracer.start_as_current_span("companion.check_response_criteria") as span:
            span.set_attribute("companion.name", companion.name)
            span.set_attribute("combat_active", combat_active)

            companion_name_lower = companion.name.lower()
            player_action_lower = player_action.lower()
            dm_narration_lower = dm_narration.lower()

            # Check combat turn
            if combat_active and f"{companion_name_lower}'s turn" in dm_narration_lower:
                span.set_attribute("reason", "combat_turn")
                return True

            # Check direct address
            if companion_name_lower in player_action_lower:
                span.set_attribute("reason", "direct_address")
                return True

            # Check opinion keywords
            opinion_keywords = [
                "what do you think",
                "your opinion",
                "companion",
                "what should we",
                "any ideas",
            ]
            if any(keyword in player_action_lower for keyword in opinion_keywords):
                span.set_attribute("reason", "opinion_request")
                return True

            # Check mentioned in narration
            if companion_name_lower in dm_narration_lower:
                span.set_attribute("reason", "mentioned_in_narration")
                return True

            # Random chance (10%)
            if random.random() < 0.1:
                span.set_attribute("reason", "random_chance")
                return True

            span.set_attribute("reason", "no_trigger")
            return False

    @trace_async("companion.update_loyalty")
    async def update_companion_loyalty(
        self,
        companion: Companion,
        event_description: str,
        loyalty_change: int,
        db: AsyncSession,
    ) -> None:
        """Update companion loyalty based on player actions."""
        tracer = get_tracer()

        with tracer.start_as_current_span("companion.calculate_loyalty") as span:
            old_loyalty = companion.loyalty  # type: ignore[assignment]
            companion.loyalty = max(0, min(100, companion.loyalty + loyalty_change))  # type: ignore[assignment,operator]

            logger.debug(
                f"Loyalty calculation for {companion.name}",
                extra={"extra_data": {
                    "companion_id": companion.id,
                    "companion_name": companion.name,
                    "old_loyalty": old_loyalty,
                    "loyalty_change": loyalty_change,
                    "new_loyalty": companion.loyalty,
                    "was_clamped": (old_loyalty + loyalty_change) != companion.loyalty,
                    "event_description": event_description[:100] if event_description else None
                }}
            )

            span.set_attribute("companion.name", companion.name)
            span.set_attribute("loyalty.old", old_loyalty)
            span.set_attribute("loyalty.new", companion.loyalty)  # type: ignore[arg-type]
            span.set_attribute("loyalty.change", loyalty_change)
            span.set_attribute("event", event_description[:100])

            # Use setattr to properly update SQLAlchemy columns
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(companion, "loyalty")

            # Update relationship status based on new loyalty
            if companion.loyalty >= 80:  # type: ignore[operator]
                companion.relationship_status = "trusted"  # type: ignore[assignment]
            elif companion.loyalty >= 60:  # type: ignore[operator]
                companion.relationship_status = "friend"  # type: ignore[assignment]
            elif companion.loyalty >= 40:  # type: ignore[operator]
                companion.relationship_status = "ally"  # type: ignore[assignment]
        elif companion.loyalty >= 20:  # type: ignore[operator]
            companion.relationship_status = "suspicious"  # type: ignore[assignment]
        else:
            companion.relationship_status = "just_met"  # type: ignore[assignment]
        flag_modified(companion, "relationship_status")

        companion.add_important_event(
            f"Loyalty changed from {old_loyalty} to {companion.loyalty}: {event_description}"  # type: ignore[str-format]
        )

        await db.commit()

        logger.info(
            f"Companion '{companion.name}' loyalty: {old_loyalty} -> {companion.loyalty} ({companion.relationship_status})"
        )
