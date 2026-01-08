"""User model."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


class UserRole(str, enum.Enum):
    """User role enumeration for multi-tenancy hierarchy."""
    SUPER_ADMIN = "super_admin"  # Top level - can manage everything
    ADMIN = "admin"  # Can manage organizations (under SuperAdmin)
    USER = "user"  # Private user - direct access, NOT in organization (organization_id = None)
    ORG_ADMIN = "org_admin"  # Organization admin - manages organization and users within it
    ORG_USER = "org_user"  # Organization user - regular user within an organization


class User(Base):
    """User model for authentication with multi-tenancy support."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Role-based access control
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False, index=True)  # Default: private user
    
    # Multi-tenancy relationships
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Legacy admin flag (for backward compatibility, maps to role)
    is_admin = Column(Boolean, default=False)  # Deprecated: use role instead
    
    # User settings
    chat_limit = Column(Integer, default=3)  # Default 3 chats per user
    system_prompt = Column(Text, nullable=True)  # User's custom system prompt
    used_tokens = Column(Integer, default=0, nullable=False)  # Total tokens used by user
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="users", foreign_keys=[organization_id])
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    
    def has_role(self, *roles: UserRole) -> bool:
        """Check if user has any of the specified roles."""
        return self.role in roles
    
    def can_access_organization(self, org_id: int) -> bool:
        """Check if user can access a specific organization."""
        if self.role == UserRole.SUPER_ADMIN:
            return True
        if self.role == UserRole.ADMIN:
            return True  # Admins can access all organizations
        if self.role == UserRole.ORG_ADMIN:
            return self.organization_id == org_id
        if self.role == UserRole.ORG_USER:
            return self.organization_id == org_id
        # Private Users (USER role) cannot access organizations
        return False
    
    def is_organization_user(self) -> bool:
        """Check if user belongs to an organization."""
        return self.role in [UserRole.ORG_ADMIN, UserRole.ORG_USER] and self.organization_id is not None
    
    def is_private_user(self) -> bool:
        """Check if user is a private user (not in organization)."""
        return self.role == UserRole.USER and self.organization_id is None
