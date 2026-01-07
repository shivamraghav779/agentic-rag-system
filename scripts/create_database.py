#!/usr/bin/env python3
"""
MySQL Database Creation Script
Creates the chatbot database with proper UTF-8 encoding.
"""
import sys
import os
import getpass
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pymysql
except ImportError:
    print("Error: pymysql is not installed.")
    print("Install it with: pip install pymysql")
    sys.exit(1)

def parse_database_url(db_url: str):
    """Parse MySQL database URL."""
    # Format: mysql+pymysql://user:password@host:port/database
    if not db_url.startswith('mysql+pymysql://'):
        return None
    
    # Remove protocol
    db_url = db_url.replace('mysql+pymysql://', '')
    
    # Split user:pass@host:port/database
    if '@' in db_url:
        auth, rest = db_url.split('@', 1)
        if ':' in auth:
            user, password = auth.split(':', 1)
        else:
            user = auth
            password = None
    else:
        user = 'root'
        password = None
        rest = db_url
    
    # Split host:port/database
    if '/' in rest:
        host_port, database = rest.split('/', 1)
        # Remove query parameters if any
        database = database.split('?')[0]
    else:
        host_port = rest
        database = None
    
    if ':' in host_port:
        host, port = host_port.split(':', 1)
        port = int(port)
    else:
        host = host_port
        port = 3306
    
    return {
        'user': user,
        'password': password,
        'host': host,
        'port': port,
        'database': database or 'chatbot_db'
    }

def create_database():
    """Create the MySQL database."""
    # Try to read from .env file
    env_file = Path(__file__).parent.parent / '.env'
    db_config = None
    
    if env_file.exists():
        print("Reading database configuration from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    db_url = line.split('=', 1)[1].strip()
                    # db_config = parse_database_url(db_url)
                    db_config = {
            'user': 'ubuntu',
            'password': "techTattava@123",
            'host': 'techtattava.in',
            'port': 3306,
            'database': 'chatbot2'
        }
    
                    break
    
    if not db_config:
        print("Database configuration not found in .env, using defaults...")
        db_config = {
            'user': 'ubuntu',
            'password': "techTattava@123",
            'host': 'techtattava.in',
            'port': 3306,
            'database': 'chatbot2'
        }
    
    print(f"\nDatabase Configuration:")
    print(f"  Database: {db_config['database']}")
    print(f"  Host: {db_config['host']}")
    print(f"  Port: {db_config['port']}")
    print(f"  User: {db_config['user']}")
    print()
    
    # Get password if not provided
    if not db_config['password']:
        db_config['password'] = getpass.getpass(f"Enter MySQL password for user '{db_config['user']}': ")
    
    try:
        # Connect to MySQL (without specifying database)
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create database
            print(f"Creating database '{db_config['database']}'...")
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_config['database']}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            
            # Verify database creation
            cursor.execute(
                "SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
                "FROM information_schema.SCHEMATA "
                f"WHERE SCHEMA_NAME = '{db_config['database']}'"
            )
            result = cursor.fetchone()
            
            if result:
                print(f"\n✓ Database '{db_config['database']}' created successfully!")
                print(f"  Character Set: {result[1]}")
                print(f"  Collation: {result[2]}")
            else:
                print(f"\n✗ Failed to create database '{db_config['database']}'")
                return False
        
        connection.close()
        
        print("\n" + "="*50)
        print("Next steps:")
        print("1. Update your .env file with the correct DATABASE_URL")
        print("2. Run the application to create tables automatically:")
        print("   python main.py")
        print("="*50)
        
        return True
        
    except pymysql.Error as e:
        print(f"\n✗ Error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)

