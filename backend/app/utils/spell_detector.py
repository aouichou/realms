"""
Spell detection utility for auto-detecting spell casts in player actions.
Automatically looks up spell levels and manages spell slot consumption.
"""

import logging
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.character import Character
from app.db.models.spell import Spell

logger = logging.getLogger(__name__)


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_closest_spell(typo: str, known_spells: list[str], max_distance: int = 2) -> Optional[str]:
    """Find closest matching spell using fuzzy matching.

    Args:
        typo: The misspelled spell name
        known_spells: List of character's known spells
        max_distance: Maximum Levenshtein distance to consider (default: 2)

    Returns:
        Closest matching spell name or None
    """
    typo_lower = typo.lower()
    best_match = None
    best_distance = max_distance + 1

    for spell in known_spells:
        if not isinstance(spell, str):
            continue

        spell_lower = spell.lower()
        distance = levenshtein_distance(typo_lower, spell_lower)

        if distance < best_distance:
            best_distance = distance
            best_match = spell

    return best_match if best_distance <= max_distance else None


async def detect_spell_cast(
    player_action: str, character: Character, db: AsyncSession
) -> tuple[Optional[str], int, Optional[str], Optional[str]]:
    """
    Detect spell name and level from player action.

    Uses character_spells table as source of truth, checking is_known or is_prepared
    based on character class spellcasting type.

    Args:
        player_action: The player's action text
        character: Character object
        db: Database session

    Returns:
        tuple: (spell_name, spell_level, warning, suggestion)
        - spell_name: Detected spell name or None
        - spell_level: Spell level (0 for cantrips) or 0 if not detected
        - warning: Warning message for UI or None
        - suggestion: Spell suggestion for typos or None

    Examples:
        "I cast Fireball at the goblins" -> ("Fireball", 3, None, None)
        "I cast firreball" -> ("Fireball", 3, None, "Did you mean 'Fireball'?")
        "I cast Unknown Spell" -> (None, 0, "You don't know that spell", None)
    """
    if not player_action:
        return None, 0, None, None

    # Determine spellcasting type based on class
    # Spontaneous casters: Bard, Sorcerer, Warlock, Ranger (cast any known spell)
    # Prepared casters: Cleric, Druid, Paladin, Wizard (can only cast prepared spells)
    spontaneous_classes = {"Bard", "Sorcerer", "Warlock", "Ranger"}
    is_spontaneous = character.character_class in spontaneous_classes

    # Query character's spells from character_spells table
    try:
        from sqlalchemy import select

        from app.db.models import CharacterSpell

        # For spontaneous casters: check is_known
        # For prepared casters: check is_prepared
        if is_spontaneous:
            result = await db.execute(
                select(CharacterSpell).where(
                    CharacterSpell.character_id == character.id, CharacterSpell.is_known
                )
            )
        else:
            result = await db.execute(
                select(CharacterSpell).where(
                    CharacterSpell.character_id == character.id, CharacterSpell.is_prepared
                )
            )

        char_spells = result.scalars().all()
        character_spell_ids = {str(cs.spell_id) for cs in char_spells}

        if not character_spell_ids:
            logger.debug(
                f"Character {character.name} ({character.character_class}) has no "
                f"{'known' if is_spontaneous else 'prepared'} spells"
            )
            # Continue anyway - we'll check against all spells and warn
        else:
            logger.debug(
                f"Character {character.name} has {len(character_spell_ids)} "
                f"{'known' if is_spontaneous else 'prepared'} spells"
            )
    except Exception as e:
        logger.error(f"Failed to query character spells: {e}")
        character_spell_ids = set()

    # Spell casting patterns
    cast_patterns = [
        r"(?:cast|use|invoke|channel)\s+['\"]?([a-zA-Z\s'-]+?)['\"]?\s+(?:at|on|to|toward)",
        r"(?:cast|use|invoke|channel)\s+['\"]?([a-zA-Z\s'-]+?)['\"]?(?:\.|!|$)",
        r"I\s+['\"]?([a-zA-Z\s'-]+?)['\"]?\s+(?:at|on|the|to)",  # "I Fireball the orc"
    ]

    for pattern in cast_patterns:
        matches = re.finditer(pattern, player_action, re.IGNORECASE)

        for match in matches:
            potential_spell = match.group(1).strip()

            # Skip common non-spell words
            skip_words = {
                "attack",
                "hit",
                "strike",
                "move",
                "walk",
                "run",
                "hide",
                "sneak",
                "search",
                "look",
                "take",
                "grab",
                "open",
                "close",
                "talk",
                "speak",
                "say",
                "tell",
                "ask",
                "go",
                "try",
                "attempt",
            }
            if potential_spell.lower() in skip_words:
                continue

            # Try to look up spell in database by name
            result = await db.execute(select(Spell).where(Spell.name.ilike(potential_spell)))
            spell = result.scalar_one_or_none()

            if spell:
                # Found spell in database - verify character knows/prepared it
                if character_spell_ids:
                    spell_id_str = str(spell.id)
                    if spell_id_str not in character_spell_ids:
                        # Character doesn't know/prepared this spell
                        caster_verb = "prepared" if not is_spontaneous else "known"
                        logger.info(
                            f"Character tried to cast un{caster_verb} spell: '{spell.name}' "
                            f"(ID: {spell.id}, {character.character_class})"
                        )
                        warning = f"⚠️ You haven't {caster_verb} the spell '{spell.name}'"
                        return None, 0, warning, None
                else:
                    # No spells configured - allow any spell but warn
                    logger.warning(
                        f"Character {character.name} ({character.character_class}) "
                        f"has no spells configured. Allowing {spell.name} cast."
                    )

                logger.info(
                    f"Detected spell cast: {spell.name} (Level {spell.level}) "
                    f"by {character.name} ({character.character_class})"
                )
                return spell.name, spell.level, None, None

            # Spell not found by exact name - try fuzzy matching against character's spells
            if character_spell_ids:
                # Load all character's spells for fuzzy matching
                result = await db.execute(
                    select(Spell).where(Spell.id.in_([int(sid) for sid in character_spell_ids]))
                )
                available_spells = result.scalars().all()
                available_spell_names = [s.name for s in available_spells]

                closest_spell = find_closest_spell(potential_spell, available_spell_names)
                if closest_spell:
                    # Found a close match - suggest it
                    logger.info(
                        f"Fuzzy match found: '{potential_spell}' -> '{closest_spell}' "
                        f"for {character.name}"
                    )
                    result = await db.execute(select(Spell).where(Spell.name.ilike(closest_spell)))
                    spell = result.scalar_one_or_none()
                    if spell:
                        suggestion = f"Did you mean '{spell.name}'?"
                        return spell.name, spell.level, None, suggestion

            # Pattern matched but spell not found or not known
            logger.info(f"Unknown spell attempted: '{potential_spell}' by {character.name}")
            warning = f"⚠️ The spell '{potential_spell}' doesn't exist or you don't know it"
            return None, 0, warning, None

    # No spell detected
    return None, 0, None, None


