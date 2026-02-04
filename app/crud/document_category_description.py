"""CRUD operations for document category descriptions."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.document_category_description import DocumentCategoryDescription
from app.schemas.document_category_description import (
    DocumentCategoryDescriptionCreate,
    DocumentCategoryDescriptionUpdate,
)


class CRUDDocumentCategoryDescription(
    CRUDBase[
        DocumentCategoryDescription,
        DocumentCategoryDescriptionCreate,
        DocumentCategoryDescriptionUpdate,
    ]
):
    """CRUD operations for document category descriptions."""

    async def get_by_organization_and_category(
        self,
        db: AsyncSession,
        *,
        organization_id: int,
        category: str
    ) -> Optional[DocumentCategoryDescription]:
        """Get category description for a specific organization and category."""
        result = await db.execute(
            select(DocumentCategoryDescription).where(
                DocumentCategoryDescription.organization_id == organization_id,
                DocumentCategoryDescription.category == category
            )
        )
        return result.scalar_one_or_none()

    async def get_by_organization(
        self,
        db: AsyncSession,
        *,
        organization_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentCategoryDescription]:
        """Get all category descriptions for an organization."""
        result = await db.execute(
            select(DocumentCategoryDescription)
            .where(DocumentCategoryDescription.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


document_category_description = CRUDDocumentCategoryDescription(DocumentCategoryDescription)
