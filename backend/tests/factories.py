"""
Model factory functions for tests.

Each factory returns a valid SQLAlchemy model instance with sensible
defaults. Every field can be overridden via ``**kwargs``.

Usage::

    user = make_user(username="alice")
    char = make_character(user=user, name="Gandalf")
    db_session.add_all([user, char])
    await db_session.flush()
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.db.models import (
    Adventure,
    AdventureMemory,
    Character,
    CharacterCondition,
    CharacterQuest,
    CharacterSpell,
    CombatEncounter,
    Companion,
    CompanionConversation,
    ConversationMessage,
    Creature,
    Encounter,
    GameSession,
    Item,
    ItemCatalog,
    Quest,
    QuestObjective,
    Spell,
    User,
)
from app.db.models.enums import (
    CastingTime,
    CharacterClass,
    CharacterRace,
    CharacterType,
    ConditionType,
    EventType,
    ItemType,
    MessageRole,
    QuestState,
    SpellSchool,
)
from app.schemas.effects import ActiveEffect, EffectDuration, EffectType

# ── helpers ────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── User ───────────────────────────────────────────────────────────────────


def make_user(**overrides) -> User:
    defaults: dict = {
        "id": uuid.uuid4(),
        "username": f"testuser_{uuid.uuid4().hex[:8]}",
        "email": None,
        "email_blind_index": None,
        # bcrypt hash of "TestPassword123!"
        "password_hash": ("$2b$12$LJ3m4ys3Lg7E16eDKeRJLuuN9MWc4NX.XW/m3uP4EeqGPR8F5OVZC"),
        "is_guest": False,
        "guest_token": None,
        "is_active": True,
        "is_verified": False,
        "preferred_language": "en",
        "created_at": _now(),
        "last_login": None,
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return User(**defaults)


# ── Character ──────────────────────────────────────────────────────────────


def make_character(user: User | None = None, **overrides) -> Character:
    defaults: dict = {
        "id": uuid.uuid4(),
        "user_id": user.id if user else uuid.uuid4(),
        "name": "Test Character",
        "character_type": CharacterType.PLAYER,
        "character_class": CharacterClass.FIGHTER,
        "race": CharacterRace.HUMAN,
        "level": 1,
        "hp_current": 12,
        "hp_max": 12,
        "strength": 16,
        "dexterity": 14,
        "constitution": 15,
        "intelligence": 10,
        "wisdom": 12,
        "charisma": 8,
        "carrying_capacity": 240,
        "spell_slots": {},
        "active_concentration_spell": None,
        "skill_proficiencies": ["athletics", "perception"],
        "background_name": "Soldier",
        "background_description": "A veteran warrior",
        "background_skill_proficiencies": [],
        "known_spells": [],
        "prepared_spells": [],
        "cantrips": [],
        "asi_distribution": {},
        "experience_points": 0,
        "gold": 10,
        "silver": 0,
        "copper": 0,
        "background": None,
        "personality": None,
        "personality_trait": "I'm always polite and respectful.",
        "ideal": "Greater Good",
        "bond": "I protect those who cannot protect themselves.",
        "flaw": "I have a weakness for the vices of the city.",
        "motivation": "glory",
        "created_at": _now(),
        "updated_at": _now(),
        "deleted_at": None,
    }
    defaults.update(overrides)
    return Character(**defaults)


# ── GameSession ────────────────────────────────────────────────────────────


def make_session(
    user: User | None = None,
    character: Character | None = None,
    **overrides,
) -> GameSession:
    defaults: dict = {
        "id": uuid.uuid4(),
        "user_id": user.id if user else uuid.uuid4(),
        "character_id": character.id if character else uuid.uuid4(),
        "companion_id": None,
        "is_active": True,
        "current_location": "Tavern",
        "state_snapshot": {},
        "started_at": _now(),
        "last_activity_at": _now(),
    }
    defaults.update(overrides)
    return GameSession(**defaults)


# ── ConversationMessage ────────────────────────────────────────────────────


def make_message(session: GameSession | None = None, **overrides) -> ConversationMessage:
    defaults: dict = {
        "id": uuid.uuid4(),
        "session_id": session.id if session else uuid.uuid4(),
        "role": MessageRole.USER,
        "content": "Hello, I look around the tavern.",
        "tokens_used": 10,
        "scene_image_url": None,
        "companion_id": None,
        "created_at": _now(),
    }
    defaults.update(overrides)
    return ConversationMessage(**defaults)


# ── Spell ──────────────────────────────────────────────────────────────────


def make_spell(**overrides) -> Spell:
    defaults: dict = {
        "id": uuid.uuid4(),
        "name": f"Test Spell {uuid.uuid4().hex[:6]}",
        "level": 1,
        "school": SpellSchool.EVOCATION,
        "casting_time": CastingTime.ACTION,
        "range": "120 feet",
        "duration": "Instantaneous",
        "verbal": True,
        "somatic": True,
        "material": None,
        "description": "A bright streak flashes from your finger.",
        "is_concentration": False,
        "is_ritual": False,
        "damage_dice": "1d10",
        "damage_type": "fire",
    }
    defaults.update(overrides)
    return Spell(**defaults)


# ── Item ───────────────────────────────────────────────────────────────────


def make_item(character: Character | None = None, **overrides) -> Item:
    defaults: dict = {
        "id": uuid.uuid4(),
        "character_id": character.id if character else uuid.uuid4(),
        "name": "Longsword",
        "item_type": ItemType.WEAPON,
        "weight": 3,
        "value": 15,
        "properties": {
            "damage": "1d8",
            "damage_type": "slashing",
            "versatile": "1d10",
        },
        "equipped": False,
        "quantity": 1,
    }
    defaults.update(overrides)
    return Item(**defaults)


# ── Creature (integer PK — do NOT pass id, let DB auto-generate) ──────────


def make_creature(**overrides) -> Creature:
    defaults: dict = {
        "name": "Goblin",
        "size": "Small",
        "creature_type": "humanoid",
        "alignment": "neutral evil",
        "ac": 15,
        "armor_type": "leather armor, shield",
        "hp": 7,
        "hit_dice": "2d6",
        "speed": {"walk": "30 ft."},
        "strength": 8,
        "dexterity": 14,
        "constitution": 10,
        "intelligence": 10,
        "wisdom": 8,
        "charisma": 8,
        "saving_throws": None,
        "skills": "Stealth +6",
        "damage_resistances": None,
        "damage_immunities": None,
        "condition_immunities": None,
        "senses": "darkvision 60 ft., passive Perception 9",
        "languages": "Common, Goblin",
        "cr": "1/4",
        "xp": "50",
    }
    defaults.update(overrides)
    return Creature(**defaults)


# ── Companion (old-style Column()) ────────────────────────────────────────


def make_companion(
    character: Character | None = None,
    creature: Creature | None = None,
    **overrides,
) -> Companion:
    defaults: dict = {
        "id": uuid.uuid4(),
        "character_id": character.id if character else uuid.uuid4(),
        "creature_id": creature.id if creature else 1,
        "name": "Elara Swiftwind",
        "creature_name": "Elf Scout",
        "personality": "brave, loyal, curious",
        "goals": "Find her missing brother",
        "secrets": None,
        "background": "A ranger from the northern forests",
        "relationship_status": "just_met",
        "loyalty": 50,
        "hp": 16,
        "max_hp": 16,
        "ac": 13,
    }
    defaults.update(overrides)
    return Companion(**defaults)


# ── Quest ──────────────────────────────────────────────────────────────────


def make_quest(**overrides) -> Quest:
    defaults: dict = {
        "id": uuid.uuid4(),
        "title": "The Missing Merchant",
        "description": "Find the merchant who disappeared on the road.",
        "state": QuestState.NOT_STARTED,
        "quest_giver_id": None,
        "rewards": {"xp": 100, "gold": 50},
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return Quest(**defaults)


# ── QuestObjective ────────────────────────────────────────────────────────


def make_quest_objective(quest: Quest | None = None, **overrides) -> QuestObjective:
    defaults: dict = {
        "id": uuid.uuid4(),
        "quest_id": quest.id if quest else uuid.uuid4(),
        "description": "Talk to the innkeeper about the merchant.",
        "order": 1,
        "is_completed": False,
    }
    defaults.update(overrides)
    return QuestObjective(**defaults)


# ── Adventure ─────────────────────────────────────────────────────────────


def make_adventure(character: Character | None = None, **overrides) -> Adventure:
    defaults: dict = {
        "id": uuid.uuid4(),
        "character_id": character.id if character else uuid.uuid4(),
        "setting": "haunted_castle",
        "goal": "rescue_mission",
        "tone": "epic_heroic",
        "title": "The Cursed Keep",
        "description": "A dark keep looms on the horizon...",
        "scenes": [
            {
                "scene_number": 1,
                "title": "Arrival",
                "description": "You arrive at the keep.",
            }
        ],
        "is_completed": False,
        "created_at": _now(),
        "updated_at": _now(),
    }
    defaults.update(overrides)
    return Adventure(**defaults)


# ── AdventureMemory ───────────────────────────────────────────────────────
# NOTE: The actual model fields are ``importance`` (int, not float) and
# ``timestamp`` (not ``created_at`` for the primary ts column).
# ``embedding`` (Vector) is nullable — skip it for SQLite tests.
# ``tags``, ``npcs_involved``, ``locations``, ``items_involved`` are
# ARRAY(String) — not supported on SQLite, so we omit them here.


def make_memory(session: GameSession | None = None, **overrides) -> AdventureMemory:
    defaults: dict = {
        "id": uuid.uuid4(),
        "session_id": session.id if session else uuid.uuid4(),
        "event_type": EventType.COMBAT,
        "content": "The party defeated the goblin ambush.",
        "importance": 7,
        "timestamp": _now(),
        "created_at": _now(),
    }
    defaults.update(overrides)
    return AdventureMemory(**defaults)


# ── CombatEncounter ───────────────────────────────────────────────────────


def make_combat(session: GameSession | None = None, **overrides) -> CombatEncounter:
    defaults: dict = {
        "id": uuid.uuid4(),
        "session_id": session.id if session else uuid.uuid4(),
        "is_active": True,
        "current_turn": 0,
        "round_number": 1,
        "participants": [
            {
                "name": "Player",
                "initiative": 15,
                "hp_current": 12,
                "hp_max": 12,
                "ac": 16,
                "is_enemy": False,
            }
        ],
        "turn_order": [0],
        "combat_log": [],
        "started_at": _now(),
        "ended_at": None,
    }
    defaults.update(overrides)
    return CombatEncounter(**defaults)


# ── Encounter (general) ──────────────────────────────────────────────────


def make_encounter(**overrides) -> Encounter:
    defaults: dict = {
        "id": uuid.uuid4(),
        "name": "Goblin Ambush",
        "description": "A group of goblins spring from the bushes.",
        "participants": [{"name": "Goblin", "count": 3}],
        "data": {},
        "started_at": _now(),
        "ended_at": None,
    }
    defaults.update(overrides)
    return Encounter(**defaults)


# ── ActiveEffect (table in app/schemas/effects.py, integer PK) ───────────


def make_active_effect(character: Character | None = None, **overrides) -> ActiveEffect:
    defaults: dict = {
        "character_id": character.id if character else uuid.uuid4(),
        "session_id": None,
        "name": "Bless",
        "effect_type": EffectType.BUFF,
        "description": "Blessed by divine power",
        "source": "Bless spell",
        "source_character_id": None,
        "duration_type": EffectDuration.CONCENTRATION,
        "duration_value": 10,
        "rounds_remaining": 10,
        "expires_at": None,
        "bonus_value": 0,
        "dice_bonus": "1d4",
        "advantage": False,
        "disadvantage": False,
        "stacks": False,
        "stack_count": 1,
        "requires_concentration": True,
        "concentration_dc": 10,
        "is_active": True,
        "is_visible": True,
    }
    defaults.update(overrides)
    return ActiveEffect(**defaults)


# ── CharacterSpell ────────────────────────────────────────────────────────


def make_character_spell(
    character: Character | None = None,
    spell: Spell | None = None,
    **overrides,
) -> CharacterSpell:
    defaults: dict = {
        "id": uuid.uuid4(),
        "character_id": character.id if character else uuid.uuid4(),
        "spell_id": spell.id if spell else uuid.uuid4(),
        "is_known": True,
        "is_prepared": False,
        "created_at": _now(),
    }
    defaults.update(overrides)
    return CharacterSpell(**defaults)


# ── CharacterCondition ────────────────────────────────────────────────────


def make_condition(character: Character | None = None, **overrides) -> CharacterCondition:
    defaults: dict = {
        "id": uuid.uuid4(),
        "character_id": character.id if character else uuid.uuid4(),
        "condition": ConditionType.POISONED,
        "duration": 5,
        "source": "Poison trap",
        "applied_at": _now(),
    }
    defaults.update(overrides)
    return CharacterCondition(**defaults)


# ── CharacterQuest ────────────────────────────────────────────────────────


def make_character_quest(
    character: Character | None = None,
    quest: Quest | None = None,
    **overrides,
) -> CharacterQuest:
    defaults: dict = {
        "id": uuid.uuid4(),
        "character_id": character.id if character else uuid.uuid4(),
        "quest_id": quest.id if quest else uuid.uuid4(),
        "accepted_at": _now(),
    }
    defaults.update(overrides)
    return CharacterQuest(**defaults)


# ── CompanionConversation (old-style Column()) ────────────────────────────


def make_companion_conversation(
    companion: Companion | None = None,
    character: Character | None = None,
    **overrides,
) -> CompanionConversation:
    defaults: dict = {
        "id": uuid.uuid4(),
        "companion_id": companion.id if companion else uuid.uuid4(),
        "character_id": character.id if character else uuid.uuid4(),
        "role": "player",
        "message": "Where did you come from?",
        "shared_with_dm": False,
        "created_at": _now(),
    }
    defaults.update(overrides)
    return CompanionConversation(**defaults)


# ── ItemCatalog (old-style Column(), integer PK) ──────────────────────────


def make_item_catalog_entry(**overrides) -> ItemCatalog:
    defaults: dict = {
        "name": f"Test Item {uuid.uuid4().hex[:6]}",
        "description": "A test item",
        "category": "weapon",
        "item_type": "longsword",
        "rarity": "common",
    }
    defaults.update(overrides)
    return ItemCatalog(**defaults)
