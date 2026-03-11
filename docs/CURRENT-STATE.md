# Mistral Realms — Current State

> As of February 28, 2026. This document synthesizes all historical docs, tickets, and audits into a single source of truth about what currently exists, what decisions were made, and why.

---

## What Currently Exists and Works

### Core Systems — Fully Operational

| System | Status | Implementation |
|--------|--------|---------------|
| **DM Engine** | Complete | 1,991-line orchestrator with multi-iteration tool-calling loop (max 10), bilingual system prompts (EN/FR), token-accurate context management (28K budget), regex-based roll/quest extraction |
| **16 Tool-Calling Functions** | Complete | `request_player_roll`, `roll_for_npc`, `update_character_hp`, `consume_spell_slot`, `get_creature_stats`, `search_items`, `give_item`, `search_memories`, `search_monsters`, `search_spells`, `introduce_companion`, `companion_suggest_action`, `companion_share_knowledge`, `generate_treasure_hoard`, `list_available_tools` — all in Mistral's format |
| **Provider System** | Complete | 6 providers (Mistral, Qwen, Groq, Cerebras, Together, SambaNova) with priority-based selection, automatic fallback, context transfer on switches, per-provider statistics |
| **DM Supervisor** | Complete (RL-140) | 9 regex-based mistake patterns, semantic retrieval from `dm_knowledge/` rule files, silent regeneration on confidence < 0.7 |
| **DM Preheater** | Complete (RL-142) | 5 warmup exchange pairs on first turn, periodic reminders every 10 turns |
| **Adaptive Narration** | Complete (RL-145) | 10 action categories × 5 templates, selected via embedding similarity when AI returns empty content with tool calls |
| **RAG Memory** | Complete | Mistral `mistral-embed` (1024d) → pgvector cosine similarity → context injection. Text-search fallback. |
| **Semantic Search** | Complete (RL-144) | Local `paraphrase-multilingual-MiniLM-L12-v2` (384d) for items (14,351), monsters (11,172), spells (4,759). Centralized from 3 fragmented implementations. |
| **Image Generation** | Complete | Mistral Agent API, persistent agent ("D&D Scene Illustrator"), hash deduplication, DB cache, 429 cooldown (5-min), hourly quotas |
| **Scene Detection** | Complete | Sentence-transformers embeddings against 18 scene templates, cosine similarity ≥ 0.5 triggers generation |
| **True Randomness** | Complete | Random.org hybrid pool (200 integers, refill at 50, fallback to `random.randint()`) |
| **Character System** | Complete | Full D&D 5e character sheet: 9 races, 12 classes, 6 ability scores (27-point buy), skill proficiencies, backgrounds (13), personality, spell selection |
| **Spell System** | Complete | 4,759 spells seeded, learn/prepare/cast, spell slot tracking, concentration, ritual, rest recovery |
| **Companion System** | Complete (RL-131) | AI companions with personality types, loyalty (0-100), combat stats (copied from creature DB), private chat, DM-introduced creation via tools |
| **Inventory System** | Complete | 14,351-item catalog, equip/unequip, weight tracking, carrying capacity |
| **Quest System** | Complete | State machine (not_started → in_progress → completed/failed), objectives, XP/gold/item rewards |
| **Dice System** | Complete | XdY+Z notation, advantage/disadvantage, drop lowest/highest, ability modifiers, DC checks, true randomness integration |
| **Save/Load** | Complete | Game state snapshots with slot management, auto-save every 5 minutes |
| **Authentication** | Complete | JWT (httpOnly cookies), refresh tokens, guest mode, guest→registered account claiming, bcrypt |
| **Effects System** | Complete | Spell effect lifecycle: application, concentration tracking, duration ticks, rest-based cleanup |
| **Progression** | Complete | XP awards, level-up, proficiency bonus calculation |
| **Conditions** | Complete | 14 D&D 5e conditions with mechanical effects |

### Frontend — Fully Operational