def can_cast_spell(character: Character, spell_level: int) -> tuple[bool, str]:
    """
    Check if character has available spell slots for a given spell level.

    Args:
        character: Character object
        spell_level: Spell level (0 for cantrips)

    Returns:
        tuple: (can_cast: bool, reason: str)

    Examples:
        can_cast_spell(char, 0) -> (True, "Cantrips don't require spell slots")
        can_cast_spell(char, 3) -> (True, "")
        can_cast_spell(char, 5) -> (False, "No 5th level spell slots remaining")
    """
    # Cantrips are free
    if spell_level == 0:
        return True, "Cantrips don't require spell slots"

    # Check spell slots
    spell_slots = character.spell_slots or {}

    # Convert spell_level to string key (database stores as string keys)
    slot_key = str(spell_level)

    if slot_key not in spell_slots:
        return False, f"Character doesn't have {spell_level}th level spell slots"

    remaining_slots = spell_slots.get(slot_key, 0)

    if remaining_slots <= 0:
        return False, f"No {spell_level}th level spell slots remaining"

    return True, ""


def consume_spell_slot(character: Character, spell_level: int) -> tuple[bool, Optional[str]]:
    """
    Consume a spell slot for casting a spell.

    Args:
        character: Character object (will be modified in place)
        spell_level: Spell level (0 for cantrips)

    Returns:
        tuple: (success: bool, warning: Optional[str])
        - success: True if slot was consumed or cantrip, False otherwise
        - warning: Warning message if slot couldn't be consumed, None otherwise

    Note:
        - Cantrips (level 0) don't consume slots
        - Modifies character.spell_slots in place
        - Caller must use flag_modified() and flush/commit to persist changes
    """
    # Cantrips don't consume slots
    if spell_level == 0:
        logger.debug("Cantrip cast - no spell slot consumed")
        return True, None

    # Check if can cast
    can_cast, reason = can_cast_spell(character, spell_level)
    if not can_cast:
        logger.warning(f"Cannot cast spell: {reason}")
        # Return user-friendly warning
        ordinal = (
            "st"
            if spell_level == 1
            else "nd"
            if spell_level == 2
            else "rd"
            if spell_level == 3
            else "th"
        )
        warning = f"⚠️ No {spell_level}{ordinal} level spell slots remaining"
        return False, warning

    # Consume slot
    spell_slots = character.spell_slots or {}
    slot_key = str(spell_level)

    if slot_key in spell_slots:
        spell_slots[slot_key] -= 1
        character.spell_slots = spell_slots  # Reassign to trigger SQLAlchemy detection
        logger.info(
            f"Consumed {spell_level}th level spell slot for {character.name}. "
            f"Remaining: {spell_slots[slot_key]}"
        )
        return True, None

    return False, None
