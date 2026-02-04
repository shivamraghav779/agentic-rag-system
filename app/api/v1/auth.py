"""Authentication API routes."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.schemas.user import UserSignup, UserLogin, Token, UserResponse, SystemPromptUpdate, RefreshTokenRequest
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserSignup,
    db: AsyncSession = Depends(async_get_db)
):
    """Register a new user."""
    auth_service = AuthService(db)
    return await auth_service.signup(user_data)


@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(async_get_db)
):
    """Login and get access token."""
    auth_service = AuthService(db)
    return await auth_service.login(user_credentials)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(async_get_db)
):
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)
    return await auth_service.refresh_access_token(refresh_data.refresh_token)


@router.patch("/me/system-prompt", response_model=UserResponse)
async def update_system_prompt(
    prompt_data: SystemPromptUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update the current user's system prompt."""
    auth_service = AuthService(db)
    return await auth_service.update_system_prompt(current_user, prompt_data)

