# TravelPlannerAgent Database Save Feature

The `test_planner_agent.py` script now supports saving generated itineraries directly to your Supabase database!

## Quick Start

### Basic Usage (No Database Save)
```bash
cd /home/mihai/repos/travel-companion/packages/api/src/test_agents_sdk
uv run python test_planner_agent.py
```

This will:
- Generate a trip itinerary using TravelPlannerAgent
- Save JSON output to `itinerary_output.json`
- Display the itinerary in the console
- ⚠️ **NOT** save to database (use `--save-to-db` flag)

### Save to Database
```bash
uv run python test_planner_agent.py --save-to-db
```

This will do everything above **PLUS**:
- Save the trip to your Supabase `trips` table
- Use a test user ID (default: `00000000-0000-0000-0000-000000000001`)
- Display the trip ID for verification

### Save with Specific User ID
```bash
# Use your actual user ID from Supabase
uv run python test_planner_agent.py --save-to-db --user-id=123e4567-e89b-12d3-a456-426614174000
```

### Disable Text Streaming
```bash
# Print instantly instead of character-by-character
uv run python test_planner_agent.py --no-streaming --save-to-db
```

## Command-Line Options

| Option | Alias | Description |
|--------|-------|-------------|
| `--save-to-db` | `--db` | Save generated itinerary to database |
| `--user-id=UUID` | `--user=UUID` | Specify user ID for database save |
| `--no-streaming` | | Disable text streaming animation |
| `--help` | `-h` | Show help message |

## Requirements

### 1. Database Setup
Make sure you've set up the database schema:
```bash
cd /home/mihai/repos/travel-companion/packages/api
uv run python scripts/setup_trips_schema.py
```

Then run the SQL in your Supabase SQL Editor.

### 2. Environment Variables
Ensure your `.env` file has:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-or-anon-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### 3. Test User (Optional)
To use a real user instead of the test user, create one via API or Supabase:

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#",
    "first_name": "Test",
    "last_name": "User"
  }'
```

Then use the returned `user_id` with `--user-id=<UUID>`.

## What Gets Saved

The script saves to the `trips` table:
- **trip_id**: Auto-generated UUID
- **user_id**: Specified user or test user
- **name**: "Trip to {destination}"
- **description**: "AI-generated travel plan for {destination}"
- **destination**: City name
- **start_date**: From trip requirements
- **end_date**: From trip requirements
- **total_budget**: From trip requirements
- **traveler_count**: From trip requirements
- **status**: "planning"
- **preferences**: JSONB with travel class, accommodation, currency, destination details
- **itinerary_data**: Complete ItineraryOutput JSON with:
  - Trip info (destination, dates, travelers, budget)
  - Flight details
  - Accommodation details
  - Day-by-day itinerary
  - Budget breakdown
  - Travel tips

## Verification

### 1. Check Console Output
After running with `--save-to-db`, you'll see:
```
✅ Trip saved to database!
   Trip ID: 550e8400-e29b-41d4-a716-446655440000
   User ID: 00000000-0000-0000-0000-000000000001
   Status: planning
   Created: 2025-10-23 14:30:00+00:00

🔗 View in Supabase:
   https://app.supabase.com → Table Editor → trips → {trip_id}
```

### 2. Check Supabase Dashboard
1. Go to https://app.supabase.com
2. Select your project
3. Click **Table Editor**
4. Select **trips** table
5. Find your trip by the `trip_id` shown in console

### 3. Verify via API
```bash
# Start the API server
uv run uvicorn travel_companion.main:app --reload

# Get your trip (after authenticating)
curl -X GET http://localhost:8000/api/v1/trips/{trip_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Examples

### 1. Quick Test (No DB Save)
```bash
uv run python test_planner_agent.py --no-streaming
```

### 2. Full Production Test
```bash
# 1. Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!@#", "first_name": "Test", "last_name": "User"}'

# 2. Save the user_id from response

# 3. Run test with that user
uv run python test_planner_agent.py --save-to-db --user-id=YOUR_USER_ID
```

### 3. Multiple Trips for Same User
```bash
# Run multiple times with same user_id
for i in {1..3}; do
  uv run python test_planner_agent.py --save-to-db --user-id=YOUR_USER_ID
  sleep 5
done

# Check Supabase to see all 3 trips!
```

## Troubleshooting

### Error: "relation 'trips' does not exist"
**Solution:** Run the database setup script:
```bash
uv run python scripts/setup_trips_schema.py
```

### Error: "User ID not found" or RLS Policy Error
**Solution:**
1. Make sure the user exists in the `users` table
2. Or use the test user ID: `00000000-0000-0000-0000-000000000001`
3. Check RLS policies in Supabase

### Error: "SUPABASE_URL not set"
**Solution:** Make sure `.env` file has correct Supabase credentials

### Trip Saved But Not Visible
**Check:**
1. Are you looking at the right Supabase project?
2. Is the user_id correct?
3. Check RLS policies (may prevent access if user mismatch)

## Tips

1. **Always use `--save-to-db` flag** - Database save is OFF by default to avoid accidental test data

2. **Use real user IDs** - Create users via API and use their IDs for realistic testing

3. **Check JSON file first** - The `itinerary_output.json` is always created, check it before DB save

4. **Clean up test data** - Delete test trips from Supabase dashboard when done testing

5. **Monitor database** - Watch Supabase real-time for trips being created

## Next Steps

- Modify the trip parameters in `test_planner_agent.py` (lines 75-115)
- Change destination, dates, budget, etc.
- Run with `--save-to-db` to see different itineraries in your database
- Use the saved trips in your frontend application!
