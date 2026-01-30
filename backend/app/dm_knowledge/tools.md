# DM Tools Reference Guide

## Tool Usage Philosophy

**Golden Rule**: When in doubt about whether the system can handle something, there's probably a tool for it. Use tools for game mechanics, save narration for storytelling.

## Tool Categories

### 1. Dice Rolling Tools
### 2. Character State Tools
### 3. Content Database Tools
### 4. Companion Tools
### 5. Utility Tools

---

## 1. DICE ROLLING TOOLS

### request_player_roll

**Purpose**: Request ANY dice roll from the player

**When to Use**:
- ✅ Player attacks in combat
- ✅ Player ability checks (Stealth, Perception, Athletics, etc.)
- ✅ Player saving throws (vs spells, traps, effects)
- ✅ Player damage rolls
- ✅ Initiative rolls for player

**Parameters**:
- `roll_type`: "attack", "ability_check", "saving_throw", "damage"
- `ability_or_skill`: "STR", "DEX", "Stealth", "Perception", "melee", "ranged", etc.
- `dc`: Difficulty Class (optional, for checks and saves)
- `advantage`: true/false (optional)
- `disadvantage`: true/false (optional)
- `description`: Brief context (optional but helpful)

**Examples**:
```python
# Attack roll
request_player_roll(
    roll_type="attack",
    ability_or_skill="melee",
    description="longsword attack"
)

# Ability check
request_player_roll(
    roll_type="ability_check",
    ability_or_skill="Stealth",
    dc=15,
    description="sneaking past guards"
)

# Saving throw
request_player_roll(
    roll_type="saving_throw",
    ability_or_skill="DEX",
    dc=13,
    description="dodging fireball"
)

# With advantage
request_player_roll(
    roll_type="ability_check",
    ability_or_skill="Perception",
    dc=10,
    advantage=true,
    description="searching well-lit room"
)
```

**Common Mistakes**:
- ❌ Narrating "You roll 18 and hit" instead of calling tool
- ❌ Saying "Make a Stealth check" without using tool (unreliable detection)
- ❌ Forgetting to specify DC for checks and saves

---

### roll_for_npc

**Purpose**: Roll dice for NPCs, monsters, and enemies

**When to Use**:
- ✅ ANY NPC/monster attack roll
- ✅ ANY NPC/monster damage roll
- ✅ NPC/monster saving throws
- ✅ NPC/monster ability checks
- ✅ Initiative rolls for NPCs/monsters

**Parameters**:
- `npc_name`: Name of the NPC/monster (e.g., "Goblin", "Guard Captain")
- `roll_type`: "attack", "damage", "saving_throw", "ability_check", "initiative"
- `dice_expression`: Dice notation (e.g., "d20+4", "2d6+3", "d20")
- `target_name`: Target of the action (optional, for attacks)
- `context`: Brief description (optional but helpful)

**Examples**:
```python
# Monster attack
roll_for_npc(
    npc_name="Goblin",
    roll_type="attack",
    dice_expression="d20+4",
    target_name="player",
    context="scimitar attack"
)

# Monster damage
roll_for_npc(
    npc_name="Goblin",
    roll_type="damage",
    dice_expression="1d6+2",
    context="scimitar damage"
)

# Monster saving throw
roll_for_npc(
    npc_name="Bandit",
    roll_type="saving_throw",
    dice_expression="d20+1",
    context="DEX save vs spell"
)

# Initiative
roll_for_npc(
    npc_name="Guard",
    roll_type="initiative",
    dice_expression="d20+2"
)
```

**Critical Rule**: NEVER narrate NPC roll results. ALWAYS use this tool.

**Common Mistakes**:
- ❌ "The goblin attacks and hits you for 8 damage" (missing both attack and damage rolls)
- ❌ "The guard rolls a 15 on Perception" (narrated instead of rolled)
- ❌ Using this for player rolls (use request_player_roll instead)

---

## 2. CHARACTER STATE TOOLS

### update_character_hp

**Purpose**: Modify character hit points

**When to Use**:
- ✅ IMMEDIATELY after any damage (combat, falling, traps, poison)
- ✅ IMMEDIATELY after any healing (potions, spells, rest)
- ✅ Every single HP change, no exceptions

**Parameters**:
- `amount`: Integer (negative for damage, positive for healing)
- `damage_type`: "slashing", "piercing", "bludgeoning", "fire", "cold", "lightning", "acid", "poison", "necrotic", "radiant", "force", "psychic", "thunder"
- `reason`: Brief explanation (optional but helpful for logs)

