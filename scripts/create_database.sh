#!/bin/bash

# MySQL Database Creation Script
# This script creates the chatbot database for MySQL

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}MySQL Database Creation Script${NC}"
echo "================================"
echo ""

# Default values
DB_NAME="chatbot_db"
DB_USER="root"
DB_HOST="localhost"
DB_PORT="3306"

# Check if .env file exists and read database URL
if [ -f .env ]; then
    echo -e "${YELLOW}Reading database configuration from .env file...${NC}"
    DB_URL=$(grep "^DATABASE_URL=" .env | cut -d '=' -f2-)
    
    if [ ! -z "$DB_URL" ]; then
        # Parse MySQL connection string: mysql+pymysql://user:password@host:port/database
        # Extract components
        DB_USER=$(echo $DB_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
        DB_PASS=$(echo $DB_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
        DB_HOST=$(echo $DB_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_PORT=$(echo $DB_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        DB_NAME=$(echo $DB_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
        
        echo -e "Database: ${GREEN}$DB_NAME${NC}"
        echo -e "Host: ${GREEN}$DB_HOST${NC}"
        echo -e "Port: ${GREEN}$DB_PORT${NC}"
        echo -e "User: ${GREEN}$DB_USER${NC}"
        echo ""
    fi
fi

# Prompt for MySQL root password
read -sp "Enter MySQL password for user '$DB_USER': " MYSQL_PASSWORD
echo ""

# Create database
echo -e "${YELLOW}Creating database '$DB_NAME'...${NC}"

mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$MYSQL_PASSWORD" << EOF
CREATE DATABASE IF NOT EXISTS $DB_NAME 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE $DB_NAME;

SELECT 
    SCHEMA_NAME as 'Database',
    DEFAULT_CHARACTER_SET_NAME as 'Charset',
    DEFAULT_COLLATION_NAME as 'Collation'
FROM information_schema.SCHEMATA 
WHERE SCHEMA_NAME = '$DB_NAME';
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database '$DB_NAME' created successfully!${NC}"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Update your .env file with the correct DATABASE_URL"
    echo "2. Run the application to create tables automatically"
    echo "   python main.py"
else
    echo -e "${RED}✗ Failed to create database. Please check your MySQL credentials.${NC}"
    exit 1
fi

