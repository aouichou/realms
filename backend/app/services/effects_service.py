"""
Active Effects Service

Manages temporary buffs, debuffs, conditions, and spell effects on characters.
Handles effect application, duration tracking, concentration, and expiration.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.logger import get_logger
from app.observability.tracing import get_tracer, trace_async
from app.schemas.effects import ActiveEffect, EffectDuration, EffectType

logger = get_logger(__name__)


class EffectsService:
    """Service for managing active effects on characters."""

    @staticmethod
    @trace_async("effects.apply")
    async def apply_effect(
        db: AsyncSession,
        character_id: UUID,
        name: str,
        effect_type: EffectType,
        duration_type: EffectDuration,
        session_id: Optional[UUID] = None,
        description: Optional[str] = None,
        source: Optional[str] = None,
        duration_value: Optional[int] = None,
        bonus_value: int = 0,
        dice_bonus: Optional[str] = None,
        advantage: bool = False,
        disadvantage: bool = False,
        requires_concentration: bool = False,
        stacks: bool = False,
    ) -> ActiveEffect:
        """
        Apply a new effect to a character.

        Args:
            db: Database session
            character_id: Character to apply effect to
            name: Effect name (e.g., "Bless", "Poisoned")
            effect_type: Type of effect (buff, debuff, condition, etc.)
            duration_type: How duration is measured
            session_id: Game session (optional)
            description: Effect description
            source: What caused this effect
            duration_value: Number of rounds/minutes/hours
            bonus_value: Numeric bonus (e.g., +1d4)
            dice_bonus: Dice bonus notation (e.g., "1d4")
            advantage: Grants advantage on rolls
            disadvantage: Imposes disadvantage
            requires_concentration: Spell needs concentration
            stacks: Can multiple instances exist

        Returns:
            Created ActiveEffect instance
        """
        tracer = get_tracer()
        with tracer.start_as_current_span("effects.calculate") as span:
            span.set_attribute("effect.name", name)
            span.set_attribute("effect.type", effect_type.value)
            span.set_attribute("effect.duration_type", duration_type.value)
            span.set_attribute("effect.requires_concentration", requires_concentration)
            span.set_attribute("character_id", str(character_id))
            if duration_value:
                span.set_attribute("effect.duration_value", duration_value)

        # If requires concentration, end other concentration effects
        if requires_concentration:
            await EffectsService.break_concentration(db, character_id)

        # Check if effect already exists and doesn't stack
        if not stacks:
            existing = await db.execute(
                select(ActiveEffect).where(
                    ActiveEffect.character_id == character_id,
                    ActiveEffect.name == name,
                    ActiveEffect.is_active,
                )
            )
            existing_effect = existing.scalar_one_or_none()
            if existing_effect:
                # Refresh duration instead of creating new
                if duration_value:
                    existing_effect.rounds_remaining = duration_value
                if duration_type == EffectDuration.MINUTES and duration_value:
                    existing_effect.expires_at = datetime.datetime.now(timezone.utc) + timedelta(
                        minutes=duration_value
                    )
                elif duration_type == EffectDuration.HOURS and duration_value:
                    existing_effect.expires_at = datetime.datetime.now(timezone.utc) + timedelta(
                        hours=duration_value
                    )
                await db.commit()
                await db.refresh(existing_effect)
                return existing_effect

        # Calculate expiration time for time-based effects
        expires_at = None
        if duration_type == EffectDuration.MINUTES and duration_value:
            expires_at = datetime.datetime.now(timezone.utc) + timedelta(minutes=duration_value)
        elif duration_type == EffectDuration.HOURS and duration_value:
            expires_at = datetime.datetime.now(timezone.utc) + timedelta(hours=duration_value)

        # Create new effect
        effect = ActiveEffect(
            character_id=character_id,
            session_id=session_id,
            name=name,
            effect_type=effect_type,
            description=description or f"{name} effect",
            source=source,
            duration_type=duration_type,
            duration_value=duration_value,
            rounds_remaining=duration_value if duration_type == EffectDuration.ROUNDS else None,
            expires_at=expires_at,
            bonus_value=bonus_value,
            dice_bonus=dice_bonus,
            advantage=advantage,
            disadvantage=disadvantage,
            requires_concentration=requires_concentration,
            stacks=stacks,
            is_active=True,
        )

        db.add(effect)
        await db.commit()
        await db.refresh(effect)

        logger.info(f"Applied effect '{name}' to character {character_id}")
        return effect

    @staticmethod
    async def get_active_effects(
        db: AsyncSession, character_id: UUID, session_id: Optional[UUID] = None
    ) -> list[ActiveEffect]:
        """
        Get all active effects for a character.

        Args:
            db: Database session
            character_id: Character ID
            session_id: Optional session filter

        Returns:
            List of active effects
        """
        query = select(ActiveEffect).where(
            ActiveEffect.character_id == character_id, ActiveEffect.is_active
        )

        if session_id:
            query = query.where(ActiveEffect.session_id == session_id)

        result = await db.execute(query.order_by(ActiveEffect.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    @trace_async("effects.remove")
    async def remove_effect(db: AsyncSession, effect_id: int) -> bool:
        """
        Remove an active effect.

        Args:
            db: Database session
            effect_id: Effect ID to remove

        Returns:
            True if removed, False if not found
        """
        tracer = get_tracer()
        result = await db.execute(select(ActiveEffect).where(ActiveEffect.id == effect_id))
        effect = result.scalar_one_or_none()

        with tracer.start_as_current_span("effects.remove_execute") as span:
            span.set_attribute("effect.id", effect_id)
            if effect:
                span.set_attribute("effect.name", effect.name)
                span.set_attribute("effect.type", effect.effect_type.value)
                span.set_attribute("character_id", str(effect.character_id))
                effect.is_active = False
                await db.commit()
                logger.info(f"Removed effect '{effect.name}' (ID: {effect_id})")
                return True

            span.set_attribute("effect.found", False)
            return False

    @staticmethod
    async def break_concentration(db: AsyncSession, character_id: UUID) -> int:
        """
        Break concentration on all spells for a character.

        Called when character takes damage, is incapacitated, or casts new concentration spell.

        Args:
            db: Database session
            character_id: Character ID

        Returns:
            Number of effects ended
        """
        result = await db.execute(
            select(ActiveEffect).where(
                ActiveEffect.character_id == character_id,
                ActiveEffect.requires_concentration,
                ActiveEffect.is_active,
            )
        )
        concentration_effects = result.scalars().all()

        count = 0
        for effect in concentration_effects:
            effect.is_active = False
            count += 1

        if count > 0:
            await db.commit()
            logger.info(f"Broke concentration on {count} effect(s) for character {character_id}")

        return count

    @staticmethod
    @trace_async("effects.process_round_end")
    async def process_round_end(db: AsyncSession, character_id: UUID) -> list[str]:
        """
        Process end of combat round for a character.

        Decrements round-based effects and removes expired ones.

        Args:
            db: Database session
            character_id: Character ID

        Returns:
            List of effect names that expired
        """
        tracer = get_tracer()
        with tracer.start_as_current_span("effects.tick_processing") as span:
            span.set_attribute("character_id", str(character_id))

            effects = await EffectsService.get_active_effects(db, character_id)
            expired_names = []
            span.set_attribute("effects.count", len(effects))

            for effect in effects:
                if effect.duration_type == EffectDuration.ROUNDS:
                    logger.debug(
                        f"Processing effect tick: {effect.name}",
                        extra={
                            "extra_data": {
                                "effect_id": effect.id,
                                "effect_name": effect.name,
                                "effect_type": effect.effect_type.value,
                                "rounds_remaining": effect.rounds_remaining,
                                "requires_concentration": effect.requires_concentration,
                                "character_id": str(character_id),
                            }
                        },
                    )
                    if effect.decrement_duration():
                        expired_names.append(effect.name)
                        logger.info(f"Effect '{effect.name}' expired for character {character_id}")

            span.set_attribute("effects.expired_count", len(expired_names))
            await db.commit()
            return expired_names

    @staticmethod
    async def process_rest(
        db: AsyncSession, character_id: UUID, is_long_rest: bool = False
    ) -> list[str]:
        """
        Process rest for a character, removing appropriate effects.

        Args:
            db: Database session
            character_id: Character ID
            is_long_rest: True for long rest, False for short rest

        Returns:
            List of effect names that were removed
        """
        query = select(ActiveEffect).where(
            ActiveEffect.character_id == character_id, ActiveEffect.is_active
        )

        if is_long_rest:
            # Long rest removes almost everything except permanent effects
            query = query.where(ActiveEffect.duration_type != EffectDuration.PERMANENT)
        else:
            # Short rest only removes UNTIL_SHORT_REST effects
            query = query.where(ActiveEffect.duration_type == EffectDuration.UNTIL_SHORT_REST)

        result = await db.execute(query)
        effects_to_remove = result.scalars().all()

        removed_names = []
        for effect in effects_to_remove:
            effect.is_active = False
            removed_names.append(effect.name)

        if removed_names:
            await db.commit()
            rest_type = "long" if is_long_rest else "short"
            logger.info(
                f"Removed {len(removed_names)} effect(s) after {rest_type} rest for character {character_id}"
            )

        return removed_names

    @staticmethod
    async def cleanup_expired_effects(db: AsyncSession) -> int:
        """
        Remove all expired effects from database.

        Should be called periodically (e.g., every minute).

        Args:
            db: Database session

        Returns:
            Number of effects cleaned up
        """
        result = await db.execute(
            select(ActiveEffect).where(ActiveEffect.is_active, ActiveEffect.expires_at.isnot(None))
        )
        effects = result.scalars().all()

        count = 0
        for effect in effects:
            if effect.is_expired():
                effect.is_active = False
                count += 1

        if count > 0:
            await db.commit()
            logger.info(f"Cleaned up {count} expired effect(s)")

        return count
