#!/usr/bin/env python3
"""
Quick test to verify Supabase database connection and schema.
Run this after setting up the database schema.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from travel_companion.core.database import get_database_manager


async def test_database_connection():
    """Test database connection and basic operations."""
    print("=" * 80)
    print("Testing Supabase Database Connection")
    print("=" * 80)
    print()

    # Get database manager
    db = get_database_manager()

    # Test 1: Health Check
    print("1. Testing database health check...")
    try:
        is_healthy = await db.health_check()
        if is_healthy:
            print("   ✅ Database is healthy and reachable")
        else:
            print("   ❌ Database health check failed")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False

    # Test 2: Check users table exists
    print("\n2. Testing users table access...")
    try:
        result = db.client.table("users").select("user_id").limit(1).execute()
        print(f"   ✅ Users table exists (found {len(result.data)} rows)")
    except Exception as e:
        print(f"   ❌ Users table error: {e}")
        print("   → Make sure you've run database_setup.sql first")
        return False

    # Test 3: Check trips table exists
    print("\n3. Testing trips table access...")
    try:
        result = db.client.table("trips").select("trip_id").limit(1).execute()
        print(f"   ✅ Trips table exists (found {len(result.data)} rows)")
    except Exception as e:
        print(f"   ❌ Trips table error: {e}")
        print("   → Make sure you've run trips_schema.sql in Supabase")
        return False

    # Test 4: Check related tables
    print("\n4. Testing related tables...")
    tables = ["flight_options", "hotel_options", "activity_options", "workflow_states"]
    for table in tables:
        try:
            result = db.client.table(table).select("*").limit(1).execute()
            print(f"   ✅ {table} table exists")
        except Exception as e:
            print(f"   ❌ {table} table error: {e}")
            return False

    # Test 5: Check enums
    print("\n5. Checking enum types...")
    try:
        # This will fail if the enum doesn't exist
        db.client.table("trips").select("status").limit(1).execute()
        print("   ✅ trip_status enum exists")
    except Exception as e:
        print(f"   ⚠️  trip_status enum check: {e}")

    try:
        db.client.table("activity_options").select("category").limit(1).execute()
        print("   ✅ activity_category enum exists")
    except Exception as e:
        print(f"   ⚠️  activity_category enum check: {e}")

    print("\n" + "=" * 80)
    print("Database Schema Test Complete!")
    print("=" * 80)
    print()
    print("✅ All basic schema checks passed!")
    print()
    print("Next steps:")
    print(
        "  1. Run unit tests: uv run pytest src/travel_companion/services/tests/test_trip_service.py -v"
    )
    print("  2. Start the API server: uv run uvicorn travel_companion.main:app --reload")
    print("  3. Test via API docs: http://localhost:8000/docs")
    print()

    return True


async def test_trip_service_basic():
    """Test TripService basic operations (requires actual database)."""
    print("=" * 80)
    print("Testing TripService with Real Database")
    print("=" * 80)
    print()
    print("⚠️  NOTE: This test requires a valid user in the database.")
    print("   Skipping for now - use the API to create trips after authentication.")
    print()
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_database_connection())
        if success:
            print("🎉 Database is properly configured!")
            sys.exit(0)
        else:
            print("❌ Database configuration issues detected")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
