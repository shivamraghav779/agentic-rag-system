"""add_category_descriptions_and_system_prompt

Revision ID: 8d9e2efd309c
Revises: 15f4e7f7e618
Create Date: 2026-01-09 03:24:50.819666

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '8d9e2efd309c'
down_revision: Union[str, None] = '15f4e7f7e618'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add category descriptions table, system_prompt to organizations, and change category to string.
    
    Changes:
    1. Add system_prompt column to organizations table
    2. Create document_category_descriptions table
    3. Change documents.category from ENUM to VARCHAR(100)
    4. Migrate existing ENUM values to strings (if any exist)
    """
    connection = op.get_bind()
    
    # Step 1: Add system_prompt column to organizations table
    op.add_column('organizations', sa.Column('system_prompt', sa.Text(), nullable=True))
    
    # Step 2: Create document_category_descriptions table
    op.create_table(
        'document_category_descriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'category', name='uq_org_category')
    )
    op.create_index(op.f('ix_document_category_descriptions_organization_id'), 'document_category_descriptions', ['organization_id'], unique=False)
    op.create_index(op.f('ix_document_category_descriptions_category'), 'document_category_descriptions', ['category'], unique=False)
    
    # Step 3: Change documents.category from ENUM to VARCHAR(100)
    # First, check if category column exists and what type it is
    result = connection.execute(sa.text("""
        SELECT COLUMN_TYPE 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'documents' 
        AND COLUMN_NAME = 'category'
    """))
    column_type = result.scalar()
    
    if column_type:
        # If it's an ENUM, we need to convert it
        if 'enum' in column_type.lower() or 'ENUM' in str(column_type):
            # First, update any existing ENUM values to their string equivalents
            # Get all distinct category values
            category_result = connection.execute(sa.text("""
                SELECT DISTINCT category 
                FROM documents 
                WHERE category IS NOT NULL
            """))
            categories = [row[0] for row in category_result.fetchall()]
            
            # Now alter the column to VARCHAR
            # For MySQL, we need to use MODIFY COLUMN
            op.execute("""
                ALTER TABLE documents 
                MODIFY COLUMN category VARCHAR(100) NULL
            """)
        else:
            # If it's already a string type, just ensure it's VARCHAR(100)
            op.alter_column('documents', 'category',
                          existing_type=sa.String(),
                          type_=sa.String(length=100),
                          existing_nullable=True)
    else:
        # Column doesn't exist, add it
        op.add_column('documents', sa.Column('category', sa.String(length=100), nullable=True))
        op.create_index(op.f('ix_documents_category'), 'documents', ['category'], unique=False)


def downgrade() -> None:
    """
    Revert changes: remove system_prompt, drop category_descriptions table, revert category to ENUM.
    """
    # Drop document_category_descriptions table
    op.drop_index(op.f('ix_document_category_descriptions_category'), table_name='document_category_descriptions')
    op.drop_index(op.f('ix_document_category_descriptions_organization_id'), table_name='document_category_descriptions')
    op.drop_table('document_category_descriptions')
    
    # Remove system_prompt column from organizations
    op.drop_column('organizations', 'system_prompt')
    
    # Revert documents.category back to ENUM
    # Note: This will lose any custom category names that don't match the enum values
    op.alter_column('documents', 'category',
                  existing_type=sa.String(length=100),
                  type_=sa.Enum('hr', 'sales', 'legal', 'ops', 'general', name='documentcategory'),
                  existing_nullable=True)
