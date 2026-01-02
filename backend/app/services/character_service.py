"""Character service for business logic."""
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Character, CharacterType, CharacterClass, Item
from app.schemas.character import CharacterCreate, CharacterUpdate
from app.utils.starting_equipment import get_starting_equipment


class CharacterService:
    """Service for character management operations."""
    
    @staticmethod
    def calculate_hp_max(character_class: str, constitution: int, level: int = 1) -> int:
        """Calculate maximum HP based on class, constitution, and level.
        
        D&D 5e HP calculation:
        - Level 1: Class hit die max + CON modifier
        - CON modifier = (constitution - 10) // 2
        """
        hit_dice = {
            'Fighter': 10,
            'Cleric': 8,
            'Rogue': 8,
            'Wizard': 6
        }
        
        con_modifier = (constitution - 10) // 2
        hit_die = hit_dice.get(character_class, 8)
        
        # Level 1: max hit die + CON modifier
        return hit_die + con_modifier
    
    @staticmethod
    async def create_character(
        db: AsyncSession,
        character_data: CharacterCreate,
        user_id: Optional[UUID] = None
    ) -> Character:
        """Create a new character with starting equipment."""
        # Get ability scores from either format
        ability_scores = character_data.get_ability_scores()
        
        # Calculate initial HP
        hp_max = CharacterService.calculate_hp_max(
            character_data.character_class,
            ability_scores['constitution']
        )
        
        # Calculate carrying capacity (STR × 15 pounds)
        carrying_capacity = ability_scores['strength'] * 15
        
        character = Character(
            id=uuid.uuid4(),
            user_id=user_id,
            name=character_data.name,
            character_type=CharacterType.PLAYER,
            character_class=character_data.character_class,
            race=character_data.race,
            level=character_data.level,
            hp_current=hp_max,
            hp_max=hp_max,
            strength=ability_scores['strength'],
            dexterity=ability_scores['dexterity'],
            constitution=ability_scores['constitution'],
            intelligence=ability_scores['intelligence'],
            wisdom=ability_scores['wisdom'],
            charisma=ability_scores['charisma'],
            background=character_data.background,
            personality=character_data.personality,
            carrying_capacity=carrying_capacity
        )
        
        db.add(character)
        await db.flush()  # Flush to get character ID for items
        
        # Add starting equipment based on class
        class_enum = CharacterClass[character_data.character_class.upper()]
        starting_equipment = get_starting_equipment(class_enum)
        
        for equipment_item in starting_equipment:
            item = Item(
                id=uuid.uuid4(),
                character_id=character.id,
                name=equipment_item.name,
                item_type=equipment_item.item_type,
                weight=equipment_item.weight,
                value=equipment_item.value,
                properties=equipment_item.properties,
                equipped=equipment_item.equipped,
                quantity=equipment_item.quantity
            )
            db.add(item)
        
        await db.commit()
        await db.refresh(character)
        return character
    
    @staticmethod
    async def get_character(db: AsyncSession, character_id: UUID) -> Optional[Character]:
        """Get a character by ID."""
        result = await db.execute(
            select(Character).where(Character.id == character_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_characters(
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Character], int]:
        """Get all characters for a user with pagination."""
        # Get total count
        count_result = await db.execute(
            select(Character).where(Character.user_id == user_id)
        )
        total = len(count_result.all())
        
        # Get paginated results
        result = await db.execute(
            select(Character)
            .where(Character.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        characters = result.scalars().all()
        return list(characters), total
    
    @staticmethod
    async def update_character(
        db: AsyncSession,
        character_id: UUID,
        character_data: CharacterUpdate
    ) -> Optional[Character]:
        """Update a character."""
        character = await CharacterService.get_character(db, character_id)
        if not character:
            return None
        
        update_data = character_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(character, field, value)
        
        await db.commit()
        await db.refresh(character)
        return character
    
    @staticmethod
    async def delete_character(db: AsyncSession, character_id: UUID) -> bool:
        """Delete a character."""
        character = await CharacterService.get_character(db, character_id)
        if not character:
            return False
        
        await db.delete(character)
        await db.commit()
        return True
    
    @staticmethod
    def calculate_ability_modifier(ability_score: int) -> int:
        """Calculate D&D 5e ability modifier: (score - 10) / 2, rounded down"""
        return (ability_score - 10) // 2
    
    @staticmethod
    def calculate_proficiency_bonus(level: int) -> int:
        """Calculate proficiency bonus based on character level.
        
        D&D 5e proficiency bonus:
        - Levels 1-4: +2
        - Levels 5-8: +3
        - Levels 9-12: +4
        - Levels 13-16: +5
        - Levels 17-20: +6
        """
        return 2 + ((level - 1) // 4)
    
    @staticmethod
    async def calculate_character_stats(
        db: AsyncSession,
        character_id: UUID
    ) -> Optional[dict]:
        """Calculate full character stats including equipment bonuses."""
        character = await CharacterService.get_character(db, character_id)
        if not character:
            return None
        
        # Get equipped items
        result = await db.execute(
            select(Item)
            .where(Item.character_id == character_id, Item.equipped == True)
        )
        equipped_items = result.scalars().all()
        
        # Calculate ability modifiers
        str_mod = CharacterService.calculate_ability_modifier(character.strength)
        dex_mod = CharacterService.calculate_ability_modifier(character.dexterity)
        con_mod = CharacterService.calculate_ability_modifier(character.constitution)
        int_mod = CharacterService.calculate_ability_modifier(character.intelligence)
        wis_mod = CharacterService.calculate_ability_modifier(character.wisdom)
        cha_mod = CharacterService.calculate_ability_modifier(character.charisma)
        
        # Proficiency bonus
        prof_bonus = CharacterService.calculate_proficiency_bonus(character.level)
        
        # Calculate AC from equipment
        base_ac = 10 + dex_mod  # Unarmored AC
        ac_bonuses = []
        
        for item in equipped_items:
            if item.item_type.value == 'armor':
                props = item.properties or {}
                
                # Armor provides base AC
                if 'ac_base' in props:
                    if props.get('ac_dex_bonus'):
                        # Light/Medium armor adds DEX
                        dex_to_add = dex_mod
                        if 'ac_dex_max' in props:
                            dex_to_add = min(dex_mod, props['ac_dex_max'])
                        base_ac = props['ac_base'] + dex_to_add
                    else:
                        # Heavy armor doesn't add DEX
                        base_ac = props['ac_base']
                    
                    ac_bonuses.append({
                        'item_name': item.name,
                        'ac_bonus': 0,
                        'attack_bonus': 0,
                        'damage_bonus': '',
                        'other_properties': props
                    })
                
                # Shield adds bonus to AC
                if 'ac_bonus' in props:
                    base_ac += props['ac_bonus']
                    ac_bonuses.append({
                        'item_name': item.name,
                        'ac_bonus': props['ac_bonus'],
                        'attack_bonus': 0,
                        'damage_bonus': '',
                        'other_properties': props
                    })
        
        # Determine spellcasting ability modifier
        spellcasting_mod = 0
        if character.character_class == CharacterClass.WIZARD:
            spellcasting_mod = int_mod
        elif character.character_class in [CharacterClass.CLERIC, CharacterClass.RANGER]:
            spellcasting_mod = wis_mod
        elif character.character_class == CharacterClass.PALADIN:
            spellcasting_mod = cha_mod
        
        # D&D 5e skill list with ability mappings
        skill_abilities = {
            'Athletics': str_mod,
            'Acrobatics': dex_mod,
            'Sleight of Hand': dex_mod,
            'Stealth': dex_mod,
            'Arcana': int_mod,
            'History': int_mod,
            'Investigation': int_mod,
            'Nature': int_mod,
            'Religion': int_mod,
            'Animal Handling': wis_mod,
            'Insight': wis_mod,
            'Medicine': wis_mod,
            'Perception': wis_mod,
            'Survival': wis_mod,
            'Deception': cha_mod,
            'Intimidation': cha_mod,
            'Performance': cha_mod,
            'Persuasion': cha_mod
        }
        
        # For now, assume no skill proficiencies (we'll add this in a future ticket)
        skills = {skill: modifier for skill, modifier in skill_abilities.items()}
        
        # Saving throws (for now, no proficiencies)
        saving_throws = {
            'Strength': str_mod,
            'Dexterity': dex_mod,
            'Constitution': con_mod,
            'Intelligence': int_mod,
            'Wisdom': wis_mod,
            'Charisma': cha_mod
        }
        
        return {
            'strength': character.strength,
            'dexterity': character.dexterity,
            'constitution': character.constitution,
            'intelligence': character.intelligence,
            'wisdom': character.wisdom,
            'charisma': character.charisma,
            'strength_modifier': str_mod,
            'dexterity_modifier': dex_mod,
            'constitution_modifier': con_mod,
            'intelligence_modifier': int_mod,
            'wisdom_modifier': wis_mod,
            'charisma_modifier': cha_mod,
            'proficiency_bonus': prof_bonus,
            'armor_class': base_ac,
            'base_armor_class': 10 + dex_mod,
            'armor_class_bonuses': ac_bonuses,
            'initiative_bonus': dex_mod,
            'melee_attack_bonus': str_mod + prof_bonus,
            'ranged_attack_bonus': dex_mod + prof_bonus,
            'spell_save_dc': 8 + prof_bonus + spellcasting_mod,
            'hp_current': character.hp_current,
            'hp_max': character.hp_max,
            'speed': 30,  # Standard for most races
            'saving_throws': saving_throws,
            'skills': skills,
            'equipped_items': ac_bonuses
        }
