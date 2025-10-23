#!/usr/bin/env python3
"""
Database setup script for Trip Planning schema.

This script helps set up the Supabase database with the required trip planning
tables, enums, and security policies.
"""

import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def print_instructions():
    """Print setup instructions."""
    print("=" * 80)
    print("Travel Companion - Trip Planning Database Setup")
    print("=" * 80)
    print()
    print("This script will provide you with SQL to set up trip planning tables.")
    print()
    print("SETUP INSTRUCTIONS:")
    print("=" * 80)
    print()
    print("1. Log into your Supabase Dashboard")
    print("   -> https://app.supabase.com")
    print()
    print("2. Select your project")
    print()
    print("3. Go to 'SQL Editor' in the left sidebar")
    print()
    print("4. Click 'New Query'")
    print()
    print("5. Copy and paste the SQL below into the editor")
    print()
    print("6. Click 'Run' to execute the SQL")
    print()
    print("7. Verify success - you should see 'Success. No rows returned'")
    print()
    print("=" * 80)
    print()


def main():
    """Main setup function."""
    print_instructions()

    # Read the SQL file
    sql_file = Path(__file__).parent.parent / "src" / "travel_companion" / "core" / "trips_schema.sql"

    if not sql_file.exists():
        print(f"❌ ERROR: SQL file not found at {sql_file}")
        sys.exit(1)

    sql_content = sql_file.read_text()

    print("SQL TO EXECUTE IN SUPABASE SQL EDITOR:")
    print("=" * 80)
    print()
    print(sql_content)
    print()
    print("=" * 80)
    print()
    print("AFTER RUNNING THE SQL:")
    print("-" * 80)
    print("✅ The following will be created:")
    print("   • trips table - for storing trip plans and itineraries")
    print("   • flight_options table - for flight search results")
    print("   • hotel_options table - for accommodation options")
    print("   • activity_options table - for activities and attractions")
    print("   • workflow_states table - for workflow state tracking")
    print("   • trip_status enum - for trip status values")
    print("   • activity_category enum - for activity categories")
    print("   • Row Level Security policies - users can only access their own data")
    print("   • Indexes for query performance")
    print("   • Triggers for automatic updated_at timestamps")
    print()
    print("✅ You can verify the setup by:")
    print("   1. Going to 'Table Editor' in Supabase")
    print("   2. Checking that the 'trips' table exists")
    print("   3. Running: uv run pytest src/tests/test_api/test_trips.py")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