| Feature | Status | Notes |
|---------|--------|-------|
| Game interface | Complete | 1,153-line game page with chat, side panels, roll queue |
| Character creation | Complete | 6-step wizard |
| Adventure selection | Complete | Preset + custom AI wizard with preview |
| Typewriter narration | Complete | ~120 chars/sec, click-to-skip — simulated streaming, not SSE |
| Scene images | Complete | Background overlay, fullscreen viewer, gallery |
| Companion chat | Complete | Private sidebar chat with "share with DM" toggle |
| Spell management | Complete | Browse, filter, cast, track slots, prepare, concentration |
| Inventory | Complete | Grid/list view, equip/unequip, weight, filter |
| Ability checks | Complete | 18 D&D 5e skills, advantage/disadvantage, DC |
| i18n | Complete | EN/FR via custom `useTranslation` hook (1,173-line translation object) |
| Demo mode | Complete | Instant play (auto-guest + fighter + Goblin Ambush) + custom character path |
| Save/Load | Complete | Manual save + load from slots |
| Tool call badges | Complete | Shows AI tool calls per response |
| Quest completion | Complete | Celebration modal with rewards |

### Infrastructure — Fully Operational

| Component | Status | Details |
|-----------|--------|---------|
| Docker stack | Complete | 7 services, multi-stage builds, non-root users, health checks |
| OpenTelemetry → Jaeger | Complete | Auto-instrumented FastAPI, HTTPX, Redis, SQLAlchemy + custom spans |
| Prometheus metrics | Complete | 40+ metrics, 15 alert rules in 6 groups |
| Grafana dashboards | Complete | Auto-provisioned with Prometheus + Jaeger datasources |
| Database migrations | Complete | 16 Alembic migrations, async, auto-seeding |
| Middleware stack | Complete | 9 layers: CORS, HTTPS, CSRF, error logging, language, observability, rate limiting, performance, query monitoring |
| Tests | Partial | 121 tests across 15 files (unit + integration + performance). DM Engine and newer services need more coverage. |

---

## Development Timeline

### Week 1 (Late Dec 2025 – Early Jan 2026): Foundation
- Day 1: FastAPI backend, Mistral AI integration, basic narration
- Day 2: Character CRUD, game sessions, conversation persistence
- Day 3: Combat system, inventory, dice rolling (Python `random`)
- Day 4: Quest system, XP/progression, Docker Compose
- Days 5–6: Spell system (620 spells initially, 15 components, 73 files, 11,220 insertions)

### Week 2 (Jan ~5–10): AI & Integration
- RL-81: Vector memory system (pgvector, `mistral-embed`, RAG pattern)
- Authentication: JWT, guest mode, refresh tokens, bcrypt
- Image generation: Mistral Agent API (Pixtral), scene detection, filesystem caching
- Save/Load system
- True randomness: Random.org hybrid pool

### Week 3 (Jan ~13–17): Advanced Mechanics & Observability
- RL-124–129: Game mechanics overhaul — removed combat panel, narrative combat, Mistral tool calling (7→16 tools), roll parsing
- RL-130: Creature stats dataset (initially ~50 monsters)
- RL-131: Companion system overhaul (6 personality types, DM-introduced via tool)
- RL-135 + RL-89: Comprehensive OpenTelemetry tracing (Jaeger, Prometheus, Grafana)
- RL-137: Multi-provider hot-swap with context transfer
- RL-140: DM Agentic Supervisor with reference knowledge base

### Week 4 (Jan ~23–30): Content & Semantic Search
- RL-132: Imported 30K D&D 5e entries (14,351 items, 11,172 monsters, 4,759 spells)
- RL-144: Semantic search service using local MiniLM-L12 model
- RL-148: Performance investigation (confirmed bottleneck is LLM API call latency)
- Semantic search refactoring: centralized 3 fragmented implementations
- DM Engine audit: identified and fixed gaps in AI knowledge of 30K entries

