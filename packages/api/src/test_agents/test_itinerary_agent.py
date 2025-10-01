from datetime import date
from decimal import Decimal
import os
import asyncio
from dotenv import load_dotenv
from travel_companion.agents.itinerary_agent import ItineraryAgent
from travel_companion.models.trip import (
    AccommodationType,
    TravelClass,
    TripDestination,
    TripPlanRequest,
    TripRequirements,
)


def sample_trip_request() -> TripPlanRequest:
    """Create a sample trip request for testing."""
    destination = TripDestination(
        city="Paris",
        country="France",
        country_code="FR",
        airport_code="CDG",
        latitude=48.8566,
        longitude=2.3522,
    )

    requirements = TripRequirements(
        budget=Decimal("2000.00"),
        currency="USD",
        start_date=date(2024, 6, 15),
        end_date=date(2024, 6, 18),
        travelers=2,
        travel_class=TravelClass.ECONOMY,
        accommodation_type=AccommodationType.HOTEL,
    )

    return TripPlanRequest(
        destination=destination,
        requirements=requirements,
        preferences={
            "cuisine": ["french", "local"],
            "activities": ["culture", "sightseeing"],
        },
    )


async def main():
    load_dotenv()
    agent = ItineraryAgent()

    trip = sample_trip_request()
    response = await agent.process(trip.model_dump())
    print(response)


if __name__ == "__main__":
    asyncio.run(main())


"""
- flight agent call fails and fallsback on mock data
- weather agent also fails, even though test_weather_agent.py successfully calls openweather api and returns valid data
- hotel, activity and food agent are not called at all
"""
