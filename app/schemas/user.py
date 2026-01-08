"""User-related Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class UserSignup(BaseModel):
    """User signup request model."""
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """User login request model."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    role: UserRole
    organization_id: Optional[int] = None
    chat_limit: int
    system_prompt: str | None = None
    used_tokens: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation model with multi-tenancy."""
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER
    organization_id: Optional[int] = None
    chat_limit: int = 3


class UserUpdate(BaseModel):
    """User update model."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    organization_id: Optional[int] = None
    chat_limit: Optional[int] = None
    system_prompt: Optional[str] = None


class PasswordUpdate(BaseModel):
    """Password update model."""
    new_password: str


class ChatLimitUpdate(BaseModel):
    """Chat limit update model."""
    chat_limit: int


class SystemPromptUpdate(BaseModel):
    """System prompt update model."""
    system_prompt: str | None = None

