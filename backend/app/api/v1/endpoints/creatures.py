"""
API endpoints for creature/monster/NPC lookup.
Part of RL-130: Creature Stats Dataset

Provides REST API for querying D&D 5e creature statistics.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models.creature import Creature
from app.db.models.user import User
from app.middleware.auth import get_current_user

router = APIRouter()


@router.get("/{creature_name}", response_model=dict[str, Any])
async def get_creature_by_name(
    creature_name: str,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get creature stats by name (fuzzy match).

    Returns creature data including full stat block.
    Uses case-insensitive partial matching.
    """
    # Try exact match first
    query = select(Creature).where(
        func.lower(Creature.name) == func.lower(creature_name)
    )
    result = await db.execute(query)
    creature = result.scalar_one_or_none()

    # If no exact match, try fuzzy match
    if not creature:
        query = select(Creature).where(
            func.lower(Creature.name).contains(func.lower(creature_name))
        )
        result = await db.execute(query.limit(1))
        creature = result.scalar_one_or_none()

    if not creature:
        raise HTTPException(
            status_code=404,
            detail=f"Creature '{creature_name}' not found. Try a more specific name.",
        )

    return {
        "creature": creature.to_dict(),
        "stat_block": creature.get_stat_block(),
    }


@router.get("/", response_model=dict[str, Any])
async def list_creatures(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    creature_type: str | None = Query(None, description="Filter by creature type (e.g., dragon, humanoid)"),
    min_cr: float | None = Query(None, description="Minimum Challenge Rating"),
    max_cr: float | None = Query(None, description="Maximum Challenge Rating"),
    search: str | None = Query(None, description="Search in name"),
    limit: int = Query(50, le=100, description="Max results to return"),
    offset: int = Query(0, description="Results to skip"),
) -> dict[str, Any]:
    """
    List creatures with optional filtering.

    Supports filtering by:
    - creature_type: dragon, humanoid, undead, etc.
    - min_cr/max_cr: Challenge Rating range
    - search: Partial name match

    Returns list of creatures with pagination.
    """
    query = select(Creature)

    # Apply filters
    filters = []

    if creature_type:
        filters.append(Creature.creature_type == creature_type.lower())

    if min_cr is not None:
        filters.append(Creature.cr >= min_cr)

    if max_cr is not None:
        filters.append(Creature.cr <= max_cr)

    if search:
        filters.append(
            or_(
                func.lower(Creature.name).contains(func.lower(search)),
                func.lower(Creature.creature_type).contains(func.lower(search)),
            )
        )

    if filters:
        query = query.where(*filters)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Apply pagination and ordering
    query = query.order_by(Creature.cr, Creature.name).limit(limit).offset(offset)
    result = await db.execute(query)
    creatures = result.scalars().all()

    return {
        "creatures": [c.to_dict() for c in creatures],
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "creature_type": creature_type,
            "min_cr": min_cr,
            "max_cr": max_cr,
            "search": search,
        },
    }


@router.get("/types/list", response_model=dict[str, Any])
async def list_creature_types(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get list of all unique creature types in database.

    Useful for filtering and UI dropdowns.
    """
    query = select(Creature.creature_type, func.count(Creature.id)).group_by(
        Creature.creature_type
    ).order_by(func.count(Creature.id).desc())

    result = await db.execute(query)
    types = result.all()

    return {
        "creature_types": [
            {"type": type_name, "count": count}
            for type_name, count in types
        ],
        "total_types": len(types),
    }

