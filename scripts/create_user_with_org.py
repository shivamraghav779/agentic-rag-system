"""Script to create a user with organization assignment."""

import sys
import os
from getpass import getpass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import EmailStr, ValidationError

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.organization import Organization, SubOrganization

def get_db_session():
    """Get a database session."""
    try:
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(bind=engine)  # Ensure tables exist
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        print("Please ensure your .env file is correctly configured and the database is running.")
        sys.exit(1)

def list_organizations(db):
    """List all organizations."""
    orgs = db.query(Organization).all()
    if not orgs:
        print("No organizations found.")
        return []
    
    print("\nAvailable Organizations:")
    print("-" * 60)
    for org in orgs:
        print(f"  ID: {org.id} | Name: {org.name} | Slug: {org.slug}")
    print("-" * 60)
    return orgs

def list_sub_organizations(db, organization_id):
    """List sub-organizations for an organization."""
    sub_orgs = db.query(SubOrganization).filter(
        SubOrganization.organization_id == organization_id
    ).all()
    
    if not sub_orgs:
        print("No sub-organizations found for this organization.")
        return []
    
    print("\nAvailable Sub-Organizations:")
    print("-" * 60)
    for sub_org in sub_orgs:
        print(f"  ID: {sub_org.id} | Name: {sub_org.name} | Slug: {sub_org.slug}")
    print("-" * 60)
    return sub_orgs

def main():
    """Main function to create a user with organization assignment."""
    print("=" * 60)
    print("Create User with Organization Assignment".center(60))
    print("=" * 60)

    db = get_db_session()

    try:
        # Get user details
        username = input("Enter username: ").strip()
        if not username:
            print("Username cannot be empty.")
            return

        while True:
            email_input = input("Enter email: ").strip()
            try:
                email = EmailStr(email_input)
                break
            except ValidationError:
                print("Invalid email format. Please try again.")

        password = getpass("Enter password: ")
        if not password:
            print("Password cannot be empty.")
            return

        confirm_password = getpass("Confirm password: ")
        if password != confirm_password:
            print("Passwords do not match.")
            return

        # Get role
        print("\nAvailable Roles:")
        print("  1. SUPER_ADMIN - Full system access")
        print("  2. ADMIN - Can manage organizations")
        print("  3. ORG_ADMIN - Organization administrator")
        print("  4. SUB_ORG_ADMIN - Sub-organization administrator")
        print("  5. USER - Regular user")
        
        role_choice = input("\nSelect role (1-5, default: 5): ").strip() or "5"
        role_map = {
            "1": UserRole.SUPER_ADMIN,
            "2": UserRole.ADMIN,
            "3": UserRole.ORG_ADMIN,
            "4": UserRole.SUB_ORG_ADMIN,
            "5": UserRole.USER
        }
        role = role_map.get(role_choice, UserRole.USER)

        organization_id = None
        sub_organization_id = None

        # Get organization if needed
        if role in [UserRole.ORG_ADMIN, UserRole.SUB_ORG_ADMIN, UserRole.USER]:
            orgs = list_organizations(db)
            if not orgs:
                print("\nNo organizations available. Please create an organization first.")
                return
            
            org_id_input = input("\nEnter organization ID (or press Enter to skip): ").strip()
            if org_id_input:
                try:
                    organization_id = int(org_id_input)
                    # Verify organization exists
                    org = db.query(Organization).filter(Organization.id == organization_id).first()
                    if not org:
                        print(f"Organization with ID {organization_id} not found.")
                        return
                except ValueError:
                    print("Invalid organization ID.")
                    return

        # Get sub-organization if needed
        if role == UserRole.SUB_ORG_ADMIN and organization_id:
            sub_orgs = list_sub_organizations(db, organization_id)
            if sub_orgs:
                sub_org_id_input = input("\nEnter sub-organization ID (or press Enter to skip): ").strip()
                if sub_org_id_input:
                    try:
                        sub_organization_id = int(sub_org_id_input)
                        # Verify sub-org exists and belongs to organization
                        sub_org = db.query(SubOrganization).filter(
                            SubOrganization.id == sub_organization_id,
                            SubOrganization.organization_id == organization_id
                        ).first()
                        if not sub_org:
                            print(f"Sub-organization with ID {sub_organization_id} not found or doesn't belong to organization.")
                            return
                    except ValueError:
                        print("Invalid sub-organization ID.")
                        return

        # Get chat limit
        chat_limit_input = input("Enter chat limit (default: 3, press Enter to use default): ").strip()
        chat_limit = 3
        if chat_limit_input:
            try:
                chat_limit = int(chat_limit_input)
                if chat_limit < 0:
                    print("Chat limit cannot be negative. Using default.")
                    chat_limit = 3
            except ValueError:
                print("Invalid chat limit. Using default.")

        # Get active status
        is_active_input = input("Should the account be active? (y/n, default: y): ").strip().lower()
        is_active = True
        if is_active_input in ['n', 'no']:
            is_active = False

        print("\nCreating user...")

        # Check if user with this email or username already exists
        existing_user_by_email = db.query(User).filter(User.email == email).first()
        existing_user_by_username = db.query(User).filter(User.username == username).first()

        if existing_user_by_email:
            print(f"User with email '{email}' already exists.")
            return

        if existing_user_by_username:
            print(f"User with username '{username}' already exists. Please choose a different username.")
            return

        hashed_password = get_password_hash(password)

        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=is_active,
            role=role,
            organization_id=organization_id,
            sub_organization_id=sub_organization_id,
            chat_limit=chat_limit,
            is_admin=(role in [UserRole.SUPER_ADMIN, UserRole.ADMIN])  # Set legacy flag
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print("\n✅ User created successfully!")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role.value}")
        print(f"   Organization ID: {user.organization_id}")
        print(f"   Sub-Organization ID: {user.sub_organization_id}")
        print(f"   Active: {user.is_active}")
        print(f"   Chat Limit: {user.chat_limit}")
        print(f"   ID: {user.id}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()

