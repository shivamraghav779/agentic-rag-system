"""add_org_user_role_and_separate_private_users

Revision ID: 15f4e7f7e618
Revises: 0f5d49da2193
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '15f4e7f7e618'
down_revision = '0f5d49da2193'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add ORG_USER role and separate private users from organization users.
    
    Changes:
    1. Update existing users in organizations with role='user' to role='org_user'
    2. Ensure private users (role='user' with organization_id=NULL) remain as 'user'
    """
    connection = op.get_bind()
    
    # Step 1: Update users in organizations with role='user' to role='org_user'
    # These are organization users that should be ORG_USER
    op.execute("""
        UPDATE users 
        SET role = 'org_user' 
        WHERE role = 'user' 
        AND organization_id IS NOT NULL
    """)
    
    # Step 2: Ensure private users (role='user' with organization_id=NULL) remain as 'user'
    # This is already the case, but we verify
    op.execute("""
        UPDATE users 
        SET organization_id = NULL 
        WHERE role = 'user' 
        AND organization_id IS NOT NULL
    """)


def downgrade():
    """
    Revert ORG_USER role back to USER for organization users.
    """
    connection = op.get_bind()
    
    # Convert org_user back to user for organization users
    op.execute("""
        UPDATE users 
        SET role = 'user' 
        WHERE role = 'org_user'
    """)
