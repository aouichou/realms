"""
User account model with guest mode support
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """User account model with guest mode support"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Email is nullable for guest mode
    email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    # Username is always required (generated for guests)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Password hash is nullable for guest mode (changed from hashed_password to password_hash for consistency)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Guest mode flags
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guest_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )

    # User status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # User preferences
    preferred_language: Mapped[str] = mapped_column(
        String(5), default="en", nullable=False, server_default="en"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    characters = relationship("Character", back_populates="user", cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        guest_str = " (guest)" if self.is_guest else ""
        return f"<User(id={self.id}, username={self.username}{guest_str})>"
