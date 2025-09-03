"""Tests for hotel agent ranking and comparison functionality."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from travel_companion.agents.hotel_agent import HotelAgent
from travel_companion.models.external import HotelLocation, HotelOption


@pytest.fixture
def hotel_agent():
    """Create a HotelAgent instance for testing."""
    return HotelAgent()


@pytest.fixture
def sample_hotels():
    """Create sample hotels for testing ranking functionality."""
    return [
        HotelOption(
            external_id="hotel1",
            name="Budget Hotel",
            location=HotelLocation(
                latitude=40.7128, longitude=-74.0060, address="123 Budget St, New York, NY"
            ),
            price_per_night=Decimal("80.00"),
            currency="USD",
            rating=3.5,
            amenities=["WiFi", "Parking"],
            photos=["photo1.jpg"],
            booking_url="https://booking.com/hotel1",
            created_at=datetime.now(UTC),
        ),
        HotelOption(
            external_id="hotel2",
            name="Luxury Resort",
            location=HotelLocation(
                latitude=40.7589, longitude=-73.9851, address="456 Luxury Ave, New York, NY"
            ),
            price_per_night=Decimal("400.00"),
            currency="USD",
            rating=4.8,
            amenities=["WiFi", "Pool", "Gym", "Spa", "Concierge"],
            photos=["photo2.jpg", "photo3.jpg"],
            booking_url="https://booking.com/hotel2",
            created_at=datetime.now(UTC),
        ),
        HotelOption(
            external_id="hotel3",
            name="Mid-range Hotel",
            location=HotelLocation(
                latitude=40.7505, longitude=-73.9934, address="789 Mid St, New York, NY"
            ),
            price_per_night=Decimal("150.00"),
            currency="USD",
            rating=4.2,
            amenities=["WiFi", "Parking", "Breakfast"],
            photos=["photo4.jpg"],
            booking_url="https://booking.com/hotel3",
            created_at=datetime.now(UTC),
        ),
        HotelOption(
            external_id="hotel4",
            name="No Rating Hotel",
            location=HotelLocation(
                latitude=40.7400, longitude=-74.0000, address="999 Unknown St, New York, NY"
            ),
            price_per_night=Decimal("120.00"),
            currency="USD",
            rating=None,
            amenities=["WiFi"],
            photos=[],
            booking_url="https://booking.com/hotel4",
            created_at=datetime.now(UTC),
        ),
    ]


class TestHotelDistanceCalculation:
    """Test suite for distance calculations."""

    def test_calculate_distance_km_same_point(self, hotel_agent):
        """Test distance calculation for same point."""
        distance = hotel_agent._calculate_distance_km(40.7128, -74.0060, 40.7128, -74.0060)
        assert distance == 0.0

    def test_calculate_distance_km_known_distance(self, hotel_agent):
        """Test distance calculation for known coordinates."""
        # NYC to LA approximate coordinates
        nyc_lat, nyc_lon = 40.7128, -74.0060
        la_lat, la_lon = 34.0522, -118.2437

        distance = hotel_agent._calculate_distance_km(nyc_lat, nyc_lon, la_lat, la_lon)

        # Should be approximately 3944 km (can vary slightly due to Earth's shape)
        assert 3900 <= distance <= 4000

    def test_calculate_distance_km_close_points(self, hotel_agent):
        """Test distance calculation for nearby points in NYC."""
        # Two points in Manhattan
        point1_lat, point1_lon = 40.7128, -74.0060  # Near Financial District
        point2_lat, point2_lon = 40.7589, -73.9851  # Near Times Square

        distance = hotel_agent._calculate_distance_km(
            point1_lat, point1_lon, point2_lat, point2_lon
        )

        # Should be around 6-8 km
        assert 5 <= distance <= 10


class TestLocationCoordinateParsing:
    """Test suite for location coordinate parsing."""

    def test_parse_location_coordinates_valid(self, hotel_agent):
        """Test parsing valid coordinate strings."""
        # Test basic format
        result = hotel_agent._parse_location_coordinates("40.7128,-74.0060")
        assert result == (40.7128, -74.0060)

        # Test with spaces
        result = hotel_agent._parse_location_coordinates("40.7128, -74.0060")
        assert result == (40.7128, -74.0060)

    def test_parse_location_coordinates_invalid(self, hotel_agent):
        """Test parsing invalid coordinate strings."""
        # Invalid format
        assert hotel_agent._parse_location_coordinates("New York, NY") is None
        assert hotel_agent._parse_location_coordinates("invalid") is None
        assert hotel_agent._parse_location_coordinates("") is None

        # Out of range coordinates
        assert hotel_agent._parse_location_coordinates("91.0,0.0") is None  # Lat > 90
        assert hotel_agent._parse_location_coordinates("0.0,181.0") is None  # Lon > 180

    def test_parse_location_coordinates_edge_cases(self, hotel_agent):
        """Test parsing edge case coordinates."""
        # Valid edge cases
        assert hotel_agent._parse_location_coordinates("90.0,180.0") == (90.0, 180.0)
        assert hotel_agent._parse_location_coordinates("-90.0,-180.0") == (-90.0, -180.0)
        assert hotel_agent._parse_location_coordinates("0.0,0.0") == (0.0, 0.0)


class TestHotelRankingScore:
    """Test suite for hotel ranking score calculations."""

    def test_calculate_ranking_score_default_preferences(self, hotel_agent, sample_hotels):
        """Test ranking score calculation with default preferences."""
        hotel = sample_hotels[0]  # Budget Hotel

        score, reasons = hotel_agent._calculate_hotel_ranking_score(hotel)

        assert 0 <= score <= 100
        assert len(reasons) == 4  # Price, Rating, Location, Amenities
        assert "Price $80.00/night" in reasons
        assert "Rating 3.5/5" in reasons
        assert "2 amenities" in reasons

    def test_calculate_ranking_score_with_location(self, hotel_agent, sample_hotels):
        """Test ranking score calculation with location proximity."""
        hotel = sample_hotels[0]  # Budget Hotel
        search_center = (40.7128, -74.0060)  # Same location as hotel

        score, reasons = hotel_agent._calculate_hotel_ranking_score(hotel, search_center)

        assert 0 <= score <= 100
        assert any("Distance" in reason for reason in reasons)

    def test_calculate_ranking_score_custom_preferences(self, hotel_agent, sample_hotels):
        """Test ranking score calculation with custom preferences."""
        hotel = sample_hotels[1]  # Luxury Resort
        preferences = {
            "price_weight": 0.1,
            "rating_weight": 0.7,  # Heavily weight rating
            "location_weight": 0.1,
            "amenities_weight": 0.1,
        }

        score, reasons = hotel_agent._calculate_hotel_ranking_score(hotel, preferences=preferences)

        # High-rated hotel should score well with rating-heavy preferences
        assert score > 70  # Should be a good score due to 4.8 rating

    def test_calculate_ranking_score_missing_data(self, hotel_agent, sample_hotels):
        """Test ranking score calculation with missing data."""
        hotel = sample_hotels[3]  # No Rating Hotel

        score, reasons = hotel_agent._calculate_hotel_ranking_score(hotel)

        assert 0 <= score <= 100
        assert "Rating not available" in reasons


class TestHotelRanking:
    """Test suite for hotel ranking functionality."""

    def test_rank_hotels_basic(self, hotel_agent, sample_hotels):
        """Test basic hotel ranking without filters."""
        results = hotel_agent.rank_hotels(sample_hotels)

        assert len(results) == 4
        # Results should be sorted by score (highest first)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

        # Check that all required fields are populated
        for result in results:
            assert result.hotel is not None
            assert 0 <= result.score <= 100
            assert result.price_rank >= 1
            assert result.location_rank >= 1
            assert result.rating_rank >= 1
            assert 0 <= result.value_score <= 1
            assert len(result.reasons) > 0

    def test_rank_hotels_with_budget_filter(self, hotel_agent, sample_hotels):
        """Test hotel ranking with budget filter."""
        budget_filter = Decimal("200.00")
        results = hotel_agent.rank_hotels(sample_hotels, budget_filter=budget_filter)

        # Should exclude luxury resort ($400/night)
        assert len(results) == 3
        for result in results:
            assert result.hotel.price_per_night <= budget_filter

    def test_rank_hotels_with_amenities_filter(self, hotel_agent, sample_hotels):
        """Test hotel ranking with required amenities filter."""
        required_amenities = ["WiFi", "Pool"]
        results = hotel_agent.rank_hotels(sample_hotels, required_amenities=required_amenities)

        # Only luxury resort has both WiFi and Pool
        assert len(results) == 1
        assert results[0].hotel.external_id == "hotel2"

    def test_rank_hotels_with_location_filter(self, hotel_agent, sample_hotels):
        """Test hotel ranking with location distance filter."""
        search_location = "40.7128,-74.0060"  # Near Budget Hotel
        max_distance_km = 2.0

        results = hotel_agent.rank_hotels(
            sample_hotels, search_location=search_location, max_distance_km=max_distance_km
        )

        # Should only include hotels within 2km
        assert len(results) >= 1
        for result in results:
            distance = hotel_agent._calculate_distance_km(
                40.7128, -74.0060, result.hotel.location.latitude, result.hotel.location.longitude
            )
            assert distance <= max_distance_km

    def test_rank_hotels_empty_list(self, hotel_agent):
        """Test ranking with empty hotel list."""
        results = hotel_agent.rank_hotels([])
        assert results == []

    def test_rank_hotels_price_ranking(self, hotel_agent, sample_hotels):
        """Test that price rankings are calculated correctly."""
        results = hotel_agent.rank_hotels(sample_hotels)

        # Find results by external_id and check price rankings
        budget_hotel = next(r for r in results if r.hotel.external_id == "hotel1")
        mid_range_hotel = next(r for r in results if r.hotel.external_id == "hotel3")
        no_rating_hotel = next(r for r in results if r.hotel.external_id == "hotel4")
        luxury_hotel = next(r for r in results if r.hotel.external_id == "hotel2")

        # Price ranking should be: Budget(1), No-rating(2), Mid-range(3), Luxury(4)
        assert budget_hotel.price_rank == 1  # $80
        assert no_rating_hotel.price_rank == 2  # $120
        assert mid_range_hotel.price_rank == 3  # $150
        assert luxury_hotel.price_rank == 4  # $400

    def test_rank_hotels_rating_ranking(self, hotel_agent, sample_hotels):
        """Test that rating rankings are calculated correctly."""
        results = hotel_agent.rank_hotels(sample_hotels)

        # Find results and check rating rankings
        luxury_hotel = next(r for r in results if r.hotel.external_id == "hotel2")  # 4.8
        mid_range_hotel = next(r for r in results if r.hotel.external_id == "hotel3")  # 4.2
        budget_hotel = next(r for r in results if r.hotel.external_id == "hotel1")  # 3.5
        no_rating_hotel = next(r for r in results if r.hotel.external_id == "hotel4")  # None

        # Rating ranking should be: Luxury(1), Mid-range(2), Budget(3), No-rating(4)
        assert luxury_hotel.rating_rank == 1
        assert mid_range_hotel.rating_rank == 2
        assert budget_hotel.rating_rank == 3
        assert no_rating_hotel.rating_rank == 4


class TestHotelFiltering:
    """Test suite for hotel filtering functionality."""

    def test_filter_hotels_by_budget_max(self, hotel_agent, sample_hotels):
        """Test filtering hotels by maximum budget."""
        budget_max = Decimal("150.00")
        filtered = hotel_agent.filter_hotels_by_criteria(sample_hotels, budget_max=budget_max)

        assert len(filtered) == 3  # Excludes luxury resort
        for hotel in filtered:
            assert hotel.price_per_night <= budget_max

    def test_filter_hotels_by_budget_min(self, hotel_agent, sample_hotels):
        """Test filtering hotels by minimum budget."""
        budget_min = Decimal("100.00")
        filtered = hotel_agent.filter_hotels_by_criteria(sample_hotels, budget_min=budget_min)

        assert len(filtered) == 3  # Excludes budget hotel ($80)
        for hotel in filtered:
            assert hotel.price_per_night >= budget_min

    def test_filter_hotels_by_rating(self, hotel_agent, sample_hotels):
        """Test filtering hotels by minimum rating."""
        min_rating = 4.0
        filtered = hotel_agent.filter_hotels_by_criteria(sample_hotels, min_rating=min_rating)

        assert len(filtered) == 2  # Luxury (4.8) and Mid-range (4.2)
        for hotel in filtered:
            assert hotel.rating and hotel.rating >= min_rating

    def test_filter_hotels_by_amenities(self, hotel_agent, sample_hotels):
        """Test filtering hotels by required amenities."""
        required_amenities = ["WiFi", "Parking"]
        filtered = hotel_agent.filter_hotels_by_criteria(
            sample_hotels, required_amenities=required_amenities
        )

        # Budget hotel and Mid-range hotel have both WiFi and Parking
        assert len(filtered) == 2
        for hotel in filtered:
            hotel_amenities_lower = [amenity.lower() for amenity in hotel.amenities]
            assert all(req.lower() in hotel_amenities_lower for req in required_amenities)

    def test_filter_hotels_by_distance(self, hotel_agent, sample_hotels):
        """Test filtering hotels by distance from search location."""
        search_location = "40.7128,-74.0060"
        max_distance_km = 5.0

        filtered = hotel_agent.filter_hotels_by_criteria(
            sample_hotels, max_distance_km=max_distance_km, search_location=search_location
        )

        # Should filter based on distance
        assert len(filtered) >= 1

        search_center = hotel_agent._parse_location_coordinates(search_location)
        for hotel in filtered:
            distance = hotel_agent._calculate_distance_km(
                search_center[0],
                search_center[1],
                hotel.location.latitude,
                hotel.location.longitude,
            )
            assert distance <= max_distance_km

    def test_filter_hotels_combined_criteria(self, hotel_agent, sample_hotels):
        """Test filtering hotels with multiple combined criteria."""
        filtered = hotel_agent.filter_hotels_by_criteria(
            sample_hotels, budget_max=Decimal("200.00"), min_rating=3.0, required_amenities=["WiFi"]
        )

        # Should exclude luxury resort (too expensive) and no-rating hotel (no rating)
        # Should include budget hotel and mid-range hotel
        assert len(filtered) == 2

        for hotel in filtered:
            assert hotel.price_per_night <= Decimal("200.00")
            assert hotel.rating and hotel.rating >= 3.0
            assert "wifi" in [amenity.lower() for amenity in hotel.amenities]

    def test_filter_hotels_empty_list(self, hotel_agent):
        """Test filtering with empty hotel list."""
        filtered = hotel_agent.filter_hotels_by_criteria([])
        assert filtered == []

    def test_filter_hotels_no_matches(self, hotel_agent, sample_hotels):
        """Test filtering that returns no matches."""
        filtered = hotel_agent.filter_hotels_by_criteria(
            sample_hotels,
            budget_max=Decimal("50.00"),  # Lower than any hotel price
        )
        assert filtered == []


class TestHotelPagination:
    """Test suite for hotel result pagination."""

    def test_paginate_results_basic(self, hotel_agent, sample_hotels):
        """Test basic result pagination."""
        results, metadata = hotel_agent.paginate_results(sample_hotels, page=1, per_page=2)

        assert len(results) == 2
        assert metadata["page"] == 1
        assert metadata["per_page"] == 2
        assert metadata["total"] == 4
        assert metadata["pages"] == 2
        assert metadata["has_next"] is True
        assert metadata["has_prev"] is False

    def test_paginate_results_second_page(self, hotel_agent, sample_hotels):
        """Test second page pagination."""
        results, metadata = hotel_agent.paginate_results(sample_hotels, page=2, per_page=2)

        assert len(results) == 2
        assert metadata["page"] == 2
        assert metadata["has_next"] is False
        assert metadata["has_prev"] is True

    def test_paginate_results_last_partial_page(self, hotel_agent, sample_hotels):
        """Test pagination with partial last page."""
        results, metadata = hotel_agent.paginate_results(sample_hotels, page=2, per_page=3)

        assert len(results) == 1  # Only 1 result on second page
        assert metadata["page"] == 2
        assert metadata["pages"] == 2

    def test_paginate_results_invalid_page(self, hotel_agent, sample_hotels):
        """Test pagination with invalid page numbers."""
        # Page too high - should return last page
        results, metadata = hotel_agent.paginate_results(sample_hotels, page=10, per_page=2)
        assert metadata["page"] == 2  # Last valid page

        # Page too low - should return first page
        results, metadata = hotel_agent.paginate_results(sample_hotels, page=0, per_page=2)
        assert metadata["page"] == 1

    def test_paginate_results_empty_list(self, hotel_agent):
        """Test pagination with empty results."""
        results, metadata = hotel_agent.paginate_results([], page=1, per_page=10)

        assert results == []
        assert metadata["total"] == 0
        assert metadata["pages"] == 0
        assert metadata["has_next"] is False
        assert metadata["has_prev"] is False

    def test_paginate_comparison_results(self, hotel_agent, sample_hotels):
        """Test pagination with HotelComparisonResult objects."""
        comparison_results = hotel_agent.rank_hotels(sample_hotels)

        results, metadata = hotel_agent.paginate_results(comparison_results, page=1, per_page=2)

        assert len(results) == 2
        assert metadata["total"] == 4
        # Check that paginated results are still HotelComparisonResult objects
        for result in results:
            assert hasattr(result, "score")
            assert hasattr(result, "hotel")


class TestHotelRankingIntegration:
    """Integration tests for complete hotel ranking workflow."""

    def test_complete_ranking_workflow(self, hotel_agent, sample_hotels):
        """Test complete ranking workflow with all features."""
        # Step 1: Filter hotels
        filtered_hotels = hotel_agent.filter_hotels_by_criteria(
            sample_hotels, budget_max=Decimal("300.00"), min_rating=3.0
        )

        # Step 2: Rank filtered hotels
        ranked_results = hotel_agent.rank_hotels(
            filtered_hotels, search_location="40.7128,-74.0060"
        )

        # Step 3: Paginate results
        paginated_results, pagination_metadata = hotel_agent.paginate_results(
            ranked_results, page=1, per_page=2
        )

        # Verify complete workflow
        assert len(paginated_results) == 2
        assert pagination_metadata["total"] == 2  # Should match filtered results

        # Results should be properly ranked
        if len(paginated_results) > 1:
            assert paginated_results[0].score >= paginated_results[1].score

    def test_ranking_consistency(self, hotel_agent, sample_hotels):
        """Test that ranking results are consistent across multiple calls."""
        results1 = hotel_agent.rank_hotels(sample_hotels)
        results2 = hotel_agent.rank_hotels(sample_hotels)

        # Results should be identical
        assert len(results1) == len(results2)
        for i in range(len(results1)):
            assert results1[i].hotel.external_id == results2[i].hotel.external_id
            assert results1[i].score == results2[i].score

    def test_ranking_with_location_preferences(self, hotel_agent, sample_hotels):
        """Test ranking with heavy location preference weighting."""
        search_location = "40.7128,-74.0060"  # Near Budget Hotel
        location_heavy_preferences = {
            "price_weight": 0.1,
            "rating_weight": 0.1,
            "location_weight": 0.7,  # Heavy location weighting
            "amenities_weight": 0.1,
        }

        results = hotel_agent.rank_hotels(
            sample_hotels, search_location=search_location, preferences=location_heavy_preferences
        )

        # Hotels closer to search location should rank higher
        budget_hotel = next(r for r in results if r.hotel.external_id == "hotel1")

        # Budget hotel is at the exact search location, so should have very high location score
        assert budget_hotel.location_rank == 1
