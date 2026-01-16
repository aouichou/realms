"""Authentication service with JWT and guest mode"""

import secrets
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.db.models import User


async def create_guest_user(db: AsyncSession) -> User:
    """Create a new guest user"""
    guest_token = secrets.token_urlsafe(32)
    username = f"Guest_{secrets.token_hex(4)}"

    user = User(
        username=username,
        is_guest=True,
        guest_token=guest_token,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def register_user(db: AsyncSession, email: str, username: str, password: str) -> User:
    """Register a new user"""

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Check if username already exists
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Create user
    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        username=username,
        password_hash=hashed_password,
        is_guest=False,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password"""

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return None

    if not user.password_hash:
        return None

    if not verify_password(password, user.password_hash):
        return None

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    return user


async def claim_guest_account(
    db: AsyncSession, guest_token: str, email: str, password: str
) -> User:
    """Convert a guest account to a registered account"""

    # Find guest user
    result = await db.execute(
        select(User).where(User.guest_token == guest_token, User.is_guest.is_(True))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest account not found")

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Convert to registered user
    user.email = email
    user.password_hash = get_password_hash(password)
    user.is_guest = False
    user.guest_token = None

    await db.commit()
    await db.refresh(user)

    return user


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get a user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
