"""
Companion combat service for handling companion actions in combat.
Parses companion AI responses for actions and executes dice rolls.
"""


import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.companion import Companion
from app.services.dice_service import DiceService
from app.observability.logger import get_logger

logger = get_logger(__name__)


class CompanionCombatService:
    """
    Service for executing companion combat actions.

    Parses companion responses for action declarations and executes
    corresponding dice rolls and HP updates.
    """

    def __init__(self):
        self.dice_service = DiceService()
        logger.info("CompanionCombatService initialized")

    async def parse_and_execute_actions(
        self,
        companion: Companion,
        companion_response: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Parse companion response for action declarations and execute them.

        Args:
            companion: Companion model
            companion_response: Raw AI response from companion
            db: Database session

        Returns:
            Dictionary with executed actions and results
        """
        executed_actions = {
            "attack_rolls": [],
            "saving_throws": [],
            "ability_checks": [],
            "damage_dealt": 0,
            "damage_taken": 0,
        }

        # Parse for attack actions
        attack_match = re.search(
            r"\*\*Attack:\*\*.*?(?:attack|strike|hit).*?(?:with|using)\s+(\w+)",
            companion_response,
            re.IGNORECASE,
        )
        if attack_match:
            weapon = attack_match.group(1)
            attack_result = await self._execute_attack_roll(companion, weapon)
            executed_actions["attack_rolls"].append(attack_result)
            logger.info(f"Companion {companion.name} attacked with {weapon}: {attack_result}")

        # Parse for saving throws
        save_match = re.search(
            r"saving throw.*?(STR|DEX|CON|INT|WIS|CHA)", companion_response, re.IGNORECASE
        )
        if save_match:
            ability = save_match.group(1).upper()
            save_result = await self._execute_saving_throw(companion, ability)
            executed_actions["saving_throws"].append(save_result)
            logger.info(f"Companion {companion.name} made {ability} save: {save_result}")

        # Parse for ability checks
        check_match = re.search(
            r"(?:check|attempt).*?(STR|DEX|CON|INT|WIS|CHA|Perception|Stealth|Investigation)",
            companion_response,
            re.IGNORECASE,
        )
        if check_match:
            ability_or_skill = check_match.group(1)
            check_result = await self._execute_ability_check(companion, ability_or_skill)
            executed_actions["ability_checks"].append(check_result)
            logger.info(f"Companion {companion.name} made {ability_or_skill} check: {check_result}")

        return executed_actions

    async def _execute_attack_roll(self, companion: Companion, weapon: str) -> dict[str, Any]:
        """Execute an attack roll for the companion."""
        # Determine attack modifier (use DEX for ranged, STR for melee)
        # Simple heuristic: bow/crossbow = ranged
        is_ranged = "bow" in weapon.lower() or "crossbow" in weapon.lower()

        if is_ranged:
            attack_mod = companion.get_stat_modifier(companion.dexterity)  # type: ignore
        else:
            attack_mod = companion.get_stat_modifier(companion.strength)  # type: ignore

        # Roll attack (d20 + modifier) - roll_dice is async
        attack_roll_result = await self.dice_service.roll_dice("1d20")
        attack_roll = attack_roll_result[1]  # Get total from tuple (rolls, total, modifier)
        total = attack_roll + attack_mod

        # Determine if critical
        is_critical = attack_roll == 20
        is_critical_fail = attack_roll == 1

        result = {
            "type": "attack",
            "weapon": weapon,
            "roll": attack_roll,
            "modifier": attack_mod,
            "total": total,
            "is_critical": is_critical,
            "is_critical_fail": is_critical_fail,
        }

        # If hit, roll damage (simple 1d6 + mod for now)
        if total >= 10 and not is_critical_fail:  # Assume AC 10 target
            damage_roll_result = await self.dice_service.roll_dice("1d6")
            damage_roll = damage_roll_result[1]  # Get total
            damage_total = damage_roll + attack_mod
            if is_critical:
                damage_total *= 2

            result["damage"] = damage_total
            result["damage_roll"] = damage_roll

        return result

    async def _execute_saving_throw(self, companion: Companion, ability: str) -> dict[str, Any]:
        """Execute a saving throw for the companion."""
        ability_map = {  # type: ignore
            "STR": companion.strength,
            "DEX": companion.dexterity,
            "CON": companion.constitution,
            "INT": companion.intelligence,
            "WIS": companion.wisdom,
            "CHA": companion.charisma,
        }

        ability_score = ability_map.get(ability.upper(), 10)
        modifier = companion.get_stat_modifier(ability_score)  # type: ignore

        # Roll save (d20 + modifier) - roll_dice is async
        save_roll_result = await self.dice_service.roll_dice("1d20")
        save_roll = save_roll_result[1]  # Get total
        total = save_roll + modifier

        return {
            "type": "saving_throw",
            "ability": ability,
            "roll": save_roll,
            "modifier": modifier,
            "total": total,
        }

    async def _execute_ability_check(
        self, companion: Companion, ability_or_skill: str
    ) -> dict[str, Any]:
        """Execute an ability check for the companion."""
        # Map skills to abilities
        skill_to_ability = {
            "Perception": "WIS",
            "Stealth": "DEX",
            "Investigation": "INT",
            "Insight": "WIS",
            "Athletics": "STR",
            "Acrobatics": "DEX",
        }

        ability = skill_to_ability.get(ability_or_skill, ability_or_skill)

        ability_map = {  # type: ignore
            "STR": companion.strength,
            "DEX": companion.dexterity,
            "CON": companion.constitution,
            "INT": companion.intelligence,
            "WIS": companion.wisdom,
            "CHA": companion.charisma,
        }

        ability_score = ability_map.get(ability.upper(), 10)
        modifier = companion.get_stat_modifier(ability_score)  # type: ignore

        # Roll check (d20 + modifier) - roll_dice is async
        check_roll_result = await self.dice_service.roll_dice("1d20")
        check_roll = check_roll_result[1]  # Get total
        total = check_roll + modifier

        return {
            "type": "ability_check",
            "ability": ability,
            "skill": ability_or_skill if ability_or_skill in skill_to_ability else None,
            "roll": check_roll,
            "modifier": modifier,
            "total": total,
        }

    async def apply_damage_to_companion(
        self,
        companion: Companion,
        damage: int,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Apply damage to companion and handle unconsciousness/death saves.

        Args:
            companion: Companion model
            damage: Amount of damage to apply
            db: Database session

        Returns:
            Dictionary with companion status after damage
        """
        old_hp = companion.hp  # type: ignore
        new_hp = max(0, old_hp - damage)
        companion.hp = new_hp  # type: ignore

        status = {
            "old_hp": old_hp,
            "new_hp": new_hp,
            "damage": damage,
            "is_unconscious": False,
            "is_dead": False,
        }

        # Check if companion went unconscious
        if new_hp == 0 and old_hp > 0:  # type: ignore
            companion.is_alive = False  # type: ignore
            status["is_unconscious"] = True
            logger.info(f"Companion {companion.name} fell unconscious!")

        # Save changes
        await db.commit()
        await db.refresh(companion)

        return status

    async def heal_companion(
        self,
        companion: Companion,
        healing: int,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Heal companion and potentially revive if unconscious.

        Args:
            companion: Companion model
            healing: Amount of HP to restore
            db: Database session

        Returns:
            Dictionary with companion status after healing
        """
        old_hp = companion.hp  # type: ignore
        max_hp = companion.max_hp  # type: ignore
        new_hp = min(max_hp, old_hp + healing)
        companion.hp = new_hp  # type: ignore

        status = {
            "old_hp": old_hp,
            "new_hp": new_hp,
            "healing": healing,
            "revived": False,
        }

        # Revive if was unconscious
        if new_hp > 0 and not companion.is_alive:  # type: ignore
            companion.is_alive = True  # type: ignore
            companion.death_save_successes = 0  # type: ignore
            companion.death_save_failures = 0  # type: ignore
            status["revived"] = True
            logger.info(f"Companion {companion.name} was revived!")

        # Save changes
        await db.commit()
        await db.refresh(companion)

        return status
