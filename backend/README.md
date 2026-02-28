# Mistral Realms — Backend

FastAPI backend with 42 services, 80+ REST endpoints, 6 AI providers, 16 tool-calling functions, RAG memory, and full OpenTelemetry instrumentation.

---

## Service Architecture

### AI Engine (Core)

| Service | File | Description |
|---------|------|-------------|
| **DM Engine** | `services/dm_engine.py` | Core orchestrator (1,991 lines). Builds full message context, runs multi-iteration tool-calling loops (max 10 rounds), extracts `[ROLL:...]` and `[QUEST_COMPLETE:...]` tags, integrates supervisor validation. |
| **Tool Executor** | `services/tool_executor.py` | Executes the 16 game-mechanic tools called by the AI: HP changes, dice rolls, spell slot consumption, creature stats (fuzzy matching), companion creation, item giving, semantic search, loot generation. |
| **DM Tools** | `dm_tools.py` | Defines all 16 tool schemas in Mistral API format — the function-calling contract between AI and game engine. |
| **DM Supervisor** | `services/dm_supervisor.py` | Validates AI responses against D&D 5e rules using 9 regex-based mistake patterns. Loads reference knowledge from `dm_knowledge/*.md`, chunks and embeds for semantic retrieval. Triggers silent regeneration with rule reminders on failure. |
| **DM Preheater** | `services/dm_preheater.py` | Primes the AI with 5 warmup exchange pairs reinforcing tool usage. Injects periodic reminders every 10 turns to combat context window degradation. |
| **Adaptive Narration** | `services/adaptive_narration_service.py` | Generates contextual narrations when AI returns empty content alongside tool calls. 10 action categories × 5 templates, selected via embedding similarity. |

### AI Providers

| Service | File | API | Notes |
|---------|------|-----|-------|
| **Mistral Provider** | `services/mistral_provider.py` | Native Mistral SDK | Rate-limit cooldowns with auto-recovery timestamps. Sync SDK calls via `asyncio.to_thread()`. |
| **Mistral Client** | `services/mistral_client.py` | Native Mistral SDK | Lower-level client with `chat.stream()`, async lock-based rate limiting, integrated metrics/tracing. |
| **Qwen Provider** | `services/qwen_provider.py` | DashScope (OpenAI-compatible) | `dashscope-intl.aliyuncs.com`. Dynamic model switching and discovery. |
| **Groq Provider** | `services/groq_provider.py` | OpenAI-compatible | `AsyncOpenAI` with Groq `base_url`. |
| **Cerebras Provider** | `services/cerebras_provider.py` | OpenAI-compatible | Same pattern as Groq. |
| **Together Provider** | `services/together_provider.py` | OpenAI-compatible | Same pattern as Groq. |
| **SambaNova Provider** | `services/sambanova_provider.py` | OpenAI-compatible | Same pattern as Groq. |
| **Provider Selector** | `services/provider_selector.py` | — | Selects by priority, tracks per-provider stats, triggers context transfer on switch. |
| **Provider Init** | `services/provider_init.py` | — | Startup initializer. Reads config and creates/registers all providers. |
| **AI Provider ABC** | `services/ai_provider.py` | — | Abstract base class defining the provider interface. |
| **Model Discovery** | `services/model_discovery_service.py` | — | Dynamic model discovery from provider APIs. Cached results. |

### Intelligence Services

| Service | File | Description |
|---------|------|-------------|
| **Memory Service** | `services/memory_service.py` | RAG memory. Stores adventure events with `mistral-embed` (1024-dim) vectors. Retrieves via pgvector cosine similarity with text-search fallback. |
| **Embedding Service** | `services/embedding_service.py` | Generates 1024-dim embeddings using Mistral's `mistral-embed`. Singleton, async via `to_thread()`. |
| **Semantic Search** | `services/semantic_search_service.py` | NLP search across items (14,351), monsters (11,172), and spells (4,759). Local `paraphrase-multilingual-MiniLM-L12-v2` (384-dim). |
| **Context Window Manager** | `services/context_window_manager.py` | Token-accurate management using tiktoken `cl100k_base`. 28K budget (4K for response). FIFO pruning. |
| **Token Counter** | `services/token_counter.py` | Simpler 4-chars/token estimation for quick checks. |
| **Summarization Service** | `services/summarization_service.py` | Summarizes long conversations (10+ messages) using Mistral LLM. |
| **Message Summarizer** | `services/message_summarizer.py` | Higher-level summarizer. Triggers at 20+ messages AND near 28K token limit. |
| **Context Transfer** | `services/context_transfer.py` | Generates adventure summaries for seamless provider switching. |

### Image Generation

| Service | File | Description |
|---------|------|-------------|
| **Image Service** | `services/image_service.py` | Persistent Mistral agent with `image_generation` tool ("D&D Scene Illustrator"). Hash-based deduplication, DB cache, 429 cooldown (5-min), hourly quotas. |
| **Image Detection** | `services/image_detection_service.py` | Scene-change detection using sentence-transformers. 18 scene templates, cosine similarity ≥ 0.5 triggers generation. |

