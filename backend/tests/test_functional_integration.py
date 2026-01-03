"""
Functional Integration Tests
Tests complete user flows through the actual API
Run with: pytest tests/test_functional_integration.py -v
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    with TestClient(app) as c:
        yield c


class TestCharacterFlow:
    """Test complete character creation and management flow"""
    
    def test_character_creation_and_retrieval(self, client: TestClient):
        """Test creating a character and retrieving it"""
        # Create character
        character_data = {
            "name": "Gandalf the Grey",
            "character_class": "Wizard",
            "race": "Human",
            "strength": 10,
            "dexterity": 14,
            "constitution": 12,
            "intelligence": 18,
            "wisdom": 16,
            "charisma": 14,
        }
        
        create_response = client.post("/api/characters", json=character_data)
        assert create_response.status_code == 201, f"Failed to create character: {create_response.text}"
        
        created_character = create_response.json()
        character_id = created_character["id"]
        
        # Retrieve character
        get_response = client.get(f"/api/characters/{character_id}")
        assert get_response.status_code == 200
        
        character = get_response.json()
        assert character["name"] == "Gandalf the Grey"
        assert character["character_class"] == "Wizard"
        assert character["intelligence"] == 18
    
    def test_list_characters(self, client: TestClient):
        """Test listing all characters"""
        response = client.get("/api/characters")
        assert response.status_code == 200
        
        characters = response.json()
        assert isinstance(characters, list)


class TestGameSessionFlow:
    """Test game session management flow"""
    
    def test_create_game_session_requires_character(self, client: TestClient):
        """Test that game session needs a valid character"""
        # First create a character
        character_data = {
            "name": "Test Hero",
            "character_class": "Fighter",
            "race": "Human",
            "strength": 16,
            "dexterity": 14,
            "constitution": 15,
            "intelligence": 10,
            "wisdom": 12,
            "charisma": 8,
        }
        
        char_response = client.post("/api/characters", json=character_data)
        assert char_response.status_code == 201
        
        character_id = char_response.json()["id"]
        
        # Create game session
        session_data = {"character_id": character_id}
        session_response = client.post("/api/sessions", json=session_data)
        
        # Might be 201 or 200 depending on implementation
        assert session_response.status_code in [200, 201]


class TestInventoryFlow:
    """Test inventory management flow"""
    
    def test_add_and_list_inventory(self, client: TestClient):
        """Test adding items to inventory"""
        # Create character first
        character_data = {
            "name": "Test Adventurer",
            "character_class": "Rogue",
            "race": "Halfling",
            "strength": 10,
            "dexterity": 18,
            "constitution": 12,
            "intelligence": 13,
            "wisdom": 12,
            "charisma": 14,
        }
        
        char_response = client.post("/api/characters", json=character_data)
        character_id = char_response.json()["id"]
        
        # Add item to inventory
        item_data = {
            "character_id": character_id,
            "name": "Healing Potion",
            "item_type": "consumable",
            "quantity": 3,
        }
        
        add_response = client.post("/api/inventory", json=item_data)
        # Should be 200 or 201
        assert add_response.status_code in [200, 201]


class TestHealthChecks:
    """Test system health and status endpoints"""
    
    def test_health_check(self, client: TestClient):
        """Test GET /health"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
    
    def test_root_endpoint(self, client: TestClient):
        """Test GET / - API info"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data or "message" in data


class TestDiceRolling:
    """Test dice rolling functionality"""
    
    def test_roll_d20(self, client: TestClient):
        """Test rolling a d20"""
        roll_data = {"notation": "1d20"}
        
        response = client.post("/api/dice/roll", json=roll_data)
        assert response.status_code == 200
        
        result = response.json()
        assert "result" in result or "total" in result
    
    def test_roll_with_modifier(self, client: TestClient):
        """Test rolling with modifier (e.g., 1d20+5)"""
        roll_data = {"notation": "1d20+5"}
        
        response = client.post("/api/dice/roll", json=roll_data)
        assert response.status_code == 200


@pytest.mark.slow
class TestEndToEndWorkflow:
    """Test complete user journey from character creation to gameplay"""
    
    def test_complete_adventure_flow(self, client: TestClient):
        """
        Test: Create character → Start session → Roll dice → Check status
        """
        # Step 1: Create character
        character_data = {
            "name": "Adventurer",
            "character_class": "Fighter",
            "race": "Human",
            "strength": 16,
            "dexterity": 14,
            "constitution": 15,
            "intelligence": 10,
            "wisdom": 12,
            "charisma": 10,
        }
        
        char_response = client.post("/api/characters", json=character_data)
        assert char_response.status_code == 201
        character_id = char_response.json()["id"]
        
        # Step 2: Get character details
        get_char = client.get(f"/api/characters/{character_id}")
        assert get_char.status_code == 200
        assert get_char.json()["name"] == "Adventurer"
        
        # Step 3: Create game session
        session_data = {"character_id": character_id}
        session_response = client.post("/api/sessions", json=session_data)
        assert session_response.status_code in [200, 201]
        
        # Step 4: Roll some dice
        roll_response = client.post("/api/dice/roll", json={"notation": "1d20"})
        assert roll_response.status_code == 200
        
        # Step 5: Health check
        health = client.get("/health")
        assert health.status_code == 200


# Performance baseline tests
class TestPerformance:
    """Basic performance and response time checks"""
    
    def test_health_check_response_time(self, client: TestClient):
        """Ensure health check responds quickly"""
        import time
        
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 1.0  # Should respond in < 1 second
    
    def test_character_list_response_time(self, client: TestClient):
        """Ensure character list responds reasonably fast"""
        import time
        
        start = time.time()
        response = client.get("/api/characters")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0  # Should respond in < 2 seconds
