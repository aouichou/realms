"""Game session API router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_active_user
from app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionStateUpdate,
    SessionUpdate,
    SessionWithState,
)
from app.services.redis_service import session_service
from app.services.session_service import GameSessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/active/character/{character_id}", response_model=SessionResponse)
async def get_active_session_for_character(
    character_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the active session for a specific character.

    Args:
        character_id: Character UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Active session for the character

    Raises:
        HTTPException: 404 if no active session found
    """
    session = await GameSessionService.get_active_session_for_character(db, character_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session for this character")
    return session


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new game session.

    Args:
        session_data: Session creation data
        user_id: User ID (from authentication, optional for now)
        db: Database session

    Returns:
        Created session
    """
    # Create session in PostgreSQL with authenticated user
    session = await GameSessionService.create_session(db, current_user.id, session_data)

    # Create session state in Redis
    await session_service.create_session_state(
        session_id=session.id,
        character_id=session.character_id,
        companion_id=session.companion_id,
        current_location=session.current_location,
    )

    return session


@router.get("/{session_id}", response_model=SessionWithState)
async def get_session(
    session_id: UUID,
    include_state: bool = Query(True, description="Include Redis state"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a session by ID.

    Args:
        session_id: Session UUID
        include_state: Whether to include Redis state
        db: Database session

    Returns:
        Session details with optional state

    Raises:
        HTTPException: 404 if session not found
    """
    session = await GameSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get Redis state if requested
    redis_state = None
    conversation_history = None

    if include_state:
        redis_state = await session_service.get_session_state(session_id)
        conversation_history = await session_service.get_conversation_history(session_id)

    return SessionWithState(
        **session.__dict__,
        state=redis_state.get("state") if redis_state else None,
        conversation_history=conversation_history,
    )


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    active_only: bool = Query(False, description="Filter for active sessions only"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's game sessions.

    Args:
        active_only: Filter for active sessions only
        skip: Pagination offset
        limit: Pagination limit
        current_user: Authenticated user
        db: Database session

    Returns:
        List of sessions
    """
    sessions, _ = await GameSessionService.get_user_sessions(
        db, current_user.id, active_only=active_only, skip=skip, limit=limit
    )
    return sessions


@router.get("/active/current", response_model=SessionWithState)
async def get_active_session(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's currently active session.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        Active session with state

    Raises:
        HTTPException: 404 if no active session
    """
    session = await GameSessionService.get_active_session(db, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session found")

    # Get Redis state
    redis_state = await session_service.get_session_state(session.id)
    conversation_history = await session_service.get_conversation_history(session.id)

    return SessionWithState(
        **session.__dict__,
        state=redis_state.get("state") if redis_state else None,
        conversation_history=conversation_history,
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: UUID,
    session_data: SessionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a session.

    Args:
        session_id: Session UUID
        session_data: Session update data
        db: Database session

    Returns:
        Updated session

    Raises:
        HTTPException: 404 if session not found
    """
    session = await GameSessionService.update_session(db, session_id, session_data)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}/state", response_model=dict)
async def update_session_state(
    session_id: UUID,
    state_data: SessionStateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update session state in Redis.

    Args:
        session_id: Session UUID
        state_data: State update data
        db: Database session

    Returns:
        Updated state

    Raises:
        HTTPException: 404 if session not found
    """
    # Verify session exists in DB
    session = await GameSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update Redis state
    updated_state = await session_service.update_session_state(
        session_id,
        current_location=state_data.current_location,
        state_updates=state_data.state_data,
    )

    if not updated_state:
        raise HTTPException(status_code=404, detail="Session state not found in Redis")

    # Refresh TTL
    await session_service.refresh_ttl(session_id)

    return updated_state


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """End a session (set is_active to False).

    Args:
        session_id: Session UUID
        db: Database session

    Returns:
        Updated session

    Raises:
        HTTPException: 404 if session not found
    """
    session = await GameSessionService.end_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session and its Redis state.

    Args:
        session_id: Session UUID
        db: Database session

    Raises:
        HTTPException: 404 if session not found
    """
    # Delete from Redis first
    await session_service.delete_session_state(session_id)

    # Delete from database
    deleted = await GameSessionService.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