### Game Mechanics

| Service | File | Description |
|---------|------|-------------|
| **Roll Parser** | `services/roll_parser.py` | Parses `[ROLL:type:details]` tags. Comprehensive ability mapping for D&D 5e skills. |
| **Roll Executor** | `services/roll_executor.py` | XdY+Z notation, advantage/disadvantage, drop lowest/highest. Applies ability modifiers. |
| **Random Pool** | `services/random_pool.py` | Random.org atmospheric noise. Pool of 200 integers, auto-refill at 50, graceful fallback. |
| **Dice Service** | `services/dice_service.py` | Core dice parsing + rolling, integrates with Random Pool. |
| **Companion Service** | `services/companion_service.py` | AI companion NPCs with personality, loyalty tracking, conversation memory. |
| **Content Linker** | `services/content_linker.py` | Maps monster CR → item rarity for intelligent loot generation. |
| **Effects Service** | `services/effects_service.py` | Spell effect lifecycle: application, concentration, duration ticks, rest cleanup. |
| **Save Service** | `services/save_service.py` | Game save/load with state snapshot serialization. |
| **Auth Service** | `services/auth_service.py` | JWT, guest mode, account claiming. |
| **Redis Service** | `services/redis_service.py` | Session state + conversation caching. 24-hour TTL. |

---

## DM Engine In Depth

### Message Assembly Pipeline

The DM Engine builds messages in this exact order:

1. **System prompt** (~1,500 tokens): Bilingual EN+FR instructions defining the DM's persona, tool usage rules, response format
2. **Character context** (~200-500 tokens): Full D&D 5e character sheet — abilities, HP, AC, inventory, equipped items
3. **Game state** (~200-400 tokens): Active quests, companions, spell effects, location
4. **Memory context** (~300-800 tokens): RAG-retrieved relevant memories via pgvector cosine similarity
5. **Warmup messages** (first turn only): 5 synthetic user/assistant exchanges reinforcing tool behavior
6. **Periodic reminders** (every 10 turns): System message re-injecting tool usage rules
7. **Conversation history** (variable): Token-pruned, keeping system messages + most recent exchanges
8. **User message**: The player's action

Total budget: **28,000 tokens** (4K reserved for AI response).

### Tool-Calling Loop

```python
for iteration in range(MAX_TOOL_ITERATIONS):  # max 10
    response = provider.chat_complete(messages, tools=GAME_MASTER_TOOLS)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = tool_executor.execute_tool(tool_call)
            messages.append(tool_result_message(result))
        continue  # Re-call AI with tool results

    # Fallback: parse text-based tool calls via regex
    text_tools = _parse_and_execute_text_tool_calls(response.content)
    if text_tools:
        messages.extend(text_tools)
        continue

    if response.content:
        break  # Got narration, done
```

### Provider Branching

The DM Engine has explicit code paths:
- **Mistral**: Native SDK `client.chat.complete()` with `tools=GAME_MASTER_TOOLS`, `tool_choice="auto"`
- **Qwen**: `AsyncOpenAI` pointed at DashScope endpoint
- **Others** (Groq, Cerebras, Together, SambaNova): `AsyncOpenAI` with provider `base_url`

### DM Supervisor Validation

```
AI response →
  Combat keyword detection →
  9 regex patterns checked:
    • Narrated dice rolls (should use request_player_roll)
    • Damage without update_character_hp
    • Spell effects without consume_spell_slot
    • HP changes narrated without tool use
    • Item giving without give_item tool
    • Creature stats narrated without get_creature_stats
  →
  Semantic retrieval from dm_knowledge/ rules →
  If confidence < 0.7:
    → Inject rules as system message
    → Silent regeneration (player never sees error)
```

---

## Provider System

### Priority-Based Selection

```
MISTRAL_ENABLED=true  (Demo mode):
  Mistral → priority 1
  Qwen    → priority 2
  Free providers → priority 3-6

MISTRAL_ENABLED=false (Testing mode):
  Mistral → priority 99 (emergency)
  Qwen    → priority 1
  Free providers → priority 2-5
```

On provider failure: mark rate-limited → cascade to next priority → `ContextTransferService` generates session summary → inject into new provider context → track statistics.

---

## Mistral Integration

### Chat Completions
- SDK: `mistralai==1.10.0`, model: `mistral-small-latest`
- Sync calls wrapped in `asyncio.to_thread()`
- Async lock-based rate limiting with minimum interval
- Every call creates an OpenTelemetry span with `llm.vendor`, `llm.model`, `llm.prompt_tokens`, `llm.completion_tokens`

### Tool Calling (16 functions)
`request_player_roll`, `roll_for_npc`, `update_character_hp`, `consume_spell_slot`, `get_creature_stats`, `search_items`, `give_item`, `search_memories`, `search_monsters`, `search_spells`, `introduce_companion`, `companion_suggest_action`, `companion_share_knowledge`, `generate_treasure_hoard`, `list_available_tools` — all in Mistral's function-calling format with detailed parameter schemas.

