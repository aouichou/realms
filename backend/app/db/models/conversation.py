import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import MessageRole


class ConversationMessage(Base):
    """Conversation message model for persistent chat history"""

    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(
        Enum(
            MessageRole,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scene_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    companion_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companions.id", ondelete="SET NULL"),
        nullable=True,
    )  # RL-131: Link to companion if role is 'companion'

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    session = relationship("GameSession", back_populates="messages")

    # Indexes for efficient querying
    __table_args__ = (Index("ix_messages_session_created", "session_id", "created_at"),)

    def __repr__(self) -> str:
        return (
            f"<ConversationMessage(id={self.id}, session_id={self.session_id}, role={self.role})>"
        )
