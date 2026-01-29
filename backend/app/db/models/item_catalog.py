"""
Item Catalog model for D&D 5e equipment database.
Represents the master list of all available items that can be referenced.
Separate from player inventory (Item model).
"""

from sqlalchemy import Column, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class ItemCatalog(Base):
    """
    D&D 5e Equipment and Magic Items Catalog.

    Master database of all available items. Used for:
    - DM tools to give items to players
    - Character creation equipment selection
    - Random loot generation
    - Item lookup and reference

    This is separate from the Item model which tracks player inventory.
    """

    __tablename__ = "item_catalog"

    id = Column(Integer, primary_key=True, index=True)

    # Core Identity
    name = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)

    # Categorization
    category = Column(
        String(50), nullable=False, index=True
    )  # weapon, armor, shield, potion, scroll, wondrous_item, adventuring_gear
    item_type = Column(String(100))  # longsword, chain_mail, +1_weapon, potion_of_healing
    rarity = Column(
        String(100), default="common", index=True
    )  # common, uncommon, rare, very_rare, legendary, artifact (may include attunement info)

    # Armor Stats
    ac_base = Column(Integer, nullable=True)  # Base AC for armor (e.g., 16 for chain mail)
    ac_bonus = Column(Integer, nullable=True)  # AC bonus from shields (+2) or magic items (+1)

    # Weapon Stats
    damage_dice = Column(String(20), nullable=True)  # e.g., "1d8", "2d6"
    damage_type = Column(String(20), nullable=True)  # slashing, piercing, bludgeoning, fire, etc.
    versatile_damage = Column(String(20), nullable=True)  # Two-handed damage (e.g., "1d10")
    attack_bonus = Column(Integer, default=0)  # Magic weapon bonus (e.g., +1, +2, +3)
    damage_bonus = Column(Integer, default=0)  # Magic weapon damage bonus

    # Properties (stored as JSONB for flexibility)
    properties = Column(JSONB, default=dict)
    # Examples:
    # - Weapon: {"finesse": true, "light": true, "thrown": {"normal": 20, "long": 60}}
    # - Armor: {"stealth_disadvantage": true, "strength_requirement": 15}
    # - Magic: {"attunement": true, "charges": 7, "regains": "1d6+1 at dawn"}

    requirements = Column(JSONB, default=dict)  # class, level, or stat requirements
    # Example: {"class": ["wizard", "sorcerer"], "attunement": true}

    # Economics
    cost_gp = Column(Integer, default=0)  # Cost in gold pieces
    cost_cp = Column(Integer, default=0)  # Additional copper for fractional gold
    weight_lbs = Column(Float, default=0.0)  # Weight in pounds

    # Source Information
    publisher = Column(String(100), nullable=True)  # Wizards of the Coast, Kobold Press, etc.
    book = Column(String(200), nullable=True)  # Source book

    # Additional Metadata
    expansion = Column(Integer, nullable=True)  # Book/expansion ID from source data
    properties_raw = Column(JSONB, default=dict)  # Original properties from JSON

    def to_dict(self):
        """Convert item to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "item_type": self.item_type,
            "rarity": self.rarity,
            "ac_base": self.ac_base,
            "ac_bonus": self.ac_bonus,
            "damage_dice": self.damage_dice,
            "damage_type": self.damage_type,
            "versatile_damage": self.versatile_damage,
            "attack_bonus": self.attack_bonus,
            "damage_bonus": self.damage_bonus,
            "properties": self.properties,
            "requirements": self.requirements,
            "cost_gp": self.cost_gp,
            "cost_cp": self.cost_cp,
            "weight_lbs": self.weight_lbs,
            "publisher": self.publisher,
            "book": self.book,
        }

    def is_weapon(self) -> bool:
        """Check if item is a weapon."""
        return self.category and "weapon" in self.category.lower()

    def is_armor(self) -> bool:
        """Check if item is armor."""
        return self.category and "armor" in self.category.lower()

    def is_shield(self) -> bool:
        """Check if item is a shield."""
        return "shield" in self.name.lower() or (
            self.category and "shield" in self.category.lower()
        )

    def is_magic_item(self) -> bool:
        """Check if item is magical (non-common rarity)."""
        return self.rarity and self.rarity.lower() not in ("common", "")

    def get_total_cost_gp(self) -> float:
        """Get total cost in gold pieces (including copper conversion)."""
        return self.cost_gp + (self.cost_cp / 100.0)

    def __repr__(self):
        return f"<ItemCatalog {self.name} ({self.rarity} {self.category})>"
