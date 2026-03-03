"""Tests for app.services.companion_service — CompanionService class."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.services.companion_service import CompanionService
from tests.factories import make_character, make_companion, make_creature, make_user

# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _make_ai_provider(response: str = "I am ready to help!") -> MagicMock:
    provider = MagicMock()
    provider.name = "test_provider"
    provider.generate_chat = AsyncMock(return_value=response)
    return provider


def _make_companion_obj(**kw):
    """Create a companion with a linked creature for stat lookups."""
    creature = make_creature(name="Elf Scout")
    user = make_user()
    char = make_character(user=user)
    defaults = {
        "character": char,
        "creature": creature,
        "name": "Elara Swiftwind",
        "personality": "brave, loyal, curious",
        "goals": "Find her missing brother",
        "background": "A ranger from the northern forests",
        "loyalty": 50,
        "strength": 12,
        "dexterity": 16,
        "constitution": 10,
        "intelligence": 14,
        "wisdom": 12,
        "charisma": 10,
    }
    defaults.update(kw)
    return make_companion(**defaults), char


# ═══════════════════════════════════════════════════════════════════
# __init__
# ═══════════════════════════════════════════════════════════════════


class TestInit:
    def test_stores_provider(self):
        provider = _make_ai_provider()
        svc = CompanionService(provider)
        assert svc.ai_provider is provider


# ═══════════════════════════════════════════════════════════════════
# _get_loyalty_behavior
# ═══════════════════════════════════════════════════════════════════


class TestGetLoyaltyBehavior:
    def test_very_high_loyalty(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(90)
        assert "devoted" in result.lower() or "High Loyalty" in result

    def test_good_loyalty(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(65)
        assert "cooperative" in result.lower() or "Good Loyalty" in result

    def test_neutral_loyalty(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(45)
        assert "pragmatic" in result.lower() or "Neutral" in result

    def test_low_loyalty(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(25)
        assert "hesitant" in result.lower() or "Low Loyalty" in result

    def test_very_low_loyalty(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(10)
        assert "reluctant" in result.lower() or "Very Low" in result

    def test_boundary_80(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(80)
        assert "High Loyalty" in result

    def test_boundary_60(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(60)
        assert "Good Loyalty" in result

    def test_boundary_40(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(40)
        assert "Neutral" in result

    def test_boundary_20(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(20)
        assert "Low Loyalty" in result

    def test_boundary_0(self):
        svc = CompanionService(_make_ai_provider())
        result = svc._get_loyalty_behavior(0)
        assert "Very Low" in result


# ═══════════════════════════════════════════════════════════════════
# _get_loyalty_descriptor
# ═══════════════════════════════════════════════════════════════════


class TestGetLoyaltyDescriptor:
    def test_all_levels(self):
        svc = CompanionService(_make_ai_provider())
        assert svc._get_loyalty_descriptor(90) == "devoted and protective"
        assert svc._get_loyalty_descriptor(65) == "cooperative and helpful"
        assert svc._get_loyalty_descriptor(45) == "neutral and pragmatic"
        assert svc._get_loyalty_descriptor(25) == "hesitant and questioning"
        assert svc._get_loyalty_descriptor(10) == "reluctant and defiant"


# ═══════════════════════════════════════════════════════════════════
# _get_fallback_response
# ═══════════════════════════════════════════════════════════════════


class TestGetFallbackResponse:
    def test_brave_personality(self):
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(personality="brave and bold")
        result = svc._get_fallback_response(companion)
        assert companion.name in result
        assert "nods firmly" in result

    def test_cautious_personality(self):
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(personality="cautious and careful")
        result = svc._get_fallback_response(companion)
        assert "warily" in result

    def test_friendly_personality(self):
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(personality="friendly and loyal")
        result = svc._get_fallback_response(companion)
        assert "reassuring" in result

    def test_curious_personality(self):
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(personality="very curious")
        result = svc._get_fallback_response(companion)
        assert "keen interest" in result

    def test_default_personality(self):
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(personality="mysterious and aloof")
        result = svc._get_fallback_response(companion)
        assert "remains at your side" in result


# ═══════════════════════════════════════════════════════════════════
# _build_companion_prompt
# ═══════════════════════════════════════════════════════════════════


class TestBuildCompanionPrompt:
    def test_includes_companion_name(self):
        svc = CompanionService(_make_ai_provider())
        companion, char = _make_companion_obj()
        prompt = svc._build_companion_prompt(
            companion=companion,
            player_action="I look around",
            dm_narration="The forest is quiet",
            recent_context=[],
            character=char,
        )
        assert companion.name in prompt

    def test_includes_personality(self):
        svc = CompanionService(_make_ai_provider())
        companion, char = _make_companion_obj(personality="sarcastic and witty")
        prompt = svc._build_companion_prompt(
            companion=companion,
            player_action="attack",
            dm_narration="Combat begins",
            recent_context=[],
            character=char,
        )
        assert "sarcastic" in prompt

    def test_includes_goals(self):
        svc = CompanionService(_make_ai_provider())
        companion, char = _make_companion_obj(goals="Destroy the ring")
        prompt = svc._build_companion_prompt(
            companion=companion,
            player_action="rest",
            dm_narration="Night falls",
            recent_context=[],
            character=char,
        )
        assert "Destroy the ring" in prompt

    def test_includes_recent_context(self):
        svc = CompanionService(_make_ai_provider())
        companion, char = _make_companion_obj()
        context = [
            {"role": "user", "content": "Let's go north"},
            {"role": "assistant", "content": "You travel north through the woods"},
        ]
        prompt = svc._build_companion_prompt(
            companion=companion,
            player_action="continue",
            dm_narration="You see a cave",
            recent_context=context,
            character=char,
        )
        assert "go north" in prompt or "travel north" in prompt

    def test_high_stat_modifier_description(self):
        svc = CompanionService(_make_ai_provider())
        companion, char = _make_companion_obj(strength=20, dexterity=20)  # +5 mod each
        prompt = svc._build_companion_prompt(
            companion=companion,
            player_action="fight",
            dm_narration="battle",
            recent_context=[],
            character=char,
        )
        assert "very strong" in prompt
        assert "very agile" in prompt

    def test_average_abilities(self):
        svc = CompanionService(_make_ai_provider())
        companion, char = _make_companion_obj(
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
        )
        prompt = svc._build_companion_prompt(
            companion=companion,
            player_action="talk",
            dm_narration="a merchant appears",
            recent_context=[],
            character=char,
        )
        assert "average abilities" in prompt


# ═══════════════════════════════════════════════════════════════════
# generate_companion_response
# ═══════════════════════════════════════════════════════════════════


class TestGenerateCompanionResponse:
    async def test_successful_response(self):
        provider = _make_ai_provider("I shall protect you, friend!")
        svc = CompanionService(provider)
        companion, char = _make_companion_obj()

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            result = await svc.generate_companion_response(
                companion=companion,
                player_action="I draw my sword",
                dm_narration="A dragon appears!",
                recent_context=[],
                character=char,
            )

        assert result == "I shall protect you, friend!"

    async def test_fallback_on_error(self):
        provider = _make_ai_provider()
        provider.generate_chat = AsyncMock(side_effect=Exception("API error"))
        svc = CompanionService(provider)
        companion, char = _make_companion_obj(personality="brave")

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            result = await svc.generate_companion_response(
                companion=companion,
                player_action="attack",
                dm_narration="combat",
                recent_context=[],
                character=char,
            )

        assert companion.name in result  # fallback includes name


# ═══════════════════════════════════════════════════════════════════
# should_companion_respond
# ═══════════════════════════════════════════════════════════════════


class TestShouldCompanionRespond:
    async def test_combat_turn(self):
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(name="Elara")

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            result = await svc.should_companion_respond(
                companion=companion,
                player_action="I wait",
                dm_narration="It's elara's turn to act",
                combat_active=True,
            )

        assert result is True

    async def test_direct_address(self):
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(name="Elara")

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            result = await svc.should_companion_respond(
                companion=companion,
                player_action="Elara, what do you think?",
                dm_narration="The path splits.",
            )

        assert result is True

    async def test_opinion_keyword(self):
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(name="Zara")

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            result = await svc.should_companion_respond(
                companion=companion,
                player_action="what do you think we should do?",
                dm_narration="The room is empty.",
            )

        assert result is True

    async def test_mentioned_in_narration(self):
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(name="Elara")

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            result = await svc.should_companion_respond(
                companion=companion,
                player_action="I move forward",
                dm_narration="Elara notices something strange in the shadows.",
            )

        assert result is True

    async def test_no_trigger_usually_false(self):
        """Without triggers, the companion usually doesn't respond (90% chance)."""
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(name="Zxyl")

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            with patch("app.services.companion_service.random") as mock_random:
                mock_random.random.return_value = 0.5  # > 0.1, so False
                result = await svc.should_companion_respond(
                    companion=companion,
                    player_action="I walk forward",
                    dm_narration="The road is quiet.",
                )

        assert result is False

    async def test_random_chance_triggers(self):
        """10% random chance should trigger."""
        svc = CompanionService(_make_ai_provider())
        companion, _ = _make_companion_obj(name="Zxyl")

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            with patch("app.services.companion_service.random") as mock_random:
                mock_random.random.return_value = 0.05  # < 0.1, triggers
                result = await svc.should_companion_respond(
                    companion=companion,
                    player_action="I walk forward",
                    dm_narration="The road is quiet.",
                )

        assert result is True


