"""Item model for character inventory"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import ItemType


class Item(Base):
    """Item model for character inventory"""

    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    item_type: Mapped[ItemType] = mapped_column(
        Enum(
            ItemType,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )

    # Weight in pounds (D&D 5e standard)
    weight: Mapped[float] = mapped_column(Integer, default=0, nullable=False)

    # Value in gold pieces
    value: Mapped[float] = mapped_column(Integer, default=0, nullable=False)

    # Flexible storage for item-specific properties
    # Examples: damage_dice, ac_bonus, attack_bonus, charges, effects, etc.
    properties: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Inventory management
    equipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    character = relationship("Character", back_populates="items")

    # Indexes
    __table_args__ = (
        Index("ix_items_character_type", "character_id", "item_type"),
        Index("ix_items_character_equipped", "character_id", "equipped"),
    )

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, name={self.name}, type={self.item_type})>"