**Examples**:
```python
# Damage from combat
update_character_hp(
    amount=-8,
    damage_type="slashing",
    reason="goblin scimitar attack"
)

# Healing from potion
update_character_hp(
    amount=8,
    reason="healing potion"
)

# Fire damage from spell
update_character_hp(
    amount=-12,
    damage_type="fire",
    reason="enemy Fireball"
)

# Fall damage
update_character_hp(
    amount=-10,
    damage_type="bludgeoning",
    reason="fell 20 feet"
)
```

**Common Mistakes**:
- ❌ Mentioning damage in narration without calling this tool
- ❌ "You take 5 damage" - call the tool!
- ❌ Calling tool with positive number for damage (should be negative)
- ❌ Forgetting to call after healing

---

### consume_spell_slot

**Purpose**: Manually consume a spell slot

**When to Use**:
- ⚠️ RARELY needed (auto-detection usually works)
- Use only if slot tracking seems incorrect
- Override when player casts leveled spell

**Parameters**:
- `spell_level`: 1-9 (not 0 for cantrips)
- `spell_name`: Name of spell being cast

**Example**:
```python
consume_spell_slot(
    spell_level=3,
    spell_name="Fireball"
)
```

**Note**: System usually handles this automatically. Only use for manual override.

---

## 3. CONTENT DATABASE TOOLS

### get_creature_stats

**Purpose**: Retrieve full stat block for monsters/NPCs

**When to Use**:
- ✅ BEFORE combat encounters (very important!)
- ✅ When player asks about creature
- ✅ When you need accurate AC, HP, attacks, abilities

**Parameters**:
- `creature_name`: Name of creature (e.g., "Goblin", "Ancient Red Dragon", "Guard")
- `creature_type`: "monster", "npc", or "companion" (optional)

**Examples**:
```python
# Before combat
get_creature_stats(creature_name="Goblin")

# Complex creature
get_creature_stats(creature_name="Ancient Red Dragon")

# NPC
get_creature_stats(
    creature_name="Guard",
    creature_type="npc"
)
```

**Returns**: AC, HP, attacks with bonuses, damage dice, abilities, resistances, immunities

**Common Mistakes**:
- ❌ Starting combat without calling this
- ❌ Guessing creature stats instead of looking them up
- ❌ Using old stats from memory instead of fresh lookup

---

### search_items

**Purpose**: Search the 14,351-item catalog

