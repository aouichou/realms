"""
Creature database model for monsters, NPCs, and companions.
Maps to D&D 5e stat blocks from creatures_master.csv dataset.
"""

from sqlalchemy import Column, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class Creature(Base):
    """
    Represents a D&D 5e creature (monster, NPC, or companion).

    Stores complete stat blocks including abilities, actions, traits,
    and special features for DM reference during encounters.
    """

    __tablename__ = "creatures"

    id = Column(Integer, primary_key=True, index=True)

    # Core identification
    name = Column(String(200), nullable=False, index=True)
    size = Column(String(50))  # Tiny, Small, Medium, Large, Huge, Gargantuan
    creature_type = Column(String(150), index=True)  # humanoid, dragon, undead, etc.
    alignment = Column(String(100))  # lawful good, neutral evil, etc.

    # Combat stats
    ac = Column(Integer)  # Armor Class
    armor_type = Column(String(100))  # natural armor, chain mail, etc.
    hp = Column(Integer)  # Hit Points
    hit_dice = Column(String(50))  # e.g., "18d12+108"

    # Movement speeds (stored as JSONB for flexibility)
    speed = Column(JSONB)  # {"walk": "30 ft.", "fly": "60 ft.", "swim": "40 ft."}

    # Ability scores
    strength = Column(Integer)
    dexterity = Column(Integer)
    constitution = Column(Integer)
    intelligence = Column(Integer)
    wisdom = Column(Integer)
    charisma = Column(Integer)

    # Proficiencies and resistances
    saving_throws = Column(Text)  # "Dex +5, Con +11, Wis +7, Cha +9"
    skills = Column(Text)  # "Perception +12, Stealth +5"
    damage_resistances = Column(Text)  # "fire, cold"
    damage_immunities = Column(Text)  # "poison, lightning"
    condition_immunities = Column(Text)  # "charmed, frightened"

    # Senses and communication
    senses = Column(Text)  # "darkvision 60 ft., passive Perception 22"
    languages = Column(Text)  # "Common, Draconic"

    # Challenge and rewards
    cr = Column(String(100), index=True)  # Challenge Rating: "1/4", "5", "16", etc.
    xp = Column(String(100), nullable=True)  # XP value (e.g. "200", "700")

    # Abilities and actions (stored as text for DM display)
    actions = Column(Text)  # Attack descriptions, abilities
    legendary_actions = Column(Text, nullable=True)  # For legendary creatures
    traits = Column(Text, nullable=True)  # Special traits, reactions, feats

    # Spell save DC (for spellcaster creatures)
    dc = Column(Integer, nullable=True)

    # Metadata
    source = Column(String(100))  # "Hoard of the Dragon Queen", "SRD", etc.

    # Indexes for common queries
    __table_args__ = (
        Index("idx_creature_name_search", "name"),
        Index("idx_creature_type_cr", "creature_type", "cr"),
        Index("idx_creature_cr", "cr"),
    )

    def to_dict(self):
        """Convert creature to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "creature_type": self.creature_type,
            "alignment": self.alignment,
            "ac": self.ac,
            "armor_type": self.armor_type,
            "hp": self.hp,
            "hit_dice": self.hit_dice,
            "speed": self.speed,
            "abilities": {
                "str": self.strength,
                "dex": self.dexterity,
                "con": self.constitution,
                "int": self.intelligence,
                "wis": self.wisdom,
                "cha": self.charisma,
            },
            "saving_throws": self.saving_throws,
            "skills": self.skills,
            "damage_resistances": self.damage_resistances,
            "damage_immunities": self.damage_immunities,
            "condition_immunities": self.condition_immunities,
            "senses": self.senses,
            "languages": self.languages,
            "cr": self.cr,
            "xp": self.xp,
            "actions": self.actions,
            "legendary_actions": self.legendary_actions,
            "traits": self.traits,
            "dc": self.dc,
            "source": self.source,
        }

    def get_stat_block(self) -> str:
        """Format creature stats as readable text block for DM."""
        lines = [
            f"=== {self.name} ===",
            f"{self.size} {self.creature_type}, {self.alignment}",
            "",
            f"AC: {self.ac}"
            + (f" ({self.armor_type})" if self.armor_type and self.armor_type != "NONE" else ""),  # type: ignore[operator]
            f"HP: {self.hp}" + (f" ({self.hit_dice})" if self.hit_dice else ""),  # type: ignore[operator]
            f"Speed: {self._format_speed()}",
            "",
            f"STR: {self.strength}  DEX: {self.dexterity}  CON: {self.constitution}",
            f"INT: {self.intelligence}  WIS: {self.wisdom}  CHA: {self.charisma}",
        ]

        if self.saving_throws is not None:  # type: ignore[comparison-overlap]
            lines.append(f"Saves: {self.saving_throws}")
        if self.skills is not None:  # type: ignore[comparison-overlap]
            lines.append(f"Skills: {self.skills}")
        if self.damage_resistances is not None:  # type: ignore[comparison-overlap]
            lines.append(f"Resistances: {self.damage_resistances}")
        if self.damage_immunities is not None:  # type: ignore[comparison-overlap]
            lines.append(f"Immunities: {self.damage_immunities}")
        if self.condition_immunities is not None:  # type: ignore[comparison-overlap]
            lines.append(f"Condition Immunities: {self.condition_immunities}")

        lines.extend(
            [
                f"Senses: {self.senses}" if self.senses is not None else "Senses: —",  # type: ignore[comparison-overlap]
                f"Languages: {self.languages}" if self.languages is not None else "Languages: —",  # type: ignore[comparison-overlap]
                f"CR: {self.cr}" + (f" (XP: {self.xp})" if self.xp else ""),
                "",
            ]
        )

        if self.traits and self.traits.strip():  # type: ignore[operator,union-attr]
            lines.append("TRAITS:")
            lines.append(self.traits)  # type: ignore[arg-type]
            lines.append("")

        if self.actions and self.actions.strip():  # type: ignore[operator,union-attr]
            lines.append("ACTIONS:")
            lines.append(self.actions)  # type: ignore[arg-type]
            lines.append("")

        if self.legendary_actions and self.legendary_actions.strip():  # type: ignore[operator,union-attr]
            lines.append("LEGENDARY ACTIONS:")
            lines.append(self.legendary_actions)  # type: ignore[arg-type]

        return "\n".join(lines)

    def _format_speed(self) -> str:
        """Format speed from JSONB or fallback to individual fields."""
        if isinstance(self.speed, dict):
            speeds = []
            for movement_type, speed_value in self.speed.items():
                if movement_type == "walk":
                    speeds.append(speed_value)
                else:
                    speeds.append(f"{movement_type} {speed_value}")
            return ", ".join(speeds)
        return str(self.speed) if self.speed is not None else "—"  # type: ignore[comparison-overlap]

    def __repr__(self):
        return f"<Creature(name='{self.name}', cr='{self.cr}', type='{self.creature_type}')>"
