"""Database model for generated scene images"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base


class GeneratedImage(Base):
    """Stores metadata about generated scene images for reuse"""

    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, index=True)
    description_hash = Column(String(32), unique=True, index=True, nullable=False)
    description_text = Column(Text, nullable=False)
    image_path = Column(String(255), nullable=False)
    model_used = Column(String(50), default="mistral-medium-latest")
    reuse_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<GeneratedImage(hash={self.description_hash}, reuse_count={self.reuse_count})>"
