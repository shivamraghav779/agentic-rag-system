"""Service layer for document category description management."""
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.document_category_description import document_category_description as category_description_crud
from app.crud.organization import organization as organization_crud
from app.models.user import User, UserRole
from app.models.document_category_description import DocumentCategoryDescription
from app.schemas.document_category_description import (
    DocumentCategoryDescriptionCreate,
    DocumentCategoryDescriptionUpdate,
    DocumentCategoryDescriptionResponse
)


class CategoryDescriptionService:
    """Service for managing document category descriptions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.category_description_crud = category_description_crud
        self.organization_crud = organization_crud

    async def create_category_description(
        self,
        organization_id: int,
        category_data: DocumentCategoryDescriptionCreate,
        current_user: User
    ) -> DocumentCategoryDescriptionResponse:
        """Create a new category description for an organization."""
        organization = await self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        if not self._can_manage_categories(current_user, organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage categories for this organization"
            )
        existing = await self.category_description_crud.get_by_organization_and_category(
            self.db,
            organization_id=organization_id,
            category=category_data.category
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{category_data.category}' already exists for this organization"
            )
        category_dict = {
            "organization_id": organization_id,
            "category": category_data.category,
            "description": category_data.description
        }
        created = await self.category_description_crud.create_from_dict(
            self.db,
            obj_dict=category_dict
        )
        await self.db.refresh(created)
        return DocumentCategoryDescriptionResponse.model_validate(created)

    async def get_category_description(
        self,
        organization_id: int,
        category: str,
        current_user: User
    ) -> DocumentCategoryDescriptionResponse:
        """Get a specific category description."""
        organization = await self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        if not current_user.can_access_organization(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this organization"
            )
        category_desc = await self.category_description_crud.get_by_organization_and_category(
            self.db,
            organization_id=organization_id,
            category=category
        )
        if not category_desc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category}' not found for this organization"
            )
        return DocumentCategoryDescriptionResponse.model_validate(category_desc)

    async def list_category_descriptions(
        self,
        organization_id: int,
        current_user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentCategoryDescriptionResponse]:
        """List all category descriptions for an organization."""
        organization = await self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        if not current_user.can_access_organization(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this organization"
            )
        categories = await self.category_description_crud.get_by_organization(
            self.db,
            organization_id=organization_id,
            skip=skip,
            limit=limit
        )
        return [DocumentCategoryDescriptionResponse.model_validate(cat) for cat in categories]

    async def update_category_description(
        self,
        organization_id: int,
        category: str,
        category_data: DocumentCategoryDescriptionUpdate,
        current_user: User
    ) -> DocumentCategoryDescriptionResponse:
        """Update a category description."""
        organization = await self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        if not self._can_manage_categories(current_user, organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage categories for this organization"
            )
        category_desc = await self.category_description_crud.get_by_organization_and_category(
            self.db,
            organization_id=organization_id,
            category=category
        )
        if not category_desc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category}' not found for this organization"
            )
        update_dict = category_data.model_dump(exclude_unset=True)
        updated = await self.category_description_crud.update(
            self.db,
            db_obj=category_desc,
            obj_in=update_dict
        )
        await self.db.refresh(updated)
        return DocumentCategoryDescriptionResponse.model_validate(updated)

    async def delete_category_description(
        self,
        organization_id: int,
        category: str,
        current_user: User
    ) -> None:
        """Delete a category description."""
        organization = await self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        if not self._can_manage_categories(current_user, organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage categories for this organization"
            )
        category_desc = await self.category_description_crud.get_by_organization_and_category(
            self.db,
            organization_id=organization_id,
            category=category
        )
        if not category_desc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category}' not found for this organization"
            )
        await self.category_description_crud.delete(self.db, id=category_desc.id)

    def _can_manage_categories(self, user: User, organization_id: int) -> bool:
        """Check if user can manage categories for an organization."""
        if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            return True
        if user.role == UserRole.ORG_ADMIN and user.organization_id == organization_id:
            return True
        return False
