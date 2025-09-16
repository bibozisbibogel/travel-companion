#!/usr/bin/env python3
"""Simple runner for HotelAgent programmatic testing.

This script provides an easy way to run hotel agent tests directly
without needing to navigate deep into the test directory structure.

Usage:
    python run_hotel_test.py           # Run automated tests
    python run_hotel_test.py --interactive  # Interactive mode
    python run_hotel_test.py --help    # Show help
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import our programmatic test
from tests.test_agents.test_hotel_agent_programmatic import (
    test_hotel_agent_search,
    interactive_test,
    print_results_summary
)


def show_help():
    """Show help information."""
    help_text = """
HotelAgent Programmatic Test Runner

Usage:
    python run_hotel_test.py [OPTIONS]

Options:
    --interactive, -i    Run in interactive mode (prompts for search parameters)
    --help, -h          Show this help message

Examples:
    python run_hotel_test.py                    # Run automated test suite
    python run_hotel_test.py --interactive      # Interactive hotel search
    python run_hotel_test.py -i                 # Short form of interactive

Automated Test Features:
    - Tests basic hotel search functionality
    - Tests hotel ranking and scoring algorithms
    - Tests hotel filtering by criteria
    - Tests result pagination
    - Tests caching mechanisms
    - Tests raw API request processing

Interactive Test Features:
    - Prompts for custom search parameters
    - Real-time hotel search with your preferences
    - Optional hotel ranking display
    - User-friendly result formatting

Note: This uses mock external APIs for testing. To test with real APIs,
      configure proper API keys in your environment variables.
    """
    print(help_text)


async def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        show_help()
        return
    
    if '--interactive' in args or '-i' in args:
        print("🏨 Starting Interactive HotelAgent Test...")
        await interactive_test()
    else:
        print("🏨 Starting Automated HotelAgent Test Suite...")
        success = await test_hotel_agent_search()
        
        if success:
            print("\n✅ All automated tests completed successfully!")
            print("\nTip: Try interactive mode with 'python run_hotel_test.py --interactive'")
        else:
            print("\n❌ Some tests encountered issues!")
            return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)