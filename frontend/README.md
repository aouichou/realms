# Mistral Realms — Frontend

Next.js 16 + React 19 game client with typewriter narration, D&D character management, AI companion chat, scene image display, and bilingual (EN/FR) support.

---

## Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 16.1.6 | App Router framework with SSR and standalone output |
| **React** | 19.2.3 | UI library (React Compiler enabled) |
| **TypeScript** | 5.x | Type system |
| **Tailwind CSS** | 4.x | Utility-first styling |
| **TanStack React Query** | 5.90 | Server state (used selectively) |
| **Radix UI** | 1-2.x | 17 accessible primitives (checkbox, select, tabs, dialog, etc.) |
| **class-variance-authority** | 0.7 | Component variant styling |
| **lucide-react** | 0.562 | Icon library |
| **react-markdown** | 9.0 | Markdown rendering in chat messages |
| **tw-animate-css** | 1.4 | Animation utilities |
| **Turbopack** | Built-in | Next.js bundler (enabled) |
| **Google Fonts** | — | UnifrakturMaguntia + Cinzel (D&D typography) |

---

## Simulated Streaming

The game interface does **not** use SSE/EventSource. Instead, it uses a request-response model with client-side animation:

1. Player submits action → `POST /api/v1/conversations/action`
2. "DM is thinking..." indicator shown (animated bouncing purple dots)
3. Full JSON response received (narration, tool calls, images, state updates)
4. **TypewriterText component** reveals the narration character-by-character at ~120 chars/sec
5. Click anywhere to skip the animation and show full text instantly

This creates an immersive "streaming" feel without WebSocket/SSE complexity.

---

## Component Architecture

### D&D Game Components

| Component | Purpose |
|-----------|---------|
| **ChatMessage** | Renders user/assistant/companion messages with Markdown, typewriter effect, scene images, NPC roll results, and tool call badges |
| **CompanionMessage** | Companion speech bubbles with avatar, relationship status (color-coded ring), loyalty %, HP bar |
| **EnhancedCharacterSheet** | Full D&D character sheet: 6 ability scores + modifiers, AC, initiative, attack bonuses, spell save DC, skills, proficiencies |
| **AbilityCheckPanel** | All 18 D&D 5e skills organized by ability, advantage/disadvantage toggles, DC input, roll API integration |
| **SpellsPanel** | Full spell management: browse/filter/cast, track spell slots, prepare spells, concentration tracking |
| **SpellSelectionStep** | Character creation spell picker with class-specific rules (known vs prepared casters, cantrip counts) |
| **InventoryPanel** | Grid/list view inventory with equip/unequip, weight tracking, carrying capacity, type filtering |
| **CompanionListPanel** | Manage AI companions: toggle active, private chat, share with DM toggle, loyalty/relationship tracking |
| **ToolCallBadge** | Shows which AI tool calls the DM invoked (roll request, HP update, spell slot, creature stats) |
| **NPCRollResult** | Animated NPC roll results with critical hit/fail badges, color-coded by roll type |
| **QuestCompleteModal** | Celebratory quest completion overlay with XP/gold/item reward display |
| **SpellWarning / SpellWarningContainer** | Slide-in toast notifications for spell validation feedback |
| **ActiveEffectsDisplay** | Buffs/debuffs/conditions with duration tracking (rounds, rest, concentration). Polls every 10s |
| **SceneImage** | AI-generated scene images with loading skeleton, fullscreen dialog, fade-in gradient overlay |
| **ImageGalleryPanel** | Scrollable gallery of all scene images from the session |
| **TypewriterText** | Character-by-character reveal animation for DM narration (~120 chars/sec, click-to-skip) |
| **CustomAdventureWizard** | 3-step wizard: Setting → Goal → Tone, then AI generates a custom adventure |
| **AdventurePreview** | Preview AI-generated adventure with scenes, NPCs, loot items before starting |
| **SaveGameButton / SaveGameModal / SaveSlotsModal** | Manual save + load system with slot management |

### Infrastructure Components

| Component | Purpose |
|-----------|---------|
| **ErrorBoundary** | Class-based error boundary with themed D&D error page ("The mystical forces have been disrupted") |
| **QueryProvider** | TanStack Query client (10-min cache, 1 retry, no refetch-on-focus) |
| **AppHeader** | Sticky header with brand, language selector, user info, logout |
| **LanguageSelector** | EN/FR toggle persisting to localStorage, dispatching custom `languageChange` event |

### UI Primitives (17 Radix-based)
alert, badge, button, card, checkbox, dialog, input, label, loading-spinner, progress, scroll-area, select, separator, switch, tabs, textarea, toast — styled via `class-variance-authority` + `tailwind-merge`.

---

## Game State Management

No global state library (no Redux, Zustand, or Jotai). The architecture is:

| State Type | Location | Mechanism |
|-----------|----------|-----------|
| **Auth** | Global | React Context (`AuthProvider`) — user, tokens, login/logout/register/guest |
| **Game session** | Page-level | Game page manages all state via `useState`: messages, character, sessionId, panels, dice, rolls, quests, spells |
| **Character data** | Server-authoritative | Fetched via API on mount, updated locally when tool calls report changes |
| **Language** | localStorage | `dm_language` key, custom events + `useTranslation` hook |
| **Selected character** | localStorage | `selected_character_id` passed between pages |
| **Server data** | TanStack Query | Used in `AbilityCheckPanel` (`useQuery`), most API calls are manual `apiClient` with local `useState` |

**Auto-save**: Timer saves game state every 5 minutes.
**Roll queue**: Sequential processing of multiple DM-requested rolls.

