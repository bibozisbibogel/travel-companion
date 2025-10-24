import asyncio
import os
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

from travel_companion.agents.weather_agent import WeatherAgent
from travel_companion.models.external import (
    WeatherSearchRequest,
)


async def main():
    load_dotenv()
    api_key = os.getenv("OPENWEATHER_API_KEY")
    print(api_key)
    agent = WeatherAgent()
    request = WeatherSearchRequest(
        location="Paris, France",
        latitude=48.8566,  # Paris coordinates
        longitude=2.3522,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=5),
        include_alerts=True,
        include_historical=False,
    )
    response = await agent.process(request.model_dump())
    print(f"Weather search completed successfully: {response}")


if __name__ == "__main__":
    asyncio.run(main())
