"""
DM Pre-heating Service
Primes the DM with invisible messages to reinforce rule adherence
"""


class DMPreheater:
    """
    Warm up DM AI with rule reinforcement messages.
    Prevents rule degradation by priming the model with reminders.
    """

    WARMUP_EXCHANGES = [
        {
            "user": "Remember: Always use request_player_roll tool for ANY player action requiring a dice roll. Never narrate roll results.",
            "assistant": "Understood. I will use request_player_roll for player attacks, ability checks, and saving throws. I will wait for the actual roll result before narrating.",
        },
        {
            "user": "Remember: Always use roll_for_npc tool for ALL NPC/monster rolls. Never state NPC roll results narratively.",
            "assistant": "Confirmed. I will use roll_for_npc for NPC attacks, damage, saves, and checks. I will never say 'the goblin hits for 8 damage' - I will call the tool.",
        },
        {
            "user": "Remember: Use update_character_hp immediately when damage or healing occurs. Use give_item when awarding loot.",
            "assistant": "I will use update_character_hp for all HP changes and give_item when distributing loot from the item catalog.",
        },
        {
            "user": "Remember: Use get_creature_stats before combat to get accurate monster stats. Use search_items before giving loot.",
            "assistant": "I will look up creature stats at encounter start and search the item catalog before awarding items.",
        },
        {
            "user": "Start the adventure. The player is ready.",
            "assistant": "I'm ready to guide this adventure following all D&D 5e rules and using the available tools appropriately.",
        },
    ]

    @classmethod
    def get_warmup_messages(cls) -> list[dict[str, str]]:
        """
        Get warmup messages to inject at conversation start.
        These prime the AI but aren't shown to player.

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        messages = []
        for exchange in cls.WARMUP_EXCHANGES:
            messages.append({"role": "user", "content": exchange["user"]})
            messages.append({"role": "assistant", "content": exchange["assistant"]})
        return messages

    @classmethod
    def inject_periodic_reminder(cls, turn_number: int) -> dict[str, str] | None:
        """
        Inject reminder at specific intervals.

        Args:
            turn_number: Current turn number (user messages divided by 2)

        Returns:
            Message dict with reminder, or None if no reminder needed
        """
        # Every 10 turns, reinforce tool usage
        if turn_number > 0 and turn_number % 10 == 0:
            return {
                "role": "user",
                "content": "Quick reminder: Use tools for rolls (request_player_roll, roll_for_npc), HP changes (update_character_hp), and loot (give_item).",
            }
        return None
