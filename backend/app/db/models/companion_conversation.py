"""
Companion Conversation database model for storing shared player-companion chats.
Allows DMs to view conversations that players choose to share.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class CompanionConversation(Base):
    """
    Stores individual messages in companion-player conversations.
    Only saved if player chooses to share with DM.
    """

    __tablename__ = "companion_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Relationships
    companion_id = Column(
        UUID(as_uuid=True), ForeignKey("companions.id"), nullable=False, index=True
    )
    character_id = Column(
        UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False, index=True
    )

    # Message content
    role = Column(String(20), nullable=False)  # "player" or "companion"
    message = Column(Text, nullable=False)

    # Sharing control
    shared_with_dm = Column(Boolean, default=False, nullable=False, index=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    companion = relationship("Companion")
    character = relationship("Character")

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "companion_id": str(self.companion_id),
            "character_id": str(self.character_id),
            "role": self.role,
            "message": self.message,
            "shared_with_dm": self.shared_with_dm,
            "created_at": self.created_at.isoformat(),
        }
