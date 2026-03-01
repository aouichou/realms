"""Authentication service with JWT and guest mode"""

import secrets
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pii_encryption import create_blind_index, encrypt_pii
from app.core.security import get_password_hash, verify_password
from app.db.models import User
from app.services.redis_service import session_service

# Lockout configuration
LOCKOUT_THRESHOLDS = [
    (5, 15 * 60),  # 5 failures → 15 minute lock
    (10, 30 * 60),  # 10 failures → 30 minute lock
    (15, 60 * 60),  # 15+ failures → 60 minute lock
]
MAX_ATTEMPTS_WINDOW = 3600  # Count attempts in the last hour


async def _get_failed_attempts(email: str) -> int:
    """Get the number of failed login attempts in the last hour."""
    redis = session_service.redis
    if not redis:
        return 0  # Can't track without Redis — fail open

    key = f"login:failed:{email}"
    now = time.time()
    # Clean old entries and count recent ones
    await redis.zremrangebyscore(key, 0, now - MAX_ATTEMPTS_WINDOW)
    return await redis.zcard(key)


async def _record_failed_attempt(email: str) -> tuple[int, int]:
    """
    Record a failed login attempt.
    Returns (remaining_attempts_before_next_lockout, lockout_seconds_if_locked).
    """
    redis = session_service.redis
    if not redis:
        return (99, 0)  # Can't track — fail open

    key = f"login:failed:{email}"
    now = time.time()

    # Add this attempt
    await redis.zadd(key, {str(now): now})
    await redis.expire(key, MAX_ATTEMPTS_WINDOW)

    # Clean old and count
    await redis.zremrangebyscore(key, 0, now - MAX_ATTEMPTS_WINDOW)
    attempts = await redis.zcard(key)

    # Check lockout thresholds
    lockout_duration = 0
    for threshold, duration in LOCKOUT_THRESHOLDS:
        if attempts >= threshold:
            lockout_duration = duration

    if lockout_duration > 0:
        # Set lockout
        lockout_key = f"login:locked:{email}"
        await redis.setex(lockout_key, lockout_duration, str(attempts))

    # Calculate remaining attempts before next threshold
    remaining = 99
    for threshold, _ in LOCKOUT_THRESHOLDS:
        if attempts < threshold:
            remaining = threshold - attempts
            break

    return (remaining, lockout_duration)


async def _check_lockout(email: str) -> tuple[bool, int]:
    """
    Check if an account is locked out.
    Returns (is_locked, seconds_remaining).
    """
    redis = session_service.redis
    if not redis:
        return (False, 0)

    lockout_key = f"login:locked:{email}"
    ttl = await redis.ttl(lockout_key)
    if ttl > 0:
        return (True, ttl)
    return (False, 0)


async def _clear_failed_attempts(email: str) -> None:
    """Clear failed login attempts after successful login."""
    redis = session_service.redis
    if not redis:
        return

    await redis.delete(f"login:failed:{email}")
    await redis.delete(f"login:locked:{email}")


async def create_guest_user(db: AsyncSession) -> User:
    """Create a new guest user"""
    guest_token = secrets.token_urlsafe(32)
    username = f"Guest_{secrets.token_hex(4)}"

    user = User(
        username=username,
        is_guest=True,
        guest_token=guest_token,
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def register_user(db: AsyncSession, email: str, username: str, password: str) -> User:
    """Register a new user"""

    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email_blind_index == create_blind_index(email))
    )
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
        email=encrypt_pii(email),
        email_blind_index=create_blind_index(email),
        username=username,
        password_hash=hashed_password,
        is_guest=False,
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Authenticate a user by email and password.

    Raises HTTPException on failure (401 for bad credentials, 423 for lockout).
    """
    # Check lockout
    is_locked, lockout_remaining = await _check_lockout(email)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "error": "AccountLocked",
                "message": "Account temporarily locked due to too many failed login attempts",
                "lockout_remaining": lockout_remaining,
                "can_reset_password": True,
            },
        )

    result = await db.execute(
        select(User).where(User.email_blind_index == create_blind_index(email))
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        # Record failure (even for non-existent users — prevent enumeration)
        remaining, lockout_duration = await _record_failed_attempt(email)

        detail: dict = {
            "error": "InvalidCredentials",
            "message": "Incorrect email or password",
        }
        if remaining <= 2:
            detail["warning"] = f"{remaining} attempt(s) remaining before account lock"
            detail["remaining_attempts"] = remaining
        if lockout_duration > 0:
            detail["error"] = "AccountLocked"
            detail["message"] = "Account temporarily locked due to too many failed login attempts"
            detail["lockout_remaining"] = lockout_duration
            detail["can_reset_password"] = True
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=detail)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Success — clear failed attempts
    await _clear_failed_attempts(email)

    # Update last login
    user.last_login = datetime.now(timezone.utc)
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
    result = await db.execute(
        select(User).where(User.email_blind_index == create_blind_index(email))
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Convert to registered user
    user.email = encrypt_pii(email)
    user.email_blind_index = create_blind_index(email)
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
