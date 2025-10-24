"""Tests for trip planning API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from travel_companion.models.trip import TripResponse, TripStatus
from travel_companion.models.user import User


def create_mock_trip_response(
    trip_id: UUID,
    user_id: UUID,
    name: str = "Test Trip",
    description: str = "Test Description",
    destination: dict | None = None,
    requirements: dict | None = None,
    status: TripStatus = TripStatus.DRAFT,
) -> TripResponse:
    """Helper to create a properly formatted TripResponse for testing."""
    if destination is None:
        destination = {"city": "Paris", "country": "France", "country_code": "FR"}

    if requirements is None:
        requirements = {
            "budget": 2000.00,
            "currency": "EUR",
            "start_date": "2024-06-01",
            "end_date": "2024-06-07",
            "travelers": 2,
            "travel_class": "economy",
        }

    return TripResponse(
        trip_id=trip_id,
        user_id=user_id,
        name=name,
        description=description,
        destination=destination,
        requirements=requirements,
        status=status,
        plan=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestTripPlanEndpoint:
    """Test trip plan generation endpoint."""

    def test_generate_trip_plan_success(self, authenticated_client: TestClient, sample_user: User):
        """Test successful trip plan generation."""
        trip_request = {
            "destination": {
                "city": "Paris",
                "country": "France",
                "country_code": "FR",
                "airport_code": "CDG",
            },
            "requirements": {
                "budget": 2000.00,
                "currency": "EUR",
                "start_date": "2024-06-01",
                "end_date": "2024-06-07",
                "travelers": 2,
                "travel_class": "economy",
            },
        }

        # Mock TravelPlannerAgent.plan_trip() to prevent actual API calls
        with patch("travel_companion.api.v1.trips.TravelPlannerAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            # Mock the async generator plan_trip method
            async def mock_plan_trip(request):
                yield {"type": "itinerary", "data": None}

            mock_agent.plan_trip = mock_plan_trip

            # Mock TripService.create_trip to prevent database calls
            with patch("travel_companion.api.v1.trips.TripService") as mock_service_class:
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Mock the create_trip method to return a trip response
                mock_trip = create_mock_trip_response(
                    trip_id=uuid4(),
                    user_id=sample_user.user_id,
                    name="Trip to Paris",
                    description="AI-generated travel plan for Paris",
                    destination=trip_request["destination"],
                    requirements=trip_request["requirements"],
                    status=TripStatus.DRAFT,
                )

                mock_service.create_trip = AsyncMock(return_value=mock_trip)

                response = authenticated_client.post("/api/v1/trips/plan", json=trip_request)

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["message"] == "Trip plan generated and saved successfully"
                assert "data" in data
                assert data["data"]["destination"]["city"] == "Paris"
                assert data["data"]["user_id"] == str(sample_user.user_id)

    def test_generate_trip_plan_unauthenticated(self, client: TestClient):
        """Test trip plan generation without authentication."""
        trip_request = {
            "destination": {"city": "Paris", "country": "France", "country_code": "FR"},
            "requirements": {
                "budget": 2000.00,
                "currency": "EUR",
                "start_date": "2024-06-01",
                "end_date": "2024-06-07",
                "travelers": 2,
            },
        }

        response = client.post("/api/v1/trips/plan", json=trip_request)
        assert response.status_code == 403

    def test_generate_trip_plan_invalid_dates(
        self, authenticated_client: TestClient, sample_user: User
    ):
        """Test trip plan generation with invalid date range."""
        trip_request = {
            "destination": {"city": "Paris", "country": "France", "country_code": "FR"},
            "requirements": {
                "budget": 2000.00,
                "currency": "EUR",
                "start_date": "2024-06-07",
                "end_date": "2024-06-01",  # End before start
                "travelers": 2,
            },
        }

        response = authenticated_client.post("/api/v1/trips/plan", json=trip_request)

        assert response.status_code == 422  # Validation error

    def test_generate_trip_plan_invalid_budget(
        self, authenticated_client: TestClient, sample_user: User
    ):
        """Test trip plan generation with invalid budget."""
        trip_request = {
            "destination": {"city": "Paris", "country": "France", "country_code": "FR"},
            "requirements": {
                "budget": -100.00,  # Negative budget
                "currency": "EUR",
                "start_date": "2024-06-01",
                "end_date": "2024-06-07",
                "travelers": 2,
            },
        }

        response = authenticated_client.post("/api/v1/trips/plan", json=trip_request)

        assert response.status_code == 422  # Validation error


class TestCreateTripEndpoint:
    """Test trip creation endpoint."""

    def test_create_trip_success(self, authenticated_client: TestClient, sample_user: User):
        """Test successful trip creation."""
        trip_data = {
            "name": "Paris Adventure",
            "description": "A wonderful trip to Paris",
            "destination": {
                "city": "Paris",
                "country": "France",
                "country_code": "FR",
                "airport_code": "CDG",
            },
            "requirements": {
                "budget": 2000.00,
                "currency": "EUR",
                "start_date": "2024-06-01",
                "end_date": "2024-06-07",
                "travelers": 2,
                "travel_class": "economy",
            },
        }

        # Mock TripService to prevent database calls
        with patch("travel_companion.api.v1.trips.TripService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            mock_trip = create_mock_trip_response(
                trip_id=uuid4(),
                user_id=sample_user.user_id,
                name="Paris Adventure",
                description="A wonderful trip to Paris",
                destination=trip_data["destination"],
                requirements=trip_data["requirements"],
                status=TripStatus.DRAFT,
            )

            mock_service.create_trip = AsyncMock(return_value=mock_trip)

            response = authenticated_client.post("/api/v1/trips/", json=trip_data)

            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Trip created successfully"
            assert data["data"]["name"] == "Paris Adventure"
            assert data["data"]["user_id"] == str(sample_user.user_id)

    def test_create_trip_missing_required_fields(
        self, authenticated_client: TestClient, sample_user: User
    ):
        """Test trip creation with missing required fields."""
        trip_data = {
            "name": "Paris Adventure"
            # Missing destination and requirements
        }

        response = authenticated_client.post("/api/v1/trips/", json=trip_data)

        assert response.status_code == 422  # Validation error

    def test_create_trip_unauthenticated(self, client: TestClient):
        """Test trip creation without authentication."""
        trip_data = {
            "name": "Paris Adventure",
            "destination": {"city": "Paris", "country": "France", "country_code": "FR"},
            "requirements": {
                "budget": 2000.00,
                "currency": "EUR",
                "start_date": "2024-06-01",
                "end_date": "2024-06-07",
                "travelers": 2,
            },
        }

        response = client.post("/api/v1/trips/", json=trip_data)
        assert response.status_code == 403


class TestListTripsEndpoint:
    """Test trip listing endpoint."""

    def test_list_trips_success(self, authenticated_client: TestClient, sample_user: User):
        """Test successful trip listing."""
        response = authenticated_client.get("/api/v1/trips/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    def test_list_trips_with_pagination(self, authenticated_client: TestClient, sample_user: User):
        """Test trip listing with pagination parameters."""
        response = authenticated_client.get("/api/v1/trips/?page=2&per_page=10")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["per_page"] == 10

    def test_list_trips_invalid_pagination(
        self, authenticated_client: TestClient, sample_user: User
    ):
        """Test trip listing with invalid pagination parameters."""
        # Test invalid page
        response = authenticated_client.get("/api/v1/trips/?page=0")
        assert response.status_code == 400

        # Test invalid per_page
        response = authenticated_client.get("/api/v1/trips/?per_page=101")
        assert response.status_code == 400

    def test_list_trips_unauthenticated(self, client: TestClient):
        """Test trip listing without authentication."""
        response = client.get("/api/v1/trips/")
        assert response.status_code == 403


class TestGetTripEndpoint:
    """Test individual trip retrieval endpoint."""

    def test_get_trip_success(self, authenticated_client: TestClient, sample_user: User):
        """Test successful trip retrieval."""
        trip_id = uuid4()

        # Mock TripService to prevent database calls
        with patch("travel_companion.api.v1.trips.TripService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            mock_trip = create_mock_trip_response(
                trip_id=trip_id,
                user_id=sample_user.user_id,
                name="Paris Adventure",
                description="A wonderful trip to Paris",
                destination={"city": "Paris", "country": "France", "country_code": "FR"},
                status=TripStatus.DRAFT,
            )

            mock_service.get_trip_by_id = AsyncMock(return_value=mock_trip)

            response = authenticated_client.get(f"/api/v1/trips/{trip_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["trip_id"] == str(trip_id)
            assert data["data"]["user_id"] == str(sample_user.user_id)

    def test_get_trip_not_found(self, authenticated_client: TestClient, sample_user: User):
        """Test trip retrieval for non-existent trip."""
        # Use the special ID that triggers 404 in the placeholder implementation
        trip_id = "00000000-0000-4000-8000-000000000404"

        response = authenticated_client.get(f"/api/v1/trips/{trip_id}")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "TRIP_NOT_FOUND"

    def test_get_trip_invalid_uuid(self, authenticated_client: TestClient, sample_user: User):
        """Test trip retrieval with invalid UUID."""
        response = authenticated_client.get("/api/v1/trips/invalid-uuid")

        assert response.status_code == 422  # Validation error

    def test_get_trip_unauthenticated(self, client: TestClient):
        """Test trip retrieval without authentication."""
        trip_id = uuid4()
        response = client.get(f"/api/v1/trips/{trip_id}")
        assert response.status_code == 403


class TestUpdateTripEndpoint:
    """Test trip update endpoint."""

    def test_update_trip_success(self, authenticated_client: TestClient, sample_user: User):
        """Test successful trip update."""
        trip_id = uuid4()
        update_data = {
            "name": "Updated Trip Name",
            "description": "Updated description",
            "status": "planning",
        }

        # Mock TripService to prevent database calls
        with patch("travel_companion.api.v1.trips.TripService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            mock_trip = create_mock_trip_response(
                trip_id=trip_id,
                user_id=sample_user.user_id,
                name="Updated Trip Name",
                description="Updated description",
                destination={"city": "Paris", "country": "France", "country_code": "FR"},
                status=TripStatus.PLANNING,
            )

            mock_service.update_trip = AsyncMock(return_value=mock_trip)

            response = authenticated_client.put(f"/api/v1/trips/{trip_id}", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Trip updated successfully"
            assert data["data"]["name"] == "Updated Trip Name"

    def test_update_trip_partial_update(self, authenticated_client: TestClient, sample_user: User):
        """Test partial trip update."""
        trip_id = uuid4()
        update_data = {"name": "Updated Name Only"}

        # Mock TripService to prevent database calls
        with patch("travel_companion.api.v1.trips.TripService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            mock_trip = create_mock_trip_response(
                trip_id=trip_id,
                user_id=sample_user.user_id,
                name="Updated Name Only",
                description="A wonderful trip to Paris",
                destination={"city": "Paris", "country": "France", "country_code": "FR"},
                status=TripStatus.DRAFT,
            )

            mock_service.update_trip = AsyncMock(return_value=mock_trip)

            response = authenticated_client.put(f"/api/v1/trips/{trip_id}", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_update_trip_not_found(self, authenticated_client: TestClient, sample_user: User):
        """Test trip update for non-existent trip."""
        trip_id = "00000000-0000-4000-8000-000000000404"
        update_data = {"name": "New Name"}

        response = authenticated_client.put(f"/api/v1/trips/{trip_id}", json=update_data)

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "TRIP_NOT_FOUND"

    def test_update_trip_unauthenticated(self, client: TestClient):
        """Test trip update without authentication."""
        trip_id = uuid4()
        update_data = {"name": "New Name"}

        response = client.put(f"/api/v1/trips/{trip_id}", json=update_data)
        assert response.status_code == 403


class TestDeleteTripEndpoint:
    """Test trip deletion endpoint."""

    def test_delete_trip_success(self, authenticated_client: TestClient, sample_user: User):
        """Test successful trip deletion."""
        trip_id = uuid4()

        # Mock TripService to prevent database calls
        with patch("travel_companion.api.v1.trips.TripService") as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            # Mock delete_trip to return True (successful deletion)
            mock_service.delete_trip = AsyncMock(return_value=True)

            response = authenticated_client.delete(f"/api/v1/trips/{trip_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Trip deleted successfully"
            assert data["data"]["trip_id"] == str(trip_id)

    def test_delete_trip_not_found(self, authenticated_client: TestClient, sample_user: User):
        """Test trip deletion for non-existent trip."""
        trip_id = "00000000-0000-4000-8000-000000000404"

        response = authenticated_client.delete(f"/api/v1/trips/{trip_id}")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "TRIP_NOT_FOUND"

    def test_delete_trip_unauthenticated(self, client: TestClient):
        """Test trip deletion without authentication."""
        trip_id = uuid4()
        response = client.delete(f"/api/v1/trips/{trip_id}")
        assert response.status_code == 403


class TestRouterRegistration:
    """Test router registration and endpoint discovery."""

    def test_trips_endpoints_registered(self, client: TestClient):
        """Test that all trips endpoints are properly registered."""
        # Get OpenAPI schema to verify endpoints are registered
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema["paths"]

        # Verify all trip endpoints are present
        expected_endpoints = ["/api/v1/trips/plan", "/api/v1/trips/", "/api/v1/trips/{trip_id}"]

        for endpoint in expected_endpoints:
            assert endpoint in paths, f"Endpoint {endpoint} not found in OpenAPI schema"

    def test_trips_tag_present(self, client: TestClient):
        """Test that trips tag is present in OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()

        # Check that trips tag exists in at least one endpoint
        trips_tag_found = False
        for path_data in openapi_schema["paths"].values():
            for method_data in path_data.values():
                if "tags" in method_data and "trips" in method_data["tags"]:
                    trips_tag_found = True
                    break
            if trips_tag_found:
                break

        assert trips_tag_found, "Trips tag not found in any endpoint"

    def test_trips_endpoints_methods(self, client: TestClient):
        """Test that trip endpoints have correct HTTP methods."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        paths = openapi_schema["paths"]

        # Check specific methods for each endpoint
        assert "post" in paths["/api/v1/trips/plan"]
        assert "post" in paths["/api/v1/trips/"]
        assert "get" in paths["/api/v1/trips/"]
        assert "get" in paths["/api/v1/trips/{trip_id}"]
        assert "put" in paths["/api/v1/trips/{trip_id}"]
        assert "delete" in paths["/api/v1/trips/{trip_id}"]
