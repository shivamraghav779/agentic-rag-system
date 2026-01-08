"""CRUD operations for User model."""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.crud.base import CRUDBase
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for User model."""
    
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(self.model).filter(self.model.email == email).first()
    
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(self.model).filter(self.model.username == username).first()
    
    def get_by_organization(
        self, 
        db: Session, 
        *, 
        organization_id: int,
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[User]:
        """Get users by organization ID."""
        query = db.query(self.model).filter(
            self.model.organization_id == organization_id,
            self.model.role.in_([UserRole.ORG_ADMIN, UserRole.ORG_USER])
        )
        
        if role:
            query = query.filter(self.model.role == role)
        
        return query.order_by(self.model.created_at.desc()).offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Create a new user."""
        obj_dict = obj_in.dict()
        # Remove password from dict and hash it separately
        password = obj_dict.pop("password", None)
        if password:
            from app.core.security import get_password_hash
            obj_dict["hashed_password"] = get_password_hash(password)
        
        # Set is_admin based on role
        obj_dict["is_admin"] = obj_dict.get("role") in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
        
        return self.create_from_dict(db, obj_dict=obj_dict)
    
    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        
        from app.core.security import verify_password
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def is_active(self, user: User) -> bool:
        """Check if user is active."""
        return user.is_active
    
    def is_organization_user(self, user: User) -> bool:
        """Check if user belongs to an organization."""
        return user.is_organization_user()
    
    def can_access_organization(self, user: User, org_id: int) -> bool:
        """Check if user can access an organization."""
        return user.can_access_organization(org_id)


# Create instance
user = CRUDUser(User)

