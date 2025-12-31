"""Character service for business logic."""
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Character, CharacterType
from app.schemas.character import CharacterCreate, CharacterUpdate


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
        """Create a new character."""
        # Calculate initial HP
        hp_max = CharacterService.calculate_hp_max(
            character_data.character_class,
            character_data.constitution
        )
        
        character = Character(
            id=uuid.uuid4(),
            user_id=user_id,
            name=character_data.name,
            character_type=CharacterType.PLAYER,
            character_class=character_data.character_class,
            race=character_data.race,
            level=1,
            hp_current=hp_max,
            hp_max=hp_max,
            strength=character_data.strength,
            dexterity=character_data.dexterity,
            constitution=character_data.constitution,
            intelligence=character_data.intelligence,
            wisdom=character_data.wisdom,
            charisma=character_data.charisma,
            background=character_data.background,
            personality=character_data.personality
        )
        
        db.add(character)
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
