#!/usr/bin/env python3
"""
Database setup script for Travel Companion authentication.

This script helps set up the Supabase database with the required authentication
tables and security policies.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from travel_companion.core.database_init import setup_database


async def main():
    """Main setup function."""
    print("=" * 60)
    print("Travel Companion Database Setup for Authentication")
    print("=" * 60)
    print()

    print("This script will set up the database schema and security policies")
    print("required for user authentication in the Travel Companion application.")
    print()

    # Check if user wants to proceed
    response = input("Do you want to proceed with database setup? (y/N): ")
    if response.lower() not in ["y", "yes"]:
        print("Setup cancelled.")
        return

    print("\nStarting database setup...")
    print("-" * 40)

    try:
        success = await setup_database()

        print("-" * 40)
        if success:
            print("✅ Database setup completed successfully!")
            print("\nNext steps:")
            print("1. Run the SQL commands shown above in your Supabase SQL Editor")
            print("2. Verify the setup by running tests: uv run pytest")
        else:
            print("⚠️  Database setup completed with warnings.")
            print("\nPlease check the following:")
            print("1. Ensure SUPABASE_URL and SUPABASE_ANON_KEY are set in your .env file")
            print("2. Verify your Supabase project is accessible")
            print("3. Run the SQL commands shown above in your Supabase SQL Editor")

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
