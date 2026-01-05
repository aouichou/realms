"""
Starting equipment sets for D&D 5e classes
Based on official D&D 5e Player's Handbook starting equipment
"""

from typing import Any, Dict, List, Optional

from app.db.models import CharacterClass, ItemType


class StartingEquipmentItem:
    """Represents an item in a starting equipment set"""

    def __init__(
        self,
        name: str,
        item_type: ItemType,
        weight: int,
        value: int,
        equipped: bool = False,
        quantity: int = 1,
        properties: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.item_type = item_type
        self.weight = weight
        self.value = value
        self.equipped = equipped
        self.quantity = quantity
        self.properties = properties or {}


# Define starting equipment for each class
STARTING_EQUIPMENT = {
    CharacterClass.FIGHTER: [
        StartingEquipmentItem(
            name="Longsword",
            item_type=ItemType.WEAPON,
            weight=3,
            value=15,
            equipped=True,
            properties={
                "damage_dice": "1d8",
                "damage_type": "slashing",
                "weapon_properties": ["versatile"],
                "versatile_damage": "1d10",
                "attack_bonus": 0,
            },
        ),
        StartingEquipmentItem(
            name="Shield",
            item_type=ItemType.ARMOR,
            weight=6,
            value=10,
            equipped=True,
            properties={"ac_bonus": 2, "armor_type": "shield"},
        ),
        StartingEquipmentItem(
            name="Chain Mail",
            item_type=ItemType.ARMOR,
            weight=55,
            value=75,
            equipped=True,
            properties={
                "ac_base": 16,
                "armor_type": "heavy",
                "stealth_disadvantage": True,
                "str_requirement": 13,
            },
        ),
        StartingEquipmentItem(
            name="Explorer's Pack",
            item_type=ItemType.MISC,
            weight=59,
            value=10,
            properties={
                "contents": [
                    "backpack",
                    "bedroll",
                    "mess kit",
                    "tinderbox",
                    "10 torches",
                    "10 rations",
                    "waterskin",
                    "50ft rope",
                ]
            },
        ),
        StartingEquipmentItem(
            name="Healing Potion",
            item_type=ItemType.CONSUMABLE,
            weight=1,
            value=50,
            quantity=2,
            properties={
                "healing_dice": "2d4+2",
                "description": "Restores hit points when consumed",
            },
        ),
    ],
    CharacterClass.WIZARD: [
        StartingEquipmentItem(
            name="Quarterstaff",
            item_type=ItemType.WEAPON,
            weight=4,
            value=2,
            equipped=True,
            properties={
                "damage_dice": "1d6",
                "damage_type": "bludgeoning",
                "weapon_properties": ["versatile"],
                "versatile_damage": "1d8",
            },
        ),
        StartingEquipmentItem(
            name="Spellbook",
            item_type=ItemType.MISC,
            weight=3,
            value=50,
            properties={
                "item_type": "spellcasting_focus",
                "description": "Contains your wizard spells",
            },
        ),
        StartingEquipmentItem(
            name="Component Pouch",
            item_type=ItemType.MISC,
            weight=2,
            value=25,
            equipped=True,
            properties={
                "item_type": "spellcasting_focus",
                "description": "Material components for spells",
            },
        ),
        StartingEquipmentItem(
            name="Scholar's Pack",
            item_type=ItemType.MISC,
            weight=10,
            value=40,
            properties={
                "contents": [
                    "backpack",
                    "book of lore",
                    "ink",
                    "ink pen",
                    "10 parchment",
                    "bag of sand",
                    "small knife",
                ]
            },
        ),
        StartingEquipmentItem(
            name="Robes",
            item_type=ItemType.ARMOR,
            weight=4,
            value=1,
            equipped=True,
            properties={"ac_base": 10, "ac_dex_bonus": True, "armor_type": "clothing"},
        ),
    ],
    CharacterClass.ROGUE: [
        StartingEquipmentItem(
            name="Shortsword",
            item_type=ItemType.WEAPON,
            weight=2,
            value=10,
            equipped=True,
            properties={
                "damage_dice": "1d6",
                "damage_type": "piercing",
                "weapon_properties": ["finesse", "light"],
            },
        ),
        StartingEquipmentItem(
            name="Dagger",
            item_type=ItemType.WEAPON,
            weight=1,
            value=2,
            equipped=True,
            quantity=2,
            properties={
                "damage_dice": "1d4",
                "damage_type": "piercing",
                "weapon_properties": ["finesse", "light", "thrown"],
                "range": "20/60",
            },
        ),
        StartingEquipmentItem(
            name="Leather Armor",
            item_type=ItemType.ARMOR,
            weight=10,
            value=5,
            equipped=True,
            properties={"ac_base": 11, "ac_dex_bonus": True, "armor_type": "light"},
        ),
        StartingEquipmentItem(
            name="Thieves' Tools",
            item_type=ItemType.MISC,
            weight=1,
            value=25,
            properties={
                "grants_ability": "lock_picking",
                "description": "For disabling traps and picking locks",
            },
        ),
        StartingEquipmentItem(
            name="Burglar's Pack",
            item_type=ItemType.MISC,
            weight=44,
            value=16,
            properties={
                "contents": [
                    "backpack",
                    "bag of ball bearings",
                    "10ft string",
                    "bell",
                    "5 candles",
                    "crowbar",
                    "hammer",
                    "10 pitons",
                    "hooded lantern",
                    "2 flasks of oil",
                    "5 rations",
                    "tinderbox",
                    "waterskin",
                    "50ft rope",
                ]
            },
        ),
    ],
    CharacterClass.CLERIC: [
        StartingEquipmentItem(
            name="Mace",
            item_type=ItemType.WEAPON,
            weight=4,
            value=5,
            equipped=True,
            properties={"damage_dice": "1d6", "damage_type": "bludgeoning"},
        ),
        StartingEquipmentItem(
            name="Shield",
            item_type=ItemType.ARMOR,
            weight=6,
            value=10,
            equipped=True,
            properties={"ac_bonus": 2, "armor_type": "shield"},
        ),
        StartingEquipmentItem(
            name="Scale Mail",
            item_type=ItemType.ARMOR,
            weight=45,
            value=50,
            equipped=True,
            properties={
                "ac_base": 14,
                "ac_dex_bonus": True,
                "ac_dex_max": 2,
                "armor_type": "medium",
                "stealth_disadvantage": True,
            },
        ),
        StartingEquipmentItem(
            name="Holy Symbol",
            item_type=ItemType.MISC,
            weight=1,
            value=5,
            equipped=True,
            properties={
                "item_type": "spellcasting_focus",
                "description": "Divine focus for casting cleric spells",
            },
        ),
        StartingEquipmentItem(
            name="Priest's Pack",
            item_type=ItemType.MISC,
            weight=24,
            value=19,
            properties={
                "contents": [
                    "backpack",
                    "blanket",
                    "10 candles",
                    "tinderbox",
                    "alms box",
                    "2 incense blocks",
                    "censer",
                    "vestments",
                    "2 rations",
                    "waterskin",
                ]
            },
        ),
    ],
    CharacterClass.RANGER: [
        StartingEquipmentItem(
            name="Longbow",
            item_type=ItemType.WEAPON,
            weight=2,
            value=50,
            equipped=True,
            properties={
                "damage_dice": "1d8",
                "damage_type": "piercing",
                "weapon_properties": ["ammunition", "heavy", "two-handed"],
                "range": "150/600",
            },
        ),
        StartingEquipmentItem(
            name="Arrows",
            item_type=ItemType.WEAPON,
            weight=1,
            value=1,
            quantity=20,
            properties={"ammunition_type": "arrow"},
        ),
        StartingEquipmentItem(
            name="Shortsword",
            item_type=ItemType.WEAPON,
            weight=2,
            value=10,
            equipped=True,
            properties={
                "damage_dice": "1d6",
                "damage_type": "piercing",
                "weapon_properties": ["finesse", "light"],
            },
        ),
        StartingEquipmentItem(
            name="Leather Armor",
            item_type=ItemType.ARMOR,
            weight=10,
            value=5,
            equipped=True,
            properties={"ac_base": 11, "ac_dex_bonus": True, "armor_type": "light"},
        ),
        StartingEquipmentItem(
            name="Explorer's Pack",
            item_type=ItemType.MISC,
            weight=59,
            value=10,
            properties={
                "contents": [
                    "backpack",
                    "bedroll",
                    "mess kit",
                    "tinderbox",
                    "10 torches",
                    "10 rations",
                    "waterskin",
                    "50ft rope",
                ]
            },
        ),
    ],
    CharacterClass.PALADIN: [
        StartingEquipmentItem(
            name="Longsword",
            item_type=ItemType.WEAPON,
            weight=3,
            value=15,
            equipped=True,
            properties={
                "damage_dice": "1d8",
                "damage_type": "slashing",
                "weapon_properties": ["versatile"],
                "versatile_damage": "1d10",
            },
        ),
        StartingEquipmentItem(
            name="Shield",
            item_type=ItemType.ARMOR,
            weight=6,
            value=10,
            equipped=True,
            properties={"ac_bonus": 2, "armor_type": "shield"},
        ),
        StartingEquipmentItem(
            name="Chain Mail",
            item_type=ItemType.ARMOR,
            weight=55,
            value=75,
            equipped=True,
            properties={
                "ac_base": 16,
                "armor_type": "heavy",
                "stealth_disadvantage": True,
                "str_requirement": 13,
            },
        ),
        StartingEquipmentItem(
            name="Holy Symbol",
            item_type=ItemType.MISC,
            weight=1,
            value=5,
            equipped=True,
            properties={
                "item_type": "spellcasting_focus",
                "description": "Divine focus for casting paladin spells",
            },
        ),
        StartingEquipmentItem(
            name="Priest's Pack",
            item_type=ItemType.MISC,
            weight=24,
            value=19,
            properties={
                "contents": [
                    "backpack",
                    "blanket",
                    "10 candles",
                    "tinderbox",
                    "alms box",
                    "2 incense blocks",
                    "censer",
                    "vestments",
                    "2 rations",
                    "waterskin",
                ]
            },
        ),
    ],
    CharacterClass.BARBARIAN: [
        StartingEquipmentItem(
            name="Greataxe",
            item_type=ItemType.WEAPON,
            weight=7,
            value=30,
            equipped=True,
            properties={
                "damage_dice": "1d12",
                "damage_type": "slashing",
                "weapon_properties": ["heavy", "two-handed"],
            },
        ),
        StartingEquipmentItem(
            name="Handaxe",
            item_type=ItemType.WEAPON,
            weight=2,
            value=5,
            equipped=True,
            quantity=2,
            properties={
                "damage_dice": "1d6",
                "damage_type": "slashing",
                "weapon_properties": ["light", "thrown"],
                "range": "20/60",
            },
        ),
        StartingEquipmentItem(
            name="Javelin",
            item_type=ItemType.WEAPON,
            weight=2,
            value=5,
            quantity=4,
            properties={
                "damage_dice": "1d6",
                "damage_type": "piercing",
                "weapon_properties": ["thrown"],
                "range": "30/120",
            },
        ),
        StartingEquipmentItem(
            name="Explorer's Pack",
            item_type=ItemType.MISC,
            weight=59,
            value=10,
            properties={
                "contents": [
                    "backpack",
                    "bedroll",
                    "mess kit",
                    "tinderbox",
                    "10 torches",
                    "10 rations",
                    "waterskin",
                    "50ft rope",
                ]
            },
        ),
    ],
    CharacterClass.BARD: [
        StartingEquipmentItem(
            name="Rapier",
            item_type=ItemType.WEAPON,
            weight=2,
            value=25,
            equipped=True,
            properties={
                "damage_dice": "1d8",
                "damage_type": "piercing",
                "weapon_properties": ["finesse"],
            },
        ),
        StartingEquipmentItem(
            name="Dagger",
            item_type=ItemType.WEAPON,
            weight=1,
            value=2,
            equipped=True,
            properties={
                "damage_dice": "1d4",
                "damage_type": "piercing",
                "weapon_properties": ["finesse", "light", "thrown"],
                "range": "20/60",
            },
        ),
        StartingEquipmentItem(
            name="Leather Armor",
            item_type=ItemType.ARMOR,
            weight=10,
            value=5,
            equipped=True,
            properties={"ac_base": 11, "ac_dex_bonus": True, "armor_type": "light"},
        ),
        StartingEquipmentItem(
            name="Lute",
            item_type=ItemType.MISC,
            weight=2,
            value=35,
            equipped=True,
            properties={
                "item_type": "spellcasting_focus",
                "description": "Musical instrument for casting bard spells",
            },
        ),
        StartingEquipmentItem(
            name="Entertainer's Pack",
            item_type=ItemType.MISC,
            weight=38,
            value=40,
            properties={
                "contents": [
                    "backpack",
                    "bedroll",
                    "2 costumes",
                    "5 candles",
                    "5 rations",
                    "waterskin",
                    "disguise kit",
                ]
            },
        ),
    ],
    CharacterClass.DRUID: [
        StartingEquipmentItem(
            name="Scimitar",
            item_type=ItemType.WEAPON,
            weight=3,
            value=25,
            equipped=True,
            properties={
                "damage_dice": "1d6",
                "damage_type": "slashing",
                "weapon_properties": ["finesse", "light"],
            },
        ),
        StartingEquipmentItem(
            name="Wooden Shield",
            item_type=ItemType.ARMOR,
            weight=6,
            value=10,
            equipped=True,
            properties={
                "ac_bonus": 2,
                "armor_type": "shield",
                "description": "Made of wood (druids avoid metal)",
            },
        ),
        StartingEquipmentItem(
            name="Leather Armor",
            item_type=ItemType.ARMOR,
            weight=10,
            value=5,
            equipped=True,
            properties={"ac_base": 11, "ac_dex_bonus": True, "armor_type": "light"},
        ),
        StartingEquipmentItem(
            name="Druidic Focus",
            item_type=ItemType.MISC,
            weight=1,
            value=5,
            equipped=True,
            properties={
                "item_type": "spellcasting_focus",
                "description": "Totem or wooden staff for casting druid spells",
            },
        ),
        StartingEquipmentItem(
            name="Explorer's Pack",
            item_type=ItemType.MISC,
            weight=59,
            value=10,
            properties={
                "contents": [
                    "backpack",
                    "bedroll",
                    "mess kit",
                    "tinderbox",
                    "10 torches",
                    "10 rations",
                    "waterskin",
                    "50ft rope",
                ]
            },
        ),
    ],
    CharacterClass.MONK: [
        StartingEquipmentItem(
            name="Shortsword",
            item_type=ItemType.WEAPON,
            weight=2,
            value=10,
            equipped=True,
            properties={
                "damage_dice": "1d6",
                "damage_type": "piercing",
                "weapon_properties": ["finesse", "light"],
            },
        ),
        StartingEquipmentItem(
            name="Dart",
            item_type=ItemType.WEAPON,
            weight=0,
            value=1,
            quantity=10,
            properties={
                "damage_dice": "1d4",
                "damage_type": "piercing",
                "weapon_properties": ["finesse", "thrown"],
                "range": "20/60",
            },
        ),
        StartingEquipmentItem(
            name="Dungeoneer's Pack",
            item_type=ItemType.MISC,
            weight=61,
            value=12,
            properties={
                "contents": [
                    "backpack",
                    "crowbar",
                    "hammer",
                    "10 pitons",
                    "10 torches",
                    "tinderbox",
                    "10 rations",
                    "waterskin",
                    "50ft rope",
                ]
            },
        ),
    ],
    CharacterClass.SORCERER: [
        StartingEquipmentItem(
            name="Dagger",
            item_type=ItemType.WEAPON,
            weight=1,
            value=2,
            equipped=True,
            quantity=2,
            properties={
                "damage_dice": "1d4",
                "damage_type": "piercing",
                "weapon_properties": ["finesse", "light", "thrown"],
                "range": "20/60",
            },
        ),
        StartingEquipmentItem(
            name="Component Pouch",
            item_type=ItemType.MISC,
            weight=2,
            value=25,
            equipped=True,
            properties={
                "item_type": "spellcasting_focus",
                "description": "Material components for spells",
            },
        ),
        StartingEquipmentItem(
            name="Dungeoneer's Pack",
            item_type=ItemType.MISC,
            weight=61,
            value=12,
            properties={
                "contents": [
                    "backpack",
                    "crowbar",
                    "hammer",
                    "10 pitons",
                    "10 torches",
                    "tinderbox",
                    "10 rations",
                    "waterskin",
                    "50ft rope",
                ]
            },
        ),
    ],
    CharacterClass.WARLOCK: [
        StartingEquipmentItem(
            name="Dagger",
            item_type=ItemType.WEAPON,
            weight=1,
            value=2,
            equipped=True,
            quantity=2,
            properties={
                "damage_dice": "1d4",
                "damage_type": "piercing",
                "weapon_properties": ["finesse", "light", "thrown"],
                "range": "20/60",
            },
        ),
        StartingEquipmentItem(
            name="Leather Armor",
            item_type=ItemType.ARMOR,
            weight=10,
            value=5,
            equipped=True,
            properties={"ac_base": 11, "ac_dex_bonus": True, "armor_type": "light"},
        ),
        StartingEquipmentItem(
            name="Arcane Focus",
            item_type=ItemType.MISC,
            weight=1,
            value=10,
            equipped=True,
            properties={
                "item_type": "spellcasting_focus",
                "description": "Crystal, orb, or rod for casting warlock spells",
            },
        ),
        StartingEquipmentItem(
            name="Scholar's Pack",
            item_type=ItemType.MISC,
            weight=10,
            value=40,
            properties={
                "contents": [
                    "backpack",
                    "book of lore",
                    "ink",
                    "ink pen",
                    "10 parchment",
                    "bag of sand",
                    "small knife",
                ]
            },
        ),
    ],
}


def get_starting_equipment(character_class: CharacterClass) -> List[StartingEquipmentItem]:
    """
    Get the starting equipment for a character class

    Args:
        character_class: The character's class

    Returns:
        List of starting equipment items
    """
    return STARTING_EQUIPMENT.get(character_class, [])
