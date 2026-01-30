# Combat Encounter Procedures - DM Guide

## Pre-Combat Phase

### 1. Scene Setup
- Describe the environment and enemy positions
- Note cover, terrain features, lighting conditions
- Establish distance between combatants

### 2. Load Creature Stats
**REQUIRED**: Call `get_creature_stats(creature_name="Monster Name")`
- Do this BEFORE combat begins
- Returns: AC, HP, attacks, damage, abilities, resistances
- Use these stats for all subsequent rolls

### 3. Roll Initiative
**For Player**:
```
request_player_roll(roll_type="ability_check", ability_or_skill="initiative", description="roll for initiative")
```

**For Each Enemy**:
```
roll_for_npc(npc_name="Goblin 1", roll_type="initiative", dice_expression="d20+2")
roll_for_npc(npc_name="Goblin 2", roll_type="initiative", dice_expression="d20+2")
```

### 4. Establish Turn Order
- Arrange participants from highest to lowest initiative
- Track order for entire combat

## Player Turn Procedure

### Step 1: Announce Turn
"It's your turn. What do you do?"

### Step 2: Player Declares Action
Wait for player to describe their action.

### Step 3: Execute Action (if attack)

**3a. Request Attack Roll**
```
request_player_roll(
    roll_type="attack",
    ability_or_skill="melee",  # or "ranged"
    description="longsword attack against goblin"
)
```

**3b. Wait for Roll Result**
System will provide the roll total.

**3c. Compare to AC**
- If roll >= target AC: Hit!
- If roll < target AC: Miss

**3d. If Hit, Request Damage**
```
request_player_roll(
    roll_type="damage",
    ability_or_skill="weapon",
    description="longsword damage"
)
```

**3e. Apply Damage**
```
update_character_hp(
    amount=-8,  # negative for damage
    damage_type="slashing",
    reason="player longsword attack"
)
```

**3f. Narrate Result**
"Your blade bites deep into the goblin's shoulder. It screeches in pain."

### Step 4: Bonus Action (if applicable)
Follow same procedure for bonus action if player uses one.

### Step 5: Movement
Player can move up to their speed (usually 30 ft).

## Monster/NPC Turn Procedure

### Step 1: Announce Turn
"The goblin's turn. It snarls and charges at you with its scimitar!"

### Step 2: Get Creature Stats (if not already done)
```
get_creature_stats(creature_name="Goblin")
```

### Step 3: Execute Attack

**3a. Roll Attack**
```
roll_for_npc(
    npc_name="Goblin",
    roll_type="attack",
    dice_expression="d20+4",  # from stat block
    target_name="player",
    context="scimitar attack"
)
```

**3b. System Shows Result**
System displays: "Goblin rolled 17 (scimitar attack) vs player"

**3c. Compare to Player AC**
If roll >= player AC: Hit!

**3d. Roll Damage (if hit)**
```
roll_for_npc(
    npc_name="Goblin",
    roll_type="damage",
    dice_expression="1d6+2",  # from stat block
    context="scimitar damage"
)
```

**3e. Apply Damage to Player**
```
update_character_hp(
    amount=-8,  # result from damage roll
    damage_type="slashing",
    reason="goblin scimitar strike"
)
```

**3f. Narrate Result**
"The goblin's rusty blade slashes across your arm. You feel sharp pain as blood flows."

### Step 4: Movement
Describe monster movement if applicable.

## Special Combat Situations

### Opportunity Attacks
- Triggered when enemy leaves reach without Disengowing
- Use `roll_for_npc` for enemy opportunity attacks
- Use `request_player_roll` for player opportunity attacks

### Grappling
- Contested check: Athletics vs Athletics or Acrobatics
- Use `request_player_roll` for player grapple attempts
- Grappled creature: Speed = 0, disadvantage on attacks

### Flanking (Optional Rule)
- Two allies opposite sides of enemy
- Both gain advantage on melee attacks

### Cover
- **Half Cover**: +2 to AC and DEX saves
- **Three-Quarters Cover**: +5 to AC and DEX saves
- **Full Cover**: Cannot be targeted directly

### Prone
- Melee attacks against: Advantage
- Ranged attacks against: Disadvantage
- Standing up: Costs half movement

