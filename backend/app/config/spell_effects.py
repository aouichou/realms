"""
Spell Effects Configuration

Maps spell names to their active effect configurations.
Used to automatically create effects when spells are cast.
"""

from app.schemas.effects import EffectDuration, EffectType

# Configuration for spells that create active effects
SPELL_EFFECT_CONFIGS = {
    "Bless": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.MINUTES,
        "duration_value": 1,  # 1 minute = 10 rounds
        "rounds_remaining": 10,
        "description": "Add 1d4 to attack rolls and saving throws",
        "dice_bonus": "1d4",
        "requires_concentration": True,
    },
    "Haste": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.MINUTES,
        "duration_value": 1,
        "rounds_remaining": 10,
        "description": "+2 AC, advantage on DEX saves, doubled speed, extra action each turn",
        "bonus_value": 2,
        "advantage": True,
        "requires_concentration": True,
    },
    "Shield of Faith": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.MINUTES,
        "duration_value": 10,
        "rounds_remaining": 100,
        "description": "+2 AC bonus",
        "bonus_value": 2,
        "requires_concentration": True,
    },
    "Bane": {
        "effect_type": EffectType.DEBUFF,
        "duration_type": EffectDuration.MINUTES,
        "duration_value": 1,
        "rounds_remaining": 10,
        "description": "Subtract 1d4 from attack rolls and saving throws",
        "dice_bonus": "-1d4",
        "requires_concentration": True,
    },
    "Faerie Fire": {
        "effect_type": EffectType.DEBUFF,
        "duration_type": EffectDuration.MINUTES,
        "duration_value": 1,
        "rounds_remaining": 10,
        "description": "Outlined in light, attackers have advantage on attacks",
        "requires_concentration": True,
    },
    "Mage Armor": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.HOURS,
        "duration_value": 8,
        "description": "AC becomes 13 + DEX modifier",
        "bonus_value": 3,
        "requires_concentration": False,
    },
    "Blur": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.MINUTES,
        "duration_value": 1,
        "rounds_remaining": 10,
        "description": "Attackers have disadvantage on attack rolls against you",
        "requires_concentration": True,
    },
    "Heroism": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.MINUTES,
        "duration_value": 1,
        "rounds_remaining": 10,
        "description": "Immune to fear, gain temporary HP each turn",
        "requires_concentration": True,
    },
    "Invisibility": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.HOURS,
        "duration_value": 1,
        "rounds_remaining": 600,
        "description": "Invisible until you attack or cast a spell",
        "requires_concentration": True,
    },
    "Barkskin": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.HOURS,
        "duration_value": 1,
        "rounds_remaining": 600,
        "description": "AC cannot be less than 16",
        "requires_concentration": True,
    },
    "Greater Invisibility": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.MINUTES,
        "duration_value": 1,
        "rounds_remaining": 10,
        "description": "Invisible, attackers have disadvantage even when you attack",
        "requires_concentration": True,
    },
    "Fly": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.MINUTES,
        "duration_value": 10,
        "rounds_remaining": 100,
        "description": "Gain flying speed of 60 feet",
        "requires_concentration": True,
    },
    "Stoneskin": {
        "effect_type": EffectType.BUFF,
        "duration_type": EffectDuration.HOURS,
        "duration_value": 1,
        "rounds_remaining": 600,
        "description": "Resistance to nonmagical bludgeoning, piercing, and slashing damage",
        "requires_concentration": True,
    },
}

# Conditions that can be applied as effects
CONDITION_EFFECTS = {
    "Poisoned": {
        "effect_type": EffectType.CONDITION,
        "duration_type": EffectDuration.ROUNDS,
        "description": "Disadvantage on attack rolls and ability checks",
        "disadvantage": True,
    },
    "Blinded": {
        "effect_type": EffectType.CONDITION,
        "duration_type": EffectDuration.ROUNDS,
        "description": "Can't see, auto-fail sight checks, disadvantage on attacks, attackers have advantage",
        "disadvantage": True,
    },
    "Stunned": {
        "effect_type": EffectType.CONDITION,
        "duration_type": EffectDuration.ROUNDS,
        "description": "Incapacitated, can't move, auto-fail STR/DEX saves, attackers have advantage",
    },
    "Paralyzed": {
        "effect_type": EffectType.CONDITION,
        "duration_type": EffectDuration.ROUNDS,
        "description": "Incapacitated, can't move or speak, auto-fail STR/DEX saves, attackers have advantage",
    },
    "Frightened": {
        "effect_type": EffectType.CONDITION,
        "duration_type": EffectDuration.ROUNDS,
        "description": "Disadvantage on ability checks and attacks while source of fear is in sight",
        "disadvantage": True,
    },
    "Charmed": {
        "effect_type": EffectType.CONDITION,
        "duration_type": EffectDuration.ROUNDS,
        "description": "Can't attack charmer, charmer has advantage on social interactions",
    },
}


def get_effect_config(spell_name: str) -> dict | None:
    """
    Get effect configuration for a spell.

    Args:
        spell_name: Name of the spell

    Returns:
        Effect configuration dict or None if spell doesn't create effects
    """
    return SPELL_EFFECT_CONFIGS.get(spell_name)


def spell_creates_effect(spell_name: str) -> bool:
    """
    Check if a spell creates an active effect.

    Args:
        spell_name: Name of the spell

    Returns:
        True if spell creates an effect, False otherwise
    """
    return spell_name in SPELL_EFFECT_CONFIGS
