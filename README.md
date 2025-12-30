# Mistral Realms

**AI-Powered D&D Adventure Generator**

An immersive Dungeons & Dragons experience powered by Mistral AI, featuring real-time AI narration, streaming responses, and a beautiful web interface.

> Built for the Mistral AI Internship Application

## 🎮 Features

- **AI Dungeon Master**: Real-time narration powered by Mistral AI
- **Streaming Responses**: Watch your story unfold word-by-word
- **Interactive Chat**: Simple, intuitive interface for player actions
- **Focused Narration**: No meta-commentary, just immersive storytelling
- **Containerized**: Full Docker support with hot reload in development

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Mistral AI API key ([Get one here](https://console.mistral.ai/))

### 1. Clone & Configure

```bash
# Clone the repository
git clone https://github.com/aouichou/realms.git
cd realms

# Copy environment file
cp .env.example .env

# Add your Mistral API key to .env
# MISTRAL_API_KEY=your_key_here
```

### 2. Run with Docker Compose

**Production Mode:**
```bash
docker-compose up --build
```

**Development Mode (with hot reload):**
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Redis**: localhost:6379

### 4. Start Your Adventure

1. Open http://localhost:3000
2. Click "Start Your Adventure"
3. Describe your action and watch the AI respond!

## 🏗️ Architecture

```
mistral-realms/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py      # Application entry
│   │   ├── routers/     # API endpoints
│   │   ├── services/    # Business logic
│   │   │   ├── mistral_client.py  # Mistral AI integration
│   │   │   └── dm_engine.py       # DM narration engine
│   │   └── models/      # Data schemas
│   ├── tests/           # Test suite
│   └── Dockerfile       # Backend container
├── frontend/            # Next.js 16 frontend
│   ├── app/            # App Router pages
│   ├── components/     # React components
│   ├── lib/           # API client & utilities
│   └── Dockerfile     # Frontend container
├── docker-compose.yml      # Production orchestration
└── docker-compose.dev.yml  # Development orchestration
```

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI**: Mistral AI SDK with streaming
- **Caching**: Redis
- **Testing**: pytest with async support

### Frontend
- **Framework**: Next.js 16 with App Router
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS v4
- **Streaming**: Server-Sent Events (SSE)

### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose
- **Networking**: Bridge network for service communication

## 📚 Documentation

- [Backend Documentation](./backend/README.md)
- [Frontend Documentation](./frontend/README.md)
- [Architecture Details](./docs/ARCHITECTURE.md)
- [API Documentation](./docs/API.md)
- [Mistral Integration](./docs/MISTRAL-INTEGRATION.md)

## 🧪 Development

### Local Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
cd backend
pytest -v
```

### Building Images

```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend
docker-compose build frontend
```

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild and restart
docker-compose up --build --force-recreate
```

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MISTRAL_API_KEY` | Your Mistral AI API key | **Required** |
| `REDIS_HOST` | Redis hostname | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `BACKEND_PORT` | Backend API port | `8000` |
| `FRONTEND_PORT` | Frontend web port | `3000` |

## 🎯 Project Goals

This project demonstrates:
- ✅ **Deep D&D Mechanics**: Authentic DM narration with context awareness
- ✅ **Creative AI Integration**: Streaming responses with focused prompts
- ✅ **Visual Appeal**: Modern, responsive UI with Tailwind CSS
- ✅ **Technical Showcase**: Clean architecture, Docker, testing, type safety

## 🚧 Current Status

**Completed (Day 1):**
- ✅ FastAPI backend with health checks
- ✅ Mistral AI client with streaming support
- ✅ DM Engine with focused system prompts
- ✅ Next.js 16 frontend with App Router
- ✅ Chat UI with real-time streaming
- ✅ Docker containerization (backend & frontend)
- ✅ Docker Compose orchestration

**Next Steps:**
- Character creation system
- Persistent game state (PostgreSQL)
- Session management with Redis
- Observability (OpenTelemetry, Prometheus, Grafana)
- Advanced D&D mechanics (dice rolls, inventory, combat)

## 📄 License

This project is built as part of a Mistral AI internship application.

## 🤝 Contributing

This is an application project, but feedback is welcome! Feel free to open issues for suggestions.

## 📧 Contact

Built by [Amine Ouichou](https://github.com/aouichou)

---

**Note**: Make sure to add your Mistral API key to `.env` before running the application!
