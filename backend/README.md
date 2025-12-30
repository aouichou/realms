# Mistral Realms Backend

AI-Powered D&D Adventure Generator - Backend API

## 🚀 Quick Start

### Local Development

1. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your MISTRAL_API_KEY
```

4. **Run the server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Access API docs**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Docker Development

**Build the image**
```bash
docker build -t mistral-realms-backend:latest .
```

**Run the container**
```bash
# With environment file
docker run -d -p 8000:8000 --env-file .env --name realms-backend mistral-realms-backend:latest

# Or with individual env vars
docker run -d -p 8000:8000 \
  -e MISTRAL_API_KEY=your_key_here \
  --name realms-backend \
  mistral-realms-backend:latest
```

**View logs**
```bash
docker logs -f realms-backend
```

**Stop and remove**
```bash
docker stop realms-backend
docker rm realms-backend
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_health.py -v
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── routers/             # API endpoints
│   │   ├── health.py        # Health check routes
│   │   └── narrate.py       # DM narration routes (coming soon)
│   ├── services/            # Business logic
│   │   ├── mistral_client.py # Mistral AI wrapper
│   │   └── dm_engine.py     # DM narration engine
│   ├── models/              # Data models
│   │   └── schemas.py       # Pydantic models (coming soon)
│   └── utils/               # Utilities
│       └── logger.py        # Structured logging
├── tests/                   # Test suite
│   ├── test_health.py       # Health endpoint tests
│   ├── test_mistral_client.py # Mistral client tests
│   ├── test_dm_engine.py    # DM engine tests
│   └── test_integration.py  # Integration tests
├── requirements.txt         # Python dependencies
├── Dockerfile              # Multi-stage Docker build
├── .dockerignore           # Docker ignore patterns
└── .env.example            # Environment template
```

## 🔧 Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

### Key Settings:
- `MISTRAL_API_KEY`: Your Mistral AI API key (required)
- `MISTRAL_MODEL`: Model to use (default: mistral-small-latest)
- `RATE_LIMIT_PER_SECOND`: API rate limiting (default: 1)
- `REDIS_HOST`: Redis host for session storage
- `POSTGRES_HOST`: PostgreSQL host for persistence

## 📚 API Documentation

Once the server is running, visit:
- `/docs` - Interactive Swagger UI
- `/redoc` - ReDoc documentation
- `/health` - Health check endpoint

## 🛠️ Development Tools

### Code Formatting
```bash
black app/ tests/
```

### Linting
```bash
ruff check app/ tests/
```

### Type Checking
```bash
mypy app/
```

## 🐛 Troubleshooting

### Issue: Module not found
```bash
# Make sure you're in the virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Mistral API errors
- Check your API key in `.env`
- Verify your API quota at console.mistral.ai
- Check rate limiting settings

## 📝 License

Part of Mistral Realms project - Internship showcase for Mistral AI