### Week 5+ (Feb 2026): Provider Rework
- RL-150: Cleaned up old providers (removed Gemini, OpenAI, Anthropic SDKs)
- RL-151: Model discovery service for 5 providers
- RL-152–155: Qwen multi-model switching, Free Providers Pool, Mistral toggle

---

## Key Architectural Decisions and Rationale

### 1. Why `mistral-small-latest`, Not Large
**Decision**: Use Mistral Small as the primary model.
**Rationale**: Cost/speed/quality balance. At €0.20/1M input tokens, the project sustains ~10,000 player actions for €1.50. Streaming start is 100-300ms. Quality is sufficient for creative D&D storytelling. This is a portfolio project — demonstrating efficient API usage matters more than maximum quality.

### 2. Why Narrative Combat Over Combat Panel
**Decision**: RL-125 removed the separate `CombatPanel` component. All combat happens through DM narration with tool calls.
**Rationale**: (1) Showcases Mistral tool calling for the internship demo — the AI handles combat narratively using `request_player_roll`, `roll_for_npc`, `update_character_hp`. (2) More immersive gameplay. (3) Reduces frontend complexity.
**Revisitable**: A dedicated combat panel could be added back as an overlay without changing the backend.

### 3. Why Tool Calling Over Regex Parsing
**Decision**: RL-129 chose Mistral native function calling over the existing regex-based roll parsing.
**Rationale**: Showcases Mistral's advanced capabilities for the internship application. Regex kept as fallback for models that write tool calls as text instead of using the API.

### 4. Why Dual Embedding Models
**Decision**: Mistral API embeddings (1024d) for memory, local sentence-transformers (384d) for search.
**Rationale**: The `adventure_memories` table already stores 1024d vectors — changing would require re-embedding all existing memories. High-frequency DM tool searches (every tool call) need to be free and fast. Documented in `SEMANTIC-SEARCH-REFACTORING.md`.

### 5. Why Mistral Toggle Deprioritizes Instead of Blocking
**Decision**: `MISTRAL_ENABLED=false` sets Mistral to priority 99 (emergency fallback) instead of disabling it.
**Rationale**: If all free providers fail, Mistral should still be available as a last resort rather than causing total service failure. Originally planned as full disable; corrected in `PROVIDER_REWORK_PLAN_CORRECTED.md`.

### 6. Why Qwen Quota Tracking is Permanent (No TTL)
**Decision**: Redis keys for Qwen model exhaustion have no TTL (permanent until manual deletion).
**Rationale**: Alibaba Cloud's Qwen free tier gives 1M tokens per model one-time, no daily reset. The original plan had 24h TTL — corrected when understanding the actual quota structure.

### 7. Why Preheat Messages Exist
**Decision**: Inject 5 fake user/assistant exchanges on first turn + periodic reminders every 10 turns.
**Rationale**: Mistral would "forget" to use tools like `request_player_roll` over long conversations. The warmup priming + periodic reminders together combat context window degradation. This is essentially a prompt engineering technique for maintaining tool-calling behavior.

### 8. Why True Randomness via Pool (Option C)
**Decision**: Random.org atmospheric noise cached in pool of 200, not direct API calls.
**Rationale**: Three options evaluated in `TRUE_RANDOMNESS.md`: (A) seed-based defeats purpose, (B) direct API has 200-500ms latency per roll, (C) pool gives true randomness with zero latency. Capacity: ~40,000 d20 rolls/day on free tier.

### 9. Why No Global State Library (Frontend)
**Decision**: React Context for auth, local `useState` for everything else.
**Rationale**: Game state is largely server-authoritative. The game page manages session-specific state. Adding Redux/Zustand for a single-page game interface wasn't justified by complexity.

### 10. Why Custom i18n Instead of next-intl
**Decision**: Custom `useTranslation` hook with inline translations (1,173 lines).
**Rationale**: Started simple, grew organically. The inline approach avoids build-time complexity and works with custom event-based live switching. A migration to next-intl would be warranted if more languages were added.

