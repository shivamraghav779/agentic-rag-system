#!/bin/bash

# Alembic Migration Script
# This script helps you run Alembic migrations

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Alembic Migration Helper${NC}"
echo "========================"
echo ""

# Check if alembic is installed
if ! command -v alembic &> /dev/null; then
    echo -e "${RED}Error: Alembic is not installed.${NC}"
    echo "Install it with: pip install alembic"
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  init        - Create initial migration (run this first)"
    echo "  upgrade     - Apply all pending migrations"
    echo "  downgrade   - Rollback last migration"
    echo "  current     - Show current database revision"
    echo "  history     - Show migration history"
    echo "  heads       - Show current heads"
    echo ""
    echo "Examples:"
    echo "  $0 init          # Create initial migration"
    echo "  $0 upgrade       # Apply migrations"
    echo "  $0 downgrade     # Rollback last migration"
}

# Parse command
COMMAND=${1:-help}

case $COMMAND in
    init)
        echo -e "${YELLOW}Creating initial migration...${NC}"
        alembic revision --autogenerate -m "Initial migration"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Initial migration created!${NC}"
            echo ""
            echo "Next step: Review the migration file in alembic/versions/"
            echo "Then run: $0 upgrade"
        else
            echo -e "${RED}✗ Failed to create migration${NC}"
            exit 1
        fi
        ;;
    upgrade)
        echo -e "${YELLOW}Applying migrations...${NC}"
        alembic upgrade head
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Migrations applied successfully!${NC}"
        else
            echo -e "${RED}✗ Failed to apply migrations${NC}"
            exit 1
        fi
        ;;
    downgrade)
        echo -e "${YELLOW}Rolling back last migration...${NC}"
        alembic downgrade -1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Migration rolled back successfully!${NC}"
        else
            echo -e "${RED}✗ Failed to rollback migration${NC}"
            exit 1
        fi
        ;;
    current)
        echo -e "${YELLOW}Current database revision:${NC}"
        alembic current
        ;;
    history)
        echo -e "${YELLOW}Migration history:${NC}"
        alembic history
        ;;
    heads)
        echo -e "${YELLOW}Current heads:${NC}"
        alembic heads
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac

