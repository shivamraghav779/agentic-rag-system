"""Organization schemas for multi-tenancy."""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, description="Common system prompt for all organization users")
    is_active: bool = True


class AdminUserCredentials(BaseModel):
    """Admin user credentials for organization/sub-organization creation."""
    username: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""
    admin_user: AdminUserCredentials = Field(..., description="Credentials for the organization admin user")


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, description="Common system prompt for all organization users")
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True