---

## What Was Changed/Refactored and Why

### Combat Panel Removal (RL-125)
**Before**: Separate `CombatPanel` component with turn-based UI.
**After**: All combat through DM narration with tool calls.
**Why**: More immersive and better showcases AI tool calling.

### Provider Stack Overhaul (RL-150–155)
**Before**: Mistral, Gemini, OpenAI, Anthropic SDKs.
**After**: Mistral native + 5 OpenAI-compatible providers (Qwen, Groq, Cerebras, Together, SambaNova).
**Why**: Removed paid-only providers, added free/affordable alternatives. Gemini SDK removal also fixed dependency conflicts.

### Semantic Search Centralization
**Before**: 3 separate implementations with 2 different models, scattered across tool executor and services.
**After**: Single `SemanticSearchService` with 4 methods, local MiniLM model, centralized in one file.
**Why**: Eliminated duplication, reduced memory usage (one model instance), consistent search quality.

### DM Engine → Supervisor Pattern (RL-140)
**Before**: DM Engine generated responses without validation.
**After**: Supervisor validates every response against D&D 5e rules, silently regenerates errors.
**Why**: LLMs would "forget" rules over time (e.g., narrating damage without calling `update_character_hp`). The supervisor catches these before the player sees them.

### Provider Rework Plan Correction
**Before**: `PROVIDER_REWORK_PLAN.md` included HuggingFace, assumed Qwen daily reset, used 24h TTL.
**After**: `PROVIDER_REWORK_PLAN_CORRECTED.md` replaced HuggingFace with Free Providers Pool, corrected Qwen to one-time quota, removed TTL.
**Why**: Research revealed actual provider behaviors differed from initial assumptions.

---

## Known Limitations and Intentional Trade-offs

### Intentional Trade-offs

| Trade-off | Rationale |
|-----------|-----------|
| **Simulated streaming (typewriter) instead of SSE** | Avoids WebSocket/SSE complexity. Backend has partial streaming infrastructure but frontend uses request-response. Typewriter creates adequate immersion for a portfolio project. |
| **In-memory rate limiting** | Not suitable for multi-instance deployment. Redis-backed rate limiting would be proper but the project runs as a single instance. |
| **Two token counting approaches** | `context_window_manager.py` uses tiktoken (precise), `token_counter.py` uses 4-chars/token (fast). Both coexist because they serve different purposes (budget management vs quick checks). |
| **In-memory semantic search** | `SemanticSearchService` loads up to 1,000 records from DB for per-item similarity. pgvector for all embeddings would scale better but works well at current catalog size. |
| **Companion avatars commented out** | `tool_executor.py` has companion avatar generation via image service commented out. Rate limiting concerns during development. |
| **God-class DM Engine** | At 1,991 lines, `dm_engine.py` handles too many responsibilities. Decomposition planned but functional as-is. |

### Known Gaps

| Gap | Impact | Status |
|-----|--------|--------|
| No real SSE streaming | Players wait for full response (~1-3s) | Partial backend infrastructure exists; frontend would need `EventSource` implementation |
| No circuit breaker pattern | Provider failures may cascade during outages | Could be added to `ProviderSelector` with configurable thresholds |
| Limited test coverage for DM Engine | Core game logic has basic tests only | Integration tests for tool-calling loops and supervisor validation needed |
| No pagination on full conversation history | Large sessions may load slowly | Cursor-based pagination on `GET /conversations/{id}` would fix this |
| Duplicate provider implementations | Groq, Cerebras, Together, SambaNova are nearly identical (~137 lines each) | A generic `OpenAICompatibleProvider` base class would eliminate duplication |
| Some components bypass `apiClient` | `InventoryPanel`, `SpellSlotsDisplay`, `ActiveEffectsDisplay` use raw `fetch()` | Miss auth refresh, CSRF, and language header injection |
| Grafana default credentials | `admin/admin` hardcoded in docker-compose | Should use env vars or secrets |
| No Alertmanager | 15 alert rules exist but no notification channel configured | Prometheus alerts fire but aren't routed anywhere |
| Inconsistent logger usage | 20 files use `logging.getLogger` instead of structured `get_logger` | Should migrate to structured logging throughout |

