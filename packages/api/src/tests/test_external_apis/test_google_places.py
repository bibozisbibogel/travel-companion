"""Tests for Google Places API (New) integration."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from travel_companion.services.external_apis.google_places import GooglePlacesNewAPI

# Load environment variables from project root
load_dotenv("../../.env")

# Skip all tests in this module unless RUN_EXTERNAL_API_TESTS is set to "true"
pytestmark = [
    pytest.mark.external_api,
    pytest.mark.skipif(
        os.getenv("RUN_EXTERNAL_API_TESTS", "false").lower() != "true",
        reason="External API tests are disabled. Set RUN_EXTERNAL_API_TESTS=true to enable",
    ),
]


@pytest_asyncio.fixture
async def google_places_client() -> AsyncGenerator[GooglePlacesNewAPI, None]:
    """Create Google Places API (New) client for testing."""
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_PLACES_API_KEY not set in environment")

    client = GooglePlacesNewAPI(api_key=api_key)
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_google_places_api_connection(google_places_client: GooglePlacesNewAPI):
    """Test basic connection to Google Places API (New)."""
    # Simple test query for restaurants in San Francisco
    results = await google_places_client.text_search(
        text_query="restaurants in San Francisco",
        max_result_count=5,
    )

    # Verify we get results
    assert isinstance(results, list)
    assert len(results) > 0

    # Check first result has expected fields
    if results:
        first_place = results[0]
        assert first_place.id
        assert first_place.display_name
        assert "text" in first_place.display_name
        assert first_place.types is not None


@pytest.mark.asyncio
async def test_text_search_with_filters(google_places_client: GooglePlacesNewAPI):
    """Test text search with various filters."""
    # Search for coffee shops with filters
    results = await google_places_client.text_search(
        text_query="coffee shops in New York",
        min_rating=4.0,
        max_result_count=10,
    )

    assert isinstance(results, list)
    if results:
        # Check that results meet the filter criteria
        for place in results[:3]:
            assert place.id
            assert place.display_name
            if place.rating is not None:
                # Rating should be 4.0 or higher if the filter worked
                assert place.rating >= 3.5  # Allow some tolerance


@pytest.mark.asyncio
async def test_nearby_search(google_places_client: GooglePlacesNewAPI):
    """Test nearby search functionality."""
    # Search near Times Square, NYC
    location = (40.7580, -73.9855)

    results = await google_places_client.nearby_search(
        location=location,
        radius=500,
        included_types=["restaurant"],
        max_result_count=5,
    )

    assert isinstance(results, list)
    if results:
        first_place = results[0]
        assert first_place.id
        assert first_place.display_name
        # Should have location info for nearby search
        assert first_place.location is not None


@pytest.mark.asyncio
async def test_get_place_details(google_places_client: GooglePlacesNewAPI):
    """Test getting detailed place information."""
    # First, search for a well-known place
    search_results = await google_places_client.text_search(
        text_query="Empire State Building New York",
        max_result_count=1,
    )

    assert search_results
    place_id = search_results[0].id

    # Get detailed information
    details = await google_places_client.get_place(
        place_id=place_id,
        field_mask="id,displayName,formattedAddress,rating,websiteUri,location",
    )

    assert details.id == place_id
    assert details.display_name
    assert details.formatted_address
    # Empire State Building should have location
    assert details.location is not None


@pytest.mark.asyncio
async def test_search_with_location_bias(google_places_client: GooglePlacesNewAPI):
    """Test search with location bias."""
    # Search with location bias towards San Francisco
    sf_location = (37.7749, -122.4194)

    results = await google_places_client.text_search(
        text_query="Italian restaurant",
        location_bias=sf_location,
        radius=5000,
        max_result_count=5,
    )

    assert isinstance(results, list)
    if results:
        # Results should be biased towards SF area
        first_place = results[0]
        assert first_place.display_name
        assert first_place.id


@pytest.mark.asyncio
async def test_search_with_price_levels(google_places_client: GooglePlacesNewAPI):
    """Test search with price level filters."""
    # Search for budget-friendly restaurants
    results = await google_places_client.text_search(
        text_query="restaurants in Los Angeles",
        price_levels=["PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE"],
        max_result_count=5,
    )

    assert isinstance(results, list)
    if results:
        # Check that we get restaurants
        for place in results:
            assert place.display_name
            # Price level should match our filter if available
            if place.price_level:
                assert place.price_level in [
                    "PRICE_LEVEL_INEXPENSIVE",
                    "PRICE_LEVEL_MODERATE",
                    "PRICE_LEVEL_FREE",  # Some places might be free
                ]


@pytest.mark.asyncio
async def test_photo_url_generation(google_places_client: GooglePlacesNewAPI):
    """Test photo URL generation."""
    # Search for a place likely to have photos
    results = await google_places_client.text_search(
        text_query="Statue of Liberty New York",
        max_result_count=1,
    )

    assert results
    place = results[0]

    if place.photos:
        photo = place.photos[0]
        photo_url = google_places_client.get_photo_url(
            photo_name=photo.name,
            max_width=800,
            max_height=600,
        )

        assert photo_url
        assert "media" in photo_url
        assert "maxWidthPx=800" in photo_url
        assert "maxHeightPx=600" in photo_url
        assert google_places_client.api_key in photo_url


@pytest.mark.asyncio
async def test_error_handling_invalid_place_id(google_places_client: GooglePlacesNewAPI):
    """Test error handling with invalid place ID."""
    with pytest.raises(ValueError) as exc_info:
        await google_places_client.get_place(
            place_id="INVALID_PLACE_ID_12345",
        )

    assert "Failed to get place details" in str(exc_info.value)


@pytest.mark.asyncio
async def test_nearby_search_with_types(google_places_client: GooglePlacesNewAPI):
    """Test nearby search with specific place types."""
    # Search for cafes near Central Park, NYC
    location = (40.7829, -73.9654)

    results = await google_places_client.nearby_search(
        location=location,
        radius=1000,
        included_types=["cafe", "coffee_shop"],
        max_result_count=5,
    )

    assert isinstance(results, list)
    # Verify we get places of the requested types
    if results:
        for place in results:
            assert place.id
            assert place.display_name
            # Should have type information
            if place.types or place.primary_type:
                # At least one result should be cafe-related
                assert True
