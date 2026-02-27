"""
Roll Tag Parser Service

Parses DM narration text for embedded dice roll tags and extracts
structured roll request information.

Supported tag formats:
- [ROLL:attack:d20+5] - Attack roll with modifier
- [ROLL:save:dex:DC15] - Saving throw with ability and DC
- [ROLL:check:perception:DC12] - Ability check with DC
- [ROLL:damage:2d6+3] - Damage roll
- [ROLL:initiative:d20+2] - Initiative roll
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class RollType(str, Enum):
    """Types of dice rolls in D&D 5e"""

    ATTACK = "attack"
    SAVE = "save"
    CHECK = "check"
    DAMAGE = "damage"
    INITIATIVE = "initiative"
    GENERIC = "generic"


class Ability(str, Enum):
    """D&D 5e ability scores"""

    STRENGTH = "str"
    DEXTERITY = "dex"
    CONSTITUTION = "con"
    INTELLIGENCE = "int"
    WISDOM = "wis"
    CHARISMA = "cha"


# Comprehensive mapping of skill names, ability names, and alternatives to ability scores
# This allows the parser to handle natural language from the DM
ABILITY_MAPPING = {
    # Ability score abbreviations (canonical)
    "str": Ability.STRENGTH,
    "dex": Ability.DEXTERITY,
    "con": Ability.CONSTITUTION,
    "int": Ability.INTELLIGENCE,
    "wis": Ability.WISDOM,
    "cha": Ability.CHARISMA,
    # Full ability names
    "strength": Ability.STRENGTH,
    "dexterity": Ability.DEXTERITY,
    "constitution": Ability.CONSTITUTION,
    "intelligence": Ability.INTELLIGENCE,
    "wisdom": Ability.WISDOM,
    "charisma": Ability.CHARISMA,
    # Strength-based skills
    "athletics": Ability.STRENGTH,
    # Dexterity-based skills
    "acrobatics": Ability.DEXTERITY,
    "sleight of hand": Ability.DEXTERITY,
    "sleight_of_hand": Ability.DEXTERITY,
    "sleight-of-hand": Ability.DEXTERITY,
    "stealth": Ability.DEXTERITY,
    # Constitution-based (rare, but for completeness)
    "endurance": Ability.CONSTITUTION,
    "stamina": Ability.CONSTITUTION,
    # Intelligence-based skills
    "arcana": Ability.INTELLIGENCE,
    "history": Ability.INTELLIGENCE,
    "investigation": Ability.INTELLIGENCE,
    "nature": Ability.INTELLIGENCE,
    "religion": Ability.INTELLIGENCE,
    # Wisdom-based skills
    "animal handling": Ability.WISDOM,
    "animal_handling": Ability.WISDOM,
    "animal-handling": Ability.WISDOM,
    "insight": Ability.WISDOM,
    "medicine": Ability.WISDOM,
    "perception": Ability.WISDOM,
    "survival": Ability.WISDOM,
    # Charisma-based skills
    "deception": Ability.CHARISMA,
    "intimidation": Ability.CHARISMA,
    "performance": Ability.CHARISMA,
    "persuasion": Ability.CHARISMA,
    # Common tool proficiencies (map to dexterity by default)
    "thieves_tools": Ability.DEXTERITY,
    "thieves tools": Ability.DEXTERITY,
    "thieves-tools": Ability.DEXTERITY,
    "lockpicking": Ability.DEXTERITY,
    "disable device": Ability.DEXTERITY,
    # Alternative terms
    "spot": Ability.WISDOM,  # 3.5e/PF term for perception
    "search": Ability.INTELLIGENCE,  # Often used for investigation
    "hide": Ability.DEXTERITY,  # Alternative for stealth
    "move silently": Ability.DEXTERITY,  # 3.5e term
    "climb": Ability.STRENGTH,
    "jump": Ability.STRENGTH,
    "swim": Ability.STRENGTH,
    "reflex": Ability.DEXTERITY,  # Alternative save name
    "fortitude": Ability.CONSTITUTION,  # Alternative save name
    "will": Ability.WISDOM,  # Alternative save name
    "initiative": Ability.DEXTERITY,
    "reaction": Ability.DEXTERITY,
}


@dataclass
class RollRequest:
    """
    Structured representation of a dice roll request.

    Attributes:
        roll_type: Type of roll (attack, save, check, etc.)
        dice_notation: Dice expression (e.g., "d20+5", "2d6")
        ability: Ability score for checks/saves (optional)
        skill: Skill name for checks (optional)
        dc: Difficulty Class for checks/saves (optional)
        advantage: Roll with advantage (roll twice, take higher)
        disadvantage: Roll with disadvantage (roll twice, take lower)
        description: Human-readable description of the roll
        raw_tag: Original tag text from DM narration
        is_player_roll: Whether this roll should be made by the player (vs auto-executed)
    """

    roll_type: RollType
    dice_notation: str
    ability: Optional[Ability] = None
    skill: Optional[str] = None
    dc: Optional[int] = None
    advantage: bool = False
    disadvantage: bool = False
    description: str = ""
    raw_tag: str = ""
    is_player_roll: bool = True


class RollParser:
    """
    Parser for extracting dice roll requests from DM narration.

    The parser looks for tags in the format:
    [ROLL:type:notation] or [ROLL:type:ability:DC##]

    Examples:
        [ROLL:attack:d20+5] → Attack roll with +5 modifier
        [ROLL:save:dex:DC15] → Dexterity saving throw vs DC 15
        [ROLL:check:perception:DC12] → Perception check vs DC 12
        [ROLL:damage:2d6+3:adv] → Damage roll with advantage
    """

    # Regex pattern for roll tags
    # Format: [ROLL:type:details] with optional modifiers
    ROLL_TAG_PATTERN = re.compile(r"\[ROLL:([^:\]]+):([^\]]+)\]", re.IGNORECASE)

    @classmethod
    def parse_narration(cls, narration: str) -> tuple[str, List[RollRequest]]:
        """
        Parse DM narration and extract roll requests.

        Args:
            narration: DM narration text containing roll tags

        Returns:
            Tuple of (cleaned_narration, roll_requests)
            - cleaned_narration: Narration with roll tags removed
            - roll_requests: List of parsed roll requests
        """
        roll_requests = []
        cleaned_narration = narration

        # Find all roll tags
        for match in cls.ROLL_TAG_PATTERN.finditer(narration):
            raw_tag = match.group(0)
            roll_type_str = match.group(1).lower().strip()
            details = match.group(2).strip()

            # Parse the roll request
            roll_request = cls._parse_roll_details(roll_type_str, details, raw_tag)

            if roll_request:
                roll_request.is_player_roll = cls._determine_if_player_roll(roll_request, narration)
                roll_requests.append(roll_request)
                # Remove the tag from narration
                cleaned_narration = cleaned_narration.replace(raw_tag, "")

        return cleaned_narration.strip(), roll_requests

    @classmethod
    def _parse_roll_details(
        cls, roll_type_str: str, details: str, raw_tag: str
    ) -> Optional[RollRequest]:
        """
        Parse the details portion of a roll tag.

        Args:
            roll_type_str: Type of roll (attack, save, check, etc.)
            details: The details string after roll type
            raw_tag: Original tag text

        Returns:
            RollRequest object or None if parsing fails
        """
        try:
            # Map string to RollType enum
            roll_type = RollType(roll_type_str)
        except ValueError:
            # Unknown roll type, treat as generic
            roll_type = RollType.GENERIC

        # Split details by colon
        parts = [p.strip() for p in details.split(":")]

        # Check for advantage/disadvantage flags
        advantage = any("adv" in p.lower() for p in parts)
        disadvantage = any("dis" in p.lower() for p in parts)
        parts = [p for p in parts if "adv" not in p.lower() and "dis" not in p.lower()]

        if roll_type in [RollType.SAVE, RollType.CHECK]:
            # Format: ability:DC## or ability:DC:##
            return cls._parse_ability_roll(roll_type, parts, advantage, disadvantage, raw_tag)
        else:
            # Format: dice_notation (e.g., d20+5, 2d6)
            return cls._parse_dice_roll(
                roll_type, parts[0] if parts else "d20", advantage, disadvantage, raw_tag
            )

    @classmethod
    def _parse_ability_roll(
        cls,
        roll_type: RollType,
        parts: List[str],
        advantage: bool,
        disadvantage: bool,
        raw_tag: str,
    ) -> Optional[RollRequest]:
        """Parse saving throw or ability check."""
        if len(parts) < 2:
            return None

        ability_str = parts[0].lower().strip()

        # Try to map the ability string using our comprehensive mapping
        ability = ABILITY_MAPPING.get(ability_str)

        # If not found in mapping, try direct Ability enum conversion (fallback)
        if ability is None:
            try:
                ability = Ability(ability_str)
            except ValueError:
                return None

        # Parse DC
        dc = None
        dc_str = parts[1] if len(parts) > 1 else ""

        # Extract number from DC string (handles "DC15" or "15")
        dc_match = re.search(r"(\d+)", dc_str)
        if dc_match:
            dc = int(dc_match.group(1))

        # Generate description - use the original skill name if it's more descriptive than the ability
        # For example: "Perception check" is better than "WIS check"
        roll_name = "saving throw" if roll_type == RollType.SAVE else "check"
        skill = None

        # Check if the input was a skill name (not just an ability abbreviation)
        if ability_str in ["str", "dex", "con", "int", "wis", "cha"]:
            # Simple ability check, use ability abbreviation
            description = f"{ability.value.upper()} {roll_name}"
        elif ability_str in [
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ]:
            # Full ability name, use abbreviation for brevity
            description = f"{ability.value.upper()} {roll_name}"
        else:
            # Skill name or alternative - capitalize it nicely
            skill_name = ability_str.replace("_", " ").replace("-", " ").title()
            description = f"{skill_name} {roll_name}"
            skill = ability_str

        if dc:
            description += f" (DC {dc})"

        return RollRequest(
            roll_type=roll_type,
            dice_notation="d20",  # Ability rolls always use d20
            ability=ability,
            skill=skill,
            dc=dc,
            advantage=advantage,
            disadvantage=disadvantage,
            description=description,
            raw_tag=raw_tag,
        )

    @classmethod
    def _parse_dice_roll(
        cls,
        roll_type: RollType,
        dice_notation: str,
        advantage: bool,
        disadvantage: bool,
        raw_tag: str,
    ) -> RollRequest:
        """Parse attack, damage, or generic dice roll."""
        # Clean up dice notation
        dice_notation = dice_notation.strip()

        # Ensure it has a 'd' for dice
        if "d" not in dice_notation.lower():
            dice_notation = f"d{dice_notation}" if dice_notation.isdigit() else "d20"

        # Generate description
        description = f"{roll_type.value.capitalize()} roll: {dice_notation}"

        return RollRequest(
            roll_type=roll_type,
            dice_notation=dice_notation,
            advantage=advantage,
            disadvantage=disadvantage,
            description=description,
            raw_tag=raw_tag,
        )

    @classmethod
    def has_roll_tags(cls, narration: str) -> bool:
        """
        Check if narration contains any roll tags.

        Args:
            narration: Text to check

        Returns:
            True if roll tags are present
        """
        return bool(cls.ROLL_TAG_PATTERN.search(narration))

    @classmethod
    def _determine_if_player_roll(cls, roll_request: RollRequest, narration: str) -> bool:
        """
        Determine if a roll should be made by the player or auto-executed by the system.

        Player rolls:
        - Attacks (player attacking)
        - Checks (player attempting skills)
        - Initiative (player's initiative)

        NPC/DM rolls (auto-execute):
        - Saves (NPCs saving against player spells/effects)
        - Attacks where NPC is clearly the attacker
        - Damage from NPC sources
        """
        narration_lower = narration.lower()

        if roll_request.roll_type == RollType.INITIATIVE:
            return True

        if roll_request.roll_type == RollType.CHECK:
            return True

        if roll_request.roll_type == RollType.SAVE:
            player_save_indicators = [
                "you must",
                "you need to",
                "make a",
                "roll a",
                "you resist",
                "you attempt to",
                "try to resist",
            ]
            npc_save_indicators = [
                "they must",
                "he must",
                "she must",
                "it must",
                "the goblin",
                "the orc",
                "the guard",
                "the bandit",
                "your target",
                "creature must",
                "enemy must",
            ]

            if any(indicator in narration_lower for indicator in npc_save_indicators):
                return False

            if any(indicator in narration_lower for indicator in player_save_indicators):
                return True

            return False

        if roll_request.roll_type == RollType.ATTACK:
            player_attack_indicators = [
                "you swing",
                "you strike",
                "you attack",
                "you shoot",
                "you fire",
                "you throw",
                "your blade",
                "your sword",
                "your arrow",
                "your spell",
            ]
            npc_attack_indicators = [
                "attacks you",
                "swings at you",
                "strikes at you",
                "lunges at you",
                "the goblin attacks",
                "the orc swings",
                "it attacks",
                "they attack",
            ]

            if any(indicator in narration_lower for indicator in npc_attack_indicators):
                return False

            if any(indicator in narration_lower for indicator in player_attack_indicators):
                return True

            return True

        if roll_request.roll_type == RollType.DAMAGE:
            npc_damage_indicators = [
                "takes damage",
                "you take",
                "hits you",
            ]

            if any(indicator in narration_lower for indicator in npc_damage_indicators):
                return False

            return True

        return True


def detect_roll_request_from_narration(dm_response: str) -> Optional[dict]:
    """
    Detect roll requests from natural language in DM narration.

    This is a fallback for when the DM doesn't use [ROLL:...] tags.
    Parses common phrasings that indicate a roll is needed.

    Args:
        dm_response: The DM's narrative text

    Returns:
        Dictionary with roll request info, or None if no roll detected
        Format: {
            "requires_roll": True,
            "roll_type": "check|save|attack|initiative",
            "ability": "dex|str|etc",
            "skill": "stealth|perception|etc",
            "dc": 15,
            "detected_text": "make a Stealth check",
            "context": "...surrounding text..."
        }
    """
    patterns = [
        # Ability checks: "make a [ability/skill] check"
        (r"make (?:a |an )?(\w+(?:\s+\w+)?) (?:check|roll)", "check", lambda m: m.group(1).lower()),
        # Saving throws: "make a [ability] saving throw" or "[ability] save"
        (r"make (?:a |an )?(\w+) (?:saving throw|save)", "save", lambda m: m.group(1).lower()),
        (
            r"(\w+) (?:saving throw|save) (?:DC|against DC) ?(\d+)",
            "save",
            lambda m: m.group(1).lower(),
        ),
        # Generic "roll for [ability/skill]"
        (r"roll (?:for |a |an )?(?:your )?(\w+(?:\s+\w+)?)", "check", lambda m: m.group(1).lower()),
        # Attack rolls
        (r"roll (?:to hit|an attack|for attack)", "attack", lambda m: None),
        (r"make an attack roll", "attack", lambda m: None),
        # Initiative
        (r"roll initiative", "initiative", lambda m: None),
        # Stealth checks (very common)
        (
            r"(?:try to |attempt to )?(?:sneak|hide|move quietly|move silently)",
            "check",
            lambda m: "stealth",
        ),
        # Perception checks — require explicit roll/check language to avoid firing on narrative prose
        # e.g. "make a perception check", "roll to notice" — NOT "you notice three figures"
        (
            r"(?:make a perception (?:check|roll)|perception check|roll (?:to |for )?(?:notice|spot|observe)|spot (?:check|roll)|look carefully around|search (?:for clues|the area|carefully))",
            "check",
            lambda m: "perception",
        ),
        # Investigation checks
        (r"(?:investigate|examine|inspect) (?:the |for )", "check", lambda m: "investigation"),
    ]

    dm_lower = dm_response.lower()

    for pattern, roll_type, ability_extractor in patterns:
        match = re.search(pattern, dm_lower, re.IGNORECASE)
        if match:
            detected_text = match.group(0)
            context_start = max(0, match.start() - 50)
            context_end = min(len(dm_response), match.end() + 50)
            context = dm_response[context_start:context_end]

            # Extract ability/skill
            ability_or_skill = ability_extractor(match) if ability_extractor(match) else None

            # Try to map to canonical ability
            ability = None
            skill = None
            if ability_or_skill:
                # Clean up the ability/skill string
                ability_or_skill = ability_or_skill.strip().replace("-", " ").replace("_", " ")

                # Check if it's in our ability mapping
                if ability_or_skill in ABILITY_MAPPING:
                    ability = ABILITY_MAPPING[ability_or_skill].value
                    # If it's a skill, also set skill name
                    if ability_or_skill not in [
                        "str",
                        "dex",
                        "con",
                        "int",
                        "wis",
                        "cha",
                        "strength",
                        "dexterity",
                        "constitution",
                        "intelligence",
                        "wisdom",
                        "charisma",
                    ]:
                        skill = ability_or_skill
                else:
                    # Unknown, default to wisdom for checks
                    ability = "wis" if roll_type == "check" else None

            # Try to extract DC from context
            dc = None
            dc_match = re.search(r"DC[\s:]?(\d+)", dm_response, re.IGNORECASE)
            if dc_match:
                dc = int(dc_match.group(1))
            else:
                # Infer DC based on difficulty words
                if "easy" in dm_lower:
                    dc = 10
                elif "moderate" in dm_lower or "medium" in dm_lower:
                    dc = 15
                elif "hard" in dm_lower or "difficult" in dm_lower:
                    dc = 20
                elif "very hard" in dm_lower or "extremely difficult" in dm_lower:
                    dc = 25
                else:
                    # Default DCs by roll type
                    dc = 12  # Moderate default

            result = {
                "requires_roll": True,
                "roll_type": roll_type,
                "ability": ability,
                "skill": skill,
                "dc": dc,
                "detected_text": detected_text,
                "context": context.strip(),
            }

            return result

    return None
