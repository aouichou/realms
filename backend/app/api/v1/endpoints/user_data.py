"""
GDPR User Data endpoints
Provides data export and account deletion (soft delete with anonymization).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_user
from app.observability.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/user", tags=["user-data"])


@router.get("/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all user data (GDPR Article 20 — Right to Data Portability).

    Returns all personal data and associated game data in JSON format.
    """
    # Load user with relationships
    result = await db.execute(
        select(User)
        .where(User.id == current_user.id)
        .options(
            selectinload(User.characters),
            selectinload(User.game_sessions),
        )
    )
    user = result.scalar_one()

    # Build export
    export = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "data_format_version": "1.0",
        "personal_data": {
            "id": str(user.id),
            "username": user.username,
            "email": user.decrypted_email,
            "is_guest": user.is_guest,
            "preferred_language": user.preferred_language,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        },
        "characters": [
            {
                "id": str(c.id),
                "name": c.name,
                "race": c.race.value if hasattr(c, "race") and c.race else None,
                "character_class": c.character_class.value
                if hasattr(c, "character_class") and c.character_class
                else None,
                "level": c.level if hasattr(c, "level") else None,
                "created_at": c.created_at.isoformat()
                if hasattr(c, "created_at") and c.created_at
                else None,
            }
            for c in user.characters
        ],
        "game_sessions": [
            {
                "id": str(s.id),
                "started_at": s.started_at.isoformat()
                if hasattr(s, "started_at") and s.started_at
                else None,
                "is_active": s.is_active if hasattr(s, "is_active") else None,
            }
            for s in user.game_sessions
        ],
    }

    return export


@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete user account (GDPR Article 17 — Right to Erasure).

    Anonymizes all personal data instead of hard deletion:
    - Email is cleared
    - Username is anonymized to "deleted_user_<hash>"
    - Password hash is cleared
    - Account is deactivated

    Game data (characters, sessions) is preserved but de-identified.
    """
    import secrets

    # Anonymize the user
    anon_suffix = secrets.token_hex(4)

    current_user.email = None
    current_user.email_blind_index = None
    current_user.username = f"deleted_user_{anon_suffix}"
    current_user.password_hash = None
    current_user.guest_token = None
    current_user.is_active = False
    current_user.is_guest = False
    current_user.updated_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info(f"User account anonymized: {current_user.id}")

    return {
        "message": "Account successfully deleted and personal data anonymized",
        "note": "Your game characters and sessions have been preserved but de-identified",
    }
