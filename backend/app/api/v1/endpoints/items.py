"""
API endpoints for item catalog lookup.
Part of RL-132: Items Dataset

Provides REST API for querying D&D 5e equipment, weapons, armor, and magic items.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models.item_catalog import ItemCatalog
from app.db.models.user import User
from app.middleware.auth import get_current_user

router = APIRouter()


@router.get("/search", response_model=dict[str, Any])
async def search_items(
    query: str | None = Query(None, description="Search term for item name or description"),
    category: str | None = Query(
        None, description="Filter by category (e.g., weapon, armor, potion)"
    ),
    rarity: str | None = Query(None, description="Filter by rarity"),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Search items in the catalog with optional filters.

    Returns list of items matching search criteria.
    """
    # Build query
    stmt = select(ItemCatalog)

    # Apply filters
    if query:
        search_term = f"%{query.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(ItemCatalog.name).like(search_term),
                func.lower(ItemCatalog.description).like(search_term),
            )
        )

    if category:
        stmt = stmt.where(func.lower(ItemCatalog.category) == func.lower(category))

    if rarity:
        stmt = stmt.where(func.lower(ItemCatalog.rarity).like(f"%{rarity.lower()}%"))

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply pagination and execute
    stmt = stmt.offset(offset).limit(limit).order_by(ItemCatalog.name)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [item.to_dict() for item in items],
    }


@router.get("/categories", response_model=dict[str, Any])
async def list_categories(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get all unique item categories for UI filters.

    Returns list of categories with counts.
    """
    query = (
        select(ItemCatalog.category, func.count(ItemCatalog.id).label("count"))
        .group_by(ItemCatalog.category)
        .order_by(func.count(ItemCatalog.id).desc())
    )

    result = await db.execute(query)
    categories = [{"category": row[0], "count": row[1]} for row in result.all()]

    return {"categories": categories}


@router.get("/random", response_model=dict[str, Any])
async def random_item(
    category: str | None = Query(None, description="Filter by category"),
    rarity: str | None = Query(None, description="Filter by rarity"),
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get a random item for loot generation.

    Useful for DM tools to quickly generate treasure.
    """
    stmt = select(ItemCatalog)

    # Apply filters
    if category:
        stmt = stmt.where(func.lower(ItemCatalog.category) == func.lower(category))

    if rarity:
        stmt = stmt.where(func.lower(ItemCatalog.rarity).like(f"%{rarity.lower()}%"))

    # Order randomly and take first
    stmt = stmt.order_by(func.random()).limit(1)

    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=404, detail="No items found matching the specified criteria"
        )

    return {"item": item.to_dict()}


@router.get("/{item_id}", response_model=dict[str, Any])
async def get_item_by_id(
    item_id: int,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get specific item details by ID.

    Returns full item data including stats and properties.
    """
    query = select(ItemCatalog).where(ItemCatalog.id == item_id)
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail=f"Item with ID {item_id} not found")

    return {"item": item.to_dict()}


@router.get("/name/{item_name}", response_model=dict[str, Any])
async def get_item_by_name(
    item_name: str,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get item by name (fuzzy match).

    Returns item data. Uses case-insensitive partial matching.
    """
    # Try exact match first
    query = select(ItemCatalog).where(func.lower(ItemCatalog.name) == func.lower(item_name))
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    # If no exact match, try fuzzy match
    if not item:
        query = select(ItemCatalog).where(
            func.lower(ItemCatalog.name).contains(func.lower(item_name))
        )
        result = await db.execute(query.limit(1))
        item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail=f"Item '{item_name}' not found in catalog")

    return {"item": item.to_dict()}
