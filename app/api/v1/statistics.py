"""Statistics and dashboard API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_active_user, get_current_admin
from app.schemas.statistics import (
    UserStatistics,
    OrganizationStatistics,
    AdminStatistics
)
from app.services.statistics_service import StatisticsService

router = APIRouter()


@router.get("/user", response_model=UserStatistics)
async def get_user_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get statistics for the current user.
    
    Returns:
    - Total documents uploaded
    - Total conversations and chats
    - Token usage
    - Chats today and remaining
    - Documents by category
    - Recent activity
    """
    statistics_service = StatisticsService(db)
    return statistics_service.get_user_statistics(user=current_user)


@router.get("/organization/{organization_id}", response_model=OrganizationStatistics)
async def get_organization_statistics(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get statistics for a specific organization.
    
    Access:
    - OrgAdmin/OrgUser: Can view their own organization
    - Admin/SuperAdmin: Can view any organization
    
    Returns:
    - Total users, documents, conversations, chats
    - Token usage
    - Active users
    - Documents by category
    - Users by role
    - Recent activity
    """
    statistics_service = StatisticsService(db)
    return statistics_service.get_organization_statistics(
        organization_id=organization_id,
        user=current_user
    )


@router.get("/admin", response_model=AdminStatistics)
async def get_admin_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get system-wide statistics for admin users.
    
    Access: Admin, SuperAdmin only
    
    Returns:
    - System-wide totals (organizations, users, documents, etc.)
    - Active counts
    - Users by role
    - Documents by category
    - Statistics for each organization
    - Recent activity across the system
    """
    statistics_service = StatisticsService(db)
    return statistics_service.get_admin_statistics(user=current_user)

