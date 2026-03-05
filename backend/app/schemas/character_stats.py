"""Character stats schema with equipment bonuses"""

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict


class SkillData(BaseModel):
    """Skill data with modifier and proficiency status"""

    modifier: int
    proficient: bool


class EquippedItemBonus(BaseModel):
    """Represents a bonus from an equipped item"""

    item_name: str
    ac_bonus: int = 0
    attack_bonus: int = 0
    damage_bonus: str = ""
    other_properties: Dict[str, Any] = {}


class CharacterStatsResponse(BaseModel):
    """Full character statistics including equipment bonuses"""

    # Base ability scores
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int

    # Ability modifiers
    strength_modifier: int
    dexterity_modifier: int
    constitution_modifier: int
    intelligence_modifier: int
    wisdom_modifier: int
    charisma_modifier: int

    # Proficiency bonus (based on level)
    proficiency_bonus: int

    # Combat stats
    armor_class: int
    base_armor_class: int
    armor_class_bonuses: List[EquippedItemBonus]

    initiative_bonus: int

    # Attack bonuses
    melee_attack_bonus: int
    ranged_attack_bonus: int
    spell_save_dc: int  # 8 + proficiency + spellcasting modifier

    # Hit points
    hp_current: int
    hp_max: int

    # Movement
    speed: int  # Base 30 ft for most races

    # Saving throws (ability modifier + proficiency if proficient)
    saving_throws: Dict[str, int]

    # Skills (ability modifier + proficiency if proficient)
    skills: Dict[str, SkillData]

    # Equipped items providing bonuses
    equipped_items: List[EquippedItemBonus]

    model_config = ConfigDict(from_attributes=True)
