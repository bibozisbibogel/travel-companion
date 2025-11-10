"""Test script to verify Geoapify geocoding integration."""

import asyncio
import os

from travel_companion.services.geocoding_service import GeocodingService


async def main() -> None:
    """Test geocoding service with Geoapify API."""
    api_key = os.getenv("GEOAPIFY_API_KEY")

    if not api_key:
        print("❌ GEOAPIFY_API_KEY environment variable not set")
        print("Set it with: export GEOAPIFY_API_KEY=your-api-key")
        return

    print("Testing Geoapify Geocoding Service\n")
    print("=" * 50)

    service = GeocodingService(api_key=api_key)

    # Test locations
    test_locations = [
        "Eiffel Tower, Paris, France",
        "Colosseum, Rome, Italy",
        "Big Ben, London, UK",
        "Trevi Fountain, Rome, Italy",
    ]

    print("\n1. Testing single geocoding requests:")
    print("-" * 50)
    for location in test_locations[:2]:
        print(f"\n📍 Geocoding: {location}")
        result = await service.geocode_location(location)

        if result.status == "success":
            print(f"   ✅ Success!")
            print(f"   Coordinates: ({result.latitude}, {result.longitude})")
            print(f"   Formatted: {result.formatted_address}")
        else:
            print(f"   ❌ Failed: {result.error_message}")

    print("\n\n2. Testing batch geocoding:")
    print("-" * 50)
    print(f"\n📍 Batch geocoding {len(test_locations)} locations...")

    results = await service.geocode_locations_batch(test_locations)

    for location, result in zip(test_locations, results):
        if result.status == "success":
            print(f"   ✅ {location[:30]:30s} -> ({result.latitude}, {result.longitude})")
        else:
            print(f"   ❌ {location[:30]:30s} -> Failed")

    print("\n\n3. Testing cache:")
    print("-" * 50)
    print(f"\n📍 Re-geocoding first location (should use cache)...")

    result = await service.geocode_location(test_locations[0])
    if result.status == "success":
        print(f"   ✅ Cache hit! Coordinates: ({result.latitude}, {result.longitude})")
    else:
        print(f"   ❌ Failed: {result.error_message}")

    print("\n" + "=" * 50)
    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
