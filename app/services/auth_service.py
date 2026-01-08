"""Authentication service layer."""
from typing import Optional
from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_refresh_token
)
from app.core.config import settings
from app.crud.user import user as user_crud
from app.models.user import User, UserRole
from app.schemas.user import UserSignup, UserLogin, Token, SystemPromptUpdate


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: Session):
        """Initialize auth service with database session."""
        self.db = db
        self.user_crud = user_crud
    
    def signup(self, user_data: UserSignup) -> User:
        """
        Register a new private user.
        
        Args:
            user_data: User signup data
            
        Returns:
            Created user
            
        Raises:
            HTTPException: If username or email already exists
        """
        # Check if username already exists
        if self.user_crud.get_by_username(self.db, username=user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        if self.user_crud.get_by_email(self.db, email=user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new private user
        from app.schemas.user import UserCreate
        user_create = UserCreate(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            role=UserRole.USER,  # Private user role
            organization_id=None,  # Private users are not in organizations
            chat_limit=3  # Default limit
        )
        
        return self.user_crud.create(self.db, obj_in=user_create)
    
    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user by email and password.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            User if authenticated, None otherwise
        """
        return self.user_crud.authenticate(self.db, email=email, password=password)
    
    def login(self, user_credentials: UserLogin) -> Token:
        """
        Login user and generate tokens.
        
        Args:
            user_credentials: Login credentials
            
        Returns:
            Access and refresh tokens
            
        Raises:
            HTTPException: If authentication fails or user is inactive
        """
        user = self.authenticate(user_credentials.email, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
        refresh_token = create_refresh_token(
            data={"sub": user.email}, expires_delta=refresh_token_expires
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    def refresh_access_token(self, refresh_token: str) -> Token:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            New access and refresh tokens
            
        Raises:
            HTTPException: If refresh token is invalid or user is inactive
        """
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = self.user_crud.get_by_email(self.db, email=email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Create new tokens
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
        new_refresh_token = create_refresh_token(
            data={"sub": user.email}, expires_delta=refresh_token_expires
        )
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    
    def update_system_prompt(self, user: User, prompt_data: SystemPromptUpdate) -> User:
        """
        Update user's system prompt.
        
        Args:
            user: Current user
            prompt_data: System prompt update data
            
        Returns:
            Updated user
        """
        user.system_prompt = prompt_data.system_prompt
        self.db.commit()
        self.db.refresh(user)
        return user

