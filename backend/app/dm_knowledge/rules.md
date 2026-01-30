# D&D 5e Core Rules - DM Reference

## Dice Rolling Protocol

**CRITICAL RULE**: NEVER narrate dice roll results. ALWAYS use tools.

### Player Rolls
- **ALWAYS** use `request_player_roll` tool for player actions requiring rolls
- **NEVER** say: "You roll and hit", "You rolled 15", "Your attack deals 8 damage"
- Player rolls: d20 + modifier vs DC or AC
- Attack rolls: d20 + proficiency + ability mod vs target AC
- Ability checks: d20 + ability mod + proficiency (if proficient) vs DC
- Saving throws: d20 + ability mod + proficiency (if proficient) vs DC

### NPC/Monster Rolls
- **ALWAYS** use `roll_for_npc` tool for ALL NPC/monster rolls
- **NEVER** narrate: "The goblin hits for 8 damage", "The guard rolls 12"
- **REQUIRED** for: attacks, damage, saves, ability checks, initiative
- Format: roll_for_npc(npc_name="Goblin", roll_type="attack", dice_expression="d20+4")

### When to Request Rolls
Call for a roll when:
1. Action has MEANINGFUL CHANCE OF FAILURE
2. Outcome MATTERS TO THE STORY (changes what happens next)
3. RULE EXPLICITLY REQUIRES IT (attacks, spell saves, contested checks)

Do NOT call for rolls when:
- Action is trivial (opening unlocked door)
- Failure would halt story without alternative
- Character automatically succeeds/fails due to abilities

## HP Management

**CRITICAL RULE**: ALWAYS use `update_character_hp` when HP changes.

### When to Use
- **IMMEDIATELY** after damage occurs (combat, traps, falling, poison)
- **IMMEDIATELY** after healing (potions, spells, rest)
- Parameters: amount (negative for damage, positive for healing), damage_type, reason

### Damage
- Format: `update_character_hp(amount=-8, damage_type="slashing", reason="goblin scimitar")`
- Tool automatically clamps HP between 0 and max_hp
- Track damage type for resistance/vulnerability calculations

### Healing
- Format: `update_character_hp(amount=8, reason="healing potion")`
- Cannot exceed max HP (tool handles this)

### Death and Dying
- At 0 HP: Character falls unconscious, begins death saves
- Death saves: d20, 10+ = success, <10 = failure
- 3 successes = stabilized (unconscious but alive)
- 3 failures = dead
- Natural 20 = regain 1 HP, wake up
- Natural 1 = counts as 2 failures
- Taking damage while at 0 HP = automatic death save failure

## Combat Rules

### Initiative
- Roll d20 + DEX modifier for all participants
- Order: Highest to lowest
- Ties: Higher DEX modifier goes first, then roll-off

### Action Economy (Per Turn)
1. **Action**: Attack, Cast Spell, Dash, Disengage, Dodge, Help, Hide, Ready, Search, Use Object
2. **Bonus Action**: Some class features, two-weapon fighting, certain spells
3. **Reaction**: Opportunity attack, Shield spell, Counterspell (once per round)
4. **Movement**: Up to speed (usually 30 ft for most races)
5. **Free Actions**: Drop item, speak briefly, interact with one object

### Attack Sequence
1. Declare target and attack type
2. Request roll: `request_player_roll(roll_type="attack", ability_or_skill="melee")`
3. Player rolls d20 + proficiency + ability mod
4. Compare to target AC
5. If hit: Request damage: `request_player_roll(roll_type="damage", ability_or_skill="weapon")`
6. Apply damage: `update_character_hp(amount=-damage, damage_type="...")`

### Critical Hits and Misses
- **Natural 20**: Automatic hit, roll damage dice twice (modifiers once)
- **Natural 1**: Automatic miss (regardless of modifiers)

### Advantage/Disadvantage
- **Advantage**: Roll d20 twice, take higher result
- **Disadvantage**: Roll d20 twice, take lower result
- Sources: Hidden attacker (advantage), prone defender (disadvantage on ranged)
- Never stacks: Multiple sources = still roll twice

## Spell Casting

### Spell Slots
- Limited resource: Track carefully
- Cantrips: Unlimited use, no slot required
- Leveled spells: Consume slot of spell's level or higher
- Auto-detection usually works, manual override: `consume_spell_slot(spell_level=3, spell_name="Fireball")`

### Spell Save DC
- Caster DC = 8 + proficiency + spellcasting ability mod
- Target rolls saving throw vs DC
- Success: Often half damage or no effect
- Failure: Full effect

### Concentration
- Some spells require concentration (marked in spell description)
- Can only concentrate on ONE spell at a time
- Casting another concentration spell ends previous
- Taking damage: Make CON save (DC = 10 or half damage, whichever is higher)
- Failure: Lose concentration, spell ends

## Tool Usage Rules

### Tool Execution Order
1. **get_creature_stats**: Use BEFORE combat to load accurate stats
2. **request_player_roll / roll_for_npc**: For all dice rolls
3. **update_character_hp**: IMMEDIATELY after damage/healing
4. **give_item**: After using search_items to find appropriate loot
5. **search_items**: Before giving loot to see options

### Required Tool Calls
- Combat damage → MUST call `update_character_hp`
- Player action with uncertainty → MUST call `request_player_roll`
- NPC/monster action → MUST call `roll_for_npc`
- Monster encounter → SHOULD call `get_creature_stats` first
- Loot distribution → SHOULD call `search_items` then `give_item`

## Common Mistakes to Avoid

### ❌ WRONG Examples
1. "You swing your sword and hit for 8 damage" → Missing request_player_roll
2. "The goblin attacks and deals 5 damage" → Missing roll_for_npc
3. Mentioning damage without update_character_hp
4. Giving specific items without search_items first
5. Starting combat without get_creature_stats

### ✅ CORRECT Examples
1. Use request_player_roll → Wait for result → Narrate outcome
2. Use roll_for_npc → System shows roll → Narrate based on result
3. Any damage/healing → update_character_hp immediately
4. search_items first → Review options → give_item with appropriate choice
5. get_creature_stats at encounter start → Have accurate stats for combat

## Ability Scores

The six abilities:
- **STR** (Strength): Melee attacks, Athletics, carrying capacity
- **DEX** (Dexterity): Ranged attacks, AC, Acrobatics, Stealth, Initiative
- **CON** (Constitution): Hit points, concentration, poison resistance
- **INT** (Intelligence): Arcana, History, Investigation, Nature, Religion
- **WIS** (Wisdom): Perception, Insight, Survival, Medicine, Animal Handling
- **CHA** (Charisma): Persuasion, Deception, Intimidation, Performance

## Difficulty Classes

Set appropriate DCs:
- **Very Easy**: DC 5 (untrained person has good chance)
- **Easy**: DC 10 (trained person usually succeeds)
- **Moderate**: DC 15 (trained person succeeds about half the time)
- **Hard**: DC 20 (even experts struggle)
- **Very Hard**: DC 25 (only masters succeed regularly)
- **Nearly Impossible**: DC 30 (legendary feat)

## Rest and Recovery

### Short Rest
- Duration: At least 1 hour
- Hit Dice: Can spend to regain HP (roll hit die + CON mod)
- Features: Some class abilities recharge

### Long Rest
- Duration: At least 8 hours (sleeping or light activity)
- HP: Regain all hit points
- Hit Dice: Regain up to half total (minimum 1)
- Spell Slots: All slots restored
- Abilities: Most features recharge
