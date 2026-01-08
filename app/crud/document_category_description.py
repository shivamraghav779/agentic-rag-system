"""CRUD operations for document category descriptions."""
from typing import Optional
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.document_category_description import DocumentCategoryDescription
from app.schemas.document_category_description import (
    DocumentCategoryDescriptionCreate,
    DocumentCategoryDescriptionUpdate
)


class CRUDDocumentCategoryDescription(CRUDBase[DocumentCategoryDescription, DocumentCategoryDescriptionCreate, DocumentCategoryDescriptionUpdate]):
    """CRUD operations for document category descriptions."""
    
    def get_by_organization_and_category(
        self,
        db: Session,
        *,
        organization_id: int,
        category: str
    ) -> Optional[DocumentCategoryDescription]:
        """Get category description for a specific organization and category."""
        return db.query(DocumentCategoryDescription).filter(
            DocumentCategoryDescription.organization_id == organization_id,
            DocumentCategoryDescription.category == category
        ).first()
    
    def get_by_organization(
        self,
        db: Session,
        *,
        organization_id: int,
        skip: int = 0,
        limit: int = 100
    ):
        """Get all category descriptions for an organization."""
        return db.query(DocumentCategoryDescription).filter(
            DocumentCategoryDescription.organization_id == organization_id
        ).offset(skip).limit(limit).all()


# Create instance
document_category_description = CRUDDocumentCategoryDescription(DocumentCategoryDescription)

