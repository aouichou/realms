# Mistral Realms - Technical Implementation Guide

**Version**: 1.0
**Date**: January 4, 2026
**Companion to**: GAME-DESIGN.md
**Purpose**: Technical specifications, prompts, schemas, implementation details

---

## 🏗️ System Architecture Overview

### Component Interaction

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Next.js    │─────▶│   FastAPI    │─────▶│  Mistral AI  │
│   Frontend   │◀─────│   Backend    │◀─────│   API        │
└──────────────┘      └──────────────┘      └──────────────┘
       │                      │
       │                      ├─────────────────────┐
       │                      │                     │
       ▼                      ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  localStorage│      │  PostgreSQL  │      │    Redis     │
│  (guest mode)│      │  (game state)│      │   (cache)    │
└──────────────┘      └──────────────┘      └──────────────┘
```

### Tech Stack

**Backend**:
- FastAPI 0.109+
- SQLAlchemy 2.0 (ORM)
- Alembic (migrations)
- PostgreSQL 15 + pgvector extension
- Redis 7 (caching + session storage)
- PyJWT (JWT tokens)
- bcrypt (password hashing)

**Frontend**:
- Next.js 16 (App Router)
- TypeScript 5.3
- TailwindCSS + shadcn/ui
- Server-Sent Events (SSE) for streaming

**AI/ML**:
- Mistral API (mistralai Python SDK)
- Text embeddings for vector search
- Pixtral for image generation

---

## 🔐 Authentication System (RL-56, RL-59)

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,  -- nullable for guest mode
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- nullable for guest mode
    is_guest BOOLEAN DEFAULT FALSE,
    guest_token VARCHAR(255) UNIQUE,  -- for guest mode
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Update existing tables
ALTER TABLE characters
    ADD CONSTRAINT fk_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE game_sessions
    ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Indexes
CREATE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_guest_token ON users(guest_token) WHERE guest_token IS NOT NULL;
CREATE INDEX idx_characters_user ON characters(user_id);
CREATE INDEX idx_sessions_user ON game_sessions(user_id);
```

### JWT Token Strategy

```python
# backend/app/services/auth.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Guest mode token
def create_guest_user(db: Session) -> User:
    guest_token = secrets.token_urlsafe(32)
    username = f"Guest_{secrets.token_hex(4)}"

    user = User(
        username=username,
        is_guest=True,
        guest_token=guest_token
    )
    db.add(user)
    db.commit()

    return user
```

### API Endpoints

```python
# POST /api/auth/register
@router.post("/register")
async def register(
    email: EmailStr,
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    # Check existing
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already registered")

    # Hash password
    hashed = pwd_context.hash(password)

    # Create user
    user = User(email=email, username=username, password_hash=hashed)
    db.add(user)
    db.commit()

    # Generate tokens
    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": user_schema(user)
    }

# POST /api/auth/guest
@router.post("/guest")
async def create_guest(db: Session = Depends(get_db)):
    user = create_guest_user(db)
    access = create_access_token({"sub": str(user.id), "guest": True})

    return {
        "access_token": access,
        "guest_token": user.guest_token,
        "user": user_schema(user)
    }

# POST /api/auth/claim-guest
@router.post("/claim-guest")
async def claim_guest_account(
    guest_token: str,
    email: EmailStr,
    password: str,
    db: Session = Depends(get_db)
):
    # Find guest user
    user = db.query(User).filter(User.guest_token == guest_token).first()
    if not user or not user.is_guest:
        raise HTTPException(404, "Guest account not found")

    # Convert to registered
    user.email = email
    user.password_hash = pwd_context.hash(password)
    user.is_guest = False
    user.guest_token = None
    db.commit()

    return {"message": "Account claimed successfully"}
```

### Frontend Auth Flow

