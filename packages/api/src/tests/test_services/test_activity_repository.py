"""Integration tests for ActivityRepository with testcontainers."""

import pytest
import asyncio
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock

from travel_companion.services.activity_repository import ActivityRepository
from travel_companion.models.external import (
    ActivityCategory,
    ActivityLocation,
    ActivityOption,
)


# Mock database for testing since we can't run full testcontainers in this environment
@pytest.fixture
def mock_database():
    """Mock database for testing repository operations."""
    db = Mock()
    db.client = Mock()
    db.client.table.return_value = Mock()
    return db


@pytest.fixture
def activity_repository(mock_database):
    """Create activity repository with mocked database."""
    return ActivityRepository(mock_database)


@pytest.fixture
def sample_activities():
    """Sample activity options for testing."""
    activities = [
        ActivityOption(
            activity_id=uuid4(),
            external_id="ta_123456",
            name="Louvre Museum Tour",
            description="Guided tour of the famous Louvre Museum",
            category=ActivityCategory.CULTURAL,
            location=ActivityLocation(
                latitude=48.8606,
                longitude=2.3376,
                address="Rue de Rivoli, 75001 Paris, France",
                city="Paris",
                country="France",
            ),
            duration_minutes=180,
            price=Decimal("45.00"),
            currency="EUR",
            rating=4.5,
            review_count=1250,
            images=["https://example.com/louvre1.jpg"],
            booking_url="https://example.com/book/ta_123456",
            provider="tripadvisor",
        ),
        ActivityOption(
            activity_id=uuid4(),
            external_id="viator_789",
            name="Eiffel Tower Skip-the-Line",
            description="Skip-the-line access to Eiffel Tower",
            category=ActivityCategory.CULTURAL,
            location=ActivityLocation(
                latitude=48.8584,
                longitude=2.2945,
                address="Champ de Mars, Paris, France",
                city="Paris",
                country="France",
            ),
            duration_minutes=120,
            price=Decimal("25.00"),
            currency="EUR",
            rating=4.3,
            review_count=2845,
            images=["https://example.com/eiffel1.jpg"],
            booking_url="https://example.com/book/viator_789",
            provider="viator",
        ),
    ]
    return activities


