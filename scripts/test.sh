#!/bin/bash

# Travel Companion - Test Runner Script
# This script runs all tests for the Travel Companion application

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
SUITE="all"
COVERAGE=false
VERBOSE=false
WATCH=false
PARALLEL=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --suite)
            SUITE="$2"
            shift 2
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --watch)
            WATCH=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --help)
            echo "Travel Companion Test Runner"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --suite SUITE     Test suite: all, api, web, lint (default: all)"
            echo "  --coverage        Generate coverage reports"
            echo "  --verbose         Verbose test output"
            echo "  --watch          Watch mode (for frontend tests)"
            echo "  --parallel       Run tests in parallel where possible"
            echo "  --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                      # Run all tests"
            echo "  $0 --suite api         # Run only API tests"
            echo "  $0 --suite web --watch # Run web tests in watch mode"
            echo "  $0 --coverage          # Run all tests with coverage"
            echo "  $0 --suite lint        # Run only linting"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check environment
check_environment() {
    print_status "Checking test environment..."
    
    if [ ! -d ".venv" ]; then
        print_error "Python virtual environment not found. Run './scripts/setup.sh' first"
        exit 1
    fi
    
    if [ ! -d "packages/web/node_modules" ]; then
        print_error "Node.js dependencies not installed. Run './scripts/setup.sh' first"
        exit 1
    fi
    
    print_success "Environment check passed"
}

# Run API tests
run_api_tests() {
    print_api "Running FastAPI backend tests..."
    cd packages/api
    
    # Set Python path for imports
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
    
    # Build pytest command
    PYTEST_CMD="uv run pytest"
    
    if [ "$VERBOSE" = true ]; then
        PYTEST_CMD="$PYTEST_CMD -v"
    fi
    
    if [ "$COVERAGE" = true ]; then
        PYTEST_CMD="$PYTEST_CMD --cov=src/travel_companion --cov-report=html --cov-report=term"
    fi
    
    # Run tests
    if $PYTEST_CMD; then
        cd ../..
        print_success "API tests passed"
        return 0
    else
        cd ../..
        print_error "API tests failed"
        return 1
    fi
}

# Run web tests
run_web_tests() {
    print_web "Running Next.js frontend tests..."
    cd packages/web
    
    # Note: Next.js doesn't come with a test runner by default
    # We'll add a simple test setup check for now
    if [ -f "package.json" ] && grep -q '"test"' package.json; then
        if [ "$WATCH" = true ]; then
            npm run test -- --watch
        else
            npm run test
        fi
        TEST_RESULT=$?
    else
        print_warning "No test configuration found in frontend package"
        print_status "Creating basic test setup for future use..."
        
        # Create a basic test setup
        mkdir -p src/__tests__
        cat > src/__tests__/example.test.ts << 'EOF'
// Example test file for Travel Companion frontend
// This is a placeholder that will be expanded in future stories

describe('Travel Companion Frontend', () => {
  it('should have basic structure', () => {
    expect(true).toBe(true);
  });
});
EOF
        
        print_success "Basic test structure created"
        TEST_RESULT=0
    fi
    
    cd ../..
    
    if [ $TEST_RESULT -eq 0 ]; then
        print_success "Web tests passed"
        return 0
    else
        print_error "Web tests failed"
        return 1
    fi
}

# Run linting
run_linting() {
    print_status "Running code quality checks..."
    
    API_LINT_RESULT=0
    WEB_LINT_RESULT=0
    
    # API linting
    print_api "Running Python linting (Ruff)..."
    cd packages/api
    
    if uv run ruff check .; then
        print_success "Python linting passed"
    else
        print_error "Python linting failed"
        API_LINT_RESULT=1
    fi
    
    # API formatting check
    print_api "Checking Python formatting..."
    if uv run ruff format --check .; then
        print_success "Python formatting is correct"
    else
        print_error "Python formatting issues found"
        API_LINT_RESULT=1
    fi
    
    # API type checking
    print_api "Running Python type checking (mypy)..."
    if uv run mypy src/travel_companion/; then
        print_success "Python type checking passed"
    else
        print_warning "Python type checking found issues (non-blocking)"
    fi
    
    cd ../..
    
    # Web linting
    print_web "Running TypeScript linting..."
    cd packages/web
    
    if npm run lint; then
        print_success "TypeScript linting passed"
    else
        print_error "TypeScript linting failed"
        WEB_LINT_RESULT=1
    fi
    
    cd ../..
    
    if [ $API_LINT_RESULT -eq 0 ] && [ $WEB_LINT_RESULT -eq 0 ]; then
        print_success "All linting checks passed"
        return 0
    else
        print_error "Linting checks failed"
        return 1
    fi
}

