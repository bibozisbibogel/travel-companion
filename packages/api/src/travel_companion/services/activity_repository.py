"""Activity repository for database operations."""

import logging
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from travel_companion.core.database import DatabaseManager
from travel_companion.models.external import ActivityOption


class ActivityRepository:
    """Repository for activity database operations."""

    def __init__(self, database: DatabaseManager) -> None:
        """Initialize activity repository.
        
        Args:
            database: Database manager instance
        """
        self.db = database
        self.logger = logging.getLogger("travel_companion.services.activity_repository")

    async def insert_activity_options(
        self, 
        activities: list[ActivityOption], 
        trip_id: UUID
    ) -> list[UUID]:
        """Insert activity options into database.
        
        Args:
            activities: List of activity options to persist
            trip_id: Associated trip ID
            
        Returns:
            List of inserted activity IDs
        """
        if not activities:
            return []

        try:
            # Prepare batch insert data
            insert_data = []
            for activity in activities:
                activity_data = {
                    "activity_id": str(activity.activity_id),
                    "trip_id": str(trip_id),
                    "external_id": activity.external_id,
                    "name": activity.name,
                    "description": activity.description,
                    "category": activity.category.value,
                    "location": {
                        "latitude": activity.location.latitude,
                        "longitude": activity.location.longitude,
                        "address": activity.location.address,
                        "city": activity.location.city,
                        "country": activity.location.country,
                        "postal_code": activity.location.postal_code,
                    },
                    "duration_minutes": activity.duration_minutes,
                    "price": float(activity.price),
                    "currency": activity.currency,
                    "rating": activity.rating,
                    "review_count": activity.review_count,
                    "images": activity.images,
                    "booking_url": activity.booking_url,
                    "provider": activity.provider,
                    "created_at": activity.created_at.isoformat(),
                }
                insert_data.append(activity_data)

            # Batch insert using Supabase
            result = self.db.client.table("activity_options").insert(insert_data).execute()
            
            inserted_ids = [UUID(record["activity_id"]) for record in result.data]
            
            self.logger.info(f"Inserted {len(inserted_ids)} activity options for trip {trip_id}")
            return inserted_ids
            
        except Exception as e:
            self.logger.error(f"Failed to insert activity options: {e}")
            raise

    async def get_activities_by_trip(self, trip_id: UUID) -> list[dict[str, Any]]:
        """Get all activities for a specific trip.
        
        Args:
            trip_id: Trip ID to search for
            
        Returns:
            List of activity dictionaries
        """
        try:
            result = (
                self.db.client.table("activity_options")
                .select("*")
                .eq("trip_id", str(trip_id))
                .order("created_at", desc=True)
                .execute()
            )
            
            self.logger.debug(f"Retrieved {len(result.data)} activities for trip {trip_id}")
            return result.data
            
        except Exception as e:
            self.logger.error(f"Failed to get activities for trip {trip_id}: {e}")
            raise

    async def search_activities_by_location(
        self, 
        latitude: float, 
        longitude: float, 
        radius_km: float = 25.0,
        category: str | None = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search activities by geographic location.
        
        Args:
            latitude: Search center latitude
            longitude: Search center longitude  
            radius_km: Search radius in kilometers
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List of activity dictionaries within radius
        """
        try:
            # Build query with PostGIS distance calculation
            query = self.db.client.table("activity_options").select("*")
            
            # Add category filter if specified
            if category:
                query = query.eq("category", category)
                
            # Execute query (Supabase PostGIS functions would be used in production)
            # For now, we'll do a simple query and filter in Python
            result = query.limit(limit * 2).execute()  # Get more to filter by distance
            
            # Filter by distance (simplified - in production use PostGIS ST_DWithin)
            filtered_activities = []
            for activity in result.data:
                location = activity.get("location", {})
                if not location:
                    continue
                    
                act_lat = location.get("latitude")
                act_lng = location.get("longitude")
                
                if act_lat is None or act_lng is None:
                    continue
                    
                # Simple distance calculation (Haversine would be more accurate)
                lat_diff = abs(act_lat - latitude)
                lng_diff = abs(act_lng - longitude)
                
                # Rough approximation: 1 degree ≈ 111km
                distance_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111
                
                if distance_km <= radius_km:
                    activity["distance_km"] = round(distance_km, 2)
                    filtered_activities.append(activity)
                    
                if len(filtered_activities) >= limit:
                    break
            
            # Sort by distance
            filtered_activities.sort(key=lambda x: x.get("distance_km", 0))
            
            self.logger.debug(
                f"Found {len(filtered_activities)} activities within {radius_km}km of "
                f"({latitude}, {longitude})"
            )
            
            return filtered_activities
            
        except Exception as e:
            self.logger.error(f"Failed to search activities by location: {e}")
            raise

    async def filter_activities_by_criteria(
        self,
        trip_id: UUID | None = None,
        category: str | None = None,
        min_rating: float | None = None,
        max_price: float | None = None,
        min_duration: int | None = None,
        max_duration: int | None = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Filter activities by various criteria.
        
        Args:
            trip_id: Optional trip ID filter
            category: Optional category filter
            min_rating: Minimum rating threshold
            max_price: Maximum price threshold
            min_duration: Minimum duration in minutes
            max_duration: Maximum duration in minutes
            limit: Maximum number of results
            
        Returns:
            List of filtered activity dictionaries
        """
        try:
            query = self.db.client.table("activity_options").select("*")
            
            # Apply filters
            if trip_id:
                query = query.eq("trip_id", str(trip_id))
            if category:
                query = query.eq("category", category)
            if min_rating:
                query = query.gte("rating", min_rating)
            if max_price:
                query = query.lte("price", max_price)
            if min_duration:
                query = query.gte("duration_minutes", min_duration)
            if max_duration:
                query = query.lte("duration_minutes", max_duration)
                
            result = query.order("rating", desc=True).limit(limit).execute()
            
            self.logger.debug(f"Filtered activities returned {len(result.data)} results")
            return result.data
            
        except Exception as e:
            self.logger.error(f"Failed to filter activities: {e}")
            raise

    async def cleanup_activities_for_completed_trip(self, trip_id: UUID) -> int:
        """Clean up activity options for completed trips older than 30 days.
        
        Args:
            trip_id: Trip ID to clean up
            
        Returns:
            Number of activities cleaned up
        """
        try:
            # In a production system, you'd check trip completion status and date
            # For now, we'll implement basic cleanup
            
            result = (
                self.db.client.table("activity_options")
                .delete()
                .eq("trip_id", str(trip_id))
                .execute()
            )
            
            cleanup_count = len(result.data) if result.data else 0
            
            self.logger.info(f"Cleaned up {cleanup_count} activities for trip {trip_id}")
            return cleanup_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup activities for trip {trip_id}: {e}")
            raise

    async def get_activity_by_id(self, activity_id: UUID) -> dict[str, Any] | None:
        """Get a specific activity by ID.
        
        Args:
            activity_id: Activity ID to retrieve
            
        Returns:
            Activity dictionary or None if not found
        """
        try:
            result = (
                self.db.client.table("activity_options")
                .select("*")
                .eq("activity_id", str(activity_id))
                .single()
                .execute()
            )
            
            return result.data if result.data else None
            
        except Exception as e:
            self.logger.error(f"Failed to get activity {activity_id}: {e}")
            return None

    async def update_activity_rating(self, activity_id: UUID, rating: float, review_count: int) -> bool:
        """Update activity rating and review count.
        
        Args:
            activity_id: Activity ID to update
            rating: New rating value
            review_count: New review count
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            result = (
                self.db.client.table("activity_options")
                .update({"rating": rating, "review_count": review_count})
                .eq("activity_id", str(activity_id))
                .execute()
            )
            
            success = len(result.data) > 0 if result.data else False
            if success:
                self.logger.debug(f"Updated rating for activity {activity_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update activity rating {activity_id}: {e}")
            return False