---

## User Journey

```
Landing Page (/)
  ├── Login (/auth/login) → Character Select
  ├── Register (/auth/register) → Character Create
  └── Demo (/demo)
         ├── Instant Demo → auto-creates guest + fighter + starts Goblin Ambush → Game
         └── Custom Hero → auto-creates guest → Character Create

Character Create (/character/create) — 6-step wizard:
  1. Name, race (9), class (12), level, ability scores (27-point buy)
  2. Skill proficiencies
  3. Background (13 D&D 5e backgrounds)
  4. Personality traits, ideal, bond, flaw
  5. Spell selection (spellcasters only)
  6. Motivation
  → Adventure Selection

Character Select (/character/select)
  → View characters, delete, or select → Adventure Selection
  → "Load Game" from saved slots

Adventure Selection (/adventure/select/[characterId])
  Tab "Preset": Pick from server adventures → Start → Game
  Tab "Custom": 3-step AI wizard (Setting → Goal → Tone)
    → Preview (NPCs, scenes, loot) → Start → Game

Game (/game/[characterId]?session=xxx)
  → "Start Session" → DM opening narration
  → Chat loop: type action → DM responds → rolls → companion responses
  → Side panels: Stats, Inventory, Dice, Spells, Checks, Companion, Images
  → Auto-save every 5 min, manual save available
```

---

## Routes

| Route | File | Description |
|-------|------|-------------|
| `/` | `app/page.tsx` | Landing page (redirects to `/character/select` if authenticated) |
| `/auth/login` | `app/auth/login/page.tsx` | Login form + guest mode |
| `/auth/register` | `app/auth/register/page.tsx` | Registration form |
| `/demo` | `app/demo/page.tsx` | Demo landing (instant play + custom character) |
| `/character/create` | `app/character/create/page.tsx` | 6-step character creation wizard |
| `/character/select` | `app/character/select/page.tsx` | Character list with play/delete + load saved |
| `/adventure/select/[id]` | `app/adventure/select/[characterId]/page.tsx` | Adventure selection (preset + custom AI wizard) |
| `/game/[characterId]` | `app/game/[characterId]/page.tsx` | Main game interface (1,153 lines) |

---

## UX Patterns

1. **Typewriter narration**: DM text appears character-by-character at 120 chars/sec with blinking cursor. Click anywhere to skip. Creates tabletop immersion.

2. **Scene background overlay**: Most recent AI-generated scene image becomes a full-screen background at 60% opacity behind the chat.

3. **DM Roll Request cards**: When the AI requests a player roll, an amber-highlighted prompt card appears above the input with a "Roll Now" button. Rolls are queued sequentially.

4. **Companion private chat**: In-sidebar conversation with AI companions, "share with DM" toggle for roleplay privacy.

5. **Tool call transparency**: Badges showing which AI tools were used per response (HP Update, Spell Slot, Creature Stats) — demonstrates AI capabilities.

6. **"DM is thinking..."**: Three bouncing purple dots with staggered animation delays.

7. **Quest completion ceremony**: Full-screen modal with XP, gold, and item rewards.

8. **Visual identity**: "Modern Grimoire" — UnifrakturMaguntia + Cinzel fonts, Elder Scroll color palette, glass morphism (`backdrop-blur-md`), D&D-themed error pages.

---

## i18n

Custom implementation (no library):

- **Languages**: English (`en`) and French (`fr`)
- **`useTranslation()` hook**: Returns `{ t, language, setLanguage }`. `t("key.path")` does dot-notation lookup on an inline translation object (1,173 lines).
- **Persistence**: `localStorage("dm_language")`, defaults to `en`
- **Live switching**: `LanguageSelector` dispatches `CustomEvent("languageChange")` on `window`; `useTranslation` listens for it
- **Backend integration**: `apiClient` sends `Accept-Language` header with every request — the AI DM responds in the selected language
- **Coverage**: Complete — home, auth, demo, character creation (all steps), game UI (all panels), adventure selection, save/load

---

## API Client

The API client (`lib/api-client.ts`) implements:

1. **httpOnly cookie auth**: All requests use `credentials: 'include'`. No `Authorization` header — tokens in httpOnly cookies.

2. **Token refresh with request queuing**: On 401, enters "refresh mode" — subsequent requests queued in a `failedQueue[]` promise array. After `authService.refreshToken()` completes, all queued requests retry. Prevents thundering herd on concurrent 401s.

3. **CSRF Double-Submit Cookie**: State-changing requests (POST/PUT/PATCH/DELETE) include `X-CSRF-Token` header read from cookies. Auth endpoints exempted.

4. **Language injection**: Every request includes `Accept-Language` from `localStorage("dm_language")`.

5. **JWT expiry monitoring**: 60-second interval decodes JWT payload client-side to proactively refresh 5 minutes before expiry.

6. **Guest flow**: `createGuest()` → `claimGuest(email, password)` conversion after 30 minutes of play.

---

## Running

### Docker
```bash
docker-compose up --build
# Frontend at http://localhost:3000
```

### Local Development
```bash
cd frontend
npm install
npm run dev
# Requires backend running at http://localhost:8000
```

### Build
```bash
npm run build     # Next.js standalone output
npm run start     # Production server
npm run lint      # ESLint
```

### Docker Build (3-stage)
1. **deps**: `npm ci --only=production`
2. **builder**: Full `npm ci` + `npm run build` (standalone output)
3. **runner**: `node:20-alpine`, non-root `nextjs` user (UID 1001), `node server.js`