# ═══════════════════════════════════════════════════════════════════
# update_companion_loyalty
# ═══════════════════════════════════════════════════════════════════


class TestUpdateCompanionLoyalty:
    async def test_increase_loyalty(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Guard")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature, loyalty=50)
        db_session.add(companion)
        await db_session.flush()

        svc = CompanionService(_make_ai_provider())

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            await svc.update_companion_loyalty(
                companion=companion,
                event_description="Saved companion from danger",
                loyalty_change=20,
                db=db_session,
            )

        assert companion.loyalty == 70
        assert companion.relationship_status == "friend"

    async def test_decrease_loyalty(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Guard")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature, loyalty=30)
        db_session.add(companion)
        await db_session.flush()

        svc = CompanionService(_make_ai_provider())

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            await svc.update_companion_loyalty(
                companion=companion,
                event_description="Left companion behind",
                loyalty_change=-15,
                db=db_session,
            )

        assert companion.loyalty == 15
        assert companion.relationship_status == "just_met"

    async def test_loyalty_clamped_at_100(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Guard")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature, loyalty=90)
        db_session.add(companion)
        await db_session.flush()

        svc = CompanionService(_make_ai_provider())

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            await svc.update_companion_loyalty(
                companion=companion,
                event_description="Epic heroism",
                loyalty_change=50,
                db=db_session,
            )

        assert companion.loyalty == 100
        assert companion.relationship_status == "trusted"

    async def test_loyalty_clamped_at_0(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Guard")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature, loyalty=10)
        db_session.add(companion)
        await db_session.flush()

        svc = CompanionService(_make_ai_provider())

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            await svc.update_companion_loyalty(
                companion=companion,
                event_description="Terrible betrayal",
                loyalty_change=-50,
                db=db_session,
            )

        assert companion.loyalty == 0
        assert companion.relationship_status == "just_met"

    async def test_relationship_status_trusted(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Guard")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature, loyalty=75)
        db_session.add(companion)
        await db_session.flush()

        svc = CompanionService(_make_ai_provider())

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            await svc.update_companion_loyalty(
                companion=companion,
                event_description="Grand sacrifice",
                loyalty_change=10,
                db=db_session,
            )

        assert companion.loyalty == 85
        assert companion.relationship_status == "trusted"

    async def test_relationship_status_ally(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Guard")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature, loyalty=45)
        db_session.add(companion)
        await db_session.flush()

        svc = CompanionService(_make_ai_provider())

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            await svc.update_companion_loyalty(
                companion=companion,
                event_description="Minor help",
                loyalty_change=0,
                db=db_session,
            )

        assert companion.loyalty == 45
        assert companion.relationship_status == "ally"

    async def test_relationship_status_suspicious(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature(name="Guard")
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature, loyalty=35)
        db_session.add(companion)
        await db_session.flush()

        svc = CompanionService(_make_ai_provider())

        with patch("app.services.companion_service.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.return_value.start_as_current_span.return_value = mock_span

            await svc.update_companion_loyalty(
                companion=companion,
                event_description="Questionable action",
                loyalty_change=-10,
                db=db_session,
            )

        assert companion.loyalty == 25
        assert companion.relationship_status == "suspicious"
