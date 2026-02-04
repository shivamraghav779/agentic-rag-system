#!/usr/bin/env python3
"""Script to create a super admin user in the database."""
import argparse
import sys
import getpass
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash


def create_super_admin_user(
    username: str,
    email: str,
    password: str,
    chat_limit: int = 500,
    is_active: bool = True,
    update_existing: bool = False,
) -> bool:
    """Create a super admin user in the database.
    
    Args:
        username: Username for the super admin
        email: Email for the super admin
        password: Plain text password (will be hashed)
        chat_limit: Chat limit for the super admin (default: 500)
        is_active: Whether the super admin account is active (default: True)
        update_existing: If True and username exists, update that user to superadmin with given email/password
        
    Returns:
        True if super admin was created/updated successfully, False otherwise
    """
    db: Session = SessionLocal()
    try:
        # Check if user with this email already exists
        existing_by_email = db.query(User).filter(User.email == email).first()
        if existing_by_email:
            print(f"❌ Error: User with email '{email}' already exists.")
            if existing_by_email.role == UserRole.SUPER_ADMIN:
                print(f"   This user is already a super admin.")
            else:
                print(f"   Would you like to make this user a super admin? (y/n): ", end="")
                response = input().strip().lower()
                if response == 'y':
                    existing_by_email.role = UserRole.SUPER_ADMIN
                    existing_by_email.is_admin = True  # Legacy flag
                    existing_by_email.is_active = is_active
                    if chat_limit:
                        existing_by_email.chat_limit = chat_limit
                    db.commit()
                    print(f"✅ User is now a super admin.")
                    return True
            return False
        
        # Check if user with this username already exists
        existing_by_username = db.query(User).filter(User.username == username).first()
        if existing_by_username:
            if update_existing:
                existing_by_username.email = email
                existing_by_username.hashed_password = get_password_hash(password)
                existing_by_username.role = UserRole.SUPER_ADMIN
                existing_by_username.is_admin = True
                existing_by_username.is_active = is_active
                existing_by_username.chat_limit = chat_limit
                existing_by_username.organization_id = None  # SuperAdmin has no org
                db.commit()
                db.refresh(existing_by_username)
                print(f"✅ Existing user '{username}' updated to super admin with given email/password.")
                print(f"   Username: {existing_by_username.username}")
                print(f"   Email: {existing_by_username.email}")
                print(f"   Role: {existing_by_username.role.value}")
                return True
            print(f"❌ Error: User with username '{username}' already exists.")
            print(f"   To update that user to super admin with this email/password, run with --update-existing")
            return False
        
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create super admin user
        super_admin_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=UserRole.SUPER_ADMIN,
            is_admin=True,  # Legacy flag for backward compatibility
            is_active=is_active,
            chat_limit=chat_limit
        )
        
        db.add(super_admin_user)
        db.commit()
        db.refresh(super_admin_user)
        
        print(f"✅ Super admin user created successfully!")
        print(f"   Username: {super_admin_user.username}")
        print(f"   Email: {super_admin_user.email}")
        print(f"   Role: {super_admin_user.role.value}")
        print(f"   Admin: {super_admin_user.is_admin}")
        print(f"   Active: {super_admin_user.is_active}")
        print(f"   Chat Limit: {super_admin_user.chat_limit}")
        print(f"   ID: {super_admin_user.id}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating super admin user: {str(e)}")
        return False
    finally:
        db.close()


def main():
    """Main function to create a super admin user (interactive or via CLI args)."""
    parser = argparse.ArgumentParser(description="Create a super admin user in the database.")
    parser.add_argument("--username", "-u", type=str, help="Username for the super admin")
    parser.add_argument("--email", "-e", type=str, help="Email for the super admin")
    parser.add_argument("--password", "-p", type=str, help="Password (plain text; prefer env or interactive)")
    parser.add_argument("--chat-limit", type=int, default=500, help="Chat limit (default: 500)")
    parser.add_argument("--inactive", action="store_true", help="Create account as inactive")
    parser.add_argument("--update-existing", action="store_true", help="If username exists, update that user to super admin with given email/password")
    args = parser.parse_args()

    print("=" * 60)
    print("Create Super Admin User")
    print("=" * 60)
    print()

    # Username
    username = (args.username or "").strip() if args.username else None
    if not username:
        username = input("Enter username: ").strip()
    if not username:
        print("❌ Username cannot be empty.")
        sys.exit(1)

    # Email
    email = (args.email or "").strip() if args.email else None
    if not email:
        email = input("Enter email: ").strip()
    if not email:
        print("❌ Email cannot be empty.")
        sys.exit(1)
    if "@" not in email or "." not in email.split("@")[1]:
        print("❌ Invalid email format.")
        sys.exit(1)

    # Password
    password = args.password
    if not password:
        password = getpass.getpass("Enter password: ")
        if not password:
            print("❌ Password cannot be empty.")
            sys.exit(1)
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("❌ Passwords do not match.")
            sys.exit(1)

    chat_limit = args.chat_limit if args.chat_limit and args.chat_limit >= 1 else 500
    is_active = not args.inactive

    print()
    print("Creating super admin user...")
    print()

    success = create_super_admin_user(
        username=username,
        email=email,
        password=password,
        chat_limit=chat_limit,
        is_active=is_active,
        update_existing=getattr(args, "update_existing", False),
    )

    if success:
        print()
        print("=" * 60)
        print("✅ Super admin user created successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ Failed to create super admin user.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

