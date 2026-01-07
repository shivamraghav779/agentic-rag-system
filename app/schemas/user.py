"""User-related Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserSignup(BaseModel):
    """User signup request model."""
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """User login request model."""
    username: str
    password: str


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    chat_limit: int
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordUpdate(BaseModel):
    """Password update model."""
    new_password: str


class ChatLimitUpdate(BaseModel):
    """Chat limit update model."""
    chat_limit: int

