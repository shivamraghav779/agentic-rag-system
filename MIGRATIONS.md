# Database Migrations with Alembic

This project uses Alembic for database migrations. Alembic allows you to version control your database schema and apply changes incrementally.

## Setup

Alembic is already configured in this project. The configuration files are:
- `alembic.ini` - Alembic configuration
- `alembic/env.py` - Migration environment setup
- `alembic/versions/` - Directory containing migration files

## Quick Start

### 1. Create Initial Migration

After setting up your database, create the initial migration:

```bash
alembic revision --autogenerate -m "Initial migration"
```

Or use the helper script:
```bash
./scripts/run_migrations.sh init
```

This will:
- Analyze your models in `app/models/`
- Generate a migration file in `alembic/versions/`
- Include all table creations based on your SQLAlchemy models

### 2. Review the Migration

Before applying, review the generated migration file in `alembic/versions/` to ensure it's correct.

### 3. Apply Migrations

Apply all pending migrations:

```bash
alembic upgrade head
```

Or use the helper script:
```bash
./scripts/run_migrations.sh upgrade
```

## Common Commands

### Create a New Migration

When you modify your models, create a new migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

Example:
```bash
alembic revision --autogenerate -m "Add system_prompt to users table"
```

### Apply Migrations

Apply all pending migrations to the latest version:

```bash
alembic upgrade head
```

Apply migrations up to a specific revision:

```bash
alembic upgrade <revision_id>
```

### Rollback Migrations

Rollback the last migration:

```bash
alembic downgrade -1
```

Rollback to a specific revision:

```bash
alembic downgrade <revision_id>
```

### Check Current Status

View current database revision:

```bash
alembic current
```

View migration history:

```bash
alembic history
```

View current heads (latest migrations):

```bash
alembic heads
```

## Using the Helper Script

The project includes a helper script for common operations:

```bash
./scripts/run_migrations.sh [command]
```

Available commands:
- `init` - Create initial migration
- `upgrade` - Apply all pending migrations
- `downgrade` - Rollback last migration
- `current` - Show current database revision
- `history` - Show migration history
- `heads` - Show current heads

## Workflow

### Adding a New Field to a Model

1. **Modify the model** in `app/models/`:
   ```python
   class User(Base):
       # ... existing fields ...
       new_field = Column(String(100), nullable=True)
   ```

2. **Create a migration**:
   ```bash
   alembic revision --autogenerate -m "Add new_field to users"
   ```

3. **Review the migration file** in `alembic/versions/`

4. **Apply the migration**:
   ```bash
   alembic upgrade head
   ```

### Removing a Field

1. **Remove from model** in `app/models/`

2. **Create a migration**:
   ```bash
   alembic revision --autogenerate -m "Remove old_field from users"
   ```

3. **Review and apply** the migration

## Migration File Structure

Each migration file contains:

```python
"""Add system_prompt to users

Revision ID: abc123
Revises: xyz789
Create Date: 2024-01-01 12:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123'
down_revision = 'xyz789'

def upgrade():
    # Apply changes
    op.add_column('users', sa.Column('system_prompt', sa.Text(), nullable=True))

def downgrade():
    # Rollback changes
    op.drop_column('users', 'system_prompt')
```

## Important Notes

1. **Always review auto-generated migrations** - Alembic's autogenerate is smart but not perfect
2. **Test migrations** - Test both upgrade and downgrade on a development database
3. **Backup before migrations** - Always backup production databases before applying migrations
4. **Migration order matters** - Migrations are applied in order based on revision IDs
5. **Don't edit old migrations** - If you need to change something, create a new migration

## Troubleshooting

### Migration conflicts

If you have multiple heads (branches), merge them:

```bash
alembic merge heads -m "Merge migration branches"
```

### Database out of sync

If your database is out of sync with migrations:

1. Check current revision: `alembic current`
2. Check migration history: `alembic history`
3. Manually sync or create a new migration to match current state

### Autogenerate not detecting changes

If Alembic doesn't detect your model changes:

1. Ensure all models are imported in `app/models/__init__.py`
2. Check that `target_metadata` in `alembic/env.py` includes all models
3. Try creating a manual migration instead

## Production Deployment

For production:

1. **Backup the database** before migrations
2. **Test migrations** on a staging environment first
3. **Apply migrations** during maintenance window if possible
4. **Monitor** the application after migration
5. **Have a rollback plan** ready

Example production workflow:

```bash
# 1. Backup database
mysqldump -u user -p database_name > backup.sql

# 2. Apply migrations
alembic upgrade head

# 3. Verify application works

# 4. If issues, rollback
alembic downgrade -1
```

## Configuration

Alembic reads the database URL from your `.env` file via `app/core/config.py`. Make sure your `DATABASE_URL` is correctly set:

```env
DATABASE_URL=mysql+pymysql://username:password@host:port/database
```

The configuration is automatically loaded in `alembic/env.py`.

