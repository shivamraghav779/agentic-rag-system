"""Organization service layer."""
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.organization import organization as organization_crud
from app.crud.user import user as user_crud
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.schemas.user import UserCreate
from app.core.security import get_password_hash


class OrganizationService:
    """Service for organization operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.organization_crud = organization_crud
        self.user_crud = user_crud

    async def create_organization(
        self,
        org_data: OrganizationCreate,
        current_user: User
    ) -> Organization:
        """Create a new organization with admin user."""
        if await self.user_crud.get_by_username(self.db, username=org_data.admin_user.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        if await self.user_crud.get_by_email(self.db, email=org_data.admin_user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        org_dict = org_data.model_dump(exclude={"admin_user"})
        organization = Organization(**org_dict)
        self.db.add(organization)
        await self.db.flush()
        hashed_password = get_password_hash(org_data.admin_user.password)
        admin_user_dict = {
            "username": org_data.admin_user.username,
            "email": org_data.admin_user.email,
            "hashed_password": hashed_password,
            "role": UserRole.ORG_ADMIN,
            "organization_id": organization.id,
            "chat_limit": 100,
            "is_active": True,
            "is_admin": False
        }
        await self.user_crud.create_from_dict(self.db, obj_dict=admin_user_dict)
        await self.db.refresh(organization)
        return organization

    async def list_organizations(
        self,
        user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[Organization]:
        """List organizations accessible by user."""
        return await self.organization_crud.get_by_user_access(
            self.db,
            user=user,
            skip=skip,
            limit=limit
        )

    async def get_organization(self, organization_id: int, user: User) -> Organization:
        """Get organization by ID."""
        organization = await self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        if not self.organization_crud.can_access(organization, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
        return organization

    async def update_organization(
        self,
        organization_id: int,
        org_data: OrganizationUpdate,
        current_user: User
    ) -> Organization:
        """Update an organization."""
        organization = await self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        return await self.organization_crud.update(
            self.db,
            db_obj=organization,
            obj_in=org_data
        )

    async def delete_organization(
        self,
        organization_id: int,
        current_user: User
    ) -> None:
        """Delete an organization."""
        organization = await self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        await self.organization_crud.delete(self.db, id=organization_id)
        from app.core.artifact_paths import delete_organization_artifacts
        delete_organization_artifacts(organization_id)

    async def list_organization_users(
        self,
        organization_id: int,
        user: User,
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """List users in an organization."""
        if not user.can_access_organization(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
        return await self.user_crud.get_by_organization(
            self.db,
            organization_id=organization_id,
            role=role,
            skip=skip,
            limit=limit
        )

    async def create_organization_user(
        self,
        organization_id: int,
        user_data: UserCreate,
        current_user: User
    ) -> User:
        """Create a user in an organization."""
        if not current_user.can_access_organization(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
        org = await self.organization_crud.get(self.db, id=organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        if await self.user_crud.get_by_username(self.db, username=user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        if await self.user_crud.get_by_email(self.db, email=user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        if user_data.role not in [UserRole.ORG_ADMIN, UserRole.ORG_USER]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only ORG_ADMIN and ORG_USER roles can be created in organizations"
            )
        if current_user.role == UserRole.ORG_ADMIN:
            if user_data.role != UserRole.ORG_USER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Organization admins can only create ORG_USER role"
                )
        user_data.organization_id = organization_id
        return await self.user_crud.create(self.db, obj_in=user_data)
