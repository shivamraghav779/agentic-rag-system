"""remove_sub_organizations

Revision ID: 0f5d49da2193
Revises: 41d6ef7310d5
Create Date: 2024-12-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0f5d49da2193'
down_revision = '41d6ef7310d5'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Update users with SUB_ORG_ADMIN role to USER role
    # (since SUB_ORG_ADMIN role is being removed)
    op.execute("""
        UPDATE users 
        SET role = 'user' 
        WHERE role = 'sub_org_admin'
    """)
    
    # Step 2: Remove sub_organization_id foreign key constraint from users table
    # Find foreign key constraints that reference sub_organizations table
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT tc.CONSTRAINT_NAME 
        FROM information_schema.TABLE_CONSTRAINTS tc
        JOIN information_schema.KEY_COLUMN_USAGE kcu 
        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
        ON tc.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
        WHERE tc.TABLE_SCHEMA = DATABASE() 
        AND tc.TABLE_NAME = 'users' 
        AND tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
        AND kcu.COLUMN_NAME = 'sub_organization_id'
        AND rc.REFERENCED_TABLE_NAME = 'sub_organizations'
    """))
    constraints = [row[0] for row in result]
    
    for constraint_name in constraints:
        try:
            op.drop_constraint(constraint_name, 'users', type_='foreignkey')
        except Exception:
            # Constraint might not exist or already dropped
            pass
    
    # Step 3: Drop index on sub_organization_id if it exists
    result = connection.execute(sa.text("""
        SELECT INDEX_NAME 
        FROM information_schema.STATISTICS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'users' 
        AND COLUMN_NAME = 'sub_organization_id'
    """))
    indexes = [row[0] for row in result]
    for index_name in indexes:
        try:
            op.drop_index(index_name, table_name='users')
        except Exception:
            # Index might not exist or already dropped
            pass
    
    # Step 4: Drop sub_organization_id column from users table
    # Check if column exists first
    result = connection.execute(sa.text("""
        SELECT COLUMN_NAME 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'users' 
        AND COLUMN_NAME = 'sub_organization_id'
    """))
    if result.fetchone():
        op.drop_column('users', 'sub_organization_id')
    
    # Step 5: Remove sub_organization_id foreign key constraint from documents table
    result = connection.execute(sa.text("""
        SELECT tc.CONSTRAINT_NAME 
        FROM information_schema.TABLE_CONSTRAINTS tc
        JOIN information_schema.KEY_COLUMN_USAGE kcu 
        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
        ON tc.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
        WHERE tc.TABLE_SCHEMA = DATABASE() 
        AND tc.TABLE_NAME = 'documents' 
        AND tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
        AND kcu.COLUMN_NAME = 'sub_organization_id'
        AND rc.REFERENCED_TABLE_NAME = 'sub_organizations'
    """))
    constraints = [row[0] for row in result]
    
    for constraint_name in constraints:
        try:
            op.drop_constraint(constraint_name, 'documents', type_='foreignkey')
        except Exception:
            # Constraint might not exist or already dropped
            pass
    
    # Step 6: Drop index on sub_organization_id if it exists
    result = connection.execute(sa.text("""
        SELECT INDEX_NAME 
        FROM information_schema.STATISTICS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'documents' 
        AND COLUMN_NAME = 'sub_organization_id'
    """))
    indexes = [row[0] for row in result]
    for index_name in indexes:
        try:
            op.drop_index(index_name, table_name='documents')
        except Exception:
            # Index might not exist or already dropped
            pass
    
    # Step 7: Drop sub_organization_id column from documents table
    result = connection.execute(sa.text("""
        SELECT COLUMN_NAME 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'documents' 
        AND COLUMN_NAME = 'sub_organization_id'
    """))
    if result.fetchone():
        op.drop_column('documents', 'sub_organization_id')
    
    # Step 8: Drop sub_organizations table
    # Check if table exists first
    result = connection.execute(sa.text("""
        SELECT TABLE_NAME 
        FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'sub_organizations'
    """))
    if result.fetchone():
        op.drop_table('sub_organizations')


def downgrade():
    # Recreate sub_organizations table
    op.create_table(
        'sub_organizations',
        sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('organization_id', mysql.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('name', mysql.VARCHAR(length=255), nullable=False),
        sa.Column('description', mysql.TEXT(), nullable=True),
        sa.Column('is_active', mysql.BOOLEAN(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='sub_organizations_ibfk_1'),
        sa.PrimaryKeyConstraint('id'),
        mysql_collate='utf8mb4_unicode_ci',
        mysql_default_charset='utf8mb4',
        mysql_engine='InnoDB'
    )
    op.create_index(op.f('ix_sub_organizations_id'), 'sub_organizations', ['id'], unique=False)
    op.create_index(op.f('ix_sub_organizations_organization_id'), 'sub_organizations', ['organization_id'], unique=False)
    op.create_index(op.f('ix_sub_organizations_name'), 'sub_organizations', ['name'], unique=False)
    
    # Add sub_organization_id column to documents table
    op.add_column('documents', sa.Column('sub_organization_id', mysql.INTEGER(), nullable=True))
    op.create_foreign_key('documents_ibfk_sub_org', 'documents', 'sub_organizations', ['sub_organization_id'], ['id'])
    op.create_index(op.f('ix_documents_sub_organization_id'), 'documents', ['sub_organization_id'], unique=False)
    
    # Add sub_organization_id column to users table
    op.add_column('users', sa.Column('sub_organization_id', mysql.INTEGER(), nullable=True))
    op.create_foreign_key('users_ibfk_sub_org', 'users', 'sub_organizations', ['sub_organization_id'], ['id'])
    op.create_index(op.f('ix_users_sub_organization_id'), 'users', ['sub_organization_id'], unique=False)
