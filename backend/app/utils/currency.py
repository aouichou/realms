"""
D&D 5e Currency Utilities

Handles gold, silver, and copper piece conversions following D&D 5e rules:
- 1 gold piece (gp) = 10 silver pieces (sp)
- 1 silver piece (sp) = 10 copper pieces (cp)
- 1 gold piece (gp) = 100 copper pieces (cp)
"""

from dataclasses import dataclass
from typing import Tuple

# Conversion rates (all relative to copper)
CP_PER_SP = 10
CP_PER_GP = 100
SP_PER_GP = 10


@dataclass
class Currency:
    """D&D 5e currency representation"""

    gold: int = 0
    silver: int = 0
    copper: int = 0

    def to_copper(self) -> int:
        """Convert all currency to copper pieces"""
        return (self.gold * CP_PER_GP) + (self.silver * CP_PER_SP) + self.copper

    def to_gold_fractional(self) -> float:
        """Convert to gold as a decimal (e.g., 1.5 gp)"""
        return self.to_copper() / CP_PER_GP

    @classmethod
    def from_copper(cls, copper: int) -> "Currency":
        """
        Convert copper pieces to optimal currency denomination

        Args:
            copper: Total copper pieces

        Returns:
            Currency with gold, silver, copper optimally distributed
        """
        gold = copper // CP_PER_GP
        remaining = copper % CP_PER_GP
        silver = remaining // CP_PER_SP
        copper_pieces = remaining % CP_PER_SP

        return cls(gold=gold, silver=silver, copper=copper_pieces)

    @classmethod
    def from_gold(cls, gold: float) -> "Currency":
        """
        Convert fractional gold to currency

        Args:
            gold: Gold amount (can be fractional, e.g., 1.5)

        Returns:
            Currency with optimal distribution
        """
        copper_total = int(gold * CP_PER_GP)
        return cls.from_copper(copper_total)

    def __add__(self, other: "Currency") -> "Currency":
        """Add two currency amounts"""
        return Currency.from_copper(self.to_copper() + other.to_copper())

    def __sub__(self, other: "Currency") -> "Currency":
        """Subtract currency (minimum 0)"""
        result = self.to_copper() - other.to_copper()
        return Currency.from_copper(max(0, result))

    def __str__(self) -> str:
        """Human-readable currency string"""
        parts = []
        if self.gold > 0:
            parts.append(f"{self.gold} gp")
        if self.silver > 0:
            parts.append(f"{self.silver} sp")
        if self.copper > 0:
            parts.append(f"{self.copper} cp")
        return ", ".join(parts) if parts else "0 cp"

    def __repr__(self) -> str:
        return f"Currency(gold={self.gold}, silver={self.silver}, copper={self.copper})"


def add_currency(character, gold: int = 0, silver: int = 0, copper: int = 0) -> Currency:
    """
    Add currency to a character and optimize denominations

    Args:
        character: Character model instance
        gold: Gold pieces to add
        silver: Silver pieces to add
        copper: Copper pieces to add

    Returns:
        New currency totals
    """
    current = Currency(
        gold=character.gold,
        silver=character.silver,
        copper=character.copper,
    )
    added = Currency(gold=gold, silver=silver, copper=copper)
    new_total = current + added

    # Update character
    character.gold = new_total.gold
    character.silver = new_total.silver
    character.copper = new_total.copper

    return new_total


def subtract_currency(
    character, gold: int = 0, silver: int = 0, copper: int = 0
) -> Tuple[bool, Currency]:
    """
    Subtract currency from a character

    Args:
        character: Character model instance
        gold: Gold pieces to subtract
        silver: Silver pieces to subtract
        copper: Copper pieces to subtract

    Returns:
        Tuple of (success, new_totals)
        success is False if character doesn't have enough currency
    """
    current = Currency(
        gold=character.gold,
        silver=character.silver,
        copper=character.copper,
    )
    cost = Currency(gold=gold, silver=silver, copper=copper)

    # Check if character has enough
    if current.to_copper() < cost.to_copper():
        return False, current

    new_total = current - cost

    # Update character
    character.gold = new_total.gold
    character.silver = new_total.silver
    character.copper = new_total.copper

    return True, new_total


def format_price(gold: int = 0, silver: int = 0, copper: int = 0) -> str:
    """
    Format a price in D&D currency

    Args:
        gold: Gold pieces
        silver: Silver pieces
        copper: Copper pieces

    Returns:
        Formatted string like "5 gp, 3 sp" or "15 cp"
    """
    return str(Currency(gold=gold, silver=silver, copper=copper))


def convert_to_gold(silver: int = 0, copper: int = 0) -> int:
    """
    Convert silver and copper to gold pieces (rounded down)

    Args:
        silver: Silver pieces
        copper: Copper pieces

    Returns:
        Gold pieces (integer, any remainder stays as silver/copper)
    """
    total_copper = (silver * CP_PER_SP) + copper
    return total_copper // CP_PER_GP
