"""CRUD operations for Document model."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.document import Document
from app.models.user import User, UserRole
from app.schemas.document import DocumentInfo


class CRUDDocument(CRUDBase[Document, dict, dict]):
    """CRUD operations for Document model."""

    async def get_by_organization(
        self,
        db: AsyncSession,
        *,
        organization_id: int,
        category: Optional[str] = None,
        user: Optional[User] = None
    ) -> List[Document]:
        """Get documents by organization ID with optional filtering."""
        query = select(Document).where(Document.organization_id == organization_id)
        if category:
            query = query.where(Document.category == category)
        if user:
            if user.role == UserRole.SUPER_ADMIN or user.role == UserRole.ADMIN:
                pass
            elif user.role in [UserRole.ORG_ADMIN, UserRole.ORG_USER]:
                query = query.where(Document.organization_id == user.organization_id)
            else:
                query = query.where(False)
        query = query.order_by(Document.upload_date.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: int
    ) -> List[Document]:
        """Get documents uploaded by a specific user."""
        result = await db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.upload_date.desc())
        )
        return list(result.scalars().all())

    def can_access(self, document: Document, user: User) -> bool:
        """Check if user can access a document."""
        return user.can_access_organization(document.organization_id)

    def can_delete(self, document: Document, user: User) -> bool:
        """Check if user can delete a document."""
        if document.user_id == user.id:
            return True
        if user.role == UserRole.SUPER_ADMIN:
            return True
        if user.role == UserRole.ADMIN:
            return True
        if user.role == UserRole.ORG_ADMIN and document.organization_id == user.organization_id:
            return True
        return False


document = CRUDDocument(Document)
