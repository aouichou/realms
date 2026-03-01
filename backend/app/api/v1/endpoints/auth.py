"""Authentication API endpoints"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    COOKIE_REFRESH_TOKEN_NAME,
    check_token_revoked,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
)
from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_user
from app.middleware.csrf import generate_csrf_token, set_csrf_cookie
from app.schemas.auth import (
    ClaimGuestAccount,
    GuestTokenResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    claim_guest_account,
    create_guest_user,
    register_user,
)
from app.services.redis_service import session_service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, response: Response, db: AsyncSession = Depends(get_db)):
    """Register a new user account

    Args:
        user_data: User registration data (email, username, password)
        response: FastAPI Response object for setting cookies
        db: Database session

    Returns:
        Access token, refresh token, and user data

    Raises:
        HTTPException: 400 if email or username already exists
    """
    user = await register_user(
        db, email=user_data.email, username=user_data.username, password=user_data.password
    )

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Set httpOnly cookies for XSS protection
    set_auth_cookies(response, access_token, refresh_token)

    # Generate and set CSRF token for CSRF protection
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)
    response.headers["X-CSRF-Token"] = csrf_token  # Send in header for initial setup

    return TokenResponse(user=UserResponse.from_orm(user))


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    """Login with email and password

    Args:
        login_data: Login credentials (email, password)
        response: FastAPI Response object for setting cookies
        db: Database session

    Returns:
        Access token, refresh token, and user data

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    user = await authenticate_user(db, login_data.email, login_data.password)
    # authenticate_user raises HTTPException on failure (401 or 423)

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Set httpOnly cookies for XSS protection
    set_auth_cookies(response, access_token, refresh_token)

    # Generate and set CSRF token for CSRF protection
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)
    response.headers["X-CSRF-Token"] = csrf_token  # Send in header for initial setup

    return TokenResponse(user=UserResponse.from_orm(user))


@router.post("/guest", response_model=GuestTokenResponse)
async def create_guest(response: Response, db: AsyncSession = Depends(get_db)):
    """Create a guest account for anonymous play

    No authentication required. Creates a temporary account
    that can be claimed later with email/password.

    Args:
        response: FastAPI Response object for setting cookies
        db: Database session

    Returns:
        Access token, guest token (for later claiming), and user data
    """
    user = await create_guest_user(db)

    # Generate access token
    access_token = create_access_token(data={"sub": str(user.id), "guest": True})

    # Ensure guest_token is not None
    if not user.guest_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate guest token",
        )

    # Set httpOnly cookie for guest access token
    set_auth_cookies(response, access_token, None)

    # Generate and set CSRF token for CSRF protection
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)
    response.headers["X-CSRF-Token"] = csrf_token  # Send in header for initial setup

    return GuestTokenResponse(guest_token=user.guest_token, user=UserResponse.from_orm(user))


