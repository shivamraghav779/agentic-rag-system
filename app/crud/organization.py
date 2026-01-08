"""CRUD operations for Organization model."""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
    """CRUD operations for Organization model."""
    
    def get_by_user_access(
        self,
        db: Session,
        *,
        user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[Organization]:
        """Get organizations accessible by user based on role."""
        query = db.query(self.model)
        
        if user.role == UserRole.SUPER_ADMIN or user.role == UserRole.ADMIN:
            # Can see all organizations
            pass
        elif user.role in [UserRole.ORG_ADMIN, UserRole.ORG_USER]:
            # Can only see their organization
            query = query.filter(self.model.id == user.organization_id)
        else:
            # Private users cannot see any organizations
            query = query.filter(False)
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_name(self, db: Session, *, name: str) -> Optional[Organization]:
        """Get organization by name."""
        return db.query(self.model).filter(self.model.name == name).first()
    
    def can_access(self, organization: Organization, user: User) -> bool:
        """Check if user can access an organization."""
        return user.can_access_organization(organization.id)


# Create instance
organization = CRUDOrganization(Organization)