```typescript
// frontend/lib/auth.ts
export const authService = {
  // Guest mode
  async createGuest() {
    const res = await fetch('/api/auth/guest', { method: 'POST' });
    const { access_token, guest_token, user } = await res.json();

    localStorage.setItem('access_token', access_token);
    localStorage.setItem('guest_token', guest_token);
    return user;
  },

  // Register
  async register(email: string, username: string, password: string) {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password })
    });

    const { access_token, refresh_token, user } = await res.json();
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    return user;
  },

  // Check if guest
  isGuest(): boolean {
    return !!localStorage.getItem('guest_token');
  },

  // Prompt to claim account
  shouldPromptClaim(): boolean {
    const guestCreated = localStorage.getItem('guest_created_at');
    if (!guestCreated) return false;

    const minutesPlayed = (Date.now() - parseInt(guestCreated)) / 60000;
    return minutesPlayed > 30; // After 30 min gameplay
  }
};
```

---

## 🤖 AI DM Master Prompt (Critical!)

### Base DM Prompt Template

```python
MASTER_DM_PROMPT = """You are the Dungeon Master for a D&D 5e adventure called "{adventure_title}".

CORE PRINCIPLES:
1. You NARRATE the world. You do NOT decide player actions.
2. Follow D&D 5e rules strictly. Call for ability checks when appropriate.
3. Balance encounters for level {character_level} (CR {cr_min}-{cr_max}).
4. Reference past events to maintain consistency: {recent_events}
5. Challenge the player - refuse impossible/unreasonable actions.
6. End EVERY response with "What do you do?" or similar.

CHARACTER:
Name: {character_name}
Race: {character_race} | Class: {character_class} | Level: {character_level}
Background: {character_background}
Personality: {personality_traits}
Ideal: {ideal}
Bond: {bond}
Flaw: {flaw}
Motivation: {motivation}

Current Status:
- HP: {current_hp}/{max_hp}
- Spell Slots: {spell_slots}
- Conditions: {active_conditions}
- Location: {current_location}

ADVENTURE CONTEXT:
{adventure_context}

Active Quests:
{quest_list}

NPCs Met:
{npc_list}

Party Members:
{companion_list}

Recent Events (last 3 important moments):
{memory_summary}

COMMUNICATION PROTOCOL:
- To request backend info: [DM_QUERY: your question]
  Example: [DM_QUERY: What's the DC for this lock according to adventure?]
  (Backend answers privately, user doesn't see this)

- When dice needed: "Roll {ability} ({skill}) check, DC {dc}"
  Example: "Roll Dexterity (Stealth) check, DC 15"

- For important scenes: [GENERATE_IMAGE: brief scene description]
  Example: [GENERATE_IMAGE: Dark cave entrance with goblin guards]

- To remember something: [REMEMBER: event]
  Example: [REMEMBER: Player spared goblin scout, learned about chieftain]

REFUSAL GUIDELINES:
When player attempts impossible/unreasonable actions:
- Explain why it won't work
- Offer alternatives
- Maintain immersion (don't break character)

Examples:
Player: "I seduce the dragon"
You: "The ancient dragon's eyes narrow. She's lived for centuries and seen
      countless mortals. Your charm holds no sway here. The air grows hot
      as she prepares to attack. What do you do?"

Player: "I cast Fireball" (doesn't know Fireball)
You: "You reach for the arcane formula for Fireball, but it's not among
      your known spells. Your prepared spells are: {spell_list}.
      Which spell do you cast instead?"

ENCOUNTER BALANCING:
- Easy fight: CR {character_level - 2}
- Medium fight: CR {character_level}
- Hard fight: CR {character_level + 2}
- Deadly: CR {character_level + 4} (use sparingly!)

Current scene: {scene_description}

Your narration:"""
```

### Dynamic Context Injection

