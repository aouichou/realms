"""Inventory management endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import Character, Item, ItemType
from app.schemas.inventory import InventoryResponse, ItemCreate, ItemResponse, ItemUpdate
from app.services.memory_capture import MemoryCaptureService
from app.utils.logger import logger

router = APIRouter(prefix="/api/characters", tags=["inventory"])


@router.post(
    "/{character_id}/inventory/add",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(character_id: UUID, item_data: ItemCreate, db: AsyncSession = Depends(get_db)):
    """Add an item to character's inventory"""
    # Verify character exists
    character_result = await db.execute(select(Character).where(Character.id == character_id))
    character = character_result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    # Check weight capacity
    current_weight_result = await db.execute(
        select(func.coalesce(func.sum(Item.weight * Item.quantity), 0)).where(
            Item.character_id == character_id
        )
    )
    current_weight = current_weight_result.scalar() or 0
    new_total_weight = current_weight + (item_data.weight * item_data.quantity)

    if new_total_weight > character.carrying_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adding this item would exceed carrying capacity. Current: {current_weight} lbs, "
            f"New item: {item_data.weight * item_data.quantity} lbs, "
            f"Capacity: {character.carrying_capacity} lbs",
        )

    # Create item
    new_item = Item(
        character_id=character_id,
        name=item_data.name,
        item_type=item_data.item_type,
        weight=item_data.weight,
        value=item_data.value,
        properties=item_data.properties or {},
        equipped=item_data.equipped,
        quantity=item_data.quantity,
    )

    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    # Capture loot acquisition as memory
    try:
        from app.db.models import GameSession
        result_session = await db.execute(
            select(GameSession).where(GameSession.character_id == character_id).order_by(GameSession.created_at.desc()).limit(1)
        )
        session = result_session.scalar_one_or_none()
        
        if session:
            await MemoryCaptureService.capture_loot(
                db=db,
                session_id=session.id,
                item_name=new_item.name,
                item_type=new_item.item_type.value,
                value=new_item.value,
                details=f"Acquired {new_item.quantity}x {new_item.name}",
            )
    except Exception as e:
        logger.warning(f"Failed to capture loot acquisition memory: {e}")

    return new_item


@router.get("/{character_id}/inventory", response_model=InventoryResponse)
async def get_inventory(
    character_id: UUID,
    item_type: ItemType | None = None,
    equipped: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get character's inventory with optional filters"""
    # Verify character exists and get carrying capacity
    character_result = await db.execute(select(Character).where(Character.id == character_id))
    character = character_result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    # Build query
    query = select(Item).where(Item.character_id == character_id)

    if item_type is not None:
        query = query.where(Item.item_type == item_type)

    if equipped is not None:
        query = query.where(Item.equipped == equipped)

    # Get items
    items_result = await db.execute(query)
    items = items_result.scalars().all()

    # Calculate total weight
    weight_result = await db.execute(
        select(func.coalesce(func.sum(Item.weight * Item.quantity), 0)).where(
            Item.character_id == character_id
        )
    )
    current_weight = weight_result.scalar() or 0

    return InventoryResponse(
        items=list(items),
        current_weight=current_weight,
        carrying_capacity=character.carrying_capacity,
        weight_percentage=(current_weight / character.carrying_capacity * 100)
        if character.carrying_capacity > 0
        else 0,
    )


@router.patch("/{character_id}/inventory/{item_id}/equip", response_model=ItemResponse)
async def toggle_equip_item(character_id: UUID, item_id: UUID, db: AsyncSession = Depends(get_db)):
    """Toggle item equipped status"""
    # Get item
    item_result = await db.execute(
        select(Item).where(Item.id == item_id, Item.character_id == character_id)
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found for character {character_id}",
        )

    # Toggle equipped status
    item.equipped = not item.equipped

    await db.commit()
    await db.refresh(item)

    return item


@router.patch("/{character_id}/inventory/{item_id}", response_model=ItemResponse)
async def update_item(
    character_id: UUID, item_id: UUID, item_data: ItemUpdate, db: AsyncSession = Depends(get_db)
):
    """Update item quantity or other properties"""
    # Get item
    item_result = await db.execute(
        select(Item).where(Item.id == item_id, Item.character_id == character_id)
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found for character {character_id}",
        )

    # Update fields if provided
    if item_data.quantity is not None:
        if item_data.quantity <= 0:
            # Delete item if quantity is 0 or less
            await db.delete(item)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_204_NO_CONTENT, detail="Item removed from inventory"
            )
        item.quantity = item_data.quantity

    if item_data.equipped is not None:
        item.equipped = item_data.equipped

    if item_data.properties is not None:
        item.properties = item_data.properties

    await db.commit()
    await db.refresh(item)

    return item


@router.delete("/{character_id}/inventory/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(character_id: UUID, item_id: UUID, db: AsyncSession = Depends(get_db)):
    """Remove an item from inventory"""
    # Get item
    item_result = await db.execute(
        select(Item).where(Item.id == item_id, Item.character_id == character_id)
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found for character {character_id}",
        )

    await db.delete(item)
    await db.commit()

    return None
