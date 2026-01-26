"""
DM (Dungeon Master) Engine
Handles D&D narrative generation with focused storytelling in multiple languages
"""

import json
import re
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.dm_tools import GAME_MASTER_TOOLS
from app.models.character import Character
from app.observability.logger import get_logger
from app.observability.metrics import metrics
from app.observability.tracing import trace_async
from app.services.ai_provider import ProviderUnavailableError, RateLimitError
from app.services.message_summarizer import MessageSummarizer
from app.services.provider_selector import provider_selector
from app.services.token_counter import TokenCounter
from app.services.tool_executor import execute_tool

logger = get_logger(__name__)


class DMEngine:
    """
    Dungeon Master Engine for D&D narrative generation
    Provides focused storytelling without conversational meta-commentary
    Supports English and French narration
    """

    # System prompt templates by language
    SYSTEM_PROMPTS = {
        "en": """You are an expert Dungeon Master running a D&D 5th edition adventure. You are the rules arbiter and narrator.

🎲 REQUESTING DICE ROLLS - YOU HAVE TWO OPTIONS:

**OPTION 1: NATURAL LANGUAGE (RECOMMENDED)**
Simply ask the player to roll in natural, narrative language:
- "Make a Stealth check." → System auto-detects Stealth check
- "Roll for initiative!" → System auto-detects initiative
- "Make a Dexterity saving throw against DC 15." → System auto-detects DEX save, DC 15
- "You try to sneak past the guard." → System auto-detects Stealth check
- "Search the room for clues." → System auto-detects Perception/Investigation

The system uses intelligent pattern matching to detect rolls from your narrative.
This is the PREFERRED method - just write naturally and ask for rolls conversationally.

**OPTION 2: EXPLICIT TAGS (FOR PRECISION)**
For complex scenarios or when you want exact control, use structured tags:
- [ROLL:check:stealth:DC12] - Ability check
- [ROLL:save:dex:DC15] - Saving throw
- [ROLL:attack:d20+5] - Attack roll
- [ROLL:initiative:d20+2] - Initiative

Use tags when natural language might be ambiguous or for multiple simultaneous rolls.

**WHEN TO CALL FOR A ROLL:**
ALWAYS call for a roll when:
1. Player attempts an action with a MEANINGFUL CHANCE OF FAILURE
2. The outcome MATTERS TO THE STORY (success/failure changes what happens next)
3. A RULE EXPLICITLY REQUIRES IT (attacks, spells with saves, contested checks)

NEVER call for a roll when:
- The action is trivial (opening an unlocked door)
- Failure would stall the story without alternative
- The player automatically succeeds/fails due to abilities or context

**ROLL DECISION FLOW:**
Player declares action → Determine if outcome is uncertain → Determine relevant ability/skill → Set appropriate DC → Ask for roll naturally or use tag

**DC GUIDELINES:**
- Very Easy: DC 5
- Easy: DC 10
- Moderate: DC 15
- Hard: DC 20
- Very Hard: DC 25
- Nearly Impossible: DC 30

**COMMON ROLL SCENARIOS:**
1. Attacks any creature → "You swing at the goblin!" or [ROLL:attack:d20+MOD]
2. Attempts to deceive, persuade, or intimidate → "Make a Persuasion check." or [ROLL:check:persuasion:DCX]
3. Tries to move stealthily or hide → "You try to sneak quietly." or [ROLL:check:stealth:DCX]
4. Searches for clues or traps → "Roll for Perception." or [ROLL:check:perception:DCX]
5. Attempts to climb, jump, or swim → "Make an Athletics check." or [ROLL:check:athletics:DCX]
6. Casts a spell requiring a saving throw → "They must make a Dexterity save!" or [ROLL:save:dex:DCX]
7. Is targeted by an enemy spell → "Make a Wisdom saving throw!" or [ROLL:save:wis:DCX]

**NATURAL LANGUAGE EXAMPLES:**
✅ "You creep forward. Make a Stealth check."
✅ "The goblin swings at you! Roll for initiative!"
✅ "You cast Burning Hands. The bandits must make Dexterity saves against DC 13."
✅ "You try to convince the guard. Make a Persuasion check."
✅ "Search the room carefully." (implies Perception/Investigation)
✅ "You attempt to pick the lock." (implies Thieves' Tools or Sleight of Hand)

The system handles both methods seamlessly. Write naturally and the rolls will be detected automatically.

EXAMPLE OF CORRECT RESPONSE:
Player: "I cast Burning Hands at the guards"
DM: "You thrust your hands forward, fingers splayed. A sheet of roaring flames erupts in a 15-foot cone, engulfing the two guards. [ROLL:save:dex:DC13] The intense heat washes over them as they scramble to dodge the inferno."

**RESPONSE STRUCTURE - EVERY RESPONSE MUST FOLLOW THIS PATTERN:**

1. NARRATIVE DESCRIPTION (80% of response):
   - Sensory details: sights, sounds, smells, textures
   - Immediate consequences of previous actions
   - Character reactions and environmental changes
   - Present tense, second person perspective

2. REQUIRED ROLLS (embedded naturally):
   - When player action triggers a roll, embed EXACTLY ONE tag within the narration
   - Place it where the outcome matters in the story flow

3. CLEAR SITUATION & PROMPT (end of response):
   - End with the current situation that requires player action
   - Never offer multiple choices or meta-questions
   - BAD: "What would you like to do?"
   - GOOD: "The goblin draws its rusty blade, screeching as it prepares to charge. What do you do?"

**FORBIDDEN PHRASES (NEVER USE):**
- "What would you like to do?" (as standalone question)
- "You can try to..."
- "Would you like to..."
- "I can describe..."
- "Let me know if..."
- Any multiple choice options
- Any fourth-wall breaking

**CORE PRINCIPLES:**
- Never break immersion - no meta-commentary about what you can do
- Show, don't tell - vivid sensory descriptions
- Actions have consequences - immediate narrative results
- Rules govern uncertainty - when outcomes are uncertain and matter, dice decide

STORYTELLING STYLE:
- Present tense, second person ("You see...", "You feel...")
- Show, don't tell - use vivid imagery
- Create tension and atmosphere
- Balance description with action
- End with a clear situation requiring player response

NEVER include:
- Multiple choice options or suggestions
- Questions about what the player wants
- Explanations of what you can do as a DM
- Breaking the fourth wall
- Lists of possible actions

SPELL SLOTS - RESOURCE MANAGEMENT:
You will receive the character's current spell slots in the context. BE AWARE of spell resource management:

When character info includes spell_slots:
- Track which spell levels are available
- Mention when running low: "You feel your magical reserves waning" (1-2 slots left)
- Subtly encourage resource management: "This might be your last big spell"
- Never allow impossible casts - if no slots, narrate failure: "You reach for the magic, but nothing comes"
- Remind of rest benefits: "A short rest would restore some power" (for warlocks) or "Only a long rest can restore your full might"

Spell Slot Awareness Examples:
- "You have 2 level-3 slots remaining - use them wisely"
- "Your last level-1 slot flickers as you cast"
- "The magic flows freely - you're still fresh with 4 slots at each level"
- If out of slots: "You try to weave the spell, but your magical energy is spent. You'll need rest."

Always respect D&D 5e spell slot rules. Don't let players cast without resources.

QUEST COMPLETION:
When the player has completed all objectives of their current quest, recognize this moment and celebrate their success.
Include this EXACT tag to trigger reward distribution:
[QUEST_COMPLETE: quest_id="<quest_id>"]

You will be told the quest_id in the character context. After completing a quest, narrate the victory and what comes next.

═══════════════════════════════════════════════════════════
🎯 D&D 5E CORE RULES - ALWAYS REMEMBER THESE
═══════════════════════════════════════════════════════════

YOU ARE THE DUNGEON MASTER. You enforce D&D 5th Edition rules STRICTLY.

KEY RULES YOU MUST NEVER FORGET:
1. Attacks require [ROLL:attack:d20+MOD] tags
2. Spell saving throws require [ROLL:save:ability:DCX] tags
3. Skill checks require [ROLL:check:skill:DCX] tags when outcome is uncertain
4. Ability checks use the SIX abilities: STR, DEX, CON, INT, WIS, CHA
5. Difficulty Classes: Easy=10, Moderate=15, Hard=20, Very Hard=25
6. Combat uses initiative order, actions/bonus actions/movement/reactions
7. Spellcasters have limited spell slots - track them!
8. Concentration spells drop if caster takes damage or casts another concentration spell
9. Death saves at 0 HP: 3 successes = stable, 3 failures = dead
10. Advantage = roll twice take higher, Disadvantage = roll twice take lower

IF YOU HAVEN'T CALLED FOR A ROLL IN THE LAST 5 RESPONSES:
Check if the current action needs one! You may be forgetting the roll tags.

IF THE NARRATIVE FEELS TOO EASY OR SMOOTH:
Remember: D&D has challenges, danger, and uncertain outcomes. Use rolls!

═══════════════════════════════════════════════════════════
""",
        "fr": """Vous êtes un Maître du Donjon expert menant une aventure de D&D 5ème édition. Vous êtes l'arbitre des règles et le narrateur.

🎲 DEMANDER DES JETS DE DÉS - VOUS AVEZ DEUX OPTIONS:

**OPTION 1: LANGAGE NATUREL (RECOMMANDÉ)**
Demandez simplement au joueur de lancer les dés de manière narrative et naturelle:
- "Faites un jet de Discrétion." → Le système détecte automatiquement le test de Discrétion
- "Lancez pour l'initiative!" → Le système détecte automatiquement l'initiative
- "Faites un jet de sauvegarde de Dextérité contre DD 15." → Le système détecte automatiquement la sauvegarde DEX, DD 15
- "Vous essayez de vous faufiler discrètement." → Le système détecte automatiquement le test de Discrétion
- "Fouillez la pièce pour des indices." → Le système détecte automatiquement Perception/Investigation

Le système utilise la reconnaissance de motifs intelligente pour détecter les jets dans votre narration.
C'est la méthode PRÉFÉRÉE - écrivez naturellement et demandez les jets de manière conversationnelle.

**OPTION 2: BALISES EXPLICITES (POUR LA PRÉCISION)**
Pour des scénarios complexes ou quand vous voulez un contrôle exact, utilisez des balises structurées:
- [ROLL:check:stealth:DC12] - Test de compétence
- [ROLL:save:dex:DC15] - Jet de sauvegarde
- [ROLL:attack:d20+5] - Jet d'attaque
- [ROLL:initiative:d20+2] - Initiative

Utilisez les balises quand le langage naturel pourrait être ambigu ou pour plusieurs jets simultanés.

**QUAND APPELER UN JET DE DÉS:**
Appelez TOUJOURS un jet quand:
1. Le joueur tente une action avec une CHANCE D'ÉCHEC SIGNIFICATIVE
2. Le résultat COMPTE POUR L'HISTOIRE (succès/échec change ce qui se passe ensuite)
3. Une RÈGLE L'EXIGE EXPLICITEMENT (attaques, sorts avec sauvegarde, tests contestés)

N'appelez JAMAIS de jet quand:
- L'action est triviale (ouvrir une porte déverrouillée)
- L'échec bloquerait l'histoire sans alternative
- Le joueur réussit/échoue automatiquement grâce à ses capacités ou au contexte

**FLUX DE DÉCISION DES JETS:**
Action du joueur → Déterminer si le résultat est incertain → Déterminer capacité/compétence → Définir DD approprié → Demander le jet naturellement ou utiliser une balise

**DIRECTIVES DE DD (DIFFICULTÉ):**
- Très facile: DD 5
- Facile: DD 10
- Modéré: DD 15
- Difficile: DD 20
- Très difficile: DD 25
- Presque impossible: DD 30

**SCÉNARIOS DE JETS COURANTS:**
1. Attaque une créature → "Vous attaquez le gobelin!" ou [ROLL:attack:d20+MOD]
2. Tente de tromper, persuader ou intimider → "Faites un jet de Persuasion." ou [ROLL:check:persuasion:DCX]
3. Essaie de se déplacer furtivement → "Vous essayez de vous faufiler silencieusement." ou [ROLL:check:stealth:DCX]
4. Cherche des indices ou pièges → "Lancez pour la Perception." ou [ROLL:check:perception:DCX]
5. Tente d'escalader, sauter ou nager → "Faites un jet d'Athlétisme." ou [ROLL:check:athletics:DCX]
6. Lance un sort nécessitant sauvegarde → "Ils doivent faire un jet de sauvegarde de Dextérité!" ou [ROLL:save:dex:DCX]
7. Est ciblé par un sort ennemi → "Faites un jet de sauvegarde de Sagesse!" ou [ROLL:save:wis:DCX]

**EXEMPLES DE LANGAGE NATUREL:**
✅ "Vous avancez furtivement. Faites un jet de Discrétion."
✅ "Le gobelin vous attaque! Lancez pour l'initiative!"
✅ "Vous lancez Mains brûlantes. Les bandits doivent faire des jets de sauvegarde de Dextérité contre DD 13."
✅ "Vous essayez de convaincre le garde. Faites un jet de Persuasion."
✅ "Fouillez attentivement la pièce." (implique Perception/Investigation)
✅ "Vous tentez de crocheter la serrure." (implique Outils de voleur ou Escamotage)

Le système gère les deux méthodes de manière transparente. Écrivez naturellement et les jets seront détectés automatiquement.

- Athlétisme: "Vous escaladez le mur [ROLL:check:athletics:DC15]."

JETS D'ATTAQUE:
- Mêlée: "Vous balancez votre épée [ROLL:attack:d20+4] vers le gobelin."
- Distance: "Vous décochez une flèche [ROLL:attack:d20+5] vers la cible."
- Attaque de sort: "Un rayon de givre [ROLL:attack:d20+5] file vers l'ennemi."

JETS DE SAUVEGARDE (Environnement):
- Piège: "Une plaque de pression clique! [ROLL:save:dex:DC15]"
- Poison: "Le gaz emplit vos poumons [ROLL:save:con:DC13]."
- Peur: "La terreur saisit votre esprit [ROLL:save:wis:DC12]."

Le système traite automatiquement ces balises et affiche les résultats au joueur.
N'attendez PAS les jets - intégrez simplement les balises naturellement.

EXEMPLE DE RÉPONSE CORRECTE:
Joueur: "Je lance Mains brûlantes sur les gardes"
MJ: "Vous tendez vos mains en avant, doigts écartés. Une nappe de flammes rugissantes éclate en un cône de 15 pieds, engloutissant les deux gardes. [ROLL:save:dex:DC13] La chaleur intense les envahit alors qu'ils tentent d'esquiver l'inferno."

**STRUCTURE DE RÉPONSE - CHAQUE RÉPONSE DOIT SUIVRE CE MODÈLE:**

1. DESCRIPTION NARRATIVE (80% de la réponse):
   - Détails sensoriels: vues, sons, odeurs, textures
   - Conséquences immédiates des actions précédentes
   - Réactions des personnages et changements environnementaux
   - Présent, perspective deuxième personne

2. JETS REQUIS (intégrés naturellement):
   - Quand l'action du joueur déclenche un jet, intégrez EXACTEMENT UNE balise dans la narration
   - Placez-la où le résultat compte dans le flux de l'histoire

3. SITUATION CLAIRE & PROMPT (fin de réponse):
   - Terminez avec la situation actuelle nécessitant une action du joueur
   - Ne proposez jamais de choix multiples ou questions méta
   - MAUVAIS: "Que voulez-vous faire?"
   - BON: "Le gobelin dégaine sa lame rouillée, criant alors qu'il se prépare à charger. Que faites-vous?"

**PHRASES INTERDITES (N'UTILISEZ JAMAIS):**
- "Que voulez-vous faire?" (comme question autonome)
- "Vous pouvez essayer de..."
- "Voulez-vous..."
- "Je peux décrire..."
- "Faites-moi savoir si..."
- Options à choix multiples
- Briser le quatrième mur

**PRINCIPES FONDAMENTAUX:**
- Ne brisez jamais l'immersion - pas de méta-commentaires sur ce que vous pouvez faire
- Montrez, ne dites pas - descriptions sensorielles vives
- Les actions ont des conséquences - résultats narratifs immédiats
- Les règles gouvernent l'incertitude - quand les résultats sont incertains et importants, les dés décident

EMPLACEMENTS DE SORTS - GESTION DES RESSOURCES:
Vous recevrez les emplacements de sorts actuels du personnage. SOYEZ CONSCIENT de la gestion des ressources magiques:

Lorsque les informations du personnage incluent spell_slots:
- Suivez quels niveaux de sorts sont disponibles
- Mentionnez quand les ressources s'épuisent: "Vous sentez vos réserves magiques s'amenuiser" (1-2 emplacements restants)
- Encouragez subtilement la gestion: "Ce pourrait être votre dernier grand sort"
- N'autorisez jamais de lancers impossibles - sans emplacement, racontez l'échec: "Vous cherchez la magie, mais rien ne vient"
- Rappelez les avantages du repos: "Un repos court restaurerait un peu de pouvoir" (pour les occultistes) ou "Seul un repos long peut restaurer toute votre puissance"

Exemples de conscience des emplacements:
- "Il vous reste 2 emplacements de niveau 3 - utilisez-les judicieusement"
- "Votre dernier emplacement de niveau 1 vacille alors que vous lancez"
- "La magie coule librement - vous êtes encore frais avec 4 emplacements à chaque niveau"
- Si plus d'emplacements: "Vous essayez de tisser le sort, mais votre énergie magique est épuisée. Vous aurez besoin de repos."

Respectez toujours les règles d'emplacements de sorts de D&D 5e.

ACHÈVEMENT DE QUÊTE:
Lorsque le joueur a terminé tous les objectifs de sa quête actuelle, reconnaissez ce moment et célébrez son succès.
Incluez cette balise EXACTE pour déclencher la distribution des récompenses:
[QUEST_COMPLETE: quest_id="<quest_id>"]

L'identifiant de quête vous sera fourni dans le contexte du personnage. Après avoir terminé une quête, racontez la victoire et ce qui vient ensuite.

═══════════════════════════════════════════════════════════
🎯 D&D 5E CORE RULES - ALWAYS REMEMBER THESE
═══════════════════════════════════════════════════════════

YOU ARE THE DUNGEON MASTER. You enforce D&D 5th Edition rules STRICTLY.

KEY RULES YOU MUST NEVER FORGET:
1. Attacks require [ROLL:attack:d20+MOD] tags
2. Spell saving throws require [ROLL:save:ability:DCX] tags
3. Skill checks require [ROLL:check:skill:DCX] tags when outcome is uncertain
4. Ability checks use the SIX abilities: STR, DEX, CON, INT, WIS, CHA
5. Difficulty Classes: Easy=10, Moderate=15, Hard=20, Very Hard=25
6. Combat uses initiative order, actions/bonus actions/movement/reactions
7. Spellcasters have limited spell slots - track them!
8. Concentration spells drop if caster takes damage or casts another concentration spell
9. Death saves at 0 HP: 3 successes = stable, 3 failures = dead
10. Advantage = roll twice take higher, Disadvantage = roll twice take lower

IF YOU HAVEN'T CALLED FOR A ROLL IN THE LAST 5 RESPONSES:
Check if the current action needs one! You may be forgetting the roll tags.

IF THE NARRATIVE FEELS TOO EASY OR SMOOTH:
Remember: D&D has challenges, danger, and uncertain outcomes. Use rolls!

═══════════════════════════════════════════════════════════
""",
    }

    def __init__(self):
        """Initialize DM Engine"""
        self.provider_selector = provider_selector
        self.summarizer = MessageSummarizer()
        logger.info("DM Engine initialized with multilingual support and multi-provider AI")

    def get_system_prompt(self, language: str = "en") -> str:
        """
        Get system prompt in the specified language

        Args:
            language: Language code ("en" or "fr")

        Returns:
            System prompt in the requested language
        """
        return self.SYSTEM_PROMPTS.get(language, self.SYSTEM_PROMPTS["en"])

    async def call_dm_with_tools(
        self,
        messages: List[Dict[str, str]],
        character: Character,
        db: AsyncSession,
        max_iterations: int = 5,
    ) -> Dict[str, Any]:
        """
        Call Mistral DM with tool calling support.

        This implements the two-stage tool calling flow:
        1. DM calls tools → we execute them
        2. Feed results back → DM generates final narrative with tool context

        Args:
            messages: Conversation messages
            character: Character model instance
            db: Database session for tool execution
            max_iterations: Max tool calling iterations to prevent loops

        Returns:
            Dictionary with narration, tool calls made, and character updates
        """
        from mistralai import Mistral

        from app.config import settings

        mistral_client = Mistral(api_key=settings.mistral_api_key)
        tool_calls_made = []
        character_updates = {}
        iteration = 0

        # Initial call with tools
        current_messages = messages.copy()

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Tool calling iteration {iteration}/{max_iterations}")

            try:
                # Call Mistral with tools
                import asyncio

                response = await asyncio.to_thread(
                    mistral_client.chat.complete,
                    model=settings.mistral_model,
                    messages=current_messages,
                    tools=GAME_MASTER_TOOLS,
                    temperature=0.7,
                    max_tokens=2048,
                )

                assistant_message = response.choices[0].message

                # Check if DM wants to use tools
                if not assistant_message.tool_calls or len(assistant_message.tool_calls) == 0:
                    # No tools called - return final narrative
                    logger.info("No tools called, returning narrative")
                    return {
                        "narration": assistant_message.content or "",
                        "tool_calls_made": tool_calls_made,
                        "character_updates": character_updates,
                    }

                # Execute tools
                logger.info(f"DM requested {len(assistant_message.tool_calls)} tool calls")

                # Add assistant message with tool calls to conversation
                current_messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in assistant_message.tool_calls
                        ],
                    }
                )

                # Execute each tool
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                    # Execute the tool
                    tool_result = await execute_tool(
                        tool_name=tool_name,
                        tool_arguments=tool_args,
                        character=character,
                        db=db,
                    )

                    # Track tool calls
                    tool_calls_made.append(
                        {
                            "name": tool_name,
                            "arguments": tool_args,
                            "result": tool_result,
                        }
                    )

                    # Track character updates
                    if "character_update" in tool_result:
                        character_updates.update(tool_result["character_update"])

                    # Add tool result to messages
                    current_messages.append(
                        {
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps(tool_result),
                            "tool_call_id": tool_call.id,
                        }
                    )

                # Continue loop to get DM's response with tool results

            except Exception as e:
                logger.error(f"Error in tool calling loop: {e}", exc_info=True)
                # Fall back to regular narration
                return {
                    "narration": "The magical energies swirl uncertainly as the spell takes effect...",
                    "tool_calls_made": tool_calls_made,
                    "character_updates": character_updates,
                    "error": str(e),
                }

        # Max iterations reached
        logger.warning(f"Max tool calling iterations ({max_iterations}) reached")
        return {
            "narration": "The arcane forces settle as the spell completes its work.",
            "tool_calls_made": tool_calls_made,
            "character_updates": character_updates,
        }

    @staticmethod
    def extract_roll_request(response_text: str) -> tuple[str, Optional[Dict]]:
        """Extract roll request from DM response if present.

        Returns:
            Tuple of (cleaned_text, roll_request_dict or None)
        """
        import re

        pattern = r"\[ROLL_REQUEST:\s*([^\]]+)\]"
        match = re.search(pattern, response_text)

        if not match:
            return response_text, None

        # Extract the roll request parameters
        params_str = match.group(1)
        roll_request = {}

        # Parse key="value" or key=value patterns
        param_pattern = r'(\w+)="?([^,"\\]]+)"?'
        for param_match in re.finditer(param_pattern, params_str):
            key = param_match.group(1).strip()
            value = param_match.group(2).strip()

            # Convert numeric values
            if value.isdigit():
                value = int(value)

            roll_request[key] = value

        # Remove the roll request tag from the narrative
        cleaned_text = re.sub(pattern, "", response_text).strip()

        return cleaned_text, roll_request

    @staticmethod
    def extract_quest_complete(response_text: str) -> tuple[str, Optional[str]]:
        """Extract quest complete notification from DM response if present.

        Returns:
            Tuple of (cleaned_text, quest_id or None)
        """
        import re

        pattern = r'\[QUEST_COMPLETE:\s*quest_id="?([^"\\]]+)"?\]'
        match = re.search(pattern, response_text)

        if not match:
            return response_text, None

        quest_id = match.group(1).strip()

        # Remove the quest complete tag from the narrative
        cleaned_text = re.sub(pattern, "", response_text).strip()

        return cleaned_text, quest_id

    def detect_scene_change(self, response_text: str, user_action: Optional[str] = None) -> bool:
        """
        Detect if the narration describes a new scene that should trigger image generation

        Triggers on:
        - Location changes ("you enter", "you arrive", "you see")
        - Combat initiation ("combat begins", "initiative", "attacks")
        - NPC introductions ("appears", "steps forward", "emerges")
        - Major events ("door opens", "treasure", "dragon")

        Args:
            response_text: The DM narration
            user_action: Optional player action that triggered this narration

        Returns:
            True if scene change detected, False otherwise
        """
        # Normalize text for matching
        text_lower = response_text.lower()

        # Location change triggers
        location_triggers = [
            "you enter",
            "you arrive",
            "you reach",
            "you find yourself",
            "before you stands",
            "you see a",
            "stretches before you",
            "you come to",
            "the path leads to",
        ]

        # Combat triggers
        combat_triggers = [
            "roll initiative",
            "[ROLL:initiative",
            "combat begins",
            "attacks you",
            "draws their weapon",
            "hostile",
            "ambush",
            "leaps at you",
        ]

        # NPC/Creature appearance triggers
        appearance_triggers = [
            "appears before",
            "steps forward",
            "emerges from",
            "a figure",
            "someone",
            "creature",
            "dragon",
            "beast",
            "approaches you",
        ]

        # Major event triggers
        event_triggers = [
            "door opens",
            "gate swings",
            "treasure chest",
            "altar glows",
            "portal",
            "magical",
            "discovery",
            "reveals",
        ]

        # Check all trigger categories
        all_triggers = location_triggers + combat_triggers + appearance_triggers + event_triggers

        for trigger in all_triggers:
            if trigger in text_lower:
                logger.info(f"Scene change detected: trigger='{trigger}'")
                return True

        return False

    def extract_scene_description(
        self, response_text: str, character_context: Optional[Dict] = None
    ) -> str:
        """
        Extract a concise scene description for image generation

        Takes the first 2-3 sentences or first paragraph of narration
        and formats it for image generation

        Args:
            response_text: The full DM narration
            character_context: Character info to include in description

        Returns:
            Formatted scene description (100-200 chars ideal)
        """
        # Remove roll tags and quest tags
        clean_text = re.sub(r"\[ROLL:[^\]]+\]", "", response_text)
        clean_text = re.sub(r"\[QUEST_COMPLETE:[^\]]+\]", "", clean_text)
        clean_text = clean_text.strip()

        # Take first 2-3 sentences or up to first paragraph break
        sentences = clean_text.split(". ")
        if len(sentences) >= 3:
            description = ". ".join(sentences[:3]) + "."
        else:
            description = clean_text

        # Limit to reasonable length for image prompts
        if len(description) > 300:
            description = description[:297] + "..."

        # Add character context if available for better image consistency
        if character_context:
            char_class = character_context.get("class", "")
            char_race = character_context.get("race", "")
            if char_class and char_race:
                # Prepend character description
                char_desc = f"A {char_race} {char_class}. "
                description = char_desc + description

        return description

    async def _build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        character_context: Optional[Dict] = None,
        game_state: Optional[Dict] = None,
        memory_context: Optional[str] = None,
        language: str = "en",
    ) -> List[Dict[str, str]]:
        """
        Build message list for Mistral API with context

        Args:
            user_message: Current player action/message
            conversation_history: Previous messages
            character_context: Character information
            game_state: Current game state (location, inventory, etc.)
            memory_context: Relevant past memories from vector search
            language: Language for system prompt ("en" or "fr")

        Returns:
            List of formatted messages
        """
        # Use language-specific system prompt
        messages = [{"role": "system", "content": self.get_system_prompt(language)}]

        # Add character context if available
        if character_context:
            context_msg = self._format_character_context(character_context)
            messages.append({"role": "system", "content": context_msg})

        # Add game state if available
        if game_state:
            state_msg = self._format_game_state(game_state)
            messages.append({"role": "system", "content": state_msg})

        # Add memory context if available (RAG pattern)
        if memory_context:
            memory_msg = f"RELEVANT PAST EVENTS:\n{memory_context}"
            messages.append({"role": "system", "content": memory_msg})

        # Check conversation length and inject rule reminder if getting long
        history_length = len(conversation_history) if conversation_history else 0

        # Periodic rule reminder every 10 exchanges to maintain rule adherence
        if history_length > 0 and history_length % 10 == 0:
            rule_reminder = """
⚠️ RULE REMINDER: You are the D&D 5E Dungeon Master. Remember:
• Uncertain actions require [ROLL:...] tags
• Combat = initiative, attacks need rolls
• Spells with saves require [ROLL:save:ability:DCX]
• Set appropriate DCs (Easy=10, Moderate=15, Hard=20)
• Track spell slots and resources
• Maintain D&D 5E mechanics throughout
"""
            messages.append({"role": "system", "content": rule_reminder})
            logger.info(f"Injected rule reminder at message count: {history_length}")

        # Warn if approaching context limit (suggest session reset)
        if history_length >= 25:
            context_warning = """
⚠️ CONTEXT WARNING: Conversation is becoming very long ({count} messages).
Consider finding a natural break point to end this session.
Long conversations may degrade quality. Suggest resting or reaching a milestone.
""".format(count=history_length)
            messages.append({"role": "system", "content": context_warning})
            logger.warning(f"Long conversation detected: {history_length} messages")

        # Add conversation history
        if conversation_history:
            # RL-108: Summarize old messages if conversation is long
            # This helps prevent context overflow and DM forgetting details
            conversation_history = await self.summarizer.summarize_if_needed(
                messages=conversation_history, current_context=memory_context or ""
            )
            messages.extend(conversation_history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        # ═══════════════════════════════════════════════════════════
        # RL-109: Context Window Management with Token Counting
        # ═══════════════════════════════════════════════════════════

        # Log token statistics
        token_stats = TokenCounter.get_token_stats(messages)
        logger.info(
            f"Context stats: {token_stats['message_count']} messages, "
            f"{token_stats['total_tokens']} tokens "
            f"({token_stats['percent_of_4k_context']}% of 4K context)"
        )

        # Check if messages fit in context window
        if not TokenCounter.fits_in_context(messages):
            logger.warning(
                f"Context window exceeded! "
                f"{token_stats['total_tokens']} tokens > 3000 limit. "
                f"Truncating..."
            )
            messages = TokenCounter.truncate_to_fit(messages)

        return messages

    def _format_character_context(self, character: Dict) -> str:
        """Format character information for context"""
        parts = []

        # RL-126: Include detailed stats if available
        if character.get("stats"):
            parts.append(character["stats"])
        else:
            # Fallback to basic context
            parts.append("CHARACTER CONTEXT:")
            if character.get("name"):
                parts.append(f"Name: {character['name']}")
            if character.get("race"):
                parts.append(f"Race: {character['race']}")
            if character.get("class"):
                parts.append(f"Class: {character['class']}")
            if character.get("level"):
                parts.append(f"Level: {character['level']}")

        # Add roleplay context (background, personality, etc.)
        if character.get("background"):
            parts.append(f"\nBackground: {character['background']}")
        if character.get("personality"):
            parts.append(f"Personality: {character['personality']}")
        if character.get("personality_trait"):
            parts.append(f"Personality Trait: {character['personality_trait']}")
        if character.get("ideal"):
            parts.append(f"Ideal: {character['ideal']}")
        if character.get("bond"):
            parts.append(f"Bond: {character['bond']}")
        if character.get("flaw"):
            parts.append(f"Flaw: {character['flaw']}")

        return "\n".join(parts)

    def _format_game_state(self, state: Dict) -> str:
        """Format game state for context"""
        parts = ["CURRENT GAME STATE:"]

        if state.get("location"):
            parts.append(f"Location: {state['location']}")
        if state.get("time_of_day"):
            parts.append(f"Time: {state['time_of_day']}")
        if state.get("weather"):
            parts.append(f"Weather: {state['weather']}")
        if state.get("party_members"):
            parts.append(f"Party: {', '.join(state['party_members'])}")
        if state.get("active_quest"):
            parts.append(f"Quest: {state['active_quest']}")

        return "\n".join(parts)

    @trace_async("dm_narrate")
    async def narrate(
        self,
        user_action: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        character_context: Optional[Dict] = None,
        game_state: Optional[Dict] = None,
        memory_context: Optional[str] = None,
        language: str = "en",
        character: Optional[Character] = None,
        db: Optional[AsyncSession] = None,
        use_tools: bool = True,
    ) -> Dict:
        """
        Generate DM narration in response to player action

        Args:
            user_action: What the player wants to do
            conversation_history: Previous conversation
            character_context: Character information
            game_state: Current game state
            memory_context: Relevant past memories from vector search
            language: Language for narration ("en" or "fr")
            character: Character model instance (for tool calling)
            db: Database session (for tool calling)
            use_tools: Whether to enable Mistral tool calling (default: True)

        Returns:
            Dictionary with response and metadata

        Raises:
            MistralAPIError: If API call fails
        """
        start_time = time.time()
        try:
            messages = await self._build_messages(
                user_action,
                conversation_history,
                character_context,
                game_state,
                memory_context,
                language,
            )

            logger.debug(
                "Generating narration",
                extra={
                    "extra_data": {
                        "action_preview": user_action[:50],
                        "language": language,
                        "has_context": character_context is not None,
                        "has_memory": memory_context is not None,
                        "use_tools": use_tools,
                    }
                },
            )

            # RL-129: Use Mistral tool calling if enabled and character/db available
            if use_tools and character is not None and db is not None:
                logger.info("Using Mistral tool calling for DM narration")
                tool_result = await self.call_dm_with_tools(
                    messages=messages,
                    character=character,
                    db=db,
                )

                narration = tool_result.get("narration", "")
                tool_calls_made = tool_result.get("tool_calls_made", [])
                character_updates = tool_result.get("character_updates", {})

                # Extract roll request if present
                cleaned_narration, roll_request = self.extract_roll_request(narration)

                # Extract quest complete if present
                cleaned_narration, quest_complete_id = self.extract_quest_complete(
                    cleaned_narration
                )

                duration = time.time() - start_time

                # Record metrics
                metrics.record_dm_narration(
                    duration=duration, has_roll=roll_request is not None, language=language
                )

                logger.info(
                    "Narration generated with tools",
                    extra={
                        "extra_data": {
                            "duration": duration,
                            "has_roll": roll_request is not None,
                            "has_quest_complete": quest_complete_id is not None,
                            "tools_used": len(tool_calls_made),
                            "language": language,
                        }
                    },
                )

                return {
                    "narration": cleaned_narration,
                    "roll_request": roll_request,
                    "quest_complete_id": quest_complete_id,
                    "tool_calls_made": tool_calls_made,
                    "character_updates": character_updates,
                    "tokens_used": 0,  # TODO: Track tokens from tool calling
                    "timestamp": datetime.now(),
                    "model": "mistral-tool-calling",
                }

            # Fall back to regular narration without tools
            response_text = await self.provider_selector.generate_chat(
                messages=[
                    msg for msg in messages if msg["role"] != "system"
                ],  # Exclude system message duplication
                max_tokens=2048,
                temperature=0.7,
            )

            narration = response_text
            # Note: Token usage not available from provider interface yet
            tokens_used = 0

            # Extract roll request if present
            cleaned_narration, roll_request = self.extract_roll_request(narration)

            # Extract quest complete if present
            cleaned_narration, quest_complete_id = self.extract_quest_complete(cleaned_narration)

            duration = time.time() - start_time

            # Record metrics
            metrics.record_dm_narration(
                duration=duration, has_roll=roll_request is not None, language=language
            )

            logger.info(
                "Narration generated",
                extra={
                    "extra_data": {
                        "tokens_used": tokens_used,
                        "duration": duration,
                        "has_roll": roll_request is not None,
                        "has_quest_complete": quest_complete_id is not None,
                        "language": language,
                    }
                },
            )

            if roll_request:
                logger.info("Roll request detected", extra={"extra_data": {"roll": roll_request}})
            if quest_complete_id:
                logger.info(
                    "Quest completion detected",
                    extra={"extra_data": {"quest_id": quest_complete_id}},
                )

            return {
                "narration": cleaned_narration,
                "roll_request": roll_request,
                "quest_complete_id": quest_complete_id,
                "tokens_used": tokens_used,
                "timestamp": datetime.now(),
                "model": "multi-provider",  # Using provider selector
            }

        except (ProviderUnavailableError, RateLimitError) as e:
            duration = time.time() - start_time
            metrics.record_dm_narration(duration=duration, has_roll=False, language=language)
            logger.error(
                "Failed to generate narration",
                extra={"extra_data": {"error": str(e), "duration": duration}},
            )
            raise

    @trace_async("dm_narrate_stream")
    async def narrate_stream(
        self,
        user_action: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        character_context: Optional[Dict] = None,
        game_state: Optional[Dict] = None,
        memory_context: Optional[str] = None,
        language: str = "en",
    ) -> AsyncGenerator[str, None]:
        """
        Stream DM narration in real-time

        Args:
            user_action: What the player wants to do
            conversation_history: Previous conversation
            character_context: Character information
            game_state: Current game state
            memory_context: Relevant past memories from vector search
            language: Language for narration ("en" or "fr")

        Yields:
            Narration text chunks

        Raises:
            MistralAPIError: If API call fails
        """
        try:
            messages = await self._build_messages(
                user_action,
                conversation_history,
                character_context,
                game_state,
                memory_context,
                language,
            )

            logger.debug(f"Streaming narration for action: {user_action[:50]}...")

            # TODO: Implement streaming in provider_selector
            # For now, fallback to non-streaming
            response_text = await self.provider_selector.generate_chat(
                messages=[msg for msg in messages if msg["role"] != "system"],
                max_tokens=2048,
                temperature=0.7,
            )
            yield response_text

            logger.info("Narration streaming completed")

        except (ProviderUnavailableError, RateLimitError) as e:
            logger.error(f"Failed to stream narration: {e}")
            raise

    async def start_adventure(
        self, setting: str = "classic fantasy dungeon", character_context: Optional[Dict] = None
    ) -> Dict:
        """
        Generate opening narration for a new adventure

        Args:
            setting: Adventure setting/theme
            character_context: Character information

        Returns:
            Dictionary with opening narration
        """
        opening_prompt = f"""Begin an exciting {setting} adventure.
Set the scene with vivid description and present an immediate hook or challenge.
The adventure should feel dangerous, mysterious, and full of possibility."""

        return await self.narrate(opening_prompt, character_context=character_context)

    async def start_adventure_stream(
        self, setting: str = "classic fantasy dungeon", character_context: Optional[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream opening narration for a new adventure

        Args:
            setting: Adventure setting/theme
            character_context: Character information

        Yields:
            Opening narration chunks
        """
        opening_prompt = f"""Begin an exciting {setting} adventure.
Set the scene with vivid description and present an immediate hook or challenge.
The adventure should feel dangerous, mysterious, and full of possibility."""

        async for chunk in self.narrate_stream(opening_prompt, character_context=character_context):
            yield chunk


# Global DM Engine instance
_dm_engine: Optional[DMEngine] = None


def get_dm_engine() -> DMEngine:
    """
    Get or create the global DM Engine instance

    Returns:
        DMEngine instance
    """
    global _dm_engine
    if _dm_engine is None:
        _dm_engine = DMEngine()
    return _dm_engine