```python
def build_dm_context(session: GameSession, character: Character) -> dict:
    """Build context dict for DM prompt"""

    # Get recent events from memory system
    recent_events = get_recent_memories(session.id, limit=3)

    # Get active quests
    active_quests = get_active_quests(character.id)
    quest_list = "\n".join([
        f"- {q.title}: {q.description} ({q.progress}/{q.objectives_total} objectives)"
        for q in active_quests
    ])

    # Get NPCs met
    npcs = get_session_npcs(session.id)
    npc_list = "\n".join([
        f"- {npc.name} ({npc.race} {npc.class_}): {npc.relationship}"
        for npc in npcs
    ])

    # Get companions
    companions = get_party_companions(session.id)
    companion_list = "\n".join([
        f"- {c.name} (HP: {c.current_hp}/{c.max_hp}, personality: {c.personality})"
        for c in companions
    ])

    # Adventure context
    if session.adventure_type == "preset":
        adventure_context = load_adventure_chapter(
            session.adventure_id,
            session.current_chapter
        )
    else:
        adventure_context = f"Custom adventure: {session.adventure_setup}"

    return {
        "adventure_title": session.adventure_title,
        "character_level": character.level,
        "cr_min": max(1, character.level - 2),
        "cr_max": character.level + 2,
        "character_name": character.name,
        "character_race": character.race,
        "character_class": character.class_,
        "character_background": character.background or "Unknown",
        "personality_traits": character.personality_traits or "Not defined",
        "ideal": character.ideal or "Unknown",
        "bond": character.bond or "Unknown",
        "flaw": character.flaw or "Unknown",
        "motivation": character.motivation or "Adventure",
        "current_hp": character.current_hp,
        "max_hp": character.max_hp,
        "spell_slots": format_spell_slots(character),
        "active_conditions": ", ".join(get_active_conditions(character.id)) or "None",
        "current_location": session.current_location or "Unknown",
        "adventure_context": adventure_context,
        "quest_list": quest_list or "None active",
        "npc_list": npc_list or "None yet",
        "companion_list": companion_list or "Traveling alone",
        "memory_summary": format_memories(recent_events),
        "scene_description": session.current_scene or "Beginning of adventure",
        "spell_list": format_known_spells(character),
        "recent_events": "; ".join([m.event for m in recent_events[:3]])
    }
```

### Hidden DM Query System (SYNC Implementation)

```python
async def process_dm_response_with_queries(
    dm_output: str,
    session_id: UUID,
    db: Session
) -> str:
    """Process [DM_QUERY] tags synchronously"""

    # Pattern: [DM_QUERY: question text]
    query_pattern = r'\[DM_QUERY:\s*([^\]]+)\]'

    while True:
        match = re.search(query_pattern, dm_output)
        if not match:
            break

        query_text = match.group(1).strip()

        # Answer query (this is the magic!)
        answer = await answer_dm_query(query_text, session_id, db)

        # Replace query with answer in DM context
        dm_output = dm_output.replace(
            match.group(0),
            f"[DM_ANSWER: {answer}]"
        )

    # Remove all [DM_ANSWER] tags before sending to user
    dm_output = re.sub(r'\[DM_ANSWER:[^\]]+\]', '', dm_output)

    return dm_output.strip()

async def answer_dm_query(query: str, session_id: UUID, db: Session) -> str:
    """Answer DM's hidden query"""

    # Example queries:
    # "Did player meet the mayor?"
    # "What's the DC for this lock?"
    # "How many goblins are in this room per adventure?"

    # Semantic search through memories
    if "did player" in query.lower() or "has player" in query.lower():
        memories = semantic_search_memories(session_id, query, top_k=3)
        return summarize_memories(memories)

    # Adventure-specific queries
    elif "according to adventure" in query.lower():
        adventure_data = load_adventure_data(session_id, db)
        return query_adventure_context(adventure_data, query)

    # Rule queries
    elif "dc" in query.lower() or "difficulty" in query.lower():
        return determine_dc_from_context(query)

    # Default: Search all available context
    else:
        context = gather_all_context(session_id, db)
        return f"Based on available context: {search_context(context, query)}"
```

### Output Streaming with Buffering ("Teleprompter Effect")

```python
async def stream_dm_response(prompt: str, context: dict):
    """Stream DM response with word-by-word buffering"""

    # Get full response from Mistral
    response = await mistral_client.chat_stream(
        model="mistral-small-latest",
        messages=[{"role": "system", "content": MASTER_DM_PROMPT.format(**context)},
                  {"role": "user", "content": prompt}]
    )

    buffer = []
    word_delay = 0.15  # 150ms per word (~400 WPM reading speed)

    async for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            words = delta.split()
            buffer.extend(words)

    # Now stream buffer with delay (while processing queries in background)
    full_text = " ".join(buffer)

    # Process queries in background (async)
    processed_text = await process_dm_response_with_queries(full_text, session_id, db)

    # Stream to user word-by-word
    words = processed_text.split()
    for word in words:
        yield word + " "
        await asyncio.sleep(word_delay)
```

