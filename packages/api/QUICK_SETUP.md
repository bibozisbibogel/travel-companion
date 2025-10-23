# Quick Database Setup - TL;DR

## For Supabase Setup

### 1️⃣ Get the SQL
```bash
cd /home/mihai/repos/travel-companion/packages/api
uv run python scripts/setup_trips_schema.py
```

### 2️⃣ Run in Supabase
1. Go to https://app.supabase.com
2. Select your project
3. Click **SQL Editor** → **New Query**
4. Copy/paste the SQL from step 1
5. Click **Run** ▶️

### 3️⃣ Verify
```bash
# Check tables exist in Supabase Dashboard → Table Editor
# Should see: trips, flight_options, hotel_options, activity_options, workflow_states
```

## Quick Test

```bash
# Run tests
uv run pytest src/tests/test_api/test_trips.py -v

# Or test manually
uv run uvicorn travel_companion.main:app --reload
# Visit http://localhost:8000/docs
```

## Tables Created

✅ **trips** - Trip plans with itineraries
✅ **flight_options** - Flight search results
✅ **hotel_options** - Hotel options
✅ **activity_options** - Activities & attractions
✅ **workflow_states** - Workflow tracking

## Security

🔒 Row Level Security (RLS) enabled
🔒 Users can only access their own data
🔒 All CRUD operations protected

## Need Help?

See [DATABASE_SETUP.md](./DATABASE_SETUP.md) for detailed instructions.

## File Locations

- **SQL Schema**: `src/travel_companion/core/trips_schema.sql`
- **Setup Script**: `scripts/setup_trips_schema.py`
- **Full Docs**: `DATABASE_SETUP.md`
