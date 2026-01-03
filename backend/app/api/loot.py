"""
Loot generation and crafting API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Optional
import random

from app.db.base import get_db
from app.db.models import Character, Item

router = APIRouter(prefix="/api", tags=["loot"])


class LootRequest(BaseModel):
    cr: int  # Challenge Rating (0-30)
    environment: str  # dungeon, forest, city, underdark, etc.


class CraftingRecipe(BaseModel):
    id: str
    name: str
    description: str
    required_items: Dict[str, int]  # item_name: quantity
    required_skill: str
    dc: int
    result_item: str
    result_quantity: int = 1


class CraftRequest(BaseModel):
    recipe_id: str
    character_id: int


# Loot tables by CR tier
COIN_TABLES = {
    "0-4": {"cp": (2, 20), "sp": (1, 10), "gp": (0, 5)},
    "5-10": {"sp": (4, 40), "gp": (2, 20), "pp": (0, 2)},
    "11-16": {"gp": (10, 100), "pp": (1, 10)},
    "17+": {"gp": (50, 500), "pp": (5, 50)},
}

GEM_TABLE = [
    {"name": "Azurite", "value": 10},
    {"name": "Quartz", "value": 10},
    {"name": "Bloodstone", "value": 50},
    {"name": "Jasper", "value": 50},
    {"name": "Amber", "value": 100},
    {"name": "Pearl", "value": 100},
    {"name": "Garnet", "value": 500},
    {"name": "Topaz", "value": 500},
    {"name": "Emerald", "value": 1000},
    {"name": "Sapphire", "value": 1000},
    {"name": "Diamond", "value": 5000},
    {"name": "Ruby", "value": 5000},
]

ART_OBJECTS = [
    {"name": "Silver Ewer", "value": 25},
    {"name": "Carved Bone Statuette", "value": 25},
    {"name": "Gold Ring with Bloodstones", "value": 250},
    {"name": "Silver Necklace with Gemstone", "value": 250},
    {"name": "Gold Crown", "value": 2500},
    {"name": "Jeweled Platinum Ring", "value": 2500},
]

MAGIC_ITEMS_COMMON = [
    "Potion of Healing",
    "Potion of Climbing",
    "Spell Scroll (Cantrip)",
    "Spell Scroll (1st Level)",
]

MAGIC_ITEMS_UNCOMMON = [
    "Potion of Greater Healing",
    "+1 Weapon",
    "Bag of Holding",
    "Cloak of Protection",
    "Ring of Protection",
    "Wand of Magic Missiles",
]

MAGIC_ITEMS_RARE = [
    "Potion of Superior Healing",
    "+2 Weapon",
    "Ring of Spell Storing",
    "Boots of Speed",
    "Cloak of Displacement",
]

# Crafting recipes
RECIPES = [
    CraftingRecipe(
        id="healing_potion",
        name="Potion of Healing",
        description="Brew a healing potion that restores 2d4+2 hit points",
        required_items={"Healing Herbs": 2, "Empty Vial": 1},
        required_skill="Medicine",
        dc=15,
        result_item="Potion of Healing",
        result_quantity=1,
    ),
    CraftingRecipe(
        id="antitoxin",
        name="Antitoxin",
        description="Create an antitoxin that grants advantage on saving throws against poison",
        required_items={"Rare Herbs": 3, "Empty Vial": 1},
        required_skill="Nature",
        dc=12,
        result_item="Antitoxin",
        result_quantity=1,
    ),
    CraftingRecipe(
        id="arrow_batch",
        name="Arrows (20)",
        description="Craft a batch of 20 arrows",
        required_items={"Wood": 1, "Metal Tip": 1, "Feathers": 1},
        required_skill="Sleight of Hand",
        dc=10,
        result_item="Arrow",
        result_quantity=20,
    ),
    CraftingRecipe(
        id="simple_weapon",
        name="Simple Weapon",
        description="Forge a simple weapon like a dagger or club",
        required_items={"Metal Ingot": 2, "Wood": 1},
        required_skill="Athletics",
        dc=15,
        result_item="Simple Weapon",
        result_quantity=1,
    ),
]


def get_cr_tier(cr: int) -> str:
    """Get the CR tier for loot tables"""
    if cr <= 4:
        return "0-4"
    elif cr <= 10:
        return "5-10"
    elif cr <= 16:
        return "11-16"
    else:
        return "17+"


def roll_dice(dice: str) -> int:
    """Roll dice notation like '2d6' or '1d20+5'"""
    parts = dice.split("+")
    base = parts[0]
    modifier = int(parts[1]) if len(parts) > 1 else 0
    
    count, sides = map(int, base.split("d"))
    return sum(random.randint(1, sides) for _ in range(count)) + modifier


@router.post("/loot/generate")
async def generate_loot(request: LootRequest, db: Session = Depends(get_db)):
    """
    Generate random loot based on CR and environment
    """
    tier = get_cr_tier(request.cr)
    loot = []
    
    # Generate coins
    coin_table = COIN_TABLES[tier]
    for coin_type, (min_val, max_val) in coin_table.items():
        amount = random.randint(min_val, max_val)
        if amount > 0:
            loot.append({
                "name": f"{coin_type.upper()}",
                "type": "currency",
                "quantity": amount,
                "value": amount,
            })
    
    # Chance for gems (increases with CR)
    gem_chance = min(10 + request.cr * 2, 80)  # 10% at CR 0, up to 80% at CR 35+
    if random.randint(1, 100) <= gem_chance:
        num_gems = random.randint(1, max(1, request.cr // 5))
        for _ in range(num_gems):
            # Higher CR = better gems
            max_gem_index = min(len(GEM_TABLE) - 1, request.cr // 3)
            gem = random.choice(GEM_TABLE[:max_gem_index + 1])
            loot.append({
                "name": gem["name"],
                "type": "gem",
                "quantity": 1,
                "value": gem["value"],
            })
    
    # Chance for art objects (rare)
    art_chance = min(5 + request.cr, 50)
    if random.randint(1, 100) <= art_chance:
        max_art_index = min(len(ART_OBJECTS) - 1, request.cr // 5)
        art = random.choice(ART_OBJECTS[:max_art_index + 1])
        loot.append({
            "name": art["name"],
            "type": "art",
            "quantity": 1,
            "value": art["value"],
        })
    
    # Chance for magic items
    if request.cr >= 1:
        magic_chance = min(5 + request.cr * 3, 90)
        if random.randint(1, 100) <= magic_chance:
            # Determine rarity based on CR
            rarity_roll = random.randint(1, 100)
            if request.cr <= 4:
                magic_item = random.choice(MAGIC_ITEMS_COMMON)
                rarity = "common"
            elif request.cr <= 10:
                if rarity_roll <= 70:
                    magic_item = random.choice(MAGIC_ITEMS_COMMON)
                    rarity = "common"
                else:
                    magic_item = random.choice(MAGIC_ITEMS_UNCOMMON)
                    rarity = "uncommon"
            elif request.cr <= 16:
                if rarity_roll <= 40:
                    magic_item = random.choice(MAGIC_ITEMS_UNCOMMON)
                    rarity = "uncommon"
                else:
                    magic_item = random.choice(MAGIC_ITEMS_RARE)
                    rarity = "rare"
            else:
                magic_item = random.choice(MAGIC_ITEMS_RARE)
                rarity = "rare"
            
            loot.append({
                "name": magic_item,
                "type": "magic_item",
                "quantity": 1,
                "rarity": rarity,
                "value": 0,  # Priceless!
            })
    
    # Environment-specific loot
    if request.environment == "forest":
        if random.randint(1, 100) <= 30:
            loot.append({
                "name": "Healing Herbs",
                "type": "consumable",
                "quantity": random.randint(1, 3),
                "value": 5,
            })
    elif request.environment == "dungeon":
        if random.randint(1, 100) <= 20:
            loot.append({
                "name": "Ancient Key",
                "type": "quest",
                "quantity": 1,
                "value": 0,
            })
    elif request.environment == "underdark":
        if random.randint(1, 100) <= 25:
            loot.append({
                "name": "Rare Mushroom",
                "type": "consumable",
                "quantity": random.randint(1, 2),
                "value": 10,
            })
    
    return {"loot": loot, "total_value": sum(item.get("value", 0) * item["quantity"] for item in loot)}


@router.get("/crafting/recipes")
async def get_recipes(skill: Optional[str] = None):
    """
    Get all crafting recipes, optionally filtered by required skill
    """
    recipes = RECIPES
    if skill:
        recipes = [r for r in recipes if r.required_skill.lower() == skill.lower()]
    
    return {"recipes": [r.dict() for r in recipes]}


@router.post("/crafting/craft")
async def craft_item(request: CraftRequest, db: Session = Depends(get_db)):
    """
    Attempt to craft an item using a recipe
    """
    # Get character
    character = db.query(Character).filter(Character.id == request.character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Find recipe
    recipe = next((r for r in RECIPES if r.id == request.recipe_id), None)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Get character's inventory
    inventory_items = db.query(Item).filter(Item.character_id == request.character_id).all()
    inventory_dict = {item.name: item for item in inventory_items}
    
    # Check if character has required materials
    missing_items = []
    for item_name, quantity in recipe.required_items.items():
        if item_name not in inventory_dict or inventory_dict[item_name].quantity < quantity:
            missing_items.append(f"{item_name} (need {quantity})")
    
    if missing_items:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required materials: {', '.join(missing_items)}"
        )
    
    # Perform skill check
    skill_name = recipe.required_skill
    
    # Get ability modifier for the skill
    skill_ability_map = {
        "Athletics": "strength",
        "Acrobatics": "dexterity",
        "Sleight of Hand": "dexterity",
        "Stealth": "dexterity",
        "Arcana": "intelligence",
        "History": "intelligence",
        "Investigation": "intelligence",
        "Nature": "intelligence",
        "Religion": "intelligence",
        "Animal Handling": "wisdom",
        "Insight": "wisdom",
        "Medicine": "wisdom",
        "Perception": "wisdom",
        "Survival": "wisdom",
        "Deception": "charisma",
        "Intimidation": "charisma",
        "Performance": "charisma",
        "Persuasion": "charisma",
    }
    
    ability = skill_ability_map.get(skill_name, "intelligence")
    ability_score = getattr(character, ability)
    ability_modifier = (ability_score - 10) // 2
    
    # Calculate proficiency bonus
    proficiency_bonus = 2 + ((character.level - 1) // 4)
    
    # Roll d20 + ability modifier + proficiency (assuming proficiency for crafting)
    roll = random.randint(1, 20)
    total = roll + ability_modifier + proficiency_bonus
    
    success = total >= recipe.dc
    
    if success:
        # Consume materials
        for item_name, quantity in recipe.required_items.items():
            item = inventory_dict[item_name]
            item.quantity -= quantity
            if item.quantity <= 0:
                db.delete(item)
        
        # Create result item
        result_item = Item(
            character_id=request.character_id,
            name=recipe.result_item,
            item_type="consumable" if "Potion" in recipe.result_item else "weapon",
            quantity=recipe.result_quantity,
            weight=0.5 if "Potion" in recipe.result_item else 1.0,
            value=0,
            is_equipped=False,
        )
        db.add(result_item)
        db.commit()
        
        return {
            "success": True,
            "roll": roll,
            "total": total,
            "dc": recipe.dc,
            "item_crafted": recipe.result_item,
            "quantity": recipe.result_quantity,
        }
    else:
        # Failed craft, materials lost anyway (50% returned)
        for item_name, quantity in recipe.required_items.items():
            item = inventory_dict[item_name]
            materials_lost = quantity // 2
            item.quantity -= materials_lost
            if item.quantity <= 0:
                db.delete(item)
        
        db.commit()
        
        return {
            "success": False,
            "roll": roll,
            "total": total,
            "dc": recipe.dc,
            "message": "Crafting failed. Some materials were lost.",
        }
