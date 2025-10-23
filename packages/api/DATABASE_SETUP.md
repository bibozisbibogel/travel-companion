# Database Setup Guide

This guide will help you set up the database schema for the Travel Companion API in your Supabase project.

## Prerequisites

- A Supabase account and project
- `SUPABASE_URL` and `SUPABASE_KEY` configured in your `.env` file

## Quick Setup

### Step 1: Set Up Users Table (Authentication)

If you haven't already set up the users table:

```bash
cd /home/mihai/repos/travel-companion/packages/api
uv run python scripts/setup_database.py
```

Follow the on-screen instructions to copy and run the SQL in your Supabase SQL Editor.

**Or manually:**

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Navigate to **SQL Editor**
4. Click **New Query**
5. Copy the contents of `src/travel_companion/core/database_setup.sql`
6. Paste into the editor
7. Click **Run**

### Step 2: Set Up Trips Tables (Trip Planning)

Run the setup script:

```bash
cd /home/mihai/repos/travel-companion/packages/api
uv run python scripts/setup_trips_schema.py
```

This will display SQL that you need to run in Supabase SQL Editor.

**Or manually:**

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Navigate to **SQL Editor**
4. Click **New Query**
5. Copy the contents of `src/travel_companion/core/trips_schema.sql`
6. Paste into the editor
7. Click **Run**

## What Gets Created

### Users Table (Authentication)
- `users` - User accounts with authentication
- RLS policies for user data security
- Indexes for email lookup and performance
- Triggers for automatic `updated_at` timestamps

### Trips Tables (Trip Planning)
- `trips` - Main trip plans and itineraries
- `flight_options` - Flight search results and bookings
- `hotel_options` - Hotel/accommodation options
- `activity_options` - Activities and attractions
- `workflow_states` - Workflow execution tracking

### Enums
- `trip_status` - draft, planning, confirmed, completed, cancelled
- `activity_category` - cultural, adventure, food, entertainment, nature, shopping, relaxation, nightlife

### Security
- Row Level Security (RLS) enabled on all tables
- Users can only access their own data
- Policies enforce user_id matching for all operations

### Performance
- Indexes on foreign keys (trip_id, user_id)
- Indexes on frequently queried fields (dates, status, email)
- Automatic timestamp updates via triggers

## Database Schema Overview

### trips table
```sql
trip_id UUID PRIMARY KEY
user_id UUID REFERENCES users(user_id)
name VARCHAR(200) NOT NULL
description TEXT
destination VARCHAR(255) NOT NULL
start_date DATE NOT NULL
end_date DATE NOT NULL
total_budget NUMERIC(10,2) NOT NULL
traveler_count INTEGER
status trip_status DEFAULT 'draft'
preferences JSONB DEFAULT '{}'
itinerary_data JSONB DEFAULT '{}'
created_at TIMESTAMP WITH TIME ZONE
updated_at TIMESTAMP WITH TIME ZONE
```

**preferences JSONB structure:**
```json
{
  "travel_class": "economy",
  "accommodation_type": "hotel",
  "currency": "USD",
  "destination_details": {
    "city": "Paris",
    "country": "France",
    "country_code": "FR",
    "airport_code": "CDG",
    "latitude": 48.8566,
    "longitude": 2.3522
  }
}
```

**itinerary_data JSONB structure:**
Contains the complete `ItineraryOutput` from the TravelPlannerAgent with:
- Trip information (destination, dates, travelers, budget)
- Flight details (outbound/return flights)
- Accommodation details
- Day-by-day itinerary
- Budget breakdown
- Travel tips

## Verification

After running the SQL, verify the setup:

### 1. Check Tables Exist

In Supabase Dashboard:
1. Go to **Table Editor**
2. You should see:
   - `users`
   - `trips`
   - `flight_options`
   - `hotel_options`
   - `activity_options`
   - `workflow_states`

### 2. Check RLS Policies

In Supabase Dashboard:
1. Go to **Authentication** → **Policies**
2. Select each table
3. Verify policies exist for SELECT, INSERT, UPDATE, DELETE

### 3. Run Tests

```bash
cd /home/mihai/repos/travel-companion/packages/api
uv run pytest src/tests/test_api/test_trips.py -v
```

### 4. Test the API

Start the API server:
```bash
uv run uvicorn travel_companion.main:app --reload
```

Test trip creation:
```bash
# Get a token first (register/login)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#",
    "first_name": "Test",
    "last_name": "User"
  }'

# Create a trip (use the token from login response)
curl -X POST http://localhost:8000/api/v1/trips \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Paris Adventure",
    "description": "A week in Paris",
    "destination": {
      "city": "Paris",
      "country": "France",
      "country_code": "FR",
      "airport_code": "CDG"
    },
    "requirements": {
      "budget": 2000,
      "currency": "EUR",
      "start_date": "2024-06-01",
      "end_date": "2024-06-07",
      "travelers": 2,
      "travel_class": "economy"
    }
  }'
```

## Troubleshooting

### Error: "relation already exists"
This is normal if you're re-running the script. The SQL uses `IF NOT EXISTS` and `DROP POLICY IF EXISTS` to handle this gracefully.

### Error: "permission denied"
Make sure you're using your **service role key** (not anon key) if running SQL directly via API. For the SQL Editor in Supabase Dashboard, you're automatically authenticated.

### Error: "function update_updated_at_column does not exist"
Run the users table setup first (`database_setup.sql`) as it creates this shared function.

### RLS Preventing Access
Make sure:
1. You're authenticated with a valid JWT token
2. The token's `user_id` matches the data you're trying to access
3. RLS policies are correctly created

Debug RLS:
```sql
-- Temporarily disable RLS for testing (DO NOT USE IN PRODUCTION)
ALTER TABLE trips DISABLE ROW LEVEL SECURITY;

-- Re-enable after testing
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
```

## Environment Variables

Make sure your `.env` file has:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-key

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Next Steps

After setting up the database:

1. ✅ Test authentication endpoints (`/api/v1/auth/register`, `/api/v1/auth/login`)
2. ✅ Test trip CRUD endpoints (`/api/v1/trips`)
3. ✅ Test trip planning endpoint (`/api/v1/trips/plan`)
4. ✅ Review the API documentation at `http://localhost:8000/docs`

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL Data Types](https://www.postgresql.org/docs/current/datatype.html)
- [JSONB in PostgreSQL](https://www.postgresql.org/docs/current/datatype-json.html)

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review Supabase logs in the Dashboard → **Logs** section
3. Check API logs when running the development server
4. Verify your `.env` configuration

## Schema Updates

To modify the schema:

1. Create a new migration SQL file in `src/travel_companion/core/`
2. Update this README with the changes
3. Run the migration in your Supabase SQL Editor
4. Test thoroughly before deploying to production

**Important:** Always backup your database before running schema modifications!
