"""
API Integration Tests
Tests the full request-response cycle for all major endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.models.game import GameSession, NPC


class TestCharacterEndpoints:
    """Integration tests for character CRUD endpoints"""
    
    def test_create_character(self, client: TestClient, character_factory):
        """Test POST /characters - Create new character"""
        character_data = character_factory.create_data(
            name="Gandalf",
            char_class="Wizard",
            intelligence=18
        )
        
        response = client.post("/characters", json=character_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Gandalf"
        assert data["char_class"] == "Wizard"
        assert data["intelligence"] == 18
        assert data["level"] == 1
        assert "id" in data
    
    def test_list_characters(self, client: TestClient, sample_character: Character):
        """Test GET /characters - List all characters"""
        response = client.get("/characters")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == sample_character.name
    
    def test_get_character(self, client: TestClient, sample_character: Character):
        """Test GET /characters/{id} - Get single character"""
        response = client.get(f"/characters/{sample_character.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_character.id)
        assert data["name"] == sample_character.name
        assert data["char_class"] == sample_character.char_class
    
    def test_get_nonexistent_character(self, client: TestClient):
        """Test GET /characters/{id} - 404 for nonexistent character"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/characters/{fake_uuid}")
        
        assert response.status_code == 404
    
    def test_update_character(self, client: TestClient, sample_character: Character):
        """Test PATCH /characters/{id} - Update character"""
        update_data = {"hp_current": 25, "xp": 1500}
        
        response = client.patch(
            f"/characters/{sample_character.id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["hp_current"] == 25
        assert data["xp"] == 1500
        assert data["name"] == sample_character.name  # Unchanged
    
    def test_delete_character(self, client: TestClient, sample_character: Character):
        """Test DELETE /characters/{id} - Soft delete character"""
        response = client.delete(f"/characters/{sample_character.id}")
        
        assert response.status_code == 204
        
        # Verify character is marked inactive
        get_response = client.get(f"/characters/{sample_character.id}")
        assert get_response.status_code == 404 or get_response.json()["active"] == False


class TestGameSessionEndpoints:
    """Integration tests for game session endpoints"""
    
    def test_create_game_session(self, client: TestClient, sample_character: Character):
        """Test POST /game - Create new game session"""
        game_data = {
            "character_id": str(sample_character.id),
            "starting_location": "Forest Path"
        }
        
        response = client.post("/game", json=game_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["character_id"] == str(sample_character.id)
        assert data["status"] == "active"
        assert "id" in data
    
    def test_get_game_session(self, client: TestClient, sample_game_session: GameSession):
        """Test GET /game/{id} - Get game session details"""
        response = client.get(f"/game/{sample_game_session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_game_session.id)
        assert data["status"] == "active"
    
    def test_end_game_session(self, client: TestClient, sample_game_session: GameSession):
        """Test POST /game/{id}/end - End game session"""
        response = client.post(f"/game/{sample_game_session.id}/end")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"


class TestCombatEndpoints:
    """Integration tests for combat system endpoints"""
    
    def test_start_combat(
        self,
        client: TestClient,
        sample_game_session: GameSession,
        sample_character: Character,
        sample_npc: NPC
    ):
        """Test POST /combat/start - Initiate combat"""
        combat_data = {
            "game_session_id": str(sample_game_session.id),
            "participants": [
                {"entity_id": str(sample_character.id), "entity_type": "character"},
                {"entity_id": str(sample_npc.id), "entity_type": "npc"}
            ]
        }
        
        response = client.post("/combat/start", json=combat_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "active"
        assert data["round_number"] == 1
        assert len(data["turn_order"]) == 2
    
    def test_attack_action(
        self,
        client: TestClient,
        sample_combat,
        sample_character: Character,
        sample_npc: NPC,
        combat_action_factory
    ):
        """Test POST /combat/attack - Perform attack"""
        attack_data = combat_action_factory.create_attack_data(
            attacker_id=str(sample_character.id),
            target_id=str(sample_npc.id)
        )
        
        response = client.post(f"/combat/{sample_combat.id}/attack", json=attack_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "hit" in data
        assert "damage" in data
        assert "description" in data
    
    def test_end_combat(self, client: TestClient, sample_combat):
        """Test POST /combat/{id}/end - End combat"""
        response = client.post(f"/combat/{sample_combat.id}/end")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"


class TestInventoryEndpoints:
    """Integration tests for inventory management"""
    
    def test_add_item(self, client: TestClient, sample_character: Character):
        """Test POST /inventory - Add item to inventory"""
        item_data = {
            "character_id": str(sample_character.id),
            "name": "Healing Potion",
            "type": "consumable",
            "quantity": 3,
            "properties": {"healing": "2d4+2"}
        }
        
        response = client.post("/inventory", json=item_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Healing Potion"
        assert data["quantity"] == 3
    
    def test_list_inventory(self, client: TestClient, sample_character: Character):
        """Test GET /inventory/{character_id} - List character inventory"""
        # First add an item
        item_data = {
            "character_id": str(sample_character.id),
            "name": "Sword",
            "type": "weapon",
            "quantity": 1
        }
        client.post("/inventory", json=item_data)
        
        # Then list inventory
        response = client.get(f"/inventory/{sample_character.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(item["name"] == "Sword" for item in data)


class TestSpellEndpoints:
    """Integration tests for spell management"""
    
    def test_add_spell(self, client: TestClient, sample_character: Character):
        """Test POST /spells - Add spell to character"""
        spell_data = {
            "character_id": str(sample_character.id),
            "name": "Fireball",
            "level": 3,
            "school": "Evocation",
            "casting_time": "1 action",
            "range": "150 feet",
            "components": "V, S, M",
            "duration": "Instantaneous",
            "description": "A bright streak flashes...",
            "damage": "8d6"
        }
        
        response = client.post("/spells", json=spell_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Fireball"
        assert data["level"] == 3
    
    def test_list_spells(self, client: TestClient, sample_character: Character):
        """Test GET /spells/{character_id} - List character spells"""
        # Add a spell first
        spell_data = {
            "character_id": str(sample_character.id),
            "name": "Magic Missile",
            "level": 1
        }
        client.post("/spells", json=spell_data)
        
        # List spells
        response = client.get(f"/spells/{sample_character.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestQuestEndpoints:
    """Integration tests for quest tracking"""
    
    def test_create_quest(self, client: TestClient, sample_game_session: GameSession):
        """Test POST /quests - Create new quest"""
        quest_data = {
            "game_session_id": str(sample_game_session.id),
            "title": "Rescue the Princess",
            "description": "Save Princess Leia from the dragon",
            "objectives": [
                {"description": "Find dragon's lair", "completed": False},
                {"description": "Defeat dragon", "completed": False}
            ]
        }
        
        response = client.post("/quests", json=quest_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Rescue the Princess"
        assert data["status"] == "active"
        assert len(data["objectives"]) == 2
    
    def test_list_quests(self, client: TestClient, sample_game_session: GameSession):
        """Test GET /quests/{game_session_id} - List active quests"""
        # Create a quest first
        quest_data = {
            "game_session_id": str(sample_game_session.id),
            "title": "Find the Artifact",
            "description": "Locate the ancient artifact"
        }
        client.post("/quests", json=quest_data)
        
        # List quests
        response = client.get(f"/quests/{sample_game_session.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Find the Artifact"


class TestProgressionEndpoints:
    """Integration tests for character progression"""
    
    def test_award_xp(self, client: TestClient, sample_character: Character):
        """Test POST /progression/xp - Award experience points"""
        xp_data = {
            "character_id": str(sample_character.id),
            "xp_amount": 500,
            "reason": "Defeated goblin"
        }
        
        response = client.post("/progression/xp", json=xp_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["xp"] >= sample_character.xp + 500
        assert "level_up" in data
    
    def test_level_up(self, client: TestClient, sample_character: Character):
        """Test POST /progression/levelup - Level up character"""
        # Award enough XP for level up
        xp_data = {
            "character_id": str(sample_character.id),
            "xp_amount": 10000
        }
        client.post("/progression/xp", json=xp_data)
        
        # Trigger level up
        response = client.post(f"/progression/levelup/{sample_character.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["level"] > sample_character.level


class TestHealthCheckEndpoints:
    """Integration tests for system health checks"""
    
    def test_health_check(self, client: TestClient):
        """Test GET /health - System health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
    
    def test_api_info(self, client: TestClient):
        """Test GET / - API information"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


# End-to-end workflow tests
class TestEndToEndWorkflows:
    """Integration tests for complete user workflows"""
    
    @pytest.mark.slow
    def test_complete_character_journey(self, client: TestClient, character_factory):
        """Test: Create character → Start game → Combat → Level up"""
        # 1. Create character
        char_data = character_factory.create_data(name="Hero")
        char_response = client.post("/characters", json=char_data)
        assert char_response.status_code == 201
        character_id = char_response.json()["id"]
        
        # 2. Start game session
        game_data = {"character_id": character_id}
        game_response = client.post("/game", json=game_data)
        assert game_response.status_code == 201
        game_id = game_response.json()["id"]
        
        # 3. Award XP
        xp_data = {"character_id": character_id, "xp_amount": 1000}
        xp_response = client.post("/progression/xp", json=xp_data)
        assert xp_response.status_code == 200
        
        # 4. Verify character progression
        char_check = client.get(f"/characters/{character_id}")
        assert char_check.json()["xp"] >= 1000
    
    @pytest.mark.slow
    def test_complete_combat_scenario(
        self,
        client: TestClient,
        sample_game_session: GameSession,
        sample_character: Character
    ):
        """Test: Start combat → Attack → End combat"""
        # 1. Create NPC
        npc_data = {
            "game_session_id": str(sample_game_session.id),
            "name": "Orc",
            "type": "enemy",
            "hp_max": 15,
            "armor_class": 13
        }
        npc_response = client.post("/npcs", json=npc_data)
        npc_id = npc_response.json()["id"]
        
        # 2. Start combat
        combat_data = {
            "game_session_id": str(sample_game_session.id),
            "participants": [
                {"entity_id": str(sample_character.id), "entity_type": "character"},
                {"entity_id": npc_id, "entity_type": "npc"}
            ]
        }
        combat_response = client.post("/combat/start", json=combat_data)
        assert combat_response.status_code == 201
        combat_id = combat_response.json()["id"]
        
        # 3. Perform attack
        attack_data = {
            "action_type": "attack",
            "attacker_id": str(sample_character.id),
            "target_id": npc_id
        }
        attack_response = client.post(f"/combat/{combat_id}/attack", json=attack_data)
        assert attack_response.status_code == 200
        
        # 4. End combat
        end_response = client.post(f"/combat/{combat_id}/end")
        assert end_response.status_code == 200
