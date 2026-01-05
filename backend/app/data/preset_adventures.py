"""Preset adventure scenarios for Mistral Realms

This module contains pre-built adventure scenarios that can be loaded
to quickly start a game session with predefined quests, encounters, and NPCs.
"""

from typing import Any, Dict, List

from app.db.models import CharacterClass, CharacterRace, ItemType


class PresetAdventure:
    """Structure for a preset adventure"""

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        recommended_level: int,
        setting: str,
        opening_narration: str,
        quest_data: Dict[str, Any],
        npcs: List[Dict[str, Any]],
        initial_location: str,
        combat_encounter: Dict[str, Any] | None = None,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.recommended_level = recommended_level
        self.setting = setting
        self.opening_narration = opening_narration
        self.quest_data = quest_data
        self.npcs = npcs
        self.initial_location = initial_location
        self.combat_encounter = combat_encounter


# Goblin Ambush Adventure
GOBLIN_AMBUSH = PresetAdventure(
    id="goblin_ambush",
    title="Goblin Ambush on the Trade Road",
    description="A simple but dangerous encounter with goblin raiders on the trade road. Perfect for beginning adventurers.",
    recommended_level=1,
    setting="Forest road near a small village",
    opening_narration="""You've been traveling along the muddy trade road for hours, the dense forest pressing in on either side. The village of Thornhaven lies just a few miles ahead, where you hope to find rest and perhaps some work.

As you round a bend, you notice fresh tracks in the mud—small, clawed footprints leading into the underbrush. Before you can investigate further, high-pitched cackling erupts from the trees!

Three goblins burst from the foliage, their yellowed teeth bared in savage grins. One clutches a crude bow, while the other two brandish rusty scimitars. Behind them, you glimpse crude traps and a small camp—these goblins have been ambushing travelers on this very spot!

"Fresh meat for the tribe!" one shrieks in broken Common, raising its blade.""",
    initial_location="Trade Road to Thornhaven",
    quest_data={
        "title": "Clear the Goblin Ambush",
        "description": "Goblin raiders have been ambushing travelers on the trade road to Thornhaven. The village elder has offered a reward for anyone brave enough to deal with the threat.",
        "objectives": [
            {
                "description": "Defeat the goblin ambushers",
                "order": 0,
            },
            {
                "description": "Search the goblin camp for stolen goods",
                "order": 1,
            },
            {
                "description": "Return to Thornhaven and report success",
                "order": 2,
            },
        ],
        "rewards": {
            "xp": 150,
            "gold": 25,
            "items": ["Potion of Healing"],
        },
    },
    npcs=[
        {
            "name": "Skrag the Sneaky",
            "race": CharacterRace.HALFELF,
            "character_class": CharacterClass.ROGUE,
            "level": 1,
            "is_enemy": True,
            "personality": "Cowardly and cunning. Will flee if health drops below 30%.",
            "hp_max": 7,
            "hp_current": 7,
            "strength": 8,
            "dexterity": 14,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 8,
            "charisma": 8,
            "equipment": [
                {
                    "name": "Shortbow",
                    "item_type": ItemType.WEAPON,
                    "equipped": True,
                    "properties": {
                        "damage_dice": "1d6",
                        "damage_type": "piercing",
                        "range": "80/320",
                    },
                },
                {
                    "name": "Leather Armor",
                    "item_type": ItemType.ARMOR,
                    "equipped": True,
                    "properties": {
                        "ac_base": 11,
                        "ac_dex_bonus": True,
                    },
                },
            ],
            "description": "A wiry goblin with a crooked nose and shifty eyes. Carries a shortbow.",
        },
        {
            "name": "Gruk the Grunt",
            "race": CharacterRace.HALFORC,
            "character_class": CharacterClass.FIGHTER,
            "level": 1,
            "is_enemy": True,
            "personality": "Aggressive and fearless. Charges into melee combat.",
            "hp_max": 9,
            "hp_current": 9,
            "strength": 13,
            "dexterity": 12,
            "constitution": 12,
            "intelligence": 8,
            "wisdom": 9,
            "charisma": 6,
            "equipment": [
                {
                    "name": "Scimitar",
                    "item_type": ItemType.WEAPON,
                    "equipped": True,
                    "properties": {
                        "damage_dice": "1d6",
                        "damage_type": "slashing",
                        "weapon_properties": ["finesse", "light"],
                    },
                },
                {
                    "name": "Leather Armor",
                    "item_type": ItemType.ARMOR,
                    "equipped": True,
                    "properties": {
                        "ac_base": 11,
                        "ac_dex_bonus": True,
                    },
                },
            ],
            "description": "A brutish goblin with scarred arms and a nasty grin. Wields a rusty scimitar.",
        },
        {
            "name": "Nix the Nasty",
            "race": CharacterRace.HALFORC,
            "character_class": CharacterClass.FIGHTER,
            "level": 1,
            "is_enemy": True,
            "personality": "Vicious and cruel. Fights to the death.",
            "hp_max": 9,
            "hp_current": 9,
            "strength": 12,
            "dexterity": 13,
            "constitution": 11,
            "intelligence": 9,
            "wisdom": 8,
            "charisma": 7,
            "equipment": [
                {
                    "name": "Scimitar",
                    "item_type": ItemType.WEAPON,
                    "equipped": True,
                    "properties": {
                        "damage_dice": "1d6",
                        "damage_type": "slashing",
                        "weapon_properties": ["finesse", "light"],
                    },
                },
                {
                    "name": "Leather Armor",
                    "item_type": ItemType.ARMOR,
                    "equipped": True,
                    "properties": {
                        "ac_base": 11,
                        "ac_dex_bonus": True,
                    },
                },
            ],
            "description": "A mean-looking goblin with filed teeth and cruel eyes. Carries a bloodstained scimitar.",
        },
    ],
    combat_encounter={
        "description": "The goblins attack immediately, trying to overwhelm you with numbers!",
        "environment": "forest road with difficult terrain (underbrush) on the sides",
        "special_mechanics": [
            "Goblins can use Nimble Escape (bonus action to Disengage or Hide)",
            "Difficult terrain in the underbrush (costs extra movement)",
            "Goblin archer has half cover (+2 AC) behind a tree",
        ],
        "tactics": {
            "Skrag the Sneaky": "Stays at range, uses shortbow, hides behind trees. Flees if brought below 3 HP.",
            "Gruk the Grunt": "Charges into melee, fights aggressively.",
            "Nix the Nasty": "Tries to flank with Gruk, uses pack tactics if possible.",
        },
        "treasure": {
            "goblin_camp": [
                {"name": "15 Gold Pieces", "description": "Stolen from travelers"},
                {"name": "Traveler's Clothes", "description": "Muddy and torn"},
                {"name": "Potion of Healing", "description": "Looted from a merchant"},
            ],
        },
    },
)


# Registry of all preset adventures
PRESET_ADVENTURES: Dict[str, PresetAdventure] = {
    "goblin_ambush": GOBLIN_AMBUSH,
}


def get_preset_adventure(adventure_id: str) -> PresetAdventure | None:
    """Get a preset adventure by ID"""
    return PRESET_ADVENTURES.get(adventure_id)


def list_preset_adventures() -> List[Dict[str, Any]]:
    """Get list of all available preset adventures with metadata"""
    return [
        {
            "id": adv.id,
            "title": adv.title,
            "description": adv.description,
            "recommended_level": adv.recommended_level,
            "setting": adv.setting,
        }
        for adv in PRESET_ADVENTURES.values()
    ]
