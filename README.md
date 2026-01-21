# Mistral Realms

**AI-Powered D&D Adventure Platform**

An immersive Dungeons & Dragons experience powered by Mistral AI, featuring real-time AI narration, intelligent memory systems, AI companions, dynamic image generation, and comprehensive character management.

> Built for the Mistral AI Internship Application

## Features

### Core Gameplay
- **AI Dungeon Master**: Real-time narration powered by Mistral AI with streaming responses
- **Intelligent Memory System**: RAG-based memory with episodic, character, dialogue, and location memories
- **Dynamic Image Generation**: AI-generated scene images that bring your adventure to life
- **Message Summarization**: Automatic conversation summarization for long sessions
- **Context Window Management**: Smart token management to handle extended gameplay

### Character Management
- **Full Character Creation**: Choose from 9 classes and 9 races with authentic D&D mechanics
- **Spell System**: 100+ spells with slot tracking, preparation, and cooldowns
- **Inventory System**: Complete item management with equipped items and weight tracking
- **Level Progression**: Experience-based leveling with automatic stat calculations
- **Status Effects**: Comprehensive buff/debuff system with condition tracking

### AI Companion
- **6 Personality Types**: Choose from helpful, brave, cautious, sarcastic, mysterious, or scholarly
- **Contextual Reactions**: Auto-responds to combat, low HP, victories, puzzles, and more
- **Customizable**: Name, race, and class selection for your AI companion
- **Real-time Integration**: Companion speech generated alongside DM narration

### Combat & Mechanics
- **Advanced Dice Rolling**: Support for ability checks, saving throws, attack rolls, and damage
- **Automatic Execution**: Dice rolls parsed from DM narration and executed automatically
- **D&D 5E Rules**: Authentic modifiers, advantage/disadvantage, critical hits
- **Quest System**: Track active quests with progress updates

### Technical Features
- **Streaming Responses**: Watch your story unfold word-by-word via SSE
- **Session Persistence**: Redis-backed session management with PostgreSQL storage
- **Authentication**: Secure JWT-based authentication with bcrypt hashing
- **REST API**: Complete OpenAPI documentation with FastAPI
- **Containerized**: Full Docker support with multi-stage builds

## Quick Start

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

## Architecture

```
mistral-realms/
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py             # Application entry
│   │   ├── api/                # API endpoints
│   │   │   ├── auth.py         # Authentication
│   │   │   ├── characters.py   # Character CRUD
│   │   │   ├── conversations.py # DM narration & actions
│   │   │   ├── companion.py    # AI companion
│   │   │   ├── spells.py       # Spell management
│   │   │   ├── inventory.py    # Item management
│   │   │   └── ...             # Combat, quests, progression
│   │   ├── services/           # Business logic
│   │   │   ├── mistral_client.py           # Mistral AI client
│   │   │   ├── dm_engine.py                # DM narration engine
│   │   │   ├── memory_service.py           # RAG memory system
│   │   │   ├── summarization_service.py    # Message summarization
│   │   │   ├── context_window_manager.py   # Token management
│   │   │   ├── companion_service.py        # AI companion
│   │   │   ├── image_service.py            # Scene generation
│   │   │   └── ...                         # Roll, spell, combat services
│   │   ├── db/                 # Database layer
│   │   │   ├── models.py       # SQLAlchemy models
│   │   │   └── base.py         # DB connection
│   │   └── schemas/            # Pydantic models
│   ├── tests/                  # Test suite
│   └── Dockerfile              # Backend container
├── frontend/                   # Next.js 16 frontend
│   ├── app/                    # App Router pages
│   │   ├── game/              # Main game interface
│   │   ├── characters/        # Character creation
│   │   └── auth/              # Login/Register
│   ├── components/             # React components
│   │   ├── GameInterface.tsx   # Main game UI
│   │   ├── CompanionPanel.tsx  # AI companion
│   │   ├── CharacterSheet.tsx  # Character stats
│   │   ├── SpellSlots.tsx      # Spell tracking
│   │   └── ...
│   ├── lib/                    # Utilities
│   │   └── api-client.ts       # Backend API client
│   └── Dockerfile              # Frontend container
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md         # System architecture
│   ├── API.md                  # API documentation
│   └── MISTRAL-INTEGRATION.md  # AI integration
├── scripts/                    # Utility scripts
├── docker-compose.yml          # Production orchestration
└── docker-compose.dev.yml      # Development orchestration
```

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.13)
- **AI**: Mistral AI SDK (mistral-large-latest) with streaming
- **Database**: PostgreSQL 15 with async SQLAlchemy
- **Caching**: Redis 7 for sessions and conversation history
- **Token Management**: tiktoken for context window tracking
- **Testing**: pytest with async support and >80% coverage