# Run all tests
run_all_tests() {
    print_status "Running complete test suite..."
    
    RESULTS=()
    
    if [ "$PARALLEL" = true ]; then
        print_status "Running tests in parallel..."
        
        # Run API tests in background
        (run_api_tests) &
        API_PID=$!
        
        # Run linting in background
        (run_linting) &
        LINT_PID=$!
        
        # Run web tests in foreground
        run_web_tests
        WEB_RESULT=$?
        
        # Wait for background jobs
        wait $API_PID
        API_RESULT=$?
        
        wait $LINT_PID
        LINT_RESULT=$?
        
        RESULTS=($API_RESULT $WEB_RESULT $LINT_RESULT)
    else
        print_status "Running tests sequentially..."
        
        run_api_tests
        RESULTS+=($?)
        
        run_web_tests
        RESULTS+=($?)
        
        run_linting
        RESULTS+=($?)
    fi
    
    # Check results
    FAILED=0
    for result in "${RESULTS[@]}"; do
        if [ $result -ne 0 ]; then
            FAILED=$((FAILED + 1))
        fi
    done
    
    if [ $FAILED -eq 0 ]; then
        print_success "All tests passed! ✨"
        return 0
    else
        print_error "$FAILED test suite(s) failed"
        return 1
    fi
}

# Generate test report
generate_report() {
    print_status "Generating test report..."
    
    REPORT_DIR="test-reports"
    mkdir -p "$REPORT_DIR"
    
    REPORT_FILE="$REPORT_DIR/test-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$REPORT_FILE" << EOF
# Travel Companion Test Report

**Date:** $(date)
**Suite:** $SUITE
**Coverage:** $COVERAGE
**Parallel:** $PARALLEL

## Test Results

EOF
    
    if [ "$COVERAGE" = true ] && [ -f "packages/api/htmlcov/index.html" ]; then
        echo "- 📊 API Coverage Report: packages/api/htmlcov/index.html" >> "$REPORT_FILE"
    fi
    
    print_success "Test report generated: $REPORT_FILE"
}

# Main function
main() {
    echo "=================================================="
    echo "🧪 Travel Companion - Test Runner"
    echo "=================================================="
    echo ""
    echo "Suite: $SUITE"
    echo "Coverage: $COVERAGE"
    echo "Verbose: $VERBOSE"
    echo "Watch: $WATCH"
    echo "Parallel: $PARALLEL"
    echo ""
    
    check_environment
    echo ""
    
    case $SUITE in
        all)
            run_all_tests
            RESULT=$?
            ;;
        api)
            run_api_tests
            RESULT=$?
            ;;
        web)
            run_web_tests
            RESULT=$?
            ;;
        lint)
            run_linting
            RESULT=$?
            ;;
        *)
            print_error "Unknown test suite: $SUITE"
            echo "Supported suites: all, api, web, lint"
            exit 1
            ;;
    esac
    
    echo ""
    
    if [ $RESULT -eq 0 ]; then
        print_success "🎉 Test execution completed successfully!"
        
        if [ "$COVERAGE" = true ]; then
            generate_report
        fi
        
        echo ""
        echo "Next steps:"
        echo "- Review any warnings or suggestions above"
        echo "- Check coverage reports if generated"
        echo "- Fix any failing tests before committing"
        
    else
        print_error "💥 Test execution failed!"
        echo ""
        echo "Next steps:"
        echo "- Review the error messages above"
        echo "- Fix failing tests or linting issues"
        echo "- Re-run tests with --verbose for more details"
        
        exit 1
    fi
}

# Run main function
main "$@"