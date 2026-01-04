"""Authentication API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_user
from app.schemas.auth import (
    ClaimGuestAccount,
    GuestTokenResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    claim_guest_account,
    create_access_token,
    create_guest_user,
    create_refresh_token,
    register_user,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account

    Args:
        user_data: User registration data (email, username, password)
        db: Database session

    Returns:
        Access token, refresh token, and user data

    Raises:
        HTTPException: 400 if email or username already exists
    """
    user = await register_user(
        db,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password
    )

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_orm(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password

    Args:
        login_data: Login credentials (email, password)
        db: Database session

    Returns:
        Access token, refresh token, and user data

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    user = await authenticate_user(db, login_data.email, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_orm(user)
    )


@router.post("/guest", response_model=GuestTokenResponse)
async def create_guest(db: AsyncSession = Depends(get_db)):
    """Create a guest account for anonymous play

    No authentication required. Creates a temporary account
    that can be claimed later with email/password.

    Args:
        db: Database session

    Returns:
        Access token, guest token (for later claiming), and user data
    """
    user = await create_guest_user(db)

    # Generate access token
    access_token = create_access_token(data={"sub": str(user.id), "guest": True})

    return GuestTokenResponse(
        access_token=access_token,
        guest_token=user.guest_token,
        user=UserResponse.from_orm(user)
    )


@router.post("/claim-guest", response_model=TokenResponse)
async def claim_guest(
    claim_data: ClaimGuestAccount,
    db: AsyncSession = Depends(get_db)
):
    """Claim a guest account with email and password

    Converts a guest account to a registered account,
    preserving all characters and game progress.

    Args:
        claim_data: Guest token and new credentials
        db: Database session

    Returns:
        New access token, refresh token, and updated user data

    Raises:
        HTTPException: 404 if guest account not found
        HTTPException: 400 if email already registered
    """
    user = await claim_guest_account(
        db,
        guest_token=claim_data.guest_token,
        email=claim_data.email,
        password=claim_data.password
    )

    # Generate new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_orm(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token

    Args:
        refresh_data: JSON with refresh_token field
        db: Database session

    Returns:
        New access token and refresh token

    Raises:
        HTTPException: 401 if refresh token is invalid
    """
    from app.services.auth_service import decode_token, get_user_by_id
    
    refresh_token = refresh_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required"
        )
    
    try:
        # Decode and validate refresh token
        payload = decode_token(refresh_token)
        
        # Check token type
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        user = await get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate new tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            user=UserResponse.from_orm(user)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user information

    Args:
        current_user: Current authenticated user from JWT

    Returns:
        User data
    """
    return UserResponse.from_orm(current_user)