### Frontend
- **Framework**: Next.js 16 with App Router and React 19
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS v4 with shadcn/ui components
- **Streaming**: Server-Sent Events (SSE) for real-time narration
- **Icons**: Lucide React
- **State Management**: React hooks and localStorage

### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose
- **Networking**: Bridge network for service communication
- **Security**: JWT authentication, password hashing, CORS protection

## Documentation

- [Backend Documentation](./backend/README.md)
- [Frontend Documentation](./frontend/README.md)
- [Architecture Details](./docs/ARCHITECTURE.md)
- [API Documentation](./docs/API.md)
- [Mistral Integration](./docs/MISTRAL-INTEGRATION.md)

## Development

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

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MISTRAL_API_KEY` | Your Mistral AI API key | - | ✅ |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` | ✅ |
| `REDIS_HOST` | Redis hostname | `redis` | ✅ |
| `REDIS_PORT` | Redis port | `6379` | ✅ |
| `JWT_SECRET_KEY` | Secret for JWT tokens | - | ✅ |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry time | `30` | No |
| `BACKEND_PORT` | Backend API port | `8000` | No |
| `FRONTEND_PORT` | Frontend web port | `3000` | No |

### Setting Up Environment

1. Copy the example file:
```bash
cp .env.example .env
```

2. Add your Mistral API key:
```
MISTRAL_API_KEY=your_key_here
```

3. Generate a secure JWT secret:
```bash
openssl rand -hex 32
```

4. Update `.env` with the generated secret:
```
JWT_SECRET_KEY=your_generated_secret
```

## Project Status

This project demonstrates advanced AI integration, full-stack development, and production-ready practices for the Mistral AI internship application.

### Completed Features (Days 1-15) ✅

**Week 1: Core Systems**
- ✅ FastAPI backend with async SQLAlchemy
- ✅ PostgreSQL database with 20+ tables
- ✅ Redis caching and session management
- ✅ JWT authentication with secure password hashing
- ✅ Character creation (9 classes, 9 races)
- ✅ Full D&D 5E attribute system
- ✅ Inventory management with equipment
- ✅ Level progression and XP tracking

**Week 2: AI & Advanced Features**
- ✅ AI Dungeon Master with Mistral Large
- ✅ Streaming narration via SSE
- ✅ Intelligent memory system (RAG pattern)
- ✅ Message summarization for long sessions
- ✅ Context window management (28k tokens)
- ✅ Dynamic scene image generation
- ✅ AI companion with 6 personalities
- ✅ Auto-contextual companion responses
- ✅ Comprehensive spell system (100+ spells)
- ✅ Spell slot tracking and preparation
- ✅ Advanced dice rolling with auto-execution
- ✅ Quest system with progress tracking
- ✅ Status effects and conditions
- ✅ Combat mechanics with modifiers

**Infrastructure & DevOps**
- ✅ Docker multi-stage builds
- ✅ Docker Compose orchestration
- ✅ Development and production configs
- ✅ Comprehensive API documentation
- ✅ Architecture documentation
- ✅ 80%+ test coverage

### In Progress 🚧
- Performance profiling and optimization
- Enhanced documentation updates

### Technical Highlights

**AI Integration**
- Mistral Large for DM narration with focused system prompts
- Token counting with tiktoken for accurate context management
- Smart conversation pruning to stay within 32k context window
- RAG-based memory retrieval for relevant context injection
- Personality-driven companion with trigger-based responses

**Database Design**
- 20+ normalized tables for characters, spells, items, sessions
- Async SQLAlchemy with connection pooling
- Efficient querying with eager loading
- Redis caching for hot data paths

**Frontend UX**
- Real-time streaming with SSE for immersive narration
- Responsive UI with Tailwind CSS and shadcn/ui
- Character sheet with live stat updates
- Spell slot management with visual indicators
- Inventory with drag-and-drop (planned)
- AI companion panel with personality selection

**Security**
- JWT authentication with refresh tokens
- bcrypt password hashing with salt
- CORS configuration for cross-origin requests
- Input validation with Pydantic
- SQL injection prevention via parameterized queries

## License

This project is built as part of a Mistral AI internship application.

## Contributing

This is an application project, but feedback is welcome! Feel free to open issues for suggestions.

## Contact

Built by [Amine Ouichou](https://github.com/aouichou)

---

**Note**: Make sure to add your Mistral API key to `.env` before running the application!
