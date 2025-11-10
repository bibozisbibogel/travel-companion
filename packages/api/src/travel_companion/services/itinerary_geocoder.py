"""Itinerary geocoding helper for adding coordinates to trip data."""

import asyncio
import logging
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any

from travel_companion.models.coordinates import Coordinates
from travel_companion.models.itinerary_output import (
    AccommodationInfo,
    Destination,
    FlightDetails,
    ItineraryActivity,
    ItineraryOutput,
    VenueInfo,
)
from travel_companion.services.geocoding_service import get_geocoding_service

logger = logging.getLogger(__name__)


class ItineraryGeocoder:
    """Helper class to geocode all locations in an itinerary."""

    def __init__(self) -> None:
        """Initialize the itinerary geocoder."""
        self.geocoding_service = get_geocoding_service()

    async def geocode_itinerary(self, itinerary: ItineraryOutput) -> ItineraryOutput:
        """
        Geocode all locations in an itinerary.

        Args:
            itinerary: Complete itinerary output

        Returns:
            Itinerary with geocoded coordinates added to all locations

        Example:
            >>> geocoder = ItineraryGeocoder()
            >>> itinerary = ItineraryOutput(...)
            >>> geocoded_itinerary = await geocoder.geocode_itinerary(itinerary)
        """
        logger.info("Starting geocoding for itinerary")

        # Collect all locations to geocode
        geocoding_tasks = []

        # 1. Geocode destination city
        destination_task = self._geocode_destination(itinerary.trip.destination)
        geocoding_tasks.append(destination_task)

        # 2. Geocode accommodation
        accommodation_task = self._geocode_accommodation(itinerary.accommodation)
        geocoding_tasks.append(accommodation_task)

        # 3. Geocode all activities across all days (with destination context)
        destination = itinerary.trip.destination
        for day in itinerary.itinerary:
            for activity in day.activities:
                activity_task = self._geocode_activity(activity, destination)
                geocoding_tasks.append(activity_task)

        # 4. Geocode flight airports
        flights_tasks = self._geocode_flights(itinerary.flights.outbound)
        geocoding_tasks.extend(flights_tasks)

        if itinerary.flights.return_flight:
            return_flights_tasks = self._geocode_flights(itinerary.flights.return_flight)
            geocoding_tasks.extend(return_flights_tasks)

        # Execute all geocoding operations concurrently (with max concurrency limit)
        logger.info(f"Geocoding {len(geocoding_tasks)} locations concurrently")
        await asyncio.gather(*geocoding_tasks, return_exceptions=True)

        logger.info("Geocoding completed for itinerary")
        return itinerary

    async def _geocode_destination(self, destination: Destination) -> None:
        """
        Geocode destination city.

        Args:
            destination: Destination object to update with coordinates
        """
        location_string = f"{destination.city}, {destination.country}"

        try:
            result = await self.geocoding_service.geocode_location(location_string)

            destination.coordinates = Coordinates(
                latitude=result.latitude if result.latitude is not None else 0.0,
                longitude=result.longitude if result.longitude is not None else 0.0,
                geocoding_status=result.status,
                geocoded_at=datetime.now(UTC) if result.status == "success" else None,
                geocoding_error_message=result.error_message,
            )

            logger.info(
                f"Geocoded destination: {location_string} -> "
                f"({result.latitude}, {result.longitude}), status={result.status}"
            )

        except Exception as e:
            logger.error(f"Failed to geocode destination {location_string}: {e}")
            destination.coordinates = Coordinates(
                latitude=0.0,
                longitude=0.0,
                geocoding_status="failed",
                geocoded_at=None,
                geocoding_error_message=f"Exception during geocoding: {str(e)}",
            )

    async def _geocode_accommodation(self, accommodation: AccommodationInfo) -> None:
        """
        Geocode accommodation location.

        Args:
            accommodation: Accommodation object to update with coordinates
        """
        # Build location string from address
        address_parts = [
            accommodation.address.street,
            accommodation.address.city,
            accommodation.address.region,
            accommodation.address.country,
        ]
        location_string = ", ".join([part for part in address_parts if part])

        try:
            result = await self.geocoding_service.geocode_location(location_string)

            accommodation.coordinates = Coordinates(
                latitude=result.latitude if result.latitude is not None else 0.0,
                longitude=result.longitude if result.longitude is not None else 0.0,
                geocoding_status=result.status,
                geocoded_at=datetime.now(UTC) if result.status == "success" else None,
                geocoding_error_message=result.error_message,
            )

            logger.info(
                f"Geocoded accommodation: {accommodation.name} -> "
                f"({result.latitude}, {result.longitude}), status={result.status}"
            )

        except Exception as e:
            logger.error(f"Failed to geocode accommodation {accommodation.name}: {e}")
            accommodation.coordinates = Coordinates(
                latitude=0.0,
                longitude=0.0,
                geocoding_status="failed",
                geocoded_at=None,
                geocoding_error_message=f"Exception during geocoding: {str(e)}",
            )

    async def _geocode_activity(
        self, activity: ItineraryActivity, destination: Destination
    ) -> None:
        """
        Geocode activity location with destination context.

        Args:
            activity: Activity object to update with coordinates
            destination: Trip destination for geographic context
        """
        if not activity.location:
            logger.debug(f"Skipping geocoding for activity '{activity.title}' - no location")
            return

        try:
            # Add destination context to ensure we geocode in the correct city
            location_with_context = f"{activity.location}, {destination.city}, {destination.country}"

            result = await self.geocoding_service.geocode_location(location_with_context)

            activity.coordinates = Coordinates(
                latitude=result.latitude if result.latitude is not None else 0.0,
                longitude=result.longitude if result.longitude is not None else 0.0,
                geocoding_status=result.status,
                geocoded_at=datetime.now(UTC) if result.status == "success" else None,
                geocoding_error_message=result.error_message,
            )

            logger.info(
                f"Geocoded activity: {activity.title} at {location_with_context} -> "
                f"({result.latitude}, {result.longitude}), status={result.status}"
            )

            # Geocode dining venue if present
            if activity.venue:
                await self._geocode_venue(activity.venue, destination)

        except Exception as e:
            logger.error(f"Failed to geocode activity {activity.title}: {e}")
            activity.coordinates = Coordinates(
                latitude=0.0,
                longitude=0.0,
                geocoding_status="failed",
                geocoded_at=None,
                geocoding_error_message=f"Exception during geocoding: {str(e)}",
            )

    async def _geocode_venue(self, venue: VenueInfo, destination: Destination) -> None:
        """
        Geocode restaurant/venue location with destination context.

        Args:
            venue: Venue object to update with coordinates
            destination: Trip destination for geographic context
        """
        if not venue.location:
            logger.debug(f"Skipping geocoding for venue '{venue.name}' - no location")
            return

        try:
            # Add destination context to ensure we geocode in the correct city
            location_with_context = f"{venue.location}, {destination.city}, {destination.country}"

            result = await self.geocoding_service.geocode_location(location_with_context)

            venue.coordinates = Coordinates(
                latitude=result.latitude if result.latitude is not None else 0.0,
                longitude=result.longitude if result.longitude is not None else 0.0,
                geocoding_status=result.status,
                geocoded_at=datetime.now(UTC) if result.status == "success" else None,
                geocoding_error_message=result.error_message,
            )

            logger.info(
                f"Geocoded venue: {venue.name} at {location_with_context} -> "
                f"({result.latitude}, {result.longitude}), status={result.status}"
            )

        except Exception as e:
            logger.error(f"Failed to geocode venue {venue.name}: {e}")
            venue.coordinates = Coordinates(
                latitude=0.0,
                longitude=0.0,
                geocoding_status="failed",
                geocoded_at=None,
                geocoding_error_message=f"Exception during geocoding: {str(e)}",
            )

    def _geocode_flights(self, flight: FlightDetails) -> list[Coroutine[Any, Any, None]]:
        """
        Create geocoding tasks for flight airports.

        Args:
            flight: Flight details to geocode

        Returns:
            List of geocoding tasks for departure and arrival airports
        """
        tasks = []

        # Geocode departure airport
        departure_task = self._geocode_airport(
            flight.route.from_airport, is_departure=True, flight=flight
        )
        tasks.append(departure_task)

        # Geocode arrival airport
        arrival_task = self._geocode_airport(
            flight.route.to_airport, is_departure=False, flight=flight
        )
        tasks.append(arrival_task)

        return tasks

    async def _geocode_airport(
        self, airport_code: str, is_departure: bool, flight: FlightDetails
    ) -> None:
        """
        Geocode airport by code.

        Args:
            airport_code: IATA airport code (e.g., 'JFK', 'FCO')
            is_departure: True for departure airport, False for arrival
            flight: Flight object to update with coordinates
        """
        # Airport geocoding: search for "{CODE} Airport"
        location_string = f"{airport_code} Airport"

        try:
            result = await self.geocoding_service.geocode_location(location_string)

            coordinates = Coordinates(
                latitude=result.latitude if result.latitude is not None else 0.0,
                longitude=result.longitude if result.longitude is not None else 0.0,
                geocoding_status=result.status,
                geocoded_at=datetime.now(UTC) if result.status == "success" else None,
                geocoding_error_message=result.error_message,
            )

            if is_departure:
                flight.departure_coordinates = coordinates
            else:
                flight.arrival_coordinates = coordinates

            logger.info(
                f"Geocoded airport: {airport_code} -> "
                f"({result.latitude}, {result.longitude}), status={result.status}"
            )

        except Exception as e:
            logger.error(f"Failed to geocode airport {airport_code}: {e}")
            coordinates = Coordinates(
                latitude=0.0,
                longitude=0.0,
                geocoding_status="failed",
                geocoded_at=None,
                geocoding_error_message=f"Exception during geocoding: {str(e)}",
            )

            if is_departure:
                flight.departure_coordinates = coordinates
            else:
                flight.arrival_coordinates = coordinates


async def geocode_itinerary(itinerary: ItineraryOutput) -> ItineraryOutput:
    """
    Convenience function to geocode an itinerary.

    Args:
        itinerary: Complete itinerary output

    Returns:
        Itinerary with geocoded coordinates

    Example:
        >>> itinerary = ItineraryOutput(...)
        >>> geocoded = await geocode_itinerary(itinerary)
    """
    geocoder = ItineraryGeocoder()
    return await geocoder.geocode_itinerary(itinerary)
