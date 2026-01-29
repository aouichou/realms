from fastapi import APIRouter

from app.api.v1.endpoints import (
    adventures,
    auth,
    characters,
    combat,
    companion,
    companions,
    conditions,
    conversations,
    creatures,
    dice,
    effects,
    game,
    images,
    inventory,
    loot,
    memories,
    narrate,
    npcs,
    progression,
    quests,
    random_status,
    rest,
    rules,
    sessions,
    spells,
)

api_router = APIRouter()
api_router.include_router(auth.router, tags=["authentication"])
api_router.include_router(characters.router, tags=["characters"])
api_router.include_router(adventures.router, tags=["adventures"])
api_router.include_router(combat.router, tags=["combat"])
api_router.include_router(companion.router, tags=["companion"])
api_router.include_router(companions.router, prefix="/companions", tags=["companions"])
api_router.include_router(conditions.router, tags=["conditions"])
api_router.include_router(conversations.router, tags=["conversations"])
api_router.include_router(creatures.router, prefix="/creatures", tags=["creatures"])
api_router.include_router(dice.router, tags=["dice"])
api_router.include_router(effects.router, tags=["effects"])
api_router.include_router(game.router, tags=["game"])
api_router.include_router(images.router, tags=["images"])
api_router.include_router(inventory.router, tags=["inventory"])
api_router.include_router(loot.router, tags=["loot"])
api_router.include_router(memories.router, tags=["memories"])
api_router.include_router(narrate.router, tags=["narration"])
api_router.include_router(npcs.router, tags=["npcs"])
api_router.include_router(progression.router, tags=["progression"])
api_router.include_router(quests.router, tags=["quests"])
api_router.include_router(random_status.router, tags=["random_status"])
api_router.include_router(rest.router, tags=["rest"])
api_router.include_router(rules.router, tags=["rules"])
api_router.include_router(sessions.router, tags=["sessions"])
api_router.include_router(spells.router, tags=["spells"])
