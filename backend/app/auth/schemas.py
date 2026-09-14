"""Pydantic schemas for authentication and user profiles."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Auth ────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """User registration payload."""

    username: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    burner_name: str = Field(..., min_length=2, max_length=100, examples=["Sparkle Pony"])
    password: str = Field(..., min_length=8, max_length=128)
    email: str | None = Field(default=None, min_length=5, max_length=255, examples=["user@burningman.org"])


class LoginRequest(BaseModel):
    """Login payload — accepts username."""

    login: str = Field(..., min_length=2, max_length=255, description="Username")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """JWT token pair returned on successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh token payload."""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Request a password reset — send an email."""

    email: str = Field(..., min_length=5, max_length=255)


class PasswordResetConfirm(BaseModel):
    """Confirm a password reset with token + new password."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── User / Profile ──────────────────────────────────────────────────────


class UserPublic(BaseModel):
    """Public user info returned from profile endpoints."""

    user_id: str
    username: str
    email: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class BurnerProfilePublic(BaseModel):
    """Public burner profile fields."""

    playa_name: str
    home_camp: str | None = None
    years_attended: list[int] = []
    vibe: str | None = Field(default=None, max_length=10, description="Emoji vibe")
    bio: str | None = Field(default=None, max_length=500)


class UserProfileResponse(BaseModel):
    """Full user profile response."""

    user: UserPublic
    burner: BurnerProfilePublic


class ProfileUpdateRequest(BaseModel):
    """Fields a user may update on their burner profile."""

    playa_name: str | None = Field(default=None, min_length=2, max_length=100)
    home_camp: str | None = Field(default=None, max_length=200)
    years_attended: list[int] | None = None
    vibe: str | None = Field(default=None, max_length=10)
    bio: str | None = Field(default=None, max_length=500)


class UserUpdateRequest(BaseModel):
    """Fields a user may update on their account."""

    email: str | None = Field(default=None, min_length=5, max_length=255)
    username: str | None = Field(default=None, min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")


# ── Error ───────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    """Standard error response."""

    detail: str
