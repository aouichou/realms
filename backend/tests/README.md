# Integration Testing Suite

## Overview
Comprehensive integration tests for Mistral Realms backend API.

## Test Coverage

### API Integration Tests (`test_api_integration.py`)
- ✅ Character CRUD operations (create, read, update, delete)
- ✅ Game session management
- ✅ Combat system endpoints
- ✅ Inventory management
- ✅ Spell management
- ✅ Quest tracking
- ✅ Character progression (XP, leveling)
- ✅ Health check endpoints
- ✅ End-to-end workflows

### Database Integration Tests (`test_database_integration.py`)
- ✅ Character model operations
- ✅ Cascade deletes and relationships
- ✅ Game session with NPCs
- ✅ Combat round progression
- ✅ Inventory item management
- ✅ Spell slot tracking
- ✅ Quest objectives
- ✅ Transaction rollback
- ✅ Query optimization (eager loading, pagination)

### External Service Tests (`test_integration.py`)
- ✅ Mistral API real calls (requires `--integration` flag)
- ✅ Mistral streaming responses

## Running Tests

### Run all unit tests (fast)
```bash
cd backend
pytest
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html
# View report at htmlcov/index.html
```

### Run integration tests (requires API keys)
```bash
pytest --integration
```

### Run specific test file
```bash
pytest tests/test_api_integration.py -v
```

### Run specific test class
```bash
pytest tests/test_api_integration.py::TestCharacterEndpoints -v
```

### Run specific test
```bash
pytest tests/test_api_integration.py::TestCharacterEndpoints::test_create_character -v
```

### Run slow tests only
```bash
pytest -m slow
```

### Run with detailed output
```bash
pytest -vv --tb=short
```

## Test Fixtures

### Database Fixtures
- `db_session`: Fresh in-memory SQLite database per test
- `sample_character`: Pre-created Fighter character (level 3)
- `sample_game_session`: Active game session
- `sample_npc`: Goblin enemy
- `sample_combat`: Active combat with character vs NPC

### Factory Fixtures
- `character_factory`: Generate character test data
- `combat_action_factory`: Generate combat action test data

## Test Markers

- `@pytest.mark.integration`: Requires real API calls (run with `--integration`)
- `@pytest.mark.slow`: Long-running tests (>5 seconds)
- `@pytest.mark.asyncio`: Async tests

## Coverage Goals

- **Target**: 80%+ code coverage
- **Current**: Run `pytest --cov` to check

### Coverage by Module
```bash
pytest --cov=app --cov-report=term-missing
```

## CI/CD Integration

Tests run automatically on:
- Pull requests to `main` or `develop`
- Push to `main` (deployment gate)

### GitHub Actions Workflow
```yaml
- name: Run tests
  run: |
    cd backend
    pytest --cov=app --cov-report=xml
```

## Test Database

Tests use in-memory SQLite for speed:
- No setup/teardown delays
- Isolated per test
- Fast (~200ms per test suite)

For PostgreSQL-specific tests, use Docker:
```bash
docker-compose up -d postgres
pytest --db-url=postgresql://...
```

## Writing New Tests

### Example: Testing a new endpoint
```python
def test_new_endpoint(client: TestClient, sample_character: Character):
    """Test POST /new-endpoint"""
    data = {"field": "value"}
    
    response = client.post(f"/new-endpoint/{sample_character.id}", json=data)
    
    assert response.status_code == 200
    assert response.json()["field"] == "value"
```

### Example: Testing database operations
```python
@pytest.mark.asyncio
async def test_new_model(db_session: AsyncSession):
    """Test creating NewModel"""
    model = NewModel(name="Test")
    db_session.add(model)
    await db_session.commit()
    
    assert model.id is not None
```

## Troubleshooting

### Tests fail with "database locked"
- Ensure only one test runs at a time
- Check for unclosed database connections

### Async tests fail
- Add `@pytest.mark.asyncio` decorator
- Ensure `pytest-asyncio` is installed

### Coverage too low
- Add tests for uncovered branches
- Test error cases and edge conditions

## Future Improvements

- [ ] E2E tests with Playwright (frontend + backend)
- [ ] Performance benchmarking tests
- [ ] Load testing with locust
- [ ] Contract tests for Mistral API
- [ ] Mutation testing with mutmut
