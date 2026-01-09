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
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


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


@dataclass
class RollRequest:
    """
    Structured representation of a dice roll request.
    
    Attributes:
        roll_type: Type of roll (attack, save, check, etc.)
        dice_notation: Dice expression (e.g., "d20+5", "2d6")
        ability: Ability score for checks/saves (optional)
        dc: Difficulty Class for checks/saves (optional)
        advantage: Roll with advantage (roll twice, take higher)
        disadvantage: Roll with disadvantage (roll twice, take lower)
        description: Human-readable description of the roll
        raw_tag: Original tag text from DM narration
    """
    roll_type: RollType
    dice_notation: str
    ability: Optional[Ability] = None
    dc: Optional[int] = None
    advantage: bool = False
    disadvantage: bool = False
    description: str = ""
    raw_tag: str = ""


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
    ROLL_TAG_PATTERN = re.compile(
        r'\[ROLL:([^:\]]+):([^\]]+)\]',
        re.IGNORECASE
    )
    
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
            roll_request = cls._parse_roll_details(
                roll_type_str,
                details,
                raw_tag
            )
            
            if roll_request:
                roll_requests.append(roll_request)
                # Remove the tag from narration
                cleaned_narration = cleaned_narration.replace(raw_tag, "")
        
        return cleaned_narration.strip(), roll_requests
    
    @classmethod
    def _parse_roll_details(
        cls,
        roll_type_str: str,
        details: str,
        raw_tag: str
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
        parts = [p.strip() for p in details.split(':')]
        
        # Check for advantage/disadvantage flags
        advantage = any('adv' in p.lower() for p in parts)
        disadvantage = any('dis' in p.lower() for p in parts)
        parts = [p for p in parts if 'adv' not in p.lower() and 'dis' not in p.lower()]
        
        if roll_type in [RollType.SAVE, RollType.CHECK]:
            # Format: ability:DC## or ability:DC:##
            return cls._parse_ability_roll(
                roll_type, parts, advantage, disadvantage, raw_tag
            )
        else:
            # Format: dice_notation (e.g., d20+5, 2d6)
            return cls._parse_dice_roll(
                roll_type, parts[0] if parts else "d20",
                advantage, disadvantage, raw_tag
            )
    
    @classmethod
    def _parse_ability_roll(
        cls,
        roll_type: RollType,
        parts: List[str],
        advantage: bool,
        disadvantage: bool,
        raw_tag: str
    ) -> Optional[RollRequest]:
        """Parse saving throw or ability check."""
        if len(parts) < 2:
            return None
        
        ability_str = parts[0].lower()
        
        # Try to parse ability
        try:
            ability = Ability(ability_str)
        except ValueError:
            return None
        
        # Parse DC
        dc = None
        dc_str = parts[1] if len(parts) > 1 else ""
        
        # Extract number from DC string (handles "DC15" or "15")
        dc_match = re.search(r'(\d+)', dc_str)
        if dc_match:
            dc = int(dc_match.group(1))
        
        # Generate description
        roll_name = "saving throw" if roll_type == RollType.SAVE else "check"
        description = f"{ability.value.upper()} {roll_name}"
        if dc:
            description += f" (DC {dc})"
        
        return RollRequest(
            roll_type=roll_type,
            dice_notation="d20",  # Ability rolls always use d20
            ability=ability,
            dc=dc,
            advantage=advantage,
            disadvantage=disadvantage,
            description=description,
            raw_tag=raw_tag
        )
    
    @classmethod
    def _parse_dice_roll(
        cls,
        roll_type: RollType,
        dice_notation: str,
        advantage: bool,
        disadvantage: bool,
        raw_tag: str
    ) -> RollRequest:
        """Parse attack, damage, or generic dice roll."""
        # Clean up dice notation
        dice_notation = dice_notation.strip()
        
        # Ensure it has a 'd' for dice
        if 'd' not in dice_notation.lower():
            dice_notation = f"d{dice_notation}" if dice_notation.isdigit() else "d20"
        
        # Generate description
        description = f"{roll_type.value.capitalize()} roll: {dice_notation}"
        
        return RollRequest(
            roll_type=roll_type,
            dice_notation=dice_notation,
            advantage=advantage,
            disadvantage=disadvantage,
            description=description,
            raw_tag=raw_tag
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
