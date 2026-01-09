"""
Roll Executor Service

Executes dice notation and calculates roll results with character modifiers.
Supports D&D 5e dice mechanics including advantage, disadvantage, and various
dice notation patterns.

Examples:
    - 1d20+5: Single d20 plus 5 modifier
    - 2d6: Two six-sided dice
    - 4d6dl1: Four d6, drop lowest (common for ability scores)
    - 3d8+2d6+5: Multiple dice types with modifier
"""

import random
import re
from dataclasses import dataclass
from typing import Optional

from app.models.character import Character
from app.services.roll_parser import Ability, RollType


@dataclass
class DiceRollResult:
    """
    Result of a dice roll execution.
    
    Attributes:
        notation: Original dice notation
        rolls: Individual die results
        modifier: Numerical modifier applied
        total: Final total value
        success: Whether roll met DC (if applicable)
        dc: Difficulty Class (if applicable)
        advantage: Whether rolled with advantage
        disadvantage: Whether rolled with disadvantage
        description: Human-readable description
    """
    notation: str
    rolls: list[int]
    modifier: int
    total: int
    success: Optional[bool] = None
    dc: Optional[int] = None
    advantage: bool = False
    disadvantage: bool = False
    description: str = ""
    
    @property
    def dice_total(self) -> int:
        """Sum of dice rolls only (excluding modifier)"""
        return sum(self.rolls)
    
    @property
    def is_critical(self) -> bool:
        """Check if this is a critical hit (natural 20 on d20)"""
        return (
            self.notation.startswith("d20") and
            len(self.rolls) > 0 and
            max(self.rolls) == 20
        )
    
    @property
    def is_critical_fail(self) -> bool:
        """Check if this is a critical failure (natural 1 on d20)"""
        return (
            self.notation.startswith("d20") and
            len(self.rolls) > 0 and
            min(self.rolls) == 1
        )
        """Check if this is a critical failure (natural 1 on d20)"""
        return (
            self.notation.startswith("d20") and
            len(self.rolls) > 0 and
            min(self.rolls) == 1
        )


