#!/bin/bash

# Travel Companion - Initial Project Setup Script
# This script sets up the development environment for the Travel Companion application

set -e

echo "🚀 Setting up Travel Companion development environment..."

# Color definitions for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_requirements() {
    print_status "Checking requirements..."
    
    # Check UV
    if ! command -v uv &> /dev/null; then
        print_error "UV is not installed. Please install UV first:"
        print_error "curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    print_success "UV is installed ($(uv --version))"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18+ first"
        exit 1
    fi
    print_success "Node.js is installed ($(node --version))"
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install npm first"
        exit 1
    fi
    print_success "npm is installed ($(npm --version))"
    
    # Check Docker (optional)
    if command -v docker &> /dev/null; then
        print_success "Docker is installed ($(docker --version | head -n1))"
    else
        print_warning "Docker is not installed. You'll need Docker for containerized development"
    fi
    
    # Check Docker Compose (optional)
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose is installed ($(docker-compose --version))"
    else
        print_warning "Docker Compose is not installed. You'll need it for multi-service development"
    fi
}

# Setup Python environment
setup_python_env() {
    print_status "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        print_status "Creating Python virtual environment..."
        uv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    cd packages/api
    uv sync --dev
    cd ../..
    print_success "Python dependencies installed"
}

# Setup Node.js environment
setup_node_env() {
    print_status "Setting up Node.js environment..."
    
    # Install frontend dependencies
    print_status "Installing frontend dependencies..."
    cd packages/web
    npm install
    cd ../..
    print_success "Node.js dependencies installed"
}

# Setup environment variables
setup_env_vars() {
    print_status "Setting up environment variables..."
    
    if [ ! -f ".env" ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_success ".env file created"
        print_warning "Please edit .env file with your actual configuration values"
    else
        print_success ".env file already exists"
    fi
}

# Setup workspace package.json
setup_workspace() {
    print_status "Setting up workspace configuration..."
    
    if [ ! -f "package.json" ]; then
        print_status "Creating root package.json for workspace management..."
        cat > package.json << 'EOF'
{
  "name": "travel-companion",
  "version": "0.1.0",
  "private": true,
  "workspaces": [
    "packages/*"
  ],
  "scripts": {
    "dev": "./scripts/dev.sh",
    "build": "npm run build:web && npm run build:api",
    "build:web": "cd packages/web && npm run build",
    "build:api": "cd packages/api && uv sync --no-dev",
    "test": "./scripts/test.sh",
    "test:web": "cd packages/web && npm run test",
    "test:api": "cd packages/api && uv run pytest",
    "lint": "npm run lint:web && npm run lint:api",
    "lint:web": "cd packages/web && npm run lint",
    "lint:api": "cd packages/api && uv run ruff check .",
    "format": "npm run format:web && npm run format:api",
    "format:web": "cd packages/web && npm run format",
    "format:api": "cd packages/api && uv run ruff format .",
    "setup": "./scripts/setup.sh",
    "docker:dev": "docker-compose -f docker-compose.dev.yml up --build",
    "docker:prod": "docker-compose up --build"
  },
  "devDependencies": {},
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=8.0.0"
  }
}
EOF
        print_success "Root package.json created"
    else
        print_success "Root package.json already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    # Create log directory
    mkdir -p logs
    
    # Create data directory for development
    mkdir -p data
    
    print_success "Directories created"
}

# Verify setup
verify_setup() {
    print_status "Verifying setup..."
    
    # Check Python environment
    if source .venv/bin/activate && python -c "import fastapi" 2>/dev/null; then
        print_success "Python environment is working"
    else
        print_error "Python environment verification failed"
        return 1
    fi
    
    # Check Node.js environment
    if cd packages/web && npm list next >/dev/null 2>&1; then
        cd ../..
        print_success "Node.js environment is working"
    else
        cd ../..
        print_error "Node.js environment verification failed"
        return 1
    fi
    
    print_success "Setup verification completed"
}

# Main setup function
main() {
    echo "=================================================="
    echo "🏝️  Travel Companion - Development Setup"
    echo "=================================================="
    echo ""
    
    check_requirements
    echo ""
    
    setup_python_env
    echo ""
    
    setup_node_env
    echo ""
    
    setup_env_vars
    echo ""
    
    setup_workspace
    echo ""
    
    create_directories
    echo ""
    
    verify_setup
    echo ""
    
    print_success "🎉 Travel Companion setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit the .env file with your configuration"
    echo "2. Run './scripts/dev.sh' to start the development environment"
    echo "3. Run './scripts/test.sh' to run tests"
    echo ""
    echo "For Docker-based development:"
    echo "- Run 'npm run docker:dev' to start with Docker Compose"
    echo ""
    echo "Happy coding! 🚀"
}

# Run main function
main "$@"