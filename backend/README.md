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

```bash
docker build -t mistral-realms-backend .
docker run -p 8000:8000 --env-file .env mistral-realms-backend
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
│   │   └── narrate.py       # DM narration routes
│   ├── services/            # Business logic
│   │   ├── mistral_client.py
│   │   └── dm_engine.py
│   ├── models/              # Data models
│   │   └── schemas.py       # Pydantic models
│   └── utils/               # Utilities
│       └── logger.py
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
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
