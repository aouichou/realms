"""Enumeration definitions for various D&D 5e concepts and game elements."""

from enum import Enum as PyEnum


class CharacterType(str, PyEnum):
    """Character type enumeration"""

    PLAYER = "player"
    COMPANION = "companion"
    NPC = "npc"


class CharacterClass(str, PyEnum):
    """D&D 5e character classes"""

    BARBARIAN = "Barbarian"
    BARD = "Bard"
    CLERIC = "Cleric"
    DRUID = "Druid"
    FIGHTER = "Fighter"
    MONK = "Monk"
    PALADIN = "Paladin"
    RANGER = "Ranger"
    ROGUE = "Rogue"
    SORCERER = "Sorcerer"
    WARLOCK = "Warlock"
    WIZARD = "Wizard"


class CharacterRace(str, PyEnum):
    """D&D 5e character races"""

    DRAGONBORN = "Dragonborn"
    DWARF = "Dwarf"
    ELF = "Elf"
    GNOME = "Gnome"
    HALFELF = "Half-Elf"
    HALFORC = "Half-Orc"
    HALFLING = "Halfling"
    HUMAN = "Human"
    TIEFLING = "Tiefling"


class ItemType(str, PyEnum):
    """Item type categories"""

    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    QUEST = "quest"
    MISC = "misc"


class SpellSchool(str, PyEnum):
    """D&D 5e schools of magic"""

    ABJURATION = "Abjuration"
    CONJURATION = "Conjuration"
    DIVINATION = "Divination"
    ENCHANTMENT = "Enchantment"
    EVOCATION = "Evocation"
    ILLUSION = "Illusion"
    NECROMANCY = "Necromancy"
    TRANSMUTATION = "Transmutation"


class CastingTime(str, PyEnum):
    """Spell casting time"""

    ACTION = "1 action"
    BONUS_ACTION = "1 bonus action"
    REACTION = "1 reaction"
    MINUTE = "1 minute"
    TEN_MINUTES = "10 minutes"
    HOUR = "1 hour"
    RITUAL = "1 minute (ritual)"


class ConditionType(str, PyEnum):
    """D&D 5e conditions"""

    BLINDED = "Blinded"
    CHARMED = "Charmed"
    DEAFENED = "Deafened"
    FRIGHTENED = "Frightened"
    GRAPPLED = "Grappled"
    INCAPACITATED = "Incapacitated"
    INVISIBLE = "Invisible"
    PARALYZED = "Paralyzed"
    PETRIFIED = "Petrified"
    POISONED = "Poisoned"
    PRONE = "Prone"
    RESTRAINED = "Restrained"
    STUNNED = "Stunned"
    UNCONSCIOUS = "Unconscious"


class QuestState(str, PyEnum):
    """Quest state enumeration"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, PyEnum):
    """Adventure memory event types"""

    COMBAT = "combat"
    DIALOGUE = "dialogue"
    DISCOVERY = "discovery"
    DECISION = "decision"
    QUEST = "quest"
    NPC_INTERACTION = "npc_interaction"
    LOOT = "loot"
    LOCATION = "location"
    OTHER = "other"


class MessageRole(str, PyEnum):
    """Conversation message roles"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