@router.post("/claim-guest", response_model=TokenResponse)
async def claim_guest(
    claim_data: ClaimGuestAccount, response: Response, db: AsyncSession = Depends(get_db)
):
    """Claim a guest account with email and password

    Converts a guest account to a registered account,
    preserving all characters and game progress.

    Args:
        claim_data: Guest token and new credentials
        response: FastAPI response object (for cookies)
        db: Database session

    Returns:
        New access token, refresh token, and updated user data

    Raises:
        HTTPException: 404 if guest account not found
        HTTPException: 400 if email already registered
    """
    user = await claim_guest_account(
        db, guest_token=claim_data.guest_token, email=claim_data.email, password=claim_data.password
    )

    # Generate new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Set httpOnly cookies for security
    set_auth_cookies(response, access_token, refresh_token)

    # Generate and set CSRF token for CSRF protection
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)
    response.headers["X-CSRF-Token"] = csrf_token  # Send in header for initial setup

    return TokenResponse(user=UserResponse.from_orm(user))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token from httpOnly cookie

    Args:
        request: FastAPI Request object for reading cookies
        response: FastAPI response object (for cookies)
        db: Database session

    Returns:
        New tokens (in cookies) and user data

    Raises:
        HTTPException: 401 if refresh token is invalid or revoked
    """
    from app.core.security import decode_token
    from app.services.auth_service import get_user_by_id

    try:
        # Read refresh token from httpOnly cookie
        refresh_token_value = request.cookies.get(COOKIE_REFRESH_TOKEN_NAME)
        if not refresh_token_value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token found",
            )

        # Decode and validate refresh token
        payload = decode_token(refresh_token_value)

        # Check if refresh token has been revoked
        if await check_token_revoked(payload):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        # Check token type
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # Get user
        user = await get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Revoke the old refresh token
        old_jti = payload.get("jti")
        old_exp = payload.get("exp", 0)
        if old_jti:
            ttl = max(0, int(old_exp - datetime.now(timezone.utc).timestamp()))
            await session_service.revoke_token(old_jti, ttl)

        # Generate new tokens (token rotation)
        access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # Set httpOnly cookies (token rotation)
        set_auth_cookies(response, access_token, new_refresh_token)

        return TokenResponse(
            user=UserResponse.from_orm(user),
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user by clearing authentication cookies and revoking refresh token

    Args:
        request: FastAPI Request object for reading cookies
        response: FastAPI response object (for cookies)

    Returns:
        Success message
    """
    from app.core.security import decode_token

    # Try to revoke the refresh token
    refresh_token_cookie = request.cookies.get(COOKIE_REFRESH_TOKEN_NAME)
    if refresh_token_cookie:
        try:
            payload = decode_token(refresh_token_cookie)
            jti = payload.get("jti")
            exp = payload.get("exp", 0)
            if jti:
                ttl = max(0, int(exp - datetime.now(timezone.utc).timestamp()))
                await session_service.revoke_token(jti, ttl)
        except Exception:
            pass  # Token might be already invalid — still clear cookies

    clear_auth_cookies(response)
    return {"message": "Successfully logged out"}


@router.get("/token-status")
async def token_status(request: Request):
    """Get current token expiry status for proactive refresh.

    Returns minutes until access token expires.
    Frontend uses this instead of reading the token body.
    """
    from app.core.security import COOKIE_ACCESS_TOKEN_NAME, decode_token

    access_token = request.cookies.get(COOKIE_ACCESS_TOKEN_NAME)
    if not access_token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"authenticated": False},
        )

    try:
        payload = decode_token(access_token)
        exp = payload.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        expires_in = max(0, int(exp - now))
        return {
            "authenticated": True,
            "expires_in_seconds": expires_in,
            "should_refresh": expires_in < 300,  # Less than 5 minutes
        }
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"authenticated": False},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information

    Args:
        current_user: Current authenticated user from JWT

    Returns:
        User data
    """
    return UserResponse.from_orm(current_user)


@router.post("/forgot-password")
async def forgot_password(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """
    Request a password reset email.

    Always returns success to prevent email enumeration.
    """
    import secrets

    from app.core.pii_encryption import create_blind_index
    from app.services.email_service import send_password_reset_email

    # Look up user by email blind index
    blind_index = create_blind_index(data.email)
    result = await db.execute(select(User).where(User.email_blind_index == blind_index))
    user = result.scalar_one_or_none()

    if user and user.is_active and not user.is_guest:
        # Generate a secure reset token
        reset_token = secrets.token_urlsafe(32)

        # Store in Redis with 30-min TTL: reset_token -> user_id
        redis = session_service.redis
        if redis:
            await redis.setex(
                f"password:reset:{reset_token}",
                1800,  # 30 minutes
                str(user.id),
            )

        # Send email (use decrypted email)
        decrypted_email = user.decrypted_email
        if decrypted_email:
            await send_password_reset_email(
                to_email=decrypted_email,
                reset_token=reset_token,
                username=user.username,
            )

    # Always return success to prevent email enumeration
    return {"message": "If an account with that email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """
    Reset password using a valid reset token.

    Clears account lockout after successful reset.
    """
    from app.core.security import get_password_hash
    from app.services.auth_service import _clear_failed_attempts

    # Validate reset token
    redis = session_service.redis
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )

    user_id = await redis.get(f"password:reset:{data.token}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Find user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    # Update password
    user.password_hash = get_password_hash(data.password)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # Invalidate the reset token (one-time use)
    await redis.delete(f"password:reset:{data.token}")

    # Clear account lockout (instant unlock feature)
    if user.decrypted_email:
        await _clear_failed_attempts(user.decrypted_email)

    return {"message": "Password has been reset successfully. You can now log in."}
