#!/usr/bin/env python3
"""Script to create an admin user in the database."""
import sys
import getpass
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash


def create_admin_user(
    username: str,
    email: str,
    password: str,
    chat_limit: int = 100,
    is_active: bool = True
) -> bool:
    """Create an admin user in the database.
    
    Args:
        username: Username for the admin
        email: Email for the admin
        password: Plain text password (will be hashed)
        chat_limit: Chat limit for the admin (default: 100)
        is_active: Whether the admin account is active (default: True)
        
    Returns:
        True if admin was created successfully, False otherwise
    """
    db: Session = SessionLocal()
    try:
        # Check if user with this email already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"❌ Error: User with email '{email}' already exists.")
            if existing_user.is_admin:
                print(f"   This user is already an admin.")
            else:
                print(f"   Would you like to make this user an admin? (y/n): ", end="")
                response = input().strip().lower()
                if response == 'y':
                    existing_user.is_admin = True
                    existing_user.is_active = is_active
                    if chat_limit:
                        existing_user.chat_limit = chat_limit
                    db.commit()
                    print(f"✅ User '{username}' is now an admin.")
                    return True
            return False
        
        # Check if user with this username already exists
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            print(f"❌ Error: User with username '{username}' already exists.")
            return False
        
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create admin user
        admin_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_admin=True,
            is_active=is_active,
            chat_limit=chat_limit
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Admin user created successfully!")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Admin: {admin_user.is_admin}")
        print(f"   Active: {admin_user.is_active}")
        print(f"   Chat Limit: {admin_user.chat_limit}")
        print(f"   ID: {admin_user.id}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
        return False
    finally:
        db.close()


def main():
    """Main function to interactively create an admin user."""
    print("=" * 60)
    print("Create Admin User")
    print("=" * 60)
    print()
    
    # Get username
    username = input("Enter username: ").strip()
    if not username:
        print("❌ Username cannot be empty.")
        sys.exit(1)
    
    # Get email
    email = input("Enter email: ").strip()
    if not email:
        print("❌ Email cannot be empty.")
        sys.exit(1)
    
    # Validate email format (basic check)
    if "@" not in email or "." not in email.split("@")[1]:
        print("❌ Invalid email format.")
        sys.exit(1)
    
    # Get password
    password = getpass.getpass("Enter password: ")
    if not password:
        print("❌ Password cannot be empty.")
        sys.exit(1)
    
    # Confirm password
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("❌ Passwords do not match.")
        sys.exit(1)
    
    # Get chat limit (optional)
    chat_limit_input = input("Enter chat limit (default: 100, press Enter to use default): ").strip()
    chat_limit = 500  # Default
    if chat_limit_input:
        try:
            chat_limit = int(chat_limit_input)
            if chat_limit < 1:
                print("⚠️  Warning: Chat limit must be at least 1. Using default value 100.")
                chat_limit = 100
        except ValueError:
            print("⚠️  Warning: Invalid chat limit. Using default value 100.")
            chat_limit = 100
    
    # Get active status (optional)
    is_active_input = input("Should the admin account be active? (y/n, default: y): ").strip().lower()
    is_active = True  # Default
    if is_active_input and is_active_input != 'y':
        is_active = False
    
    print()
    print("Creating admin user...")
    print()
    
    # Create admin user
    success = create_admin_user(
        username=username,
        email=email,
        password=password,
        chat_limit=chat_limit,
        is_active=is_active
    )
    
    if success:
        print()
        print("=" * 60)
        print("✅ Admin user created successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ Failed to create admin user.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