**When to Use**:
- ✅ BEFORE giving loot (to see what's available)
- ✅ When player asks about available items
- ✅ When determining appropriate treasure
- ✅ Planning reward options

**Parameters**:
- `query`: Search term (e.g., "sword", "healing", "armor")
- `category`: "weapon", "armor", "shield", "potion", "scroll", "wondrous_item", "general" (optional)
- `rarity`: "common", "uncommon", "rare", "very rare", "legendary", "artifact" (optional)
- `limit`: Max results (default 10, max 50)

**Examples**:
```python
# Find healing items
search_items(
    query="healing",
    category="potion",
    limit=5
)

# Find rare swords
search_items(
    query="sword",
    category="weapon",
    rarity="rare"
)

# General magic item search
search_items(
    query="magic",
    rarity="uncommon",
    limit=10
)
```

**Workflow**: search_items → review options → give_item

---

### give_item

**Purpose**: Award items from catalog to player inventory

**When to Use**:
- ✅ Loot from defeated enemies
- ✅ Quest rewards
- ✅ Treasure chest contents
- ✅ Shop purchases
- ✅ Found items

**Parameters**:
- `item_name`: Name of item (fuzzy matching supported)
- `quantity`: Number of items (default 1)
- `reason`: Why item is being given (optional but helpful)

**Examples**:
```python
# Single item
give_item(
    item_name="Healing Potion",
    reason="found in bandit camp"
)

# Multiple items
give_item(
    item_name="Arrow",
    quantity=20,
    reason="purchased from merchant"
)

# Fuzzy matching works
give_item(
    item_name="heal pot",  # finds "Healing Potion"
    quantity=3,
    reason="treasure chest loot"
)
```

**Best Practice**: Use search_items first to find appropriate items, then give_item

**Common Mistakes**:
- ❌ Giving items without using tool (they won't appear in inventory)
- ❌ Not using search_items first to verify item exists
- ❌ Giving non-existent items

---

### search_memories

**Purpose**: Recall past adventure events semantically

**When to Use**:
- ✅ When you need to remember something from earlier
- ✅ Player references past event ("Remember the dragon?")
- ✅ Checking if NPC was encountered before
- ✅ Verifying plot continuity

**Parameters**:
- `query`: What to search for (e.g., "dragon encounter", "tavern keeper", "magic sword")
- `limit`: Max results (default 5, max 10)

**Examples**:
```python
# Recall specific event
search_memories(
    query="dragon encounter",
    limit=5
)

# Find NPC interaction
search_memories(
    query="innkeeper conversation"
)

# Plot point
search_memories(
    query="mysterious artifact"
)
```

**Use Case**: Maintains plot continuity, prevents DM from forgetting important details

---

## 4. COMPANION TOOLS

### introduce_companion

**Purpose**: Create AI-driven companion NPC

**When to Use**:
- ✅ Story calls for ally/guide
- ✅ Player needs assistance
- ✅ Natural story moment (rescue, hire, meet)

**Parameters**:
- `name`: Unique companion name
- `creature_name`: Base creature from database (for stats)
- `personality`: Character traits (e.g., "brave, loyal, witty")
- `goals`: Personal motivations
- `relationship_status`: "just_met", "ally", "friend", "trusted", "suspicious"
- `background`: Brief backstory (optional)

**Example**:
```python
introduce_companion(
    name="Elara Swiftwind",
    creature_name="Elf Scout",
    personality="brave, loyal, protective",
    goals="Find her missing brother",
    relationship_status="ally",
    background="Former royal guard tracking bandits"
)
```

---

### companion_suggest_action

**Purpose**: Companion offers tactical advice

**When to Use** (2-3 times per session):
- ⚔️ Combat: Every 2-3 rounds
- 🗺️ Exploration: Companion notices something
- 💬 Social: Insight on NPC reaction
- 🚪 Decisions: Perspective on choices

**Parameters**:
- `companion_name`: Name of companion
- `suggestion`: The tactical advice
- `reason`: Why they're suggesting this (optional)
- `urgency`: "low", "moderate", "high", "critical"

**Example**:
```python
companion_suggest_action(
    companion_name="Elara Swiftwind",
    suggestion="I could flank from the left while you engage from the front",
    reason="based on my scouting training",
    urgency="moderate"
)
```

---

### companion_share_knowledge

**Purpose**: Companion shares lore/information

**When to Use** (2-3 times per session):
- 🏛️ New location: Local history
- 👹 Monster appears: Creature weaknesses
- 🔮 Magic detected: Identifies effects
- 📜 Puzzle found: Relevant lore

**Parameters**:
- `companion_name`: Name of companion
- `topic`: What the knowledge is about
- `information`: The actual information (2-4 sentences)
- `source`: How they know this (optional)
- `reliability`: "certain", "confident", "uncertain", "rumor"

**Example**:
```python
companion_share_knowledge(
    companion_name="Elara Swiftwind",
    topic="goblin tactics",
    information="Goblins always post scouts on high ground. They'll have watchers in those ruins. They favor ambush over direct assault.",
    source="from my years hunting these creatures",
    reliability="certain"
)
```

---

## 5. UTILITY TOOLS

### list_available_tools

**Purpose**: Get reminder of all available tools

**When to Use**:
- When you're unsure what tools exist
- Need a quick reference

**Example**:
```python
list_available_tools()
```

---

## Tool Usage Priorities

### Every Combat:
1. **get_creature_stats** - First, always
2. **request_player_roll** - For all player actions
3. **roll_for_npc** - For all monster actions
4. **update_character_hp** - After every damage/healing

### Every Loot Distribution:
1. **search_items** - See what's available
2. **give_item** - Award chosen items

### Plot Continuity:
1. **search_memories** - When referencing past events

### Companion Interaction:
1. **companion_suggest_action** - 2-3 times per session
2. **companion_share_knowledge** - 2-3 times per session

---

## Red Flags - When You're Making Mistakes

If you find yourself:
- ❌ Saying specific numbers without calling tools ("You hit for 8")
- ❌ Mentioning damage without update_character_hp
- ❌ Starting combat without get_creature_stats
- ❌ Giving items without give_item
- ❌ Guessing creature stats

→ **STOP and use the appropriate tool!**

---

## Tool Call Cheat Sheet

```
PLAYER WANTS TO ATTACK?
→ request_player_roll(type="attack")
  → If hit: request_player_roll(type="damage")
    → update_character_hp(amount=-X)

MONSTER ATTACKS?
→ roll_for_npc(type="attack")
  → If hit: roll_for_npc(type="damage")
    → update_character_hp(amount=-X)

COMBAT STARTING?
→ get_creature_stats("Monster Name")

GIVING LOOT?
→ search_items(query="...")
  → give_item(item_name="...")

NEED TO REMEMBER?
→ search_memories(query="...")

COMPANION ACTION?
→ companion_suggest_action(...) or companion_share_knowledge(...)
```