---

## 🤝 AI Companion Prompt System

### Companion Personality Prompts

```python
COMPANION_PERSONALITIES = {
    "helpful": {
        "system_prompt": """You are {name}, a {personality} {race} {class} companion.

        Your personality: HELPFUL
        - Always suggest optimal strategies
        - Warn of dangers before they become critical
        - Offer tactical advice in combat
        - Explain game mechanics when useful
        - Prioritize party survival

        Current situation:
        - Player HP: {player_hp}/{player_max_hp}
        - Your HP: {companion_hp}/{companion_max_hp}
        - In combat: {in_combat}
        - Enemies: {enemies}
        - Location: {location}

        Respond in-character with helpful tactical advice.
        Keep responses under 50 words unless providing crucial information.""",

        "speech_patterns": [
            "I recommend...",
            "Watch out for...",
            "We should...",
            "Here's what I know about..."
        ]
    },

    "brave": {
        "system_prompt": """You are {name}, a {personality} {race} {class} companion.

        Your personality: BRAVE
        - Encourage heroic actions
        - Never suggest retreat
        - Celebrate combat victories
        - Mock cowardice (playfully)
        - Take risks

        Current situation:
        - Player HP: {player_hp}/{player_max_hp}
        - Your HP: {companion_hp}/{companion_max_hp}
        - In combat: {in_combat}
        - Enemies: {enemies}

        Respond with bravery and encourage bold action.
        Keep responses under 40 words.""",

        "speech_patterns": [
            "Let's charge!",
            "We can take them!",
            "A warrior never retreats!",
            "For glory!"
        ]
    },

    "cautious": {
        "system_prompt": """You are {name}, a {personality} {race} {class} companion.

        Your personality: CAUTIOUS
        - Prioritize survival over glory
        - Suggest retreat when outmatched
        - Warn about traps and dangers
        - Conserve resources
        - Plan before acting

        Current situation:
        - Player HP: {player_hp}/{player_max_hp} {'(LOW!)' if player_hp < player_max_hp * 0.3 else ''}
        - Enemies: {enemies} {'(OUTNUMBERED!)' if enemy_count > 2 else ''}

        Respond with caution and concern for safety.""",

        "speech_patterns": [
            "Wait, let's think about this...",
            "We're not ready for this",
            "Maybe we should rest first",
            "That looks dangerous"
        ]
    },

    "sarcastic": {
        "system_prompt": """You are {name}, a {personality} {race} {class} companion.

        Your personality: SARCASTIC
        - Make witty comments about situations
        - Use humor to lighten mood
        - Tease player (playfully)
        - Still provide useful info, but sarcastically

        Current situation:
        {situation}

        Respond with sarcasm and wit. Keep it fun, not mean.""",

        "speech_patterns": [
            "Oh great, more {enemies}...",
            "This can't possibly go wrong",
            "Brilliant plan",
            "What could go wrong?"
        ]
    },

    "mysterious": {
        "system_prompt": """You are {name}, a {personality} {race} {class} companion.

        Your personality: MYSTERIOUS
        - Speak in cryptic hints
        - Reference hidden knowledge
        - Have a secret agenda (don't reveal fully)
        - Know more than you say

        Current situation:
        {situation}

        Respond mysteriously. Hint at deeper knowledge.""",

        "speech_patterns": [
            "This place... I've seen it before",
            "The darkness watches",
            "I sense something...",
            "Not everything is as it seems"
        ]
    },

    "scholarly": {
        "system_prompt": """You are {name}, a {personality} {race} {class} companion.

        Your personality: SCHOLARLY
        - Provide lore and history
        - Identify monsters with detail
        - Explain magic and artifacts
        - Reference books and studies

        Current situation:
        {situation}

        Respond with academic knowledge and explanations.""",

        "speech_patterns": [
            "According to ancient texts...",
            "That's a {monster} - they're known for...",
            "Interesting! The runes suggest...",
            "I've read about this"
        ]
    }
}
```

