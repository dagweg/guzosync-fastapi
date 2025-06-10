"""
Route service for managing route shapes, ETA calculations, and route optimization
"""
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import json

from core.logger import get_logger
from core.services.mapbox_service import mapbox_service
from models.transport import Route, BusStop, Bus, Location
from schemas.route import ETAResponse, RouteShapeResponse, BusETAResponse

logger = get_logger(__name__)


class RouteService:
    """Service for route management and optimization"""
    
    def __init__(self):
        self.mapbox = mapbox_service
    
    async def generate_route_shape(
        self, 
        route_id: str, 
        bus_stops: List[BusStop],
        app_state=None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate route shape from bus stops using Mapbox
        
        Args:
            route_id: Route ID
            bus_stops: List of bus stops in order
            app_state: Application state for database access
            
        Returns:
            Route shape data or None if failed
        """
        if len(bus_stops) < 2:
            logger.error(f"Route {route_id} needs at least 2 stops for shape generation")
            return None
        
        # Convert bus stops to coordinates
        coordinates = [stop.location for stop in bus_stops]
        
        try:
            # Get route shape from Mapbox
            shape_data = await self.mapbox.get_route_shape(coordinates, profile="driving")
            
            if shape_data:
                # Update route in database with shape data
                if app_state and app_state.mongodb:
                    update_data = {
                        "route_geometry": shape_data["geometry"],
                        "route_shape_data": shape_data,
                        "last_shape_update": datetime.utcnow(),
                        "total_distance": round(shape_data["distance"] / 1000, 2),  # Convert to km
                        "estimated_duration": round(shape_data["duration"] / 60, 2),  # Convert to minutes
                        "shape_cache_key": f"route_shape:{route_id}:{hash(str(coordinates))}"
                    }
                    
                    await app_state.mongodb.routes.update_one(
                        {"id": route_id},
                        {"$set": update_data}
                    )
                    
                    logger.info(f"Updated route {route_id} with Mapbox shape data")
                
                return shape_data
            else:
                logger.error(f"Failed to get route shape for route {route_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating route shape for {route_id}: {e}")
            return None
    
    async def calculate_bus_eta_to_stops(
        self, 
        bus: Bus, 
        route_stops: List[Tuple[str, BusStop]],
        app_state=None
    ) -> List[ETAResponse]:
        """
        Calculate ETA from bus current location to all stops on route
        
        Args:
            bus: Bus object with current location
            route_stops: List of (stop_id, BusStop) tuples in route order
            app_state: Application state
            
        Returns:
            List of ETA responses for each stop
        """
        if not bus.current_location:
            logger.warning(f"Bus {bus.id} has no current location for ETA calculation")
            return []
        
        try:
            # Prepare stops for ETA calculation
            stops_for_eta = [(stop_id, stop.location) for stop_id, stop in route_stops]
            
            # Calculate ETAs using Mapbox service
            eta_results = await self.mapbox.get_route_stops_eta(
                bus.current_location,
                stops_for_eta,
                bus.speed
            )
            
            # Convert to ETAResponse objects
            eta_responses = []
            for eta_data in eta_results:
                # Find corresponding stop name
                stop_name = None
                for stop_id, stop in route_stops:
                    if stop_id == eta_data["stop_id"]:
                        stop_name = stop.name
                        break
                
                eta_response = ETAResponse(
                    stop_id=eta_data["stop_id"],
                    stop_name=stop_name,
                    duration_seconds=eta_data["duration_seconds"],
                    duration_minutes=eta_data["duration_minutes"],
                    distance_meters=eta_data.get("distance_meters", eta_data.get("distance_km", 0) * 1000),
                    distance_km=eta_data.get("distance_km", eta_data.get("distance_meters", 0) / 1000),
                    estimated_arrival=eta_data["estimated_arrival"],
                    traffic_aware=eta_data.get("traffic_aware", True),
                    current_speed_kmh=eta_data.get("current_speed_kmh"),
                    calculated_at=eta_data["calculated_at"],
                    fallback_calculation=eta_data.get("fallback_calculation", False)
                )
                eta_responses.append(eta_response)
            
            return eta_responses
            
        except Exception as e:
            logger.error(f"Error calculating bus ETA for bus {bus.id}: {e}")
            return []
    
    async def get_route_shape_cached(
        self, 
        route_id: str, 
        app_state=None
    ) -> Optional[Dict[str, Any]]:
        """
        Get route shape from cache or generate if not exists
        
        Args:
            route_id: Route ID
            app_state: Application state
            
        Returns:
            Route shape data or None
        """
        if app_state is None or not hasattr(app_state, 'mongodb') or app_state.mongodb is None:
            return None
        
        try:
            # Get route from database
            route_doc = await app_state.mongodb.routes.find_one({"id": route_id})
            if not route_doc:
                logger.error(f"Route {route_id} not found")
                return None
            
            # Check if we have cached shape data
            if (route_doc.get("route_geometry") and 
                route_doc.get("last_shape_update") and
                datetime.utcnow() - route_doc["last_shape_update"] < timedelta(hours=24)):
                
                logger.debug(f"Using cached route shape for {route_id}")
                return {
                    "geometry": route_doc["route_geometry"],
                    "distance": route_doc.get("total_distance", 0) * 1000,  # Convert to meters
                    "duration": route_doc.get("estimated_duration", 0) * 60,  # Convert to seconds
                    "profile": "driving",
                    "created_at": route_doc["last_shape_update"].isoformat()
                }
            
            # Generate new shape data
            logger.info(f"Generating new route shape for {route_id}")
            
            # Get bus stops for this route
            stop_ids = route_doc.get("stop_ids", [])
            if len(stop_ids) < 2:
                logger.error(f"Route {route_id} has insufficient stops for shape generation")
                return None
            
            # Fetch bus stops from database
            bus_stops_cursor = app_state.mongodb.bus_stops.find({"id": {"$in": stop_ids}})
            bus_stops_docs = await bus_stops_cursor.to_list(length=None)
            
            # Convert to BusStop objects and maintain order
            bus_stops = []
            for stop_id in stop_ids:
                for stop_doc in bus_stops_docs:
                    if stop_doc["id"] == stop_id:
                        bus_stop = BusStop(
                            id=stop_doc["id"],
                            name=stop_doc["name"],
                            location=Location(
                                latitude=stop_doc["location"]["latitude"],
                                longitude=stop_doc["location"]["longitude"]
                            ),
                            capacity=stop_doc.get("capacity"),
                            is_active=stop_doc.get("is_active", True)
                        )
                        bus_stops.append(bus_stop)
                        break
            
            if len(bus_stops) < 2:
                logger.error(f"Could not find enough bus stops for route {route_id}")
                return None
            
            # Generate route shape
            return await self.generate_route_shape(route_id, bus_stops, app_state)
            
        except Exception as e:
            logger.error(f"Error getting route shape for {route_id}: {e}")
            return None
    
    async def update_all_route_shapes(self, app_state=None):
        """
        Background task to update all route shapes
        
        Args:
            app_state: Application state
        """
        if app_state is None or not hasattr(app_state, 'mongodb') or app_state.mongodb is None:
            logger.error("Cannot update route shapes without database connection")
            return
        
        try:
            # Get all active routes
            routes_cursor = app_state.mongodb.routes.find({"is_active": True})
            routes = await routes_cursor.to_list(length=None)
            
            logger.info(f"Updating shapes for {len(routes)} active routes")
            
            for route_doc in routes:
                try:
                    route_id = route_doc["id"]
                    
                    # Check if shape needs update (older than 24 hours)
                    last_update = route_doc.get("last_shape_update")
                    if (last_update and 
                        datetime.utcnow() - last_update < timedelta(hours=24)):
                        continue
                    
                    # Get bus stops for this route
                    stop_ids = route_doc.get("stop_ids", [])
                    if len(stop_ids) < 2:
                        continue
                    
                    # Fetch bus stops
                    bus_stops_cursor = app_state.mongodb.bus_stops.find({"id": {"$in": stop_ids}})
                    bus_stops_docs = await bus_stops_cursor.to_list(length=None)
                    
                    # Convert to BusStop objects
                    bus_stops = []
                    for stop_id in stop_ids:
                        for stop_doc in bus_stops_docs:
                            if stop_doc["id"] == stop_id:
                                bus_stop = BusStop(
                                    id=stop_doc["id"],
                                    name=stop_doc["name"],
                                    location=Location(
                                        latitude=stop_doc["location"]["latitude"],
                                        longitude=stop_doc["location"]["longitude"]
                                    ),
                                    capacity=stop_doc.get("capacity"),
                                    is_active=stop_doc.get("is_active", True)
                                )
                                bus_stops.append(bus_stop)
                                break
                    
                    if len(bus_stops) >= 2:
                        await self.generate_route_shape(route_id, bus_stops, app_state)
                        # Add small delay to avoid rate limiting
                        await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error updating shape for route {route_doc.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info("Completed route shapes update")
            
        except Exception as e:
            logger.error(f"Error in update_all_route_shapes: {e}")


# Global route service instance
route_service = RouteService()
