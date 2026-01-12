"""Comprehensive user management API routes with role-based access control."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.deps import (
    get_current_active_user,
    get_current_super_admin,
    get_current_admin
)
from app.schemas.user import (
    UserResponse,
    UserCreate,
    UserUpdate,
    PasswordUpdate,
    ChatLimitUpdate
)
from app.services.user_service import UserService

router = APIRouter()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create a new user (SuperAdmin or Admin only)."""
    user_service = UserService(db)
    return await user_service.create_user(user_data=user_data, current_user=current_user)


@router.get("", response_model=List[UserResponse])
async def list_users(
    organization_id: Optional[int] = Query(None, description="Filter by organization"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List users with role-based filtering."""
    user_service = UserService(db)
    return await user_service.list_users(
        current_user=current_user,
        organization_id=organization_id,
        role=role,
        skip=skip,
        limit=limit
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user information."""
    user_service = UserService(db)
    return await user_service.get_user(user_id=user_id, current_user=current_user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update user information (SuperAdmin or Admin only)."""
    user_service = UserService(db)
    return await user_service.update_user(
        user_id=user_id,
        user_data=user_data,
        current_user=current_user
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    """Delete a user (SuperAdmin only)."""
    user_service = UserService(db)
    await user_service.delete_user(user_id=user_id, current_user=current_user)
    return None


@router.patch("/{user_id}/password", response_model=UserResponse)
async def update_user_password(
    user_id: int,
    password_data: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update user password (SuperAdmin or Admin only)."""
    user_service = UserService(db)
    return await user_service.update_password(
        user_id=user_id,
        password_data=password_data,
        current_user=current_user
    )


@router.patch("/{user_id}/chat-limit", response_model=UserResponse)
async def update_user_chat_limit(
    user_id: int,
    limit_data: ChatLimitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update user chat limit (SuperAdmin or Admin only)."""
    user_service = UserService(db)
    return await user_service.update_chat_limit(
        user_id=user_id,
        limit_data=limit_data,
        current_user=current_user
    )


@router.patch("/{user_id}/activate", response_model=UserResponse)
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Toggle user active status (SuperAdmin or Admin only)."""
    user_service = UserService(db)
    return await user_service.toggle_active_status(user_id=user_id, current_user=current_user)