### When Companion Should Speak

```python
def should_companion_speak(
    game_state: dict,
    last_companion_message_turns_ago: int
) -> tuple[bool, str]:
    """Determine if companion should auto-speak"""

    # Critical situations (always speak)
    if game_state["player_hp"] < game_state["player_max_hp"] * 0.2:
        return True, "concern_low_hp"

    if game_state["combat_started_this_turn"]:
        return True, "combat_start"

    if game_state["trap_detected"]:
        return True, "warning"

    if game_state["puzzle_present"]:
        return True, "hint"

    # Frequency limit (don't be annoying)
    if last_companion_message_turns_ago < 3:
        return False, None

    # Random commentary (20% chance)
    if random.random() < 0.2:
        return True, "commentary"

    return False, None
```

---

## 🖼️ Image Generation System

### Pixtral Prompt Engineering

```python
async def generate_scene_image(
    scene_description: str,
    character: Character,
    mood: str = "dramatic"
) -> str:
    """Generate D&D scene image with Mistral Pixtral"""

    # Enhanced prompt for quality
    prompt = f"""A high-quality digital painting for a Dungeons & Dragons 5th Edition adventure.

Scene: {scene_description}

Include in the scene:
- A {character.race} {character.class_} as the main hero/protagonist
- {character.equipment_description}

Art style requirements:
- Official D&D 5e artwork aesthetic
- {mood} lighting and atmosphere
- Highly detailed medieval fantasy setting
- Cinematic third-person perspective
- Professional fantasy illustration quality
- Rich colors and textures

Mood: {mood}
Exclude: Text, logos, watermarks, modern elements, UI elements

Create an immersive scene that captures the essence of D&D adventure."""

    # Check cache first (scene hash)
    scene_hash = hashlib.md5(scene_description.encode()).hexdigest()
    cached_url = await redis.get(f"scene:image:{scene_hash}")

    if cached_url:
        logger.info(f"Cache hit for scene {scene_hash}")
        return cached_url

    # Generate new image
    response = await mistral_client.images.generate(
        model="pixtral-12b-2409",
        prompt=prompt,
        size="1024x1024"
    )

    image_url = response.data[0].url

    # Cache for 24 hours
    await redis.setex(f"scene:image:{scene_hash}", 86400, image_url)

    return image_url
```

### Scene Detection & Auto-Generation

```python
def detect_image_triggers(dm_message: str, game_state: dict) -> list[str]:
    """Detect when to auto-generate images"""

    triggers = []

    # Location change
    if "[SCENE_START:" in dm_message or "you enter" in dm_message.lower():
        triggers.append("location_change")

    # Combat start
    if game_state.get("combat_just_started"):
        triggers.append("combat_start")

    # NPC introduction
    if "appears" in dm_message.lower() or "steps forward" in dm_message.lower():
        triggers.append("npc_introduction")

    # Boss encounter
    if "roars" in dm_message.lower() or "emerges" in dm_message.lower():
        triggers.append("boss_encounter")

    # Explicit tag
    if "[GENERATE_IMAGE:" in dm_message:
        triggers.append("explicit_request")

    return triggers
```

---

## 🧠 Vector Memory System (PostgreSQL + pgvector)

### Database Schema

