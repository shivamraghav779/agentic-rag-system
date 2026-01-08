"""Service layer for document category description management."""
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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
    
    def __init__(self, db: Session):
        """Initialize category description service with database session."""
        self.db = db
        self.category_description_crud = category_description_crud
        self.organization_crud = organization_crud
    
    def create_category_description(
        self,
        organization_id: int,
        category_data: DocumentCategoryDescriptionCreate,
        current_user: User
    ) -> DocumentCategoryDescriptionResponse:
        """
        Create a new category description for an organization.
        
        Args:
            organization_id: Organization ID
            category_data: Category description data
            current_user: Current user
            
        Returns:
            Created category description
            
        Raises:
            HTTPException: If access denied or category already exists
        """
        # Verify organization exists
        organization = self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Verify user can manage categories for this organization
        if not self._can_manage_categories(current_user, organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage categories for this organization"
            )
        
        # Check if category description already exists
        existing = self.category_description_crud.get_by_organization_and_category(
            self.db,
            organization_id=organization_id,
            category=category_data.category
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{category_data.category}' already exists for this organization"
            )
        
        # Create category description
        category_dict = {
            "organization_id": organization_id,
            "category": category_data.category,
            "description": category_data.description
        }
        
        created = self.category_description_crud.create_from_dict(
            self.db,
            obj_dict=category_dict
        )
        
        self.db.refresh(created)
        
        return DocumentCategoryDescriptionResponse.model_validate(created)
    
    def get_category_description(
        self,
        organization_id: int,
        category: str,
        current_user: User
    ) -> DocumentCategoryDescriptionResponse:
        """
        Get a specific category description.
        
        Args:
            organization_id: Organization ID
            category: Category name
            current_user: Current user
            
        Returns:
            Category description
            
        Raises:
            HTTPException: If not found or access denied
        """
        # Verify organization exists
        organization = self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Verify user can access this organization
        if not current_user.can_access_organization(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this organization"
            )
        
        category_desc = self.category_description_crud.get_by_organization_and_category(
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
    
    def list_category_descriptions(
        self,
        organization_id: int,
        current_user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentCategoryDescriptionResponse]:
        """
        List all category descriptions for an organization.
        
        Args:
            organization_id: Organization ID
            current_user: Current user
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of category descriptions
            
        Raises:
            HTTPException: If access denied
        """
        # Verify organization exists
        organization = self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Verify user can access this organization
        if not current_user.can_access_organization(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this organization"
            )
        
        categories = self.category_description_crud.get_by_organization(
            self.db,
            organization_id=organization_id,
            skip=skip,
            limit=limit
        )
        
        return [DocumentCategoryDescriptionResponse.model_validate(cat) for cat in categories]
    
    def update_category_description(
        self,
        organization_id: int,
        category: str,
        category_data: DocumentCategoryDescriptionUpdate,
        current_user: User
    ) -> DocumentCategoryDescriptionResponse:
        """
        Update a category description.
        
        Args:
            organization_id: Organization ID
            category: Category name
            category_data: Update data
            current_user: Current user
            
        Returns:
            Updated category description
            
        Raises:
            HTTPException: If not found or access denied
        """
        # Verify organization exists
        organization = self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Verify user can manage categories for this organization
        if not self._can_manage_categories(current_user, organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage categories for this organization"
            )
        
        category_desc = self.category_description_crud.get_by_organization_and_category(
            self.db,
            organization_id=organization_id,
            category=category
        )
        
        if not category_desc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category}' not found for this organization"
            )
        
        # Update category description
        update_dict = category_data.model_dump(exclude_unset=True)
        updated = self.category_description_crud.update(
            self.db,
            db_obj=category_desc,
            obj_in=update_dict
        )
        
        self.db.refresh(updated)
        
        return DocumentCategoryDescriptionResponse.model_validate(updated)
    
    def delete_category_description(
        self,
        organization_id: int,
        category: str,
        current_user: User
    ) -> None:
        """
        Delete a category description.
        
        Args:
            organization_id: Organization ID
            category: Category name
            current_user: Current user
            
        Raises:
            HTTPException: If not found or access denied
        """
        # Verify organization exists
        organization = self.organization_crud.get(self.db, id=organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Verify user can manage categories for this organization
        if not self._can_manage_categories(current_user, organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to manage categories for this organization"
            )
        
        category_desc = self.category_description_crud.get_by_organization_and_category(
            self.db,
            organization_id=organization_id,
            category=category
        )
        
        if not category_desc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category}' not found for this organization"
            )
        
        self.category_description_crud.remove(self.db, id=category_desc.id)
    
    def _can_manage_categories(self, user: User, organization_id: int) -> bool:
        """
        Check if user can manage categories for an organization.
        
        Args:
            user: Current user
            organization_id: Organization ID
            
        Returns:
            True if user can manage categories, False otherwise
        """
        # SuperAdmin and Admin can manage all organizations
        if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            return True
        
        # OrgAdmin can manage their own organization
        if user.role == UserRole.ORG_ADMIN and user.organization_id == organization_id:
            return True
        
        return False

