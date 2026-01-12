"""Document category description API routes."""
from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_active_user
from app.schemas.document_category_description import (
    DocumentCategoryDescriptionCreate,
    DocumentCategoryDescriptionUpdate,
    DocumentCategoryDescriptionResponse
)
from app.services.category_description_service import CategoryDescriptionService

router = APIRouter()


@router.post(
    "/organizations/{organization_id}/categories",
    response_model=DocumentCategoryDescriptionResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_category_description(
    organization_id: int,
    category_data: DocumentCategoryDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new category description for an organization.
    
    Only SuperAdmin, Admin, and OrgAdmin can create categories.
    """
    category_service = CategoryDescriptionService(db)
    return await category_service.create_category_description(
        organization_id=organization_id,
        category_data=category_data,
        current_user=current_user
    )


@router.get(
    "/organizations/{organization_id}/categories",
    response_model=List[DocumentCategoryDescriptionResponse]
)
async def list_category_descriptions(
    organization_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all category descriptions for an organization.
    
    Users can view categories for organizations they have access to.
    """
    category_service = CategoryDescriptionService(db)
    return await category_service.list_category_descriptions(
        organization_id=organization_id,
        current_user=current_user,
        skip=skip,
        limit=limit
    )


@router.get(
    "/organizations/{organization_id}/categories/{category}",
    response_model=DocumentCategoryDescriptionResponse
)
async def get_category_description(
    organization_id: int,
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific category description.
    
    Users can view categories for organizations they have access to.
    """
    category_service = CategoryDescriptionService(db)
    return await category_service.get_category_description(
        organization_id=organization_id,
        category=category,
        current_user=current_user
    )


@router.patch(
    "/organizations/{organization_id}/categories/{category}",
    response_model=DocumentCategoryDescriptionResponse
)
async def update_category_description(
    organization_id: int,
    category: str,
    category_data: DocumentCategoryDescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a category description.
    
    Only SuperAdmin, Admin, and OrgAdmin can update categories.
    """
    category_service = CategoryDescriptionService(db)
    return await category_service.update_category_description(
        organization_id=organization_id,
        category=category,
        category_data=category_data,
        current_user=current_user
    )


@router.delete(
    "/organizations/{organization_id}/categories/{category}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_category_description(
    organization_id: int,
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a category description.
    
    Only SuperAdmin, Admin, and OrgAdmin can delete categories.
    """
    category_service = CategoryDescriptionService(db)
    await category_service.delete_category_description(
        organization_id=organization_id,
        category=category,
        current_user=current_user
    )
    return None