```sql
-- Install extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Memory table
CREATE TABLE adventure_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT NOW(),
    event TEXT NOT NULL,  -- Human-readable event
    importance INT CHECK (importance BETWEEN 1 AND 10),
    tags TEXT[],  -- ['combat', 'npc', 'quest', etc.]
    embedding vector(1536),  -- Mistral embedding dimension

    -- Metadata
    character_level INT,
    location VARCHAR(255),
    npcs_involved TEXT[],
    items_involved TEXT[]
);

-- Indexes
CREATE INDEX idx_memories_session ON adventure_memories(session_id);
CREATE INDEX idx_memories_importance ON adventure_memories(importance DESC);
CREATE INDEX idx_memories_timestamp ON adventure_memories(timestamp DESC);
CREATE INDEX idx_memories_tags ON adventure_memories USING GIN(tags);

-- Vector index (IVFFlat for speed)
CREATE INDEX idx_memories_embedding
    ON adventure_memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### Embedding & Storage

```python
async def store_memory(
    session_id: UUID,
    event: str,
    importance: int,
    tags: list[str],
    db: Session
):
    """Store event with embedding"""

    # Generate embedding
    embedding = await mistral_client.embeddings.create(
        model="mistral-embed",
        input=[event]
    )
    embedding_vector = embedding.data[0].embedding

    # Get current game state
    session = db.query(GameSession).get(session_id)

    # Store
    memory = AdventureMemory(
        session_id=session_id,
        event=event,
        importance=importance,
        tags=tags,
        embedding=embedding_vector,
        character_level=session.character.level,
        location=session.current_location
    )

    db.add(memory)
    db.commit()

async def semantic_search_memories(
    session_id: UUID,
    query: str,
    top_k: int = 5,
    min_importance: int = 5,
    db: Session
) -> list[AdventureMemory]:
    """Search memories by semantic similarity"""

    # Generate query embedding
    query_embedding = await mistral_client.embeddings.create(
        model="mistral-embed",
        input=[query]
    )
    query_vector = query_embedding.data[0].embedding

    # Vector search with filters
    results = db.execute(text("""
        SELECT id, event, importance, tags,
               1 - (embedding <=> :query_vector) as similarity
        FROM adventure_memories
        WHERE session_id = :session_id
          AND importance >= :min_importance
        ORDER BY embedding <=> :query_vector
        LIMIT :top_k
    """), {
        "query_vector": str(query_vector),
        "session_id": str(session_id),
        "min_importance": min_importance,
        "top_k": top_k
    }).fetchall()

    return [db.query(AdventureMemory).get(row.id) for row in results]
```

### Auto-Summarization

```python
async def auto_summarize_recent_messages(
    session_id: UUID,
    db: Session
):
    """Background job: summarize every 10 messages"""

    # Get last 10 unsummarized messages
    messages = get_recent_messages(session_id, limit=10)

    if len(messages) < 10:
        return

    # Summarize with AI
    summary_prompt = f"""Summarize these D&D game events in 2-3 sentences:

{chr(10).join([f"- {m.content}" for m in messages])}

Focus on: important decisions, combat outcomes, NPCs met, items found, locations visited."""

    response = await mistral_client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": summary_prompt}]
    )

    summary = response.choices[0].message.content

    # Determine importance
    importance = calculate_importance(summary, messages)

    # Extract tags
    tags = extract_tags(summary)

    # Store memory
    await store_memory(
        session_id=session_id,
        event=summary,
        importance=importance,
        tags=tags,
        db=db
    )

    # Mark messages as summarized
    mark_messages_summarized(messages)
```

---

## 💾 Save/Load System (RL-57)

### Database Schema

```sql
CREATE TABLE game_saves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES game_sessions(id),
    character_id UUID NOT NULL REFERENCES characters(id),

    -- Save metadata
    save_name VARCHAR(255),  -- Optional user-provided name
    save_type VARCHAR(20) CHECK (save_type IN ('manual', 'auto', 'checkpoint')),
    created_at TIMESTAMP DEFAULT NOW(),

    -- Game state snapshot (JSONB for flexibility)
    game_state JSONB NOT NULL,

    -- Quick info for display
    character_name VARCHAR(100),
    character_level INT,
    current_location VARCHAR(255),
    playtime_minutes INT,

    -- Image for save slot (optional)
    thumbnail_url VARCHAR(500)
);

