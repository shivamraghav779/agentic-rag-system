"""Admin API routes for SuperAdmin and Admin specific operations."""
from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_super_admin, get_current_admin
from app.schemas.user import UserResponse, UserCreate
from app.services.user_service import UserService

router = APIRouter()


# SuperAdmin specific endpoints

@router.get("/superadmins", response_model=List[UserResponse])
async def list_superadmins(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    """List all SuperAdmin users (SuperAdmin only)."""
    user_service = UserService(db)
    return user_service.list_users(
        current_user=current_user,
        role=UserRole.SUPER_ADMIN,
        skip=skip,
        limit=limit
    )


@router.post("/superadmins", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_superadmin(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    """Create a SuperAdmin user (SuperAdmin only)."""
    # Force role to SUPER_ADMIN and ensure no organization
    user_data.role = UserRole.SUPER_ADMIN
    user_data.organization_id = None
    
    user_service = UserService(db)
    return user_service.create_user(user_data=user_data, current_user=current_user)


# Admin specific endpoints

@router.get("/admins", response_model=List[UserResponse])
async def list_admins(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """List all Admin users (Admin or SuperAdmin only)."""
    user_service = UserService(db)
    return user_service.list_users(
        current_user=current_user,
        role=UserRole.ADMIN,
        skip=skip,
        limit=limit
    )


@router.post("/admins", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    """Create an Admin user (SuperAdmin only)."""
    # Force role to ADMIN
    user_data.role = UserRole.ADMIN
    
    user_service = UserService(db)
    return user_service.create_user(user_data=user_data, current_user=current_user)
