"""
Database Integration Tests
Tests database operations, transactions, and relationships
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.character import Character, CharacterSpell, InventoryItem
from app.models.game import NPC, Combat, GameSession, Quest, QuestObjective


class TestCharacterModel:
    """Test Character model database operations"""

    @pytest.mark.asyncio
    async def test_create_character(self, db_session: AsyncSession):
        """Test creating a character in database"""
        character = Character(
            name="Test Hero",
            char_class="Fighter",
            strength=16,
            dexterity=14,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=8,
        )

        db_session.add(character)
        await db_session.commit()
        await db_session.refresh(character)

        assert character.id is not None
        assert character.name == "Test Hero"
        assert character.level == 1  # Default
        assert character.hp_max > 0  # Should be calculated

    @pytest.mark.asyncio
    async def test_character_cascade_delete(
        self, db_session: AsyncSession, sample_character: Character
    ):
        """Test that deleting character cascades to related items"""
        # Add inventory item
        item = InventoryItem(
            character_id=sample_character.id, name="Sword", type="weapon", quantity=1
        )
        db_session.add(item)
        await db_session.commit()

        # Delete character
        await db_session.delete(sample_character)
        await db_session.commit()

        # Verify item is also deleted (cascade)
        result = await db_session.execute(
            select(InventoryItem).where(InventoryItem.character_id == sample_character.id)
        )
        items = result.scalars().all()
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_character_with_inventory_relationship(
        self, db_session: AsyncSession, sample_character: Character
    ):
        """Test eager loading character with inventory"""
        # Add items
        for i in range(3):
            item = InventoryItem(
                character_id=sample_character.id, name=f"Item {i}", type="misc", quantity=1
            )
            db_session.add(item)
        await db_session.commit()

        # Eager load with relationship
        result = await db_session.execute(
            select(Character)
            .options(selectinload(Character.inventory))
            .where(Character.id == sample_character.id)
        )
        character = result.scalar_one()

        assert len(character.inventory) == 3
        assert all(item.character_id == character.id for item in character.inventory)


class TestGameSessionModel:
    """Test GameSession model database operations"""

    @pytest.mark.asyncio
    async def test_create_game_session(self, db_session: AsyncSession, sample_character: Character):
        """Test creating a game session"""
        game = GameSession(
            character_id=sample_character.id,
            status="active",
            context={"location": "Village", "time": "morning"},
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        assert game.id is not None
        assert game.character_id == sample_character.id
        assert game.context["location"] == "Village"

    @pytest.mark.asyncio
    async def test_game_session_with_npcs(
        self, db_session: AsyncSession, sample_game_session: GameSession
    ):
        """Test game session with multiple NPCs"""
        npcs = [
            NPC(
                game_session_id=sample_game_session.id,
                name=f"NPC {i}",
                type="enemy" if i % 2 == 0 else "ally",
                hp_current=10,
                hp_max=10,
                armor_class=12,
            )
            for i in range(5)
        ]

        for npc in npcs:
            db_session.add(npc)
        await db_session.commit()

        # Query with relationship
        result = await db_session.execute(
            select(GameSession)
            .options(selectinload(GameSession.npcs))
            .where(GameSession.id == sample_game_session.id)
        )
        game = result.scalar_one()

        assert len(game.npcs) == 5
        enemies = [npc for npc in game.npcs if npc.type == "enemy"]
        assert len(enemies) == 3


class TestCombatModel:
    """Test Combat model database operations"""

    @pytest.mark.asyncio
    async def test_create_combat(self, db_session: AsyncSession, sample_game_session: GameSession):
        """Test creating a combat encounter"""
        combat = Combat(
            game_session_id=sample_game_session.id,
            status="active",
            round_number=1,
            turn_order=[
                {"entity_id": "char-1", "initiative": 18},
                {"entity_id": "npc-1", "initiative": 12},
            ],
            current_turn_index=0,
        )

        db_session.add(combat)
        await db_session.commit()
        await db_session.refresh(combat)

        assert combat.id is not None
        assert len(combat.turn_order) == 2
        assert combat.turn_order[0]["initiative"] == 18

    @pytest.mark.asyncio
    async def test_combat_round_progression(self, db_session: AsyncSession, sample_combat: Combat):
        """Test advancing combat rounds"""
        initial_round = sample_combat.round_number

        # Advance round
        sample_combat.round_number += 1
        sample_combat.current_turn_index = 0
        await db_session.commit()
        await db_session.refresh(sample_combat)

        assert sample_combat.round_number == initial_round + 1
        assert sample_combat.current_turn_index == 0


class TestInventoryModel:
    """Test InventoryItem model database operations"""

    @pytest.mark.asyncio
    async def test_add_inventory_item(self, db_session: AsyncSession, sample_character: Character):
        """Test adding item to inventory"""
        item = InventoryItem(
            character_id=sample_character.id,
            name="Healing Potion",
            type="consumable",
            quantity=3,
            properties={"healing": "2d4+2"},
        )

        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        assert item.id is not None
        assert item.quantity == 3
        assert item.properties["healing"] == "2d4+2"

    @pytest.mark.asyncio
    async def test_update_item_quantity(
        self, db_session: AsyncSession, sample_character: Character
    ):
        """Test updating item quantity (e.g., using a potion)"""
        item = InventoryItem(
            character_id=sample_character.id, name="Potion", type="consumable", quantity=5
        )
        db_session.add(item)
        await db_session.commit()

        # Use one potion
        item.quantity -= 1
        await db_session.commit()
        await db_session.refresh(item)

        assert item.quantity == 4


class TestSpellModel:
    """Test CharacterSpell model database operations"""

    @pytest.mark.asyncio
    async def test_add_spell(self, db_session: AsyncSession, sample_character: Character):
        """Test adding spell to character"""
        spell = CharacterSpell(
            character_id=sample_character.id,
            name="Fireball",
            level=3,
            school="Evocation",
            casting_time="1 action",
            range="150 feet",
            components="V, S, M",
            duration="Instantaneous",
            description="A bright streak flashes from your pointing finger",
        )

        db_session.add(spell)
        await db_session.commit()
        await db_session.refresh(spell)

        assert spell.id is not None
        assert spell.level == 3
        assert spell.school == "Evocation"

    @pytest.mark.asyncio
    async def test_spell_slots(self, db_session: AsyncSession, sample_character: Character):
        """Test spell slot tracking"""
        spell = CharacterSpell(
            character_id=sample_character.id,
            name="Magic Missile",
            level=1,
            slots_total=4,
            slots_used=0,
        )
        db_session.add(spell)
        await db_session.commit()

        # Cast spell
        spell.slots_used += 1
        await db_session.commit()
        await db_session.refresh(spell)

        assert spell.slots_used == 1
        assert spell.slots_total - spell.slots_used == 3  # Remaining slots


class TestQuestModel:
    """Test Quest model database operations"""

    @pytest.mark.asyncio
    async def test_create_quest_with_objectives(
        self, db_session: AsyncSession, sample_game_session: GameSession
    ):
        """Test creating quest with objectives"""
        quest = Quest(
            game_session_id=sample_game_session.id,
            title="Find the Artifact",
            description="Locate and retrieve the ancient artifact",
            status="active",
        )
        db_session.add(quest)
        await db_session.flush()  # Get quest ID

        # Add objectives
        objectives = [
            QuestObjective(
                quest_id=quest.id, description="Search the ruins", completed=False, order=1
            ),
            QuestObjective(
                quest_id=quest.id, description="Defeat the guardian", completed=False, order=2
            ),
            QuestObjective(
                quest_id=quest.id, description="Retrieve the artifact", completed=False, order=3
            ),
        ]

        for obj in objectives:
            db_session.add(obj)
        await db_session.commit()

        # Eager load with objectives
        result = await db_session.execute(
            select(Quest).options(selectinload(Quest.objectives)).where(Quest.id == quest.id)
        )
        loaded_quest = result.scalar_one()

        assert len(loaded_quest.objectives) == 3
        assert loaded_quest.objectives[0].order == 1

    @pytest.mark.asyncio
    async def test_complete_quest_objective(
        self, db_session: AsyncSession, sample_game_session: GameSession
    ):
        """Test completing quest objectives"""
        quest = Quest(game_session_id=sample_game_session.id, title="Test Quest", status="active")
        db_session.add(quest)
        await db_session.flush()

        objective = QuestObjective(quest_id=quest.id, description="Test objective", completed=False)
        db_session.add(objective)
        await db_session.commit()

        # Complete objective
        objective.completed = True
        await db_session.commit()
        await db_session.refresh(objective)

        assert objective.completed is True


class TestTransactions:
    """Test database transaction handling"""

    @pytest.mark.asyncio
    async def test_rollback_on_error(self, db_session: AsyncSession):
        """Test that failed transactions rollback properly"""
        character = Character(
            name="Test",
            char_class="Fighter",
            strength=16,
            dexterity=14,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=8,
        )
        db_session.add(character)
        await db_session.commit()

        initial_hp = character.hp_current

        try:
            # Start a transaction
            character.hp_current = -999  # Invalid value
            await db_session.commit()

            # This should fail, but if it doesn't, force an error
            raise ValueError("Invalid HP value")
        except Exception:
            await db_session.rollback()

        # Verify rollback worked
        await db_session.refresh(character)
        assert character.hp_current == initial_hp

    @pytest.mark.asyncio
    async def test_concurrent_updates(self, db_session: AsyncSession, sample_character: Character):
        """Test handling concurrent updates to same entity"""
        # Simulate two sessions updating the same character
        original_hp = sample_character.hp_current

        # Update 1: Damage
        sample_character.hp_current -= 10
        await db_session.commit()

        # Update 2: More damage
        sample_character.hp_current -= 5
        await db_session.commit()

        await db_session.refresh(sample_character)
        assert sample_character.hp_current == original_hp - 15


class TestQueryPerformance:
    """Test query optimization and performance"""

    @pytest.mark.asyncio
    async def test_eager_loading_vs_lazy_loading(
        self, db_session: AsyncSession, sample_character: Character
    ):
        """Test that eager loading reduces queries"""
        # Add multiple items
        for i in range(10):
            item = InventoryItem(
                character_id=sample_character.id, name=f"Item {i}", type="misc", quantity=1
            )
            db_session.add(item)
        await db_session.commit()

        # Eager load
        result = await db_session.execute(
            select(Character)
            .options(selectinload(Character.inventory))
            .where(Character.id == sample_character.id)
        )
        character = result.scalar_one()

        # Access inventory (should not trigger additional queries)
        items = character.inventory
        assert len(items) == 10

    @pytest.mark.asyncio
    async def test_pagination(self, db_session: AsyncSession):
        """Test paginated queries"""
        # Create 50 characters
        for i in range(50):
            char = Character(
                name=f"Character {i}",
                char_class="Fighter",
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
            )
            db_session.add(char)
        await db_session.commit()

        # Paginate: page 2, 10 per page
        result = await db_session.execute(
            select(Character).order_by(Character.created_at).limit(10).offset(10)
        )
        characters = result.scalars().all()

        assert len(characters) == 10
        assert characters[0].name == "Character 10"
