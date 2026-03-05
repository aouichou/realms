"""Authentication schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.password_validator import validate_password


class UserBase(BaseModel):
    """Base user schema"""

    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr] = None


class UserCreate(BaseModel):
    """Schema for user registration"""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password_strength(self) -> "UserCreate":
        errors = validate_password(self.password, username=self.username, email=self.email)
        if errors:
            raise ValueError("; ".join(errors))
        return self


class UserLogin(BaseModel):
    """Schema for user login"""

    email: EmailStr
    password: str


class ClaimGuestAccount(BaseModel):
    """Schema for claiming a guest account"""

    guest_token: str
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password_strength(self) -> "ClaimGuestAccount":
        errors = validate_password(self.password, email=self.email)
        if errors:
            raise ValueError("; ".join(errors))
        return self


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""

    refresh_token: str


class UserResponse(BaseModel):
    """Schema for user response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: Optional[str] = None
    is_guest: bool
    created_at: datetime
    last_login: Optional[datetime]

    @classmethod
    def from_orm(cls, user) -> "UserResponse":
        """Create UserResponse with decrypted email."""
        return cls(
            id=user.id,
            username=user.username,
            email=user.decrypted_email,  # Decrypt for display
            is_guest=user.is_guest,
            created_at=user.created_at,
            last_login=user.last_login,
        )


class TokenResponse(BaseModel):
    """Schema for auth response — tokens are in httpOnly cookies only"""

    token_type: str = "bearer"
    user: UserResponse


class GuestTokenResponse(BaseModel):
    """Schema for guest user creation"""

    guest_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordResetRequest(BaseModel):
    """Schema for requesting a password reset"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for confirming a password reset with new password"""

    token: str
    password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_reset_password(self) -> "PasswordResetConfirm":
        errors = validate_password(self.password)
        if errors:
            raise ValueError("; ".join(errors))
        return self
