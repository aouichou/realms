"""D&D dice rolling service."""
import random
import re
from typing import Optional

from app.schemas.dice import DiceRollResult, RollType


class DiceService:
    """Service for D&D dice rolling."""
    
    @staticmethod
    def roll_die(sides: int) -> int:
        """Roll a single die.
        
        Args:
            sides: Number of sides on the die
            
        Returns:
            Random number between 1 and sides
        """
        return random.randint(1, sides)
    
    @staticmethod
    def parse_dice_notation(notation: str) -> tuple[int, int, int]:
        """Parse dice notation into components.
        
        Args:
            notation: Dice notation (e.g., '2d6+3', 'd20', '3d8-2')
            
        Returns:
            Tuple of (count, sides, modifier)
            
        Raises:
            ValueError: If notation is invalid
        """
        notation = notation.lower().strip()
        
        # Match patterns like: 2d6+3, d20, 3d8-2, 1d4
        pattern = r'^(\d*)d(\d+)([+-]\d+)?$'
        match = re.match(pattern, notation)
        
        if not match:
            raise ValueError(f"Invalid dice notation: {notation}")
        
        count_str, sides_str, modifier_str = match.groups()
        
        count = int(count_str) if count_str else 1
        sides = int(sides_str)
        modifier = int(modifier_str) if modifier_str else 0
        
        if count < 1:
            raise ValueError("Dice count must be at least 1")
        if sides < 2:
            raise ValueError("Dice must have at least 2 sides")
        if count > 100:
            raise ValueError("Cannot roll more than 100 dice at once")
        
        return count, sides, modifier
    
    @staticmethod
    def roll_dice(
        notation: str,
        roll_type: RollType = RollType.NORMAL
    ) -> tuple[list[DiceRollResult], int, int]:
        """Roll dice according to notation and type.
        
        Args:
            notation: Dice notation (e.g., '2d6+3')
            roll_type: Normal, advantage, or disadvantage
            
        Returns:
            Tuple of (individual rolls, modifier, total)
        """
        count, sides, modifier = DiceService.parse_dice_notation(notation)
        
        die_type = f"d{sides}"
        rolls = []
        
        if roll_type == RollType.ADVANTAGE:
            # Roll twice, keep highest
            if count != 1:
                raise ValueError("Advantage/disadvantage only works with single die rolls (e.g., d20)")
            
            roll1 = DiceService.roll_die(sides)
            roll2 = DiceService.roll_die(sides)
            
            if roll1 >= roll2:
                rolls.append(DiceRollResult(die_type=die_type, roll=roll1, dropped=False))
                rolls.append(DiceRollResult(die_type=die_type, roll=roll2, dropped=True))
            else:
                rolls.append(DiceRollResult(die_type=die_type, roll=roll1, dropped=True))
                rolls.append(DiceRollResult(die_type=die_type, roll=roll2, dropped=False))
        
        elif roll_type == RollType.DISADVANTAGE:
            # Roll twice, keep lowest
            if count != 1:
                raise ValueError("Advantage/disadvantage only works with single die rolls (e.g., d20)")
            
            roll1 = DiceService.roll_die(sides)
            roll2 = DiceService.roll_die(sides)
            
            if roll1 <= roll2:
                rolls.append(DiceRollResult(die_type=die_type, roll=roll1, dropped=False))
                rolls.append(DiceRollResult(die_type=die_type, roll=roll2, dropped=True))
            else:
                rolls.append(DiceRollResult(die_type=die_type, roll=roll1, dropped=True))
                rolls.append(DiceRollResult(die_type=die_type, roll=roll2, dropped=False))
        
        else:
            # Normal roll
            for _ in range(count):
                roll = DiceService.roll_die(sides)
                rolls.append(DiceRollResult(die_type=die_type, roll=roll, dropped=False))
        
        # Calculate total (only non-dropped rolls)
        dice_total = sum(r.roll for r in rolls if not r.dropped)
        total = dice_total + modifier
        
        return rolls, modifier, total
    
    @staticmethod
    def format_breakdown(
        notation: str,
        rolls: list[DiceRollResult],
        modifier: int,
        total: int
    ) -> str:
        """Format a human-readable breakdown of the roll.
        
        Args:
            notation: Original dice notation
            rolls: Individual roll results
            modifier: Modifier value
            total: Total result
            
        Returns:
            Formatted breakdown string
        """
        # Group rolls by dropped status
        kept_rolls = [r.roll for r in rolls if not r.dropped]
        dropped_rolls = [r.roll for r in rolls if r.dropped]
        
        breakdown_parts = []
        
        # Show kept rolls
        if kept_rolls:
            rolls_str = ", ".join(str(r) for r in kept_rolls)
            breakdown_parts.append(f"[{rolls_str}]")
        
        # Show dropped rolls
        if dropped_rolls:
            dropped_str = ", ".join(str(r) for r in dropped_rolls)
            breakdown_parts.append(f"~~[{dropped_str}]~~")
        
        # Add modifier if present
        if modifier != 0:
            sign = "+" if modifier > 0 else ""
            breakdown_parts.append(f"{sign}{modifier}")
        
        # Build final breakdown
        breakdown = " ".join(breakdown_parts)
        
        return f"{notation} → {breakdown} = **{total}**"