### Embeddings
`mistral-embed` → 1024-dimensional vectors for the RAG memory system, stored in pgvector.

### Agent API (Image Generation)
Persistent "D&D Scene Illustrator" agent with `image_generation` tool. Agent created once, reused via `MISTRAL_IMAGE_AGENT_ID`. 429 cooldown (5-min), hash deduplication, DB cache, hourly quota.

---

## RAG Memory

### Dual Embedding Models
| Model | Dimensions | Use Case | Cost |
|-------|-----------|----------|------|
| `mistral-embed` (API) | 1024 | Memory storage/retrieval | Paid per call |
| `paraphrase-multilingual-MiniLM-L12-v2` (local) | 384 | DM tool searches (items/monsters/spells), scene detection | Free (CPU) |

### Write: event → embed → store in pgvector
### Read: player action → embed → cosine similarity search → inject into context

---

## Context Window Management

```
Total: 32K tokens
├── System prompt:      ~1,500
├── Character context:  ~200-500
├── Game state:         ~200-400
├── RAG memories:       ~300-800
├── Warmup/reminders:   ~500
├── Conversation:       variable
├── ─────────────────────────
├── Budget cap:         28,000
└── Response reserve:    4,000
```

Pruning: FIFO (keep system + last N). Summarization trigger: 20+ messages near limit.

---

## API Endpoints (80+)

| Group | Prefix | Count | Key Features |
|-------|--------|-------|--------------|
| Auth | `/auth` | 7 | JWT cookies, guest mode, account claiming |
| Conversations | `/conversations` | 5 | Main gameplay, message history |
| Characters | `/characters` | 10 | Full CRUD, skills, background, stats |
| Sessions | `/sessions` | 8 | State management, active session |
| Game Saves | `/game` | 4 | Save/load/list/delete |
| Companions | `/companions` | 7 | CRUD, chat, loyalty, conversations |
| Dice | `/dice` | 2 | Roll notation, ability checks |
| Spells | `/spells` | 10 | Learn, prepare, cast, rest, concentration |
| Items | `/items` | 5 | Search, categories, random, by ID/name |
| Inventory | `/inventory` | 5 | Add, list, equip, update, remove |
| Conditions | `/conditions` | 4 | Apply, remove, list, effects |
| Effects | `/effects` | 6 | Active, remove, round-end, rest, cleanup |
| Progression | `/progression` | 3 | XP, progress, level-up |
| Loot | `/loot` | 3 | Generate, recipes, craft |
| Rest | `/rest` | 2 | Short/long rest, eligibility |
| Rules | `/rules` | 7 | ASI, racial bonuses, class skills |
| Images | `/images` | 1 | Scene generation |
| Memories | `/memories` | 5 | Store, search, recent, context, clear |
| NPCs | `/npcs` | 3 | Create, list, get |

---

## Middleware Stack (9 layers)

1. **CORS** — Origin validation
2. **HTTPS** — HTTP→HTTPS redirect, HSTS (1 year)
3. **CSRF** — Double submit cookie, constant-time comparison
4. **Error Logger** — Full stack traces to `/app/logs/errors/`
5. **Language** — i18n via `Accept-Language`
6. **Observability** — Correlation IDs, HTTP metrics
7. **Rate Limiting** — IP/user sliding window, per-endpoint limits, DDoS burst protection
8. **Performance** — Slow request detection (>1s warn, >3s error)
9. **Query Monitor** — Slow queries (>500ms), N+1 detection (>10 queries)

---

## Observability

- **Tracing**: OpenTelemetry → Jaeger (auto: FastAPI, HTTPX, Redis, SQLAlchemy; custom: `@trace_async`, `trace_llm_call`)
- **Metrics**: 40+ Prometheus metrics (HTTP, LLM, DB, Redis, rate limits, auth, sessions, companions, spells, DM tools, images)
- **Logging**: Structured key=value format with ContextVars (`request_id`, `user_id`, `session_id`, `character_id`)
- **Alerts**: 15 Prometheus alert rules across 6 groups

---

## Database

PostgreSQL 16 + pgvector. 16 Alembic migrations (async). Auto-seeding on empty tables.

Key models: User, Character, GameSession, ConversationMessage, AdventureMemory (pgvector 1024d), Companion, Quest, QuestObjective, Creature (11,172), ItemCatalog (14,351), Spell (4,759), ActiveEffect, CompanionConversation, GeneratedImage.

---

## Running

### Docker
```bash
docker-compose up --build
```

### Local
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-transformers.txt
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/realms"
export REDIS_URL="redis://localhost:6379"
export MISTRAL_API_KEY="your_key"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Tests
```bash
pytest -v                         # All 121 tests
pytest tests/test_dm_engine.py    # DM engine tests
pytest --cov=app                  # With coverage
```
