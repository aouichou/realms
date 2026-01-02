"""Game session service for database operations."""
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GameSession
from app.schemas.session import SessionCreate, SessionUpdate


class GameSessionService:
    """Service for game session database operations."""
    
    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: Optional[UUID],
        session_data: SessionCreate
    ) -> GameSession:
        """Create a new game session in the database.
        
        Args:
            db: Database session
            user_id: User ID (optional for development without auth)
            session_data: Session creation data
            
        Returns:
            Created game session
        """
        session = GameSession(
            id=uuid.uuid4(),
            user_id=user_id,
            character_id=session_data.character_id,
            companion_id=session_data.companion_id,
            is_active=True,
            current_location=session_data.current_location,
            state_snapshot={}
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
    
    @staticmethod
    async def get_session(db: AsyncSession, session_id: UUID) -> Optional[GameSession]:
        """Get a session by ID.
        
        Args:
            db: Database session
            session_id: Session UUID
            
        Returns:
            Game session or None
        """
        result = await db.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_sessions(
        db: AsyncSession,
        user_id: UUID,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[GameSession], int]:
        """Get all sessions for a user.
        
        Args:
            db: Database session
            user_id: User ID
            active_only: Filter for active sessions only
            skip: Pagination offset
            limit: Pagination limit
            
        Returns:
            Tuple of (sessions list, total count)
        """
        query = select(GameSession).where(GameSession.user_id == user_id)
        
        if active_only:
            query = query.where(GameSession.is_active == True)
        
        # Get total count
        count_result = await db.execute(query)
        total = len(count_result.all())
        
        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(GameSession.last_activity_at.desc())
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        return list(sessions), total
    
    @staticmethod
    async def get_active_session(
        db: AsyncSession,
        user_id: UUID
    ) -> Optional[GameSession]:
        """Get the user's active session.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Active game session or None
        """
        result = await db.execute(
            select(GameSession)
            .where(
                and_(
                    GameSession.user_id == user_id,
                    GameSession.is_active == True
                )
            )
            .order_by(GameSession.last_activity_at.desc())
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_session(
        db: AsyncSession,
        session_id: UUID,
        session_data: SessionUpdate
    ) -> Optional[GameSession]:
        """Update a session.
        
        Args:
            db: Database session
            session_id: Session UUID
            session_data: Session update data
            
        Returns:
            Updated session or None
        """
        session = await GameSessionService.get_session(db, session_id)
        if not session:
            return None
        
        update_data = session_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(session, field, value)
        
        await db.commit()
        await db.refresh(session)
        return session
    
    @staticmethod
    async def end_session(db: AsyncSession, session_id: UUID) -> Optional[GameSession]:
        """End a session (set is_active to False).
        
        Args:
            db: Database session
            session_id: Session UUID
            
        Returns:
            Updated session or None
        """
        return await GameSessionService.update_session(
            db,
            session_id,
            SessionUpdate(is_active=False)
        )
    
    @staticmethod
    async def delete_session(db: AsyncSession, session_id: UUID) -> bool:
        """Delete a session.
        
        Args:
            db: Database session
            session_id: Session UUID
            
        Returns:
            True if deleted, False if not found
        """
        session = await GameSessionService.get_session(db, session_id)
        if not session:
            return False
        
        await db.delete(session)
        await db.commit()
        return True
