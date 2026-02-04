"""CRUD operations for Organization model."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
    """CRUD operations for Organization model."""

    async def get_by_user_access(
        self,
        db: AsyncSession,
        *,
        user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[Organization]:
        """Get organizations accessible by user based on role."""
        query = select(Organization)
        if user.role == UserRole.SUPER_ADMIN or user.role == UserRole.ADMIN:
            pass
        elif user.role in [UserRole.ORG_ADMIN, UserRole.ORG_USER]:
            query = query.where(Organization.id == user.organization_id)
        else:
            query = query.where(False)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Organization]:
        """Get organization by name."""
        result = await db.execute(select(Organization).where(Organization.name == name))
        return result.scalar_one_or_none()

    def can_access(self, organization: Organization, user: User) -> bool:
        """Check if user can access an organization."""
        return user.can_access_organization(organization.id)


organization = CRUDOrganization(Organization)