---

## What Would Be Built Next

### High Priority
1. **Real SSE streaming**: Connect the existing `narrate_stream()` / `chat_completion_stream()` backend to an `EventSource` frontend — the infrastructure is partially there
2. **OpenAI-compatible provider base class**: Deduplicate Groq/Cerebras/Together/SambaNova into a single generic implementation
3. **DM Engine decomposition**: Extract message building, tool execution, supervisor validation, and streaming into separate classes
4. **Redis-backed rate limiting**: Replace in-memory `defaultdict(list)` with Redis sliding window for multi-instance support

### Medium Priority
5. **pgvector for all semantic search**: Migrate item/monster/spell search from in-memory similarity to pgvector indexes
6. **More comprehensive testing**: Integration tests for tool-calling loops, supervisor validation, provider fallback chains
7. **API client consistency**: Migrate all frontend components to use `apiClient` instead of raw `fetch()`
8. **WebSocket for real-time events**: Companion reactions, battle state, multi-player preparation

### Nice to Have
9. **Multi-player sessions**: Multiple characters in one session with turn-based narration
10. **Voice narration**: TTS for DM responses using Mistral or external service
11. **Campaign persistence**: Multi-session campaigns with world state tracking
12. **Mobile-responsive game UI**: Currently optimized for desktop

---

## Historical Document Accuracy Guide

For anyone reviewing the `docs/` folder, here is the accuracy status of each historical document:

| Document | Accuracy | Notes |
|----------|----------|-------|
| `OBSERVABILITY.md` | **Accurate** | Reflects actual Jaeger/Prometheus/Grafana setup |
| `TRUE_RANDOMNESS.md` | **Accurate** | Clear, well-documented |
| `contextflow.md` | **Accurate** | Excellent visualization of request pipeline |
| `SEMANTIC-SEARCH-REFACTORING.md` | **Accurate, completed** | All 6 steps done |
| `COMPREHENSIVE-AUDIT-JAN9-2026.md` | **Accurate (as audit)** | Thorough, correctly debunked FEATURE-INTEGRATION-AUDIT |
| `GAME_MECHANICS_OVERHAUL.md` | **Completed** | All 8 tickets (RL-124–131) done |
| `DM_ENGINE_AUDIT.md` | **Accurate (as audit)** | Phase 1 implemented, Phase 2 (semantic search) done via RL-144 |
| `PROVIDER_REWORK_PLAN_CORRECTED.md` | **Partially implemented** | Phase 5 (toggle) complete; phases 1-4, 6 have unchecked items |
| `ARCHITECTURE.md` | **Rewritten** (Feb 28, 2026) | Now current |
| `MISTRAL-INTEGRATION.md` | **Outdated** (Dec 31, 2025) | Missing tool calling, provider fallback, supervisor, agent API |
| `API.md` | **Outdated** | Shows old routes, "no authentication", missing v1 endpoints |
| `PROVIDER_REWORK_PLAN.md` | **Superseded** | Replaced by CORRECTED version (HuggingFace → Free Pool, Qwen daily→one-time) |
| `FEATURE-INTEGRATION-AUDIT.md` | **Inaccurate** | Proven wrong by COMPREHENSIVE-AUDIT: claimed Memory 40% (actual 85%), Save/Load 50% (actual 95%) |
| `VECTOR-MEMORY-INTEGRATION-ANALYSIS.md` | **Outdated** | Issues identified were fixed shortly after writing |
| `IMAGE-GENERATION-IMPLEMENTATION.md` | **Planning doc** | Implementation may differ from plan |

All `RL-*.md` ticket files and session summaries are preserved as the project diary — they document what was planned, decided, and implemented at each point in time.
