"""CRUD operations for Document model."""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.crud.base import CRUDBase
from app.models.document import Document
from app.models.user import User, UserRole
from app.schemas.document import DocumentInfo


class CRUDDocument(CRUDBase[Document, dict, dict]):
    """CRUD operations for Document model."""
    
    def get_by_organization(
        self,
        db: Session,
        *,
        organization_id: int,
        category: Optional[str] = None,
        user: Optional[User] = None
    ) -> List[Document]:
        """Get documents by organization ID with optional filtering."""
        query = db.query(self.model).filter(
            self.model.organization_id == organization_id
        )
        
        if category:
            query = query.filter(self.model.category == category)
        
        # Apply role-based filtering
        if user:
            if user.role == UserRole.SUPER_ADMIN or user.role == UserRole.ADMIN:
                pass  # Can see all documents
            elif user.role in [UserRole.ORG_ADMIN, UserRole.ORG_USER]:
                # Only see documents in their organization
                query = query.filter(self.model.organization_id == user.organization_id)
            else:
                # Private users cannot see documents
                query = query.filter(False)
        
        return query.order_by(self.model.upload_date.desc()).all()
    
    def get_by_user(
        self,
        db: Session,
        *,
        user_id: int
    ) -> List[Document]:
        """Get documents uploaded by a specific user."""
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).order_by(self.model.upload_date.desc()).all()
    
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


# Create instance
document = CRUDDocument(Document)