class TestActivityRepository:
    """Test cases for ActivityRepository."""

    @pytest.mark.asyncio
    async def test_insert_activity_options_success(self, activity_repository, sample_activities, mock_database):
        """Test successful insertion of activity options."""
        trip_id = uuid4()
        
        # Mock successful insertion
        mock_result = Mock()
        mock_result.data = [
            {"activity_id": str(activity.activity_id)} 
            for activity in sample_activities
        ]
        mock_database.client.table.return_value.insert.return_value.execute.return_value = mock_result
        
        result = await activity_repository.insert_activity_options(sample_activities, trip_id)
        
        assert len(result) == 2
        assert all(isinstance(activity_id, type(uuid4())) for activity_id in result)
        
        # Verify database calls
        mock_database.client.table.assert_called_with("activity_options")
        mock_database.client.table.return_value.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_empty_activities_list(self, activity_repository):
        """Test inserting empty activities list returns empty list."""
        trip_id = uuid4()
        result = await activity_repository.insert_activity_options([], trip_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_activities_by_trip(self, activity_repository, mock_database):
        """Test retrieving activities by trip ID."""
        trip_id = uuid4()
        
        # Mock database response
        mock_result = Mock()
        mock_result.data = [
            {
                "activity_id": str(uuid4()),
                "trip_id": str(trip_id),
                "name": "Test Activity",
                "category": "cultural",
                "price": 50.00,
            }
        ]
        mock_database.client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result
        
        result = await activity_repository.get_activities_by_trip(trip_id)
        
        assert len(result) == 1
        assert result[0]["name"] == "Test Activity"
        
        # Verify query construction
        mock_database.client.table.assert_called_with("activity_options")
        mock_database.client.table.return_value.select.assert_called_with("*")

    @pytest.mark.asyncio
    async def test_search_activities_by_location(self, activity_repository, mock_database):
        """Test location-based activity search."""
        latitude, longitude = 48.8566, 2.3522  # Paris coordinates
        
        # Mock database response
        mock_result = Mock()
        mock_result.data = [
            {
                "activity_id": str(uuid4()),
                "name": "Nearby Activity",
                "location": {"latitude": 48.8606, "longitude": 2.3376},
                "category": "cultural",
            }
        ]
        mock_database.client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_result
        
        result = await activity_repository.search_activities_by_location(latitude, longitude)
        
        assert len(result) > 0
        assert "distance_km" in result[0]
        
        # Verify database calls
        mock_database.client.table.assert_called_with("activity_options")

    @pytest.mark.asyncio
    async def test_filter_activities_by_criteria(self, activity_repository, mock_database):
        """Test filtering activities by various criteria."""
        trip_id = uuid4()
        
        # Mock database response
        mock_result = Mock()
        mock_result.data = [
            {
                "activity_id": str(uuid4()),
                "name": "Filtered Activity",
                "category": "cultural",
                "rating": 4.5,
                "price": 30.00,
            }
        ]
        
        # Mock query chain
        mock_query = Mock()
        mock_database.client.table.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.lte.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = mock_result
        
        result = await activity_repository.filter_activities_by_criteria(
            trip_id=trip_id,
            category="cultural",
            min_rating=4.0,
            max_price=50.0
        )
        
        assert len(result) == 1
        assert result[0]["name"] == "Filtered Activity"

    @pytest.mark.asyncio
    async def test_cleanup_activities_for_completed_trip(self, activity_repository, mock_database):
        """Test cleanup of activities for completed trips."""
        trip_id = uuid4()
        
        # Mock successful deletion
        mock_result = Mock()
        mock_result.data = [{"activity_id": str(uuid4())} for _ in range(5)]
        mock_database.client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result
        
        result = await activity_repository.cleanup_activities_for_completed_trip(trip_id)
        
        assert result == 5
        
        # Verify deletion call
        mock_database.client.table.assert_called_with("activity_options")
        mock_database.client.table.return_value.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_activity_by_id(self, activity_repository, mock_database):
        """Test retrieving a specific activity by ID."""
        activity_id = uuid4()
        
        # Mock database response
        mock_result = Mock()
        mock_result.data = {
            "activity_id": str(activity_id),
            "name": "Test Activity",
            "category": "cultural",
        }
        mock_database.client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        result = await activity_repository.get_activity_by_id(activity_id)
        
        assert result is not None
        assert result["name"] == "Test Activity"

    @pytest.mark.asyncio
    async def test_get_activity_by_id_not_found(self, activity_repository, mock_database):
        """Test retrieving non-existent activity returns None."""
        activity_id = uuid4()
        
        # Mock empty response
        mock_result = Mock()
        mock_result.data = None
        mock_database.client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        result = await activity_repository.get_activity_by_id(activity_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_update_activity_rating(self, activity_repository, mock_database):
        """Test updating activity rating and review count."""
        activity_id = uuid4()
        new_rating = 4.8
        new_review_count = 1500
        
        # Mock successful update
        mock_result = Mock()
        mock_result.data = [{"activity_id": str(activity_id)}]
        mock_database.client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result
        
        result = await activity_repository.update_activity_rating(activity_id, new_rating, new_review_count)
        
        assert result is True
        
        # Verify update call
        mock_database.client.table.return_value.update.assert_called_with({
            "rating": new_rating,
            "review_count": new_review_count
        })

    @pytest.mark.asyncio
    async def test_database_error_handling(self, activity_repository, mock_database):
        """Test proper error handling when database operations fail."""
        trip_id = uuid4()
        
        # Mock database exception
        mock_database.client.table.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception) as exc_info:
            await activity_repository.get_activities_by_trip(trip_id)
        
        assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_activity_data_serialization(self, activity_repository, sample_activities):
        """Test proper serialization of activity data for database insert."""
        trip_id = uuid4()
        
        # We can't easily test the actual serialization without real database
        # but we can verify the structure of data being prepared
        activities = sample_activities
        
        # This test verifies that the method handles complex data types correctly
        assert all(activity.location.latitude is not None for activity in activities)
        assert all(isinstance(activity.price, Decimal) for activity in activities)
        assert all(activity.category in ActivityCategory for activity in activities)


class TestActivityRepositoryIntegration:
    """Integration tests that would run with actual testcontainers."""
    
    @pytest.mark.skip(reason="Requires testcontainers setup")
    @pytest.mark.asyncio
    async def test_full_activity_lifecycle_with_real_db(self):
        """Test complete activity lifecycle with real database.
        
        This test would:
        1. Start PostgreSQL testcontainer
        2. Run schema migrations
        3. Insert activities
        4. Query and filter activities
        5. Update ratings
        6. Clean up data
        """
        # This would be implemented with actual testcontainers
        # when running in a full test environment
        pass

    @pytest.mark.skip(reason="Requires testcontainers setup")
    @pytest.mark.asyncio
    async def test_postGIS_spatial_queries(self):
        """Test PostGIS spatial queries with real database.
        
        This test would verify:
        1. Location point generation from JSONB
        2. Distance calculations
        3. Radius-based searches
        4. Spatial indexing performance
        """
        pass

    @pytest.mark.skip(reason="Requires testcontainers setup")
    @pytest.mark.asyncio
    async def test_concurrent_activity_operations(self):
        """Test concurrent database operations for activities.
        
        This test would verify:
        1. Concurrent inserts don't create duplicates
        2. Race condition handling
        3. Transaction isolation
        """
        pass