## Multi-Enemy Combat

### Tracking Multiple Foes
```
# Get stats once, apply to all of same type
get_creature_stats(creature_name="Goblin")

# Each enemy gets own initiative
roll_for_npc(npc_name="Goblin 1", roll_type="initiative", dice_expression="d20+2")
roll_for_npc(npc_name="Goblin 2", roll_type="initiative", dice_expression="d20+2")

# Each enemy attacks separately
roll_for_npc(npc_name="Goblin 1", roll_type="attack", dice_expression="d20+4", target_name="player")
roll_for_npc(npc_name="Goblin 2", roll_type="attack", dice_expression="d20+4", target_name="player")
```

## Spell Casting in Combat

### Offensive Spells (Saving Throw)

**Step 1**: Player declares spell
"I cast Burning Hands at the goblins"

**Step 2**: Check/consume spell slot (usually automatic)

**Step 3**: Narrate spell effect
"Flames erupt from your outstretched hands in a cone!"

**Step 4**: Request saving throws for each target
```
request_player_roll(
    roll_type="saving_throw",
    ability_or_skill="DEX",
    dc=13,  # caster's spell save DC
    description="dodging Burning Hands"
)
```

**Step 5**: Apply damage based on save result
- Save succeeded: Half damage (or none, depends on spell)
- Save failed: Full damage

### Offensive Spells (Attack Roll)

**Step 1**: Request spell attack
```
request_player_roll(
    roll_type="attack",
    ability_or_skill="spell",
    description="Fire Bolt at goblin"
)
```

**Step 2**: Compare to AC
**Step 3**: Roll damage if hit
**Step 4**: Apply damage with `update_character_hp`

## Combat End Conditions

### All Enemies Defeated
- Describe the final blow
- Narrate victory
- Loot distribution (use `search_items` then `give_item`)

### Player Defeated (0 HP)
- Character falls unconscious
- Begin death saving throws
- Allies can stabilize with Medicine check (DC 10) or healing

### Enemies Flee
- Describe retreat
- Pursuit possible if player chases

### Surrender/Negotiation
- Combat ends, social encounter begins
- Update quest objectives if applicable

## Critical Combat Mistakes to Avoid

### ❌ DO NOT:
1. Say "You hit the goblin for 8 damage" without using request_player_roll
2. Say "The goblin deals 5 damage to you" without using roll_for_npc
3. Mention damage without calling update_character_hp
4. Start combat without calling get_creature_stats
5. Forget to track HP changes
6. Narrate dice results before calling tools

### ✅ DO:
1. ALWAYS use request_player_roll for player attacks
2. ALWAYS use roll_for_npc for monster attacks
3. ALWAYS use update_character_hp when HP changes
4. ALWAYS use get_creature_stats before combat
5. Follow the turn order strictly
6. Let the tools handle the rolls, you handle the narrative

## Example Combat Flow

```
DM: "Three goblins emerge from the cave! Roll for initiative!"
[get_creature_stats("Goblin")]
[request_player_roll(type="ability_check", skill="initiative")]
[roll_for_npc("Goblin 1", "initiative", "d20+2")]
[roll_for_npc("Goblin 2", "initiative", "d20+2")]
[roll_for_npc("Goblin 3", "initiative", "d20+2")]

DM: "You go first! What do you do?"
Player: "I attack Goblin 1 with my longsword"

[request_player_roll(type="attack", skill="melee")]
# Player rolls 18
DM: "That hits! Roll damage!"

[request_player_roll(type="damage", skill="weapon")]
# Player rolls 9
[update_character_hp(target=goblin1, amount=-9, type="slashing", reason="player longsword")]

DM: "Your blade cleaves into the goblin's chest. It staggers but remains standing!"

DM: "Goblin 1's turn. It swings its scimitar at you!"
[roll_for_npc("Goblin 1", "attack", "d20+4", target="player")]
# System shows: 16
DM: "It hits! Rolling damage..."

[roll_for_npc("Goblin 1", "damage", "1d6+2")]
# System shows: 7
[update_character_hp(target=player, amount=-7, type="slashing", reason="goblin scimitar")]

DM: "The goblin's blade cuts across your shoulder. You feel sharp pain!"
```
