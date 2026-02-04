"""CRUD operations for User model."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for User model."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_organization(
        self,
        db: AsyncSession,
        *,
        organization_id: int,
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[User]:
        """Get users by organization ID."""
        query = (
            select(User)
            .where(
                User.organization_id == organization_id,
                User.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
            )
        )
        if role is not None:
            query = query.where(User.role == role)
        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create a new user."""
        obj_dict = obj_in.model_dump()
        password = obj_dict.pop("password", None)
        if password:
            from app.core.security import get_password_hash
            obj_dict["hashed_password"] = get_password_hash(password)
        obj_dict["is_admin"] = obj_dict.get("role") in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
        return await self.create_from_dict(db, obj_dict=obj_dict)

    async def authenticate(self, db: AsyncSession, *, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        from app.core.security import verify_password
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        """Check if user is active."""
        return user.is_active

    def is_organization_user(self, user: User) -> bool:
        """Check if user belongs to an organization."""
        return user.is_organization_user()

    def can_access_organization(self, user: User, org_id: int) -> bool:
        """Check if user can access an organization."""
        return user.can_access_organization(org_id)


user = CRUDUser(User)