class RollExecutor:
    """
    Executes dice rolls with D&D 5e mechanics.
    
    Handles:
    - Standard dice notation (XdY+Z)
    - Advantage/disadvantage
    - Character ability modifiers
    - DC checks
    - Drop lowest/highest mechanics
    """
    
    # Regex for parsing dice notation
    # Matches: XdY, XdYdlZ (drop lowest), XdYdhZ (drop highest)
    DICE_PATTERN = re.compile(
        r'(\d*)d(\d+)(?:dl(\d+)|dh(\d+))?',
        re.IGNORECASE
    )
    
    @classmethod
    def execute_roll(
        cls,
        dice_notation: str,
        roll_type: RollType,
        character: Optional[Character] = None,
        ability: Optional[Ability] = None,
        dc: Optional[int] = None,
        advantage: bool = False,
        disadvantage: bool = False,
        description: str = ""
    ) -> DiceRollResult:
        """
        Execute a dice roll with modifiers.
        
        Args:
            dice_notation: Dice expression (e.g., "d20+5", "2d6")
            roll_type: Type of roll (attack, save, check, etc.)
            character: Character making the roll (for modifiers)
            ability: Ability score to use for modifier
            dc: Difficulty Class to check against
            advantage: Roll twice, take higher
            disadvantage: Roll twice, take lower
            description: Description of the roll
            
        Returns:
            DiceRollResult with outcome
        """
        # Parse notation to separate dice and modifiers
        dice_parts, base_modifier = cls._parse_notation(dice_notation)
        
        # Calculate ability modifier if needed
        ability_mod = 0
        if character and ability:
            ability_mod = cls._get_ability_modifier(character, ability)
        
        # Total modifier
        total_modifier = base_modifier + ability_mod
        
        # Roll the dice
        rolls = cls._roll_dice(dice_parts, advantage, disadvantage)
        
        # Calculate total
        total = sum(rolls) + total_modifier
        
        # Check success against DC
        success = None
        if dc is not None:
            success = total >= dc
        
        return DiceRollResult(
            notation=dice_notation,
            rolls=rolls,
            modifier=total_modifier,
            total=total,
            success=success,
            dc=dc,
            advantage=advantage,
            disadvantage=disadvantage,
            description=description or f"{roll_type.value.capitalize()} roll"
        )
    
    @classmethod
    def _parse_notation(cls, notation: str) -> tuple[list[dict], int]:
        """
        Parse dice notation into components.
        
        Args:
            notation: Dice string like "d20+5" or "2d6+1d4+3"
            
        Returns:
            Tuple of (dice_parts, modifier)
            - dice_parts: List of dice specifications
            - modifier: Numerical modifier
        """
        dice_parts = []
        modifier = 0
        
        # Clean notation
        notation = notation.replace(" ", "").lower()
        
        # Find all dice expressions
        for match in cls.DICE_PATTERN.finditer(notation):
            count = int(match.group(1)) if match.group(1) else 1
            sides = int(match.group(2))
            drop_lowest = int(match.group(3)) if match.group(3) else 0
            drop_highest = int(match.group(4)) if match.group(4) else 0
            
            dice_parts.append({
                'count': count,
                'sides': sides,
                'drop_lowest': drop_lowest,
                'drop_highest': drop_highest
            })
        
        # Find modifier (+ or - followed by number)
        mod_match = re.search(r'([+\-]\d+)(?!d)', notation)
        if mod_match:
            modifier = int(mod_match.group(1))
        
        # Default to d20 if no dice found
        if not dice_parts:
            dice_parts.append({
                'count': 1,
                'sides': 20,
                'drop_lowest': 0,
                'drop_highest': 0
            })
        
        return dice_parts, modifier
    
    @classmethod
    def _roll_dice(
        cls,
        dice_parts: list[dict],
        advantage: bool,
        disadvantage: bool
    ) -> list[int]:
        """
        Roll the dice according to specifications.
        
        Args:
            dice_parts: List of dice specifications
            advantage: Roll twice, keep higher
            disadvantage: Roll twice, keep lower
            
        Returns:
            List of individual die results
        """
        all_rolls = []
        
        for dice_spec in dice_parts:
            count = dice_spec['count']
            sides = dice_spec['sides']
            drop_lowest = dice_spec['drop_lowest']
            drop_highest = dice_spec['drop_highest']
            
            # Handle advantage/disadvantage for d20 rolls
            if sides == 20 and count == 1 and (advantage or disadvantage):
                roll1 = random.randint(1, sides)
                roll2 = random.randint(1, sides)
                
                if advantage:
                    all_rolls.append(max(roll1, roll2))
                else:  # disadvantage
                    all_rolls.append(min(roll1, roll2))
            else:
                # Normal roll
                rolls = [random.randint(1, sides) for _ in range(count)]
                
                # Apply drop mechanics
                if drop_lowest > 0:
                    rolls.sort()
                    rolls = rolls[drop_lowest:]
                elif drop_highest > 0:
                    rolls.sort(reverse=True)
                    rolls = rolls[drop_highest:]
                
                all_rolls.extend(rolls)
        
        return all_rolls
    
    @classmethod
    def _get_ability_modifier(cls, character: Character, ability: Ability) -> int:
        """
        Get ability modifier for a character.
        
        Args:
            character: Character to get modifier for
            ability: Ability score (str, dex, con, etc.)
            
        Returns:
            Modifier value (-5 to +10 typically)
        """
        # Map ability to character attribute
        ability_map = {
            Ability.STRENGTH: character.strength,
            Ability.DEXTERITY: character.dexterity,
            Ability.CONSTITUTION: character.constitution,
            Ability.INTELLIGENCE: character.intelligence,
            Ability.WISDOM: character.wisdom,
            Ability.CHARISMA: character.charisma,
        }
        
        score = ability_map.get(ability, 10)
        
        # D&D 5e modifier formula: (score - 10) // 2
        return (score - 10) // 2