CREATE INDEX idx_saves_user ON game_saves(user_id, created_at DESC);
CREATE INDEX idx_saves_session ON game_saves(session_id);
```

### Save State Structure

```python
def create_save_state(session: GameSession, character: Character) -> dict:
    """Capture complete game state"""

    return {
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat(),

        # Character state
        "character": {
            "hp": character.current_hp,
            "spell_slots": character.spell_slots_remaining,
            "inventory": [item.to_dict() for item in character.inventory],
            "equipped": character.equipped_items,
            "conditions": [c.condition_type for c in character.active_conditions],
            "xp": character.xp,
            "gold": character.gold
        },

        # Session state
        "session": {
            "current_location": session.current_location,
            "current_scene": session.current_scene,
            "current_chapter": session.current_chapter,
            "adventure_type": session.adventure_type,
            "adventure_id": session.adventure_id
        },

        # Combat state (if in combat)
        "combat": get_combat_state(session.id) if session.in_combat else None,

        # Quests
        "quests": [
            {
                "id": str(q.id),
                "title": q.title,
                "progress": q.progress,
                "objectives": q.objectives
            }
            for q in get_active_quests(character.id)
        ],

        # NPCs & Companions
        "npcs": [npc.to_dict() for npc in get_session_npcs(session.id)],
        "companions": [c.to_dict() for c in get_party_companions(session.id)],

        # Conversation history (last 20 messages)
        "conversation": [
            {"role": m.role, "content": m.content}
            for m in get_recent_messages(session.id, limit=20)
        ],

        # Important memories
        "key_memories": [
            m.event for m in get_important_memories(session.id, min_importance=8)
        ]
    }
```

### Auto-Save Implementation

```python
# Background task
@scheduler.scheduled_job('interval', minutes=5)
async def auto_save_all_active_sessions():
    """Auto-save every 5 minutes"""

    active_sessions = db.query(GameSession).filter(
        GameSession.status == "active",
        GameSession.last_activity > datetime.utcnow() - timedelta(minutes=10)
    ).all()

    for session in active_sessions:
        try:
            await create_save(
                session=session,
                save_type="auto",
                save_name=f"Auto-save {datetime.now().strftime('%H:%M')}"
            )
            logger.info(f"Auto-saved session {session.id}")
        except Exception as e:
            logger.error(f"Auto-save failed for {session.id}: {e}")
```

---

## 📊 Implementation Tickets Updated

### Day 5 Ticket Breakdown (Revised)

Based on design decisions, here's the updated implementation plan:

**RL-56 (8 pts): User Authentication Backend**
- Users table migration
- JWT token creation/validation
- Guest mode support
- Password hashing (bcrypt)
- Protected route middleware

**RL-59 (3 pts): Authentication UI**
- Login/Register pages
- Guest mode button
- Protected routes wrapper
- Token management
- "Claim account" modal

**RL-57 (5 pts): Save/Load System**
- game_saves table
- Save state serialization
- Auto-save background job
- Load game restoration
- Save slot UI

**RL-48 (8 pts): Spell Database**
- 657 spells JSON → database
- Spell seeder script
- Spell filtering API
- Class associations
- Search functionality

**RL-54 (8 pts): AI Companion**
- Companion personality system
- Companion prompts (6 personalities)
- Speech trigger logic
- Companion API endpoints
- Basic companion UI

**RL-55 (8 pts): Image Generation**
- Pixtral integration
- Scene detection system
- Image caching (Redis)
- Prompt engineering
- Image display UI

**RL-53 (4 pts): ARCHITECTURE.md**
- System diagrams
- Component architecture
- Database schema docs
- API documentation
- Deployment architecture

**RL-58 (3 pts): GAME-DESIGN.md**
- ✅ Already complete!

**NEW (Not Ticketed Yet - Day 6)**:
- Character creation: Background/Personality steps (3 pts)
- Adventure selection UI (3 pts)
- Goblin Ambush preset adventure data (2 pts)
- Vector memory system (8 pts)
- Hidden DM query system (3 pts)
- Spell selection UI polish (RL-51 - 5 pts)

---

## ✅ Next Actions

1. ✅ GAME-DESIGN.md created
2. ✅ GAME-DESIGN-TECHNICAL.md created
3. 🔄 Create Day 6 tickets for new features
4. 🔄 Begin RL-48 implementation (spell database)
5. 🔄 Run ./update-day5-tickets.sh to create Jira tickets

---

*End of Technical Implementation Guide*
