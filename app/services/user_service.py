"""User service layer."""
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import user as user_crud
from app.crud.organization import organization as organization_crud
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, PasswordUpdate, ChatLimitUpdate


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_crud = user_crud
        self.organization_crud = organization_crud

    async def create_user(self, user_data: UserCreate, current_user: User) -> User:
        """Create a new user."""
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
        if current_user.role == UserRole.ADMIN:
            if user_data.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot create SuperAdmin or Admin users"
                )
        if user_data.role in [UserRole.ORG_ADMIN, UserRole.ORG_USER]:
            if not user_data.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization ID is required for ORG_ADMIN and ORG_USER roles"
                )
            org = await self.organization_crud.get(self.db, id=user_data.organization_id)
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )
        elif user_data.role == UserRole.USER:
            if user_data.organization_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Private users (USER role) cannot be assigned to an organization"
                )
            user_data.organization_id = None

        return await self.user_crud.create(self.db, obj_in=user_data)

    async def list_users(
        self,
        current_user: User,
        organization_id: Optional[int] = None,
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """List users with role-based filtering."""
        query = select(User)
        if current_user.role == UserRole.SUPER_ADMIN or current_user.role == UserRole.ADMIN:
            pass
        elif current_user.role == UserRole.ORG_ADMIN:
            query = query.where(User.organization_id == current_user.organization_id)
        elif current_user.role == UserRole.ORG_USER:
            query = query.where(User.id == current_user.id)
        else:
            query = query.where(User.id == current_user.id)
        if organization_id is not None:
            if not current_user.can_access_organization(organization_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
            query = query.where(User.organization_id == organization_id)
        if role is not None:
            query = query.where(User.role == role)
        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user(self, user_id: int, current_user: User) -> User:
        """Get user by ID."""
        user = await self.user_crud.get(self.db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if current_user.role == UserRole.SUPER_ADMIN or current_user.role == UserRole.ADMIN:
            pass
        elif current_user.role == UserRole.ORG_ADMIN:
            if user.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        elif current_user.role == UserRole.ORG_USER:
            if user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        else:
            if user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        return user

    async def update_user(
        self,
        user_id: int,
        user_data: UserUpdate,
        current_user: User
    ) -> User:
        """Update user information."""
        user = await self.user_crud.get(self.db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if current_user.role == UserRole.ADMIN:
            if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot modify SuperAdmin or Admin users"
                )
        update_dict = {}
        if user_data.username is not None:
            existing = await self.user_crud.get_by_username(self.db, username=user_data.username)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )
            update_dict["username"] = user_data.username
        if user_data.email is not None:
            existing = await self.user_crud.get_by_email(self.db, email=user_data.email)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
            update_dict["email"] = user_data.email
        if user_data.is_active is not None:
            update_dict["is_active"] = user_data.is_active
        if user_data.role is not None:
            if current_user.role == UserRole.ADMIN:
                if user_data.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Admins cannot assign SuperAdmin or Admin roles"
                    )
            if user_data.role in [UserRole.ORG_ADMIN, UserRole.ORG_USER]:
                if user_data.organization_id is None:
                    if user.organization_id is None:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Organization ID is required for ORG_ADMIN and ORG_USER roles"
                        )
                else:
                    org = await self.organization_crud.get(self.db, id=user_data.organization_id)
                    if not org:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Organization not found"
                        )
                    update_dict["organization_id"] = user_data.organization_id
            elif user_data.role == UserRole.USER:
                update_dict["organization_id"] = None
            update_dict["role"] = user_data.role
            update_dict["is_admin"] = (user_data.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN])
        if user_data.organization_id is not None and user_data.role is None:
            if user.role in [UserRole.ORG_ADMIN, UserRole.ORG_USER]:
                org = await self.organization_crud.get(self.db, id=user_data.organization_id)
                if not org:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Organization not found"
                    )
                update_dict["organization_id"] = user_data.organization_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only ORG_ADMIN and ORG_USER can be assigned to organizations"
                )
        if user_data.chat_limit is not None:
            if user_data.chat_limit < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Chat limit must be non-negative"
                )
            update_dict["chat_limit"] = user_data.chat_limit
        if user_data.system_prompt is not None:
            update_dict["system_prompt"] = user_data.system_prompt
        return await self.user_crud.update(self.db, db_obj=user, obj_in=update_dict)

    async def delete_user(self, user_id: int, current_user: User) -> None:
        """Delete a user."""
        user = await self.user_crud.get(self.db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        await self.user_crud.delete(self.db, id=user_id)

    async def update_password(
        self,
        user_id: int,
        password_data: PasswordUpdate,
        current_user: User
    ) -> User:
        """Update user password."""
        user = await self.user_crud.get(self.db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if current_user.role == UserRole.ADMIN:
            if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot change passwords for SuperAdmin or Admin users"
                )
        from app.core.security import get_password_hash
        user.hashed_password = get_password_hash(password_data.new_password)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_chat_limit(
        self,
        user_id: int,
        limit_data: ChatLimitUpdate,
        current_user: User
    ) -> User:
        """Update user chat limit."""
        user = await self.user_crud.get(self.db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if limit_data.chat_limit < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat limit must be non-negative"
            )
        user.chat_limit = limit_data.chat_limit
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def toggle_active_status(self, user_id: int, current_user: User) -> User:
        """Toggle user active status."""
        user = await self.user_crud.get(self.db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        if current_user.role == UserRole.ADMIN:
            if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot deactivate SuperAdmin or Admin users"
                )
        user.is_active = not user.is_active
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
