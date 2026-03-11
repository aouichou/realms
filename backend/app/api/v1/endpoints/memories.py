"""Memory API endpoints for vector memory system"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_active_user
from app.observability.logger import get_logger
from app.schemas.memory import (
    MemoryContextResponse,
    MemoryCreate,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
)
from app.services.memory_service import MemoryService
from app.services.ownership import verify_session_ownership

logger = get_logger(__name__)

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=MemoryResponse, status_code=201)
async def create_memory(
    memory_data: MemoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Store a new memory with embedding

    Args:
        memory_data: Memory creation data
        db: Database session

    Returns:
        Created memory

    Raises:
        HTTPException: If memory creation fails
    """
    try:
        await verify_session_ownership(db, memory_data.session_id, current_user.id)
        memory = await MemoryService.store_memory(
            db=db,
            session_id=memory_data.session_id,
            event_type=memory_data.event_type,
            content=memory_data.content,
            importance=memory_data.importance,
            tags=memory_data.tags,
            npcs_involved=memory_data.npcs_involved,
            locations=memory_data.locations,
            items_involved=memory_data.items_involved,
        )

        return MemoryResponse.model_validate(memory)

    except Exception as e:
        logger.exception("Failed to create memory")
        raise HTTPException(status_code=500, detail="Failed to create memory")


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(
    search_request: MemorySearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Search memories using semantic similarity

    Args:
        search_request: Search parameters
        db: Database session

    Returns:
        Matching memories sorted by relevance
    """
    await verify_session_ownership(db, search_request.session_id, current_user.id)
    memories = await MemoryService.search_memories(
        db=db,
        session_id=search_request.session_id,
        query=search_request.query,
        limit=search_request.limit,
        min_importance=search_request.min_importance,
        event_types=search_request.event_types,
        tags=search_request.tags,
    )

    return MemorySearchResponse(
        memories=[MemoryResponse.model_validate(m) for m in memories],
        total=len(memories),
        query=search_request.query,
    )


@router.get("/session/{session_id}/recent", response_model=List[MemoryResponse])
async def get_recent_memories(
    session_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Max memories to return"),
    min_importance: int = Query(5, ge=1, le=10, description="Minimum importance"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent important memories for a session

    Args:
        session_id: Game session ID
        limit: Max results
        min_importance: Minimum importance threshold
        db: Database session

    Returns:
        Recent memories
    """
    await verify_session_ownership(db, session_id, current_user.id)
    memories = await MemoryService.get_recent_memories(
        db=db, session_id=session_id, limit=limit, min_importance=min_importance
    )

    return [MemoryResponse.model_validate(m) for m in memories]


@router.get("/session/{session_id}/context", response_model=MemoryContextResponse)
async def get_ai_context(
    session_id: UUID,
    situation: str = Query(..., description="Current game situation"),
    max_memories: int = Query(5, ge=1, le=10, description="Max memories to include"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get formatted memory context for AI DM

    Args:
        session_id: Game session ID
        situation: Current situation/query
        max_memories: Max memories to include
        db: Database session

    Returns:
        Formatted memory context
    """
    await verify_session_ownership(db, session_id, current_user.id)
    context = await MemoryService.get_context_for_ai(
        db=db, session_id=session_id, current_situation=situation, max_memories=max_memories
    )

    # Get the actual memories used
    memories = await MemoryService.search_memories(
        db=db,
        session_id=session_id,
        query=situation,
        limit=max_memories,
        min_importance=6,
    )

    return MemoryContextResponse(
        relevant_memories=[context],
        memory_ids=[m.id for m in memories],
        context_length=len(context),
    )


@router.delete("/session/{session_id}")
async def delete_session_memories(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all memories for a session

    Args:
        session_id: Game session ID
        db: Database session

    Returns:
        Success message
    """
    await verify_session_ownership(db, session_id, current_user.id)

    from sqlalchemy import delete, select

    from app.db.models import AdventureMemory

    # Count first
    count_result = await db.execute(
        select(AdventureMemory).where(AdventureMemory.session_id == session_id)
    )
    count = len(count_result.scalars().all())

    # Delete
    stmt = delete(AdventureMemory).where(AdventureMemory.session_id == session_id)
    await db.execute(stmt)
    await db.commit()

    return {"deleted_count": count, "message": "Memories deleted successfully"}
