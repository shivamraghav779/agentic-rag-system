"""Organization management API routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.deps import (
    get_current_active_user,
    get_current_super_admin,
    get_current_admin,
    get_current_org_admin
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse
)
from app.schemas.user import UserResponse, UserCreate
from app.services.organization_service import OrganizationService

router = APIRouter()


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create a new organization (SuperAdmin or Admin only).
    
    Automatically creates an ORG_ADMIN user for the organization.
    """
    organization_service = OrganizationService(db)
    return organization_service.create_organization(org_data=org_data, current_user=current_user)


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List organizations based on user role."""
    organization_service = OrganizationService(db)
    return organization_service.list_organizations(user=current_user, skip=skip, limit=limit)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get organization details."""
    organization_service = OrganizationService(db)
    return organization_service.get_organization(organization_id=organization_id, user=current_user)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: int,
    org_data: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update an organization (SuperAdmin or Admin only)."""
    organization_service = OrganizationService(db)
    return organization_service.update_organization(
        organization_id=organization_id,
        org_data=org_data,
        current_user=current_user
    )


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    """Delete an organization (SuperAdmin only)."""
    organization_service = OrganizationService(db)
    organization_service.delete_organization(organization_id=organization_id, current_user=current_user)
    return None


# Organization User Management

@router.get("/{organization_id}/users", response_model=List[UserResponse])
async def list_organization_users(
    organization_id: int,
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List users in an organization."""
    organization_service = OrganizationService(db)
    return organization_service.list_organization_users(
        organization_id=organization_id,
        user=current_user,
        role=role,
        skip=skip,
        limit=limit
    )


@router.post("/{organization_id}/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_organization_user(
    organization_id: int,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_org_admin)
):
    """Create a user in an organization (Org Admin, Admin, or SuperAdmin only)."""
    organization_service = OrganizationService(db)
    return organization_service.create_organization_user(
        organization_id=organization_id,
        user_data=user_data,
        current_user=current_user
    )
