#!/bin/bash

# Production startup script for Gym Manager
# This script starts the application with Gunicorn

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Gym Manager in production mode...${NC}"

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Virtual environment not activated. Activating...${NC}"
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}Error: Virtual environment not found at venv/bin/activate${NC}"
        echo "Please create a virtual environment first:"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  nano .env  # Edit with your values"
    exit 1
fi

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo -e "${RED}Error: Gunicorn not found${NC}"
    echo "Please install requirements:"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if database exists
if [ ! -f "exercises.db" ]; then
    echo -e "${YELLOW}Warning: Database file (exercises.db) not found${NC}"
    echo "The application may not work correctly without a database."
    echo "If you have a database initialization script, run it first."
fi

# Check if SECRET_KEY is set to default
if grep -q "your-secret-key-here" .env 2>/dev/null; then
    echo -e "${RED}WARNING: SECRET_KEY is still set to default value!${NC}"
    echo "Generate a secure key with:"
    echo "  python3 -c \"import secrets; print(secrets.token_hex(32))\""
    echo ""
    read -p "Continue anyway? (not recommended for production) [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}Configuration checks passed${NC}"
echo ""

# Start Gunicorn with configuration file
echo -e "${GREEN}Starting Gunicorn...${NC}"
echo "Configuration: gunicorn_config.py"
echo "WSGI module: wsgi:app"
echo ""

gunicorn --config gunicorn_config.py wsgi:app
