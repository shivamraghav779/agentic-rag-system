# Database Setup Scripts

This directory contains scripts to set up the MySQL database for the chatbot application.

## Option 1: Using SQL Script (Manual)

Run the SQL script directly using MySQL command line:

```bash
mysql -u root -p < scripts/create_database.sql
```

Or connect to MySQL and run:

```bash
mysql -u root -p
source scripts/create_database.sql
```

## Option 2: Using Shell Script (Automated)

The shell script automatically reads database configuration from `.env` file and creates the database:

```bash
./scripts/create_database.sh
```

The script will:
- Read database configuration from `.env` file (if available)
- Prompt for MySQL password
- Create the database with proper UTF-8 encoding (utf8mb4)
- Display database information

## Option 3: Using Python Script (Recommended)

The Python script is the most user-friendly option and reads configuration from `.env`:

```bash
python scripts/create_database.py
```

Or:

```bash
./scripts/create_database.py
```

The Python script will:
- Automatically read database configuration from `.env` file
- Prompt for MySQL password securely
- Create the database with proper UTF-8 encoding (utf8mb4)
- Display database information and next steps

## Manual Database Creation

If you prefer to create the database manually:

```sql
CREATE DATABASE chatbot_db 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;
```

## After Database Creation

1. Update your `.env` file with the correct `DATABASE_URL`:
   ```env
   DATABASE_URL=mysql+pymysql://username:password@localhost:3306/chatbot_db
   ```

2. Run Alembic migrations to create tables:
   ```bash
   # Create initial migration
   alembic revision --autogenerate -m "Initial migration"
   
   # Apply migrations
   alembic upgrade head
   ```

   Or use the helper script:
   ```bash
   ./scripts/run_migrations.sh init
   ./scripts/run_migrations.sh upgrade
   ```

3. Alternatively, run the application - tables will be created automatically (if not using migrations):
   ```bash
   python main.py
   ```

## Database Migrations with Alembic

See [MIGRATIONS.md](../MIGRATIONS.md) for detailed migration instructions.

Quick commands:
- `./scripts/run_migrations.sh init` - Create initial migration
- `./scripts/run_migrations.sh upgrade` - Apply all migrations
- `./scripts/run_migrations.sh downgrade` - Rollback last migration
- `./scripts/run_migrations.sh current` - Show current revision

## Creating Admin User

After setting up the database and running migrations, you can create an admin user using:

```bash
python scripts/create_admin.py
```

Or:

```bash
./scripts/create_admin.py
```

The script will:
- Prompt for username, email, and password
- Validate inputs and check for duplicates
- Hash the password using Argon2
- Create an admin user with `is_admin=True`
- Allow you to set custom chat limit (default: 100)
- Allow you to set account active status (default: active)

**Note**: If a user with the same email already exists, the script will offer to make that user an admin instead of creating a duplicate.

## Notes

- The database uses `utf8mb4` character set to support emojis and special characters
- Tables can be created automatically by SQLAlchemy or via Alembic migrations
- Make sure MySQL server is running before executing the scripts
- Admin users have elevated privileges and can access admin endpoints

