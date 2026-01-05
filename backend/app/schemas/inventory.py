"""Pydantic schemas for inventory system"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import ItemType


class ItemCreate(BaseModel):
    """Schema for creating a new item"""

    name: str = Field(..., min_length=1, max_length=100)
    item_type: ItemType
    weight: float = Field(default=0, ge=0, description="Weight in pounds")
    value: float = Field(default=0, ge=0, description="Value in gold pieces")
    properties: Optional[dict] = Field(
        default=None, description="Item-specific properties (damage, AC, effects, etc.)"
    )
    equipped: bool = Field(default=False)
    quantity: int = Field(default=1, ge=1)


class ItemUpdate(BaseModel):
    """Schema for updating an item"""

    quantity: Optional[int] = Field(default=None, ge=0)
    equipped: Optional[bool] = None
    properties: Optional[dict] = None


class ItemResponse(BaseModel):
    """Schema for item response"""

    id: UUID
    character_id: UUID
    name: str
    item_type: ItemType
    weight: float
    value: float
    properties: dict
    equipped: bool
    quantity: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryResponse(BaseModel):
    """Schema for full inventory response"""

    items: list[ItemResponse]
    current_weight: float
    carrying_capacity: int
    weight_percentage: float
