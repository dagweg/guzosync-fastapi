"""
Mapbox service for route shapes, ETA calculations, and geospatial operations
"""
import os
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import aiohttp
from geopy.distance import geodesic
from shapely.geometry import LineString, Point
import redis.asyncio as redis

from core.logger import get_logger
from models.transport import Location

logger = get_logger(__name__)


class MapboxService:
    """Service for Mapbox API integration"""
    
    def __init__(self):
        self.access_token = os.getenv("MAPBOX_ACCESS_TOKEN")
        self.base_url = "https://api.mapbox.com"
        self.redis_client: Optional[redis.Redis] = None
        self.cache_ttl = 3600  # 1 hour cache
        if not self.access_token:
            logger.debug("Mapbox access token not configured - Mapbox features will be disabled")
    
    async def initialize_redis(self):
        """Initialize Redis connection for caching"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Redis connection established for Mapbox caching")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.redis_client = None
    
    async def get_route_shape(
        self, 
        coordinates: List[Location], 
        profile: str = "driving"
    ) -> Optional[Dict[str, Any]]:
        """
        Get route shape (GeoJSON LineString) from Mapbox Directions API
        
        Args:
            coordinates: List of Location objects (waypoints)
            profile: Routing profile (driving, walking, cycling)
            
        Returns:
            Dict containing route geometry and metadata
        """
        if not self.access_token:
            logger.debug("Mapbox access token not configured - route shape unavailable")
            return None
        
        if len(coordinates) < 2:
            logger.error("At least 2 coordinates required for route")
            return None
        
        # Create cache key
        coord_str = ";".join([f"{loc.longitude},{loc.latitude}" for loc in coordinates])
        cache_key = f"mapbox:route:{profile}:{hash(coord_str)}"
        
        # Check cache first
        if self.redis_client:
            try:
                cached_result = await self.redis_client.get(cache_key)
                if cached_result:
                    logger.debug(f"Route shape cache hit for {cache_key}")
                    return json.loads(cached_result)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        # Build Mapbox API URL
        coordinates_str = ";".join([f"{loc.longitude},{loc.latitude}" for loc in coordinates])
        url = (
            f"{self.base_url}/directions/v5/mapbox/{profile}/"
            f"{coordinates_str}"
            f"?access_token={self.access_token}"
            f"&geometries=geojson"
            f"&overview=full"
            f"&steps=true"
        )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("routes"):
                            route = data["routes"][0]
                            result = {
                                "geometry": route["geometry"],
                                "distance": route["distance"],  # meters
                                "duration": route["duration"],  # seconds
                                "steps": route.get("legs", [{}])[0].get("steps", []),
                                "profile": profile,
                                "created_at": datetime.utcnow().isoformat()
                            }
                            
                            # Cache the result
                            if self.redis_client:
                                try:
                                    await self.redis_client.setex(
                                        cache_key, 
                                        self.cache_ttl, 
                                        json.dumps(result)
                                    )
                                    logger.debug(f"Cached route shape for {cache_key}")
                                except Exception as e:
                                    logger.warning(f"Cache write error: {e}")
                            
                            return result
                        else:
                            logger.error("No routes found in Mapbox response")
                            return None
                    else:
                        logger.error(f"Mapbox API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching route shape: {e}")
            return None
    
    async def calculate_eta(
        self, 
        origin: Location, 
        destination: Location, 
        current_speed: Optional[float] = None,
        traffic_aware: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate ETA between two points
        
        Args:
            origin: Starting location
            destination: End location
            current_speed: Current vehicle speed (km/h)
            traffic_aware: Whether to consider traffic conditions
            
        Returns:
            Dict containing ETA information
        """
        if not self.access_token:
            logger.error("Mapbox access token not configured")
            return None
        
        # Create cache key
        cache_key = f"mapbox:eta:{origin.latitude},{origin.longitude}:{destination.latitude},{destination.longitude}:{traffic_aware}"
        
        # Check cache (shorter TTL for ETA)
        if self.redis_client:
            try:
                cached_result = await self.redis_client.get(cache_key)
                if cached_result:
                    logger.debug(f"ETA cache hit for {cache_key}")
                    return json.loads(cached_result)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        # Build Mapbox API URL
        coordinates_str = f"{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}"
        profile = "driving-traffic" if traffic_aware else "driving"
        
        url = (
            f"{self.base_url}/directions/v5/mapbox/{profile}/"
            f"{coordinates_str}"
            f"?access_token={self.access_token}"
            f"&geometries=geojson"
            f"&overview=simplified"
        )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("routes"):
                            route = data["routes"][0]
                            
                            # Calculate straight-line distance for comparison
                            straight_distance = geodesic(
                                (origin.latitude, origin.longitude),
                                (destination.latitude, destination.longitude)
                            ).kilometers
                            
                            result = {
                                "duration_seconds": route["duration"],
                                "duration_minutes": round(route["duration"] / 60, 1),
                                "distance_meters": route["distance"],
                                "distance_km": round(route["distance"] / 1000, 2),
                                "straight_line_distance_km": round(straight_distance, 2),
                                "estimated_arrival": (
                                    datetime.utcnow() + timedelta(seconds=route["duration"])
                                ).isoformat(),
                                "traffic_aware": traffic_aware,
                                "current_speed_kmh": current_speed,
                                "calculated_at": datetime.utcnow().isoformat()
                            }
                            
                            # Adjust ETA based on current speed if provided
                            if current_speed and current_speed > 0:
                                time_based_on_speed = (route["distance"] / 1000) / current_speed * 3600
                                # Use average of Mapbox estimate and speed-based estimate
                                adjusted_duration = (route["duration"] + time_based_on_speed) / 2
                                result["adjusted_duration_seconds"] = adjusted_duration
                                result["adjusted_estimated_arrival"] = (
                                    datetime.utcnow() + timedelta(seconds=adjusted_duration)
                                ).isoformat()
                            
                            # Cache with shorter TTL for ETA (5 minutes)
                            if self.redis_client:
                                try:
                                    await self.redis_client.setex(
                                        cache_key, 
                                        300,  # 5 minutes
                                        json.dumps(result)
                                    )
                                    logger.debug(f"Cached ETA for {cache_key}")
                                except Exception as e:
                                    logger.warning(f"Cache write error: {e}")
                            
                            return result
                        else:
                            logger.error("No routes found in Mapbox ETA response")
                            return None
                    else:
                        logger.error(f"Mapbox ETA API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error calculating ETA: {e}")
            return None
    
    async def get_route_stops_eta(
        self, 
        bus_location: Location, 
        route_stops: List[Tuple[str, Location]], 
        current_speed: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate ETA to all stops on a route
        
        Args:
            bus_location: Current bus location
            route_stops: List of (stop_id, location) tuples
            current_speed: Current bus speed
            
        Returns:
            List of ETA information for each stop
        """
        results = []
        
        for stop_id, stop_location in route_stops:
            eta_info = await self.calculate_eta(
                bus_location, 
                stop_location, 
                current_speed
            )
            
            if eta_info:
                eta_info["stop_id"] = stop_id
                results.append(eta_info)
            else:
                # Fallback to straight-line calculation
                distance = geodesic(
                    (bus_location.latitude, bus_location.longitude),
                    (stop_location.latitude, stop_location.longitude)
                ).kilometers
                
                # Assume average speed of 30 km/h if no current speed
                avg_speed = current_speed if current_speed and current_speed > 0 else 30
                estimated_time = (distance / avg_speed) * 3600  # seconds
                
                results.append({
                    "stop_id": stop_id,
                    "duration_seconds": estimated_time,
                    "duration_minutes": round(estimated_time / 60, 1),
                    "distance_km": round(distance, 2),
                    "estimated_arrival": (
                        datetime.utcnow() + timedelta(seconds=estimated_time)
                    ).isoformat(),
                    "fallback_calculation": True,
                    "calculated_at": datetime.utcnow().isoformat()
                })
        
        return results
    
    def is_point_on_route(
        self, 
        point: Location, 
        route_geometry: Dict[str, Any], 
        tolerance_meters: float = 100
    ) -> bool:
        """
        Check if a point is on a route within tolerance
        
        Args:
            point: Location to check
            route_geometry: GeoJSON LineString geometry
            tolerance_meters: Distance tolerance in meters
            
        Returns:
            True if point is on route within tolerance
        """
        try:
            # Create Shapely objects
            route_line = LineString(route_geometry["coordinates"])
            point_geom = Point(point.longitude, point.latitude)
            
            # Calculate distance to route (in degrees, approximate)
            distance_degrees = route_line.distance(point_geom)
            
            # Convert to meters (rough approximation: 1 degree ≈ 111km)
            distance_meters = distance_degrees * 111000
            
            return distance_meters <= tolerance_meters
            
        except Exception as e:
            logger.error(f"Error checking if point is on route: {e}")
            return False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()


# Global Mapbox service instance
mapbox_service = MapboxService()
