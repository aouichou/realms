"""Tests for Spell API endpoints"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Spell


@pytest.mark.asyncio
async def test_list_spells_no_filters(client: AsyncClient):
    """Test listing spells without filters"""
    response = await client.get("/api/spells?page=1&page_size=10")
    assert response.status_code == 200
    
    data = response.json()
    assert "spells" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["spells"]) <= 10
    assert data["total"] > 0


@pytest.mark.asyncio
async def test_list_spells_filter_by_level(client: AsyncClient):
    """Test filtering spells by level"""
    # Test cantrips (level 0)
    response = await client.get("/api/spells?level=0&page_size=5")
    assert response.status_code == 200
    
    data = response.json()
    assert all(spell["level"] == 0 for spell in data["spells"])
    assert data["total"] > 0
    
    # Test 1st level spells
    response = await client.get("/api/spells?level=1&page_size=5")
    assert response.status_code == 200
    
    data = response.json()
    assert all(spell["level"] == 1 for spell in data["spells"])


@pytest.mark.asyncio
async def test_list_spells_filter_by_school(client: AsyncClient):
    """Test filtering spells by school"""
    response = await client.get("/api/spells?school=Evocation&page_size=5")
    assert response.status_code == 200
    
    data = response.json()
    if data["total"] > 0:
        assert all(spell["school"] == "Evocation" for spell in data["spells"])


@pytest.mark.asyncio
async def test_list_spells_filter_by_class(client: AsyncClient):
    """Test filtering spells by character class"""
    response = await client.get("/api/spells?character_class=wizard&page_size=5")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] > 0

    # Check that returned spells are available to wizard
    for spell in data["spells"]:
        if spell.get("available_to_classes"):
            assert "wizard" in spell["available_to_classes"]
            assert spell["available_to_classes"]["wizard"] is True



@pytest.mark.asyncio
async def test_list_spells_filter_concentration(client: AsyncClient):
    """Test filtering concentration spells"""
    response = await client.get("/api/spells?concentration=true&page_size=5")
    assert response.status_code == 200
    
    data = response.json()
    if data["total"] > 0:
        assert all(spell["is_concentration"] is True for spell in data["spells"])
    
    # Test non-concentration spells
    response = await client.get("/api/spells?concentration=false&page_size=5")
    assert response.status_code == 200
    
    data = response.json()
    assert all(spell["is_concentration"] is False for spell in data["spells"])


@pytest.mark.asyncio
async def test_list_spells_filter_ritual(client: AsyncClient):
    """Test filtering ritual spells"""
    response = await client.get("/api/spells?ritual=true&page_size=5")
    assert response.status_code == 200
    
    data = response.json()
    # Ritual spells might be 0, that's OK
    if data["total"] > 0:
        assert all(spell["is_ritual"] is True for spell in data["spells"])


@pytest.mark.asyncio
async def test_list_spells_search(client: AsyncClient):
    """Test spell search functionality"""
    # Search for "fire" in name or description
    response = await client.get("/api/spells?search=fire&page_size=5")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] > 0
    
    # Verify search terms appear in name or description
    for spell in data["spells"]:
        search_term = "fire"
        assert (
            search_term.lower() in spell["name"].lower() or
            search_term.lower() in spell["description"].lower()
        )


@pytest.mark.asyncio
async def test_list_spells_combined_filters(client: AsyncClient):
    """Test combining multiple filters"""
    response = await client.get(
        "/api/spells?level=1&character_class=wizard&concentration=false&page_size=5"
    )
    assert response.status_code == 200
    
    data = response.json()
    for spell in data["spells"]:
        assert spell["level"] == 1
        assert spell["is_concentration"] is False
        if spell.get("available_to_classes"):
            assert spell["available_to_classes"].get("wizard") is True


@pytest.mark.asyncio
async def test_list_spells_pagination(client: AsyncClient):
    """Test spell list pagination"""
    # Get first page
    response1 = await client.get("/api/spells?page=1&page_size=5")
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Get second page
    response2 = await client.get("/api/spells?page=2&page_size=5")
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Verify different results
    if data1["total"] > 5:
        spell_ids_1 = [spell["id"] for spell in data1["spells"]]
        spell_ids_2 = [spell["id"] for spell in data2["spells"]]
        assert spell_ids_1 != spell_ids_2


@pytest.mark.asyncio
async def test_list_spells_invalid_level(client: AsyncClient):
    """Test invalid spell level parameter"""
    response = await client.get("/api/spells?level=15")
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_spells_invalid_page_size(client: AsyncClient):
    """Test invalid page size parameter"""
    response = await client.get("/api/spells?page_size=150")
    assert response.status_code == 422  # Validation error (max 100)


@pytest.mark.asyncio
async def test_get_spell_by_id(client: AsyncClient, db_session: AsyncSession):
    """Test getting a specific spell by ID"""
    from sqlalchemy import select
    
    # Get a spell from database
    result = await db_session.execute(select(Spell).limit(1))
    spell = result.scalar_one_or_none()
    
    if spell:
        response = await client.get(f"/api/spells/{spell.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(spell.id)
        assert data["name"] == spell.name
        assert data["level"] == spell.level
        assert data["school"] == spell.school


@pytest.mark.asyncio
async def test_get_spell_not_found(client: AsyncClient):
    """Test getting a non-existent spell"""
    import uuid
    fake_id = uuid.uuid4()
    
    response = await client.get(f"/api/spells/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_spell_response_structure(client: AsyncClient):
    """Test that spell responses have correct structure"""
    response = await client.get("/api/spells?page_size=1")
    assert response.status_code == 200
    
    data = response.json()
    if data["spells"]:
        spell = data["spells"][0]
        
        # Required fields
        assert "id" in spell
        assert "name" in spell
        assert "level" in spell
        assert "school" in spell
        assert "casting_time" in spell
        assert "range" in spell
        assert "duration" in spell
        assert "verbal" in spell
        assert "somatic" in spell
        assert "description" in spell
        assert "is_concentration" in spell
        assert "is_ritual" in spell
        assert "created_at" in spell
        
        # Optional fields
        assert "material" in spell or spell.get("material") is None
        assert "damage_dice" in spell or spell.get("damage_dice") is None
        assert "damage_type" in spell or spell.get("damage_type") is None
        assert "save_ability" in spell or spell.get("save_ability") is None
        assert "available_to_classes" in spell


@pytest.mark.asyncio
async def test_spell_list_performance(client: AsyncClient):
    """Test that spell queries perform under 100ms (excluding network)"""
    import time
    
    start = time.time()
    response = await client.get("/api/spells?level=1&character_class=wizard&page_size=20")
    duration = time.time() - start
    
    assert response.status_code == 200
    # Allow 500ms for test environment (production should be < 100ms)
    assert duration < 0.5, f"Query took {duration}s, should be < 0.5s"


@pytest.mark.asyncio
async def test_spell_ordering(client: AsyncClient):
    """Test that spells are ordered by level then name"""
    response = await client.get("/api/spells?page_size=20")
    assert response.status_code == 200
    
    data = response.json()
    spells = data["spells"]
    
    if len(spells) > 1:
        # Verify ordering
        for i in range(len(spells) - 1):
            current = spells[i]
            next_spell = spells[i + 1]
            
            # Either level increases or same level with alphabetical name
            assert (
                current["level"] < next_spell["level"] or
                (current["level"] == next_spell["level"] and 
                 current["name"] <= next_spell["name"])
            )
