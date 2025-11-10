"""Tests for flight search tools in Claude Agent SDK."""

from datetime import datetime, timedelta

import pytest


@pytest.mark.asyncio
async def test_flight_search_tool_basic():
    """Test basic flight search tool functionality."""
    from travel_companion.agents_sdk.tools.flight_tools import search_flights

    # Prepare test arguments
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    arguments = {
        "origin": "JFK",
        "destination": "LAX",
        "departure_date": tomorrow,
        "return_date": next_week,
        "passengers": 2,
        "travel_class": "economy",
        "max_results": 5,
        "currency": "USD",
    }

    # Execute tool - access the underlying function via handler attribute
    result = await search_flights.handler(arguments)

    # Verify result structure
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"

    # Parse result JSON
    import json

    result_data = json.loads(result["content"][0]["text"])

    # Verify response structure
    assert result_data["status"] == "success"
    assert "flights" in result_data
    assert "total_results" in result_data
    assert "search_time_ms" in result_data


@pytest.mark.asyncio
async def test_flight_search_tool_missing_fields():
    """Test flight search tool with missing required fields."""
    from travel_companion.agents_sdk.tools.flight_tools import search_flights

    # Missing destination
    arguments = {
        "origin": "JFK",
        "departure_date": "2025-06-01",
    }

    result = await search_flights.handler(arguments)

    # Should return error
    import json

    result_data = json.loads(result["content"][0]["text"])
    assert result_data["status"] == "error"
    assert "error" in result_data


@pytest.mark.asyncio
async def test_flight_search_tool_invalid_date():
    """Test flight search tool with invalid date format."""
    from travel_companion.agents_sdk.tools.flight_tools import search_flights

    arguments = {
        "origin": "JFK",
        "destination": "LAX",
        "departure_date": "invalid-date",
    }

    result = await search_flights.handler(arguments)

    # Should return error about date format
    import json

    result_data = json.loads(result["content"][0]["text"])
    assert result_data["status"] == "error"
    assert "Invalid date format" in result_data["error"]


@pytest.mark.asyncio
async def test_flight_search_tool_with_defaults():
    """Test flight search tool using default values."""
    from travel_companion.agents_sdk.tools.flight_tools import search_flights

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Minimal arguments (only required fields)
    arguments = {
        "origin": "SFO",
        "destination": "SEA",
        "departure_date": tomorrow,
    }

    result = await search_flights.handler(arguments)

    # Should succeed with defaults
    import json

    result_data = json.loads(result["content"][0]["text"])
    assert result_data["status"] == "success"
    assert "flights" in result_data


@pytest.mark.asyncio
async def test_flight_search_tool_city_name_normalization():
    """Test that city names are properly converted to airport codes."""
    from travel_companion.agents_sdk.tools.flight_tools import search_flights

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Use city names instead of airport codes
    arguments = {
        "origin": "New York",
        "destination": "Bucharest",  # Should convert to OTP
        "departure_date": tomorrow,
        "passengers": 1,
    }

    result = await search_flights.handler(arguments)

    # Should succeed with city name normalization (without validation errors)
    import json

    result_data = json.loads(result["content"][0]["text"])
    assert result_data["status"] == "success"
    assert "flights" in result_data
    # Note: Mock data may return different destinations, but the important part
    # is that the request didn't fail with a validation error about "BUCHAREST"
    # being too long for the 4-character airport code field


def test_normalize_airport_code():
    """Test the normalize_airport_code function."""
    from travel_companion.agents_sdk.tools.flight_tools import normalize_airport_code

    # Test city name conversion
    assert normalize_airport_code("bucharest") == "OTP"
    assert normalize_airport_code("Bucharest") == "OTP"
    assert normalize_airport_code("BUCHAREST") == "OTP"
    assert normalize_airport_code("new york") == "JFK"
    assert normalize_airport_code("paris") == "CDG"
    assert normalize_airport_code("prague") == "PRG"
    assert normalize_airport_code("warsaw") == "WAW"

    # Test airport code passthrough
    assert normalize_airport_code("JFK") == "JFK"
    assert normalize_airport_code("otp") == "OTP"
    assert normalize_airport_code("CDG") == "CDG"

    # Test unknown city (should return uppercased original)
    assert normalize_airport_code("UnknownCity") == "UNKNOWNCITY"
