#!/bin/bash

# Travel Companion - Development Environment Startup Script
# This script starts the development environment with both frontend and backend services

set -e

# Color definitions for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

print_api() {
    echo -e "${PURPLE}[API]${NC} $1"
}

print_web() {
    echo -e "${CYAN}[WEB]${NC} $1"
}

# Default values
MODE="local"
SERVICES="all"
PORT_API=8000
PORT_WEB=3000

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --service)
            SERVICES="$2"
            shift 2
            ;;
        --api-port)
            PORT_API="$2"
            shift 2
            ;;
        --web-port)
            PORT_WEB="$2"
            shift 2
            ;;
        --help)
            echo "Travel Companion Development Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --mode MODE       Development mode: local, docker (default: local)"
            echo "  --service SERVICE Services to start: api, web, all (default: all)"
            echo "  --api-port PORT   API server port (default: 8000)"
            echo "  --web-port PORT   Web server port (default: 3000)"
            echo "  --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                      # Start all services locally"
            echo "  $0 --mode docker       # Start all services with Docker"
            echo "  $0 --service api       # Start only API service"
            echo "  $0 --service web       # Start only web service"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if environment is set up
check_environment() {
    print_status "Checking development environment..."
    
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your configuration"
    fi
    
    if [ "$MODE" = "local" ]; then
        # Check Python virtual environment
        if [ ! -d ".venv" ]; then
            print_error "Python virtual environment not found. Run './scripts/setup.sh' first"
            exit 1
        fi
        
        # Check Node.js dependencies
        if [ ! -d "packages/web/node_modules" ]; then
            print_error "Node.js dependencies not installed. Run './scripts/setup.sh' first"
            exit 1
        fi
    elif [ "$MODE" = "docker" ]; then
        # Check Docker and Docker Compose
        if ! command -v docker &> /dev/null; then
            print_error "Docker is not installed"
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            print_error "Docker Compose is not installed"
            exit 1
        fi
    fi
    
    print_success "Environment check passed"
}

# Start services locally
start_local() {
    print_status "Starting services locally..."
    
    # Create log directory
    mkdir -p logs
    
    # Function to start API service
    start_api() {
        print_api "Starting FastAPI backend on port $PORT_API..."
        cd packages/api
        
        # Activate virtual environment and start server
        (
            source ../../.venv/bin/activate
            export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
            uv run uvicorn travel_companion.main:app \
                --host 0.0.0.0 \
                --port $PORT_API \
                --reload \
                --reload-dir src \
                --log-level info \
                2>&1 | while read line; do print_api "$line"; done
        ) &
        API_PID=$!
        cd ../..
        
        # Wait a moment for API to start
        sleep 2
        print_success "FastAPI backend started (PID: $API_PID)"
        return $API_PID
    }
    
    # Function to start web service
    start_web() {
        print_web "Starting Next.js frontend on port $PORT_WEB..."
        cd packages/web
        
        (
            PORT=$PORT_WEB npm run dev 2>&1 | while read line; do print_web "$line"; done
        ) &
        WEB_PID=$!
        cd ../..
        
        # Wait a moment for web to start
        sleep 2
        print_success "Next.js frontend started (PID: $WEB_PID)"
        return $WEB_PID
    }
    
    # Start requested services
    PIDS=()
    
    if [ "$SERVICES" = "all" ] || [ "$SERVICES" = "api" ]; then
        start_api
        PIDS+=($!)
    fi
    
    if [ "$SERVICES" = "all" ] || [ "$SERVICES" = "web" ]; then
        start_web
        PIDS+=($!)
    fi
    
    # Wait for services to be ready
    sleep 5
    
    print_success "All services started successfully!"
    echo ""
    echo "🌐 Services available at:"
    
    if [ "$SERVICES" = "all" ] || [ "$SERVICES" = "api" ]; then
        echo "   📡 API:         http://localhost:$PORT_API"
        echo "   📊 API Docs:    http://localhost:$PORT_API/docs"
        echo "   ❤️  Health:     http://localhost:$PORT_API/api/v1/health"
    fi
    
    if [ "$SERVICES" = "all" ] || [ "$SERVICES" = "web" ]; then
        echo "   🖥️  Frontend:   http://localhost:$PORT_WEB"
    fi
    
    echo ""
    echo "📝 Logs are being displayed above"
    echo "🛑 Press Ctrl+C to stop all services"
    echo ""
    
    # Setup cleanup trap
    cleanup() {
        print_status "Shutting down services..."
        for pid in "${PIDS[@]}"; do
            if ps -p $pid > /dev/null; then
                print_status "Stopping process $pid..."
                kill $pid 2>/dev/null || true
            fi
        done
        print_success "All services stopped"
        exit 0
    }
    
    trap cleanup SIGINT SIGTERM
    
    # Wait for all background processes
    for pid in "${PIDS[@]}"; do
        wait $pid
    done
}

# Start services with Docker
start_docker() {
    print_status "Starting services with Docker Compose..."
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    # Start services based on selection
    if [ "$SERVICES" = "all" ]; then
        docker-compose -f docker-compose.dev.yml up --build
    else
        docker-compose -f docker-compose.dev.yml up --build $SERVICES
    fi
}

# Main function
main() {
    echo "=================================================="
    echo "🏝️  Travel Companion - Development Environment"
    echo "=================================================="
    echo ""
    echo "Mode: $MODE"
    echo "Services: $SERVICES"
    if [ "$MODE" = "local" ]; then
        echo "API Port: $PORT_API"
        echo "Web Port: $PORT_WEB"
    fi
    echo ""
    
    check_environment
    echo ""
    
    case $MODE in
        local)
            start_local
            ;;
        docker)
            start_docker
            ;;
        *)
            print_error "Unknown mode: $MODE"
            echo "Supported modes: local, docker"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"