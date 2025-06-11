"""
Real-time bus tracking service with enhanced Mapbox integration
"""
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from core.websocket_manager import websocket_manager
from core.logger import get_logger
import asyncio

logger = get_logger(__name__)


class BusTrackingService:
    """Service for real-time bus tracking"""
    
    @staticmethod
    async def update_bus_location(
        bus_id: str,
        latitude: float,
        longitude: float,
        heading: Optional[float] = None,
        speed: Optional[float] = None,
        app_state=None
    ):
        """Update bus location and broadcast to subscribers"""
        try:
            # Update bus location in database
            update_data = {
                "current_location.latitude": latitude,
                "current_location.longitude": longitude,
                "last_location_update": datetime.now(timezone.utc)
            }
            
            if heading is not None:
                update_data["heading"] = heading
            if speed is not None:
                update_data["speed"] = speed
            
            if app_state and app_state.mongodb:
                await app_state.mongodb.buses.update_one(
                    {"id": bus_id},
                    {"$set": update_data}
                )
            
            # Broadcast location update to subscribers
            room_id = f"bus_tracking:{bus_id}"
            message = {
                "type": "bus_location_update",
                "bus_id": str(bus_id),
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "heading": heading,
                "speed": speed,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Convert to WebSocket message format
            ws_message = {
                "type": "bus_location_update",
                **message
            }

            await websocket_manager.send_room_message(room_id, ws_message)

            # Also broadcast to route subscribers if bus is on a route
            if app_state and app_state.mongodb:
                bus = await app_state.mongodb.buses.find_one({"id": bus_id})
                if bus and bus.get("assigned_route_id"):
                    route_room_id = f"route_tracking:{bus['assigned_route_id']}"
                    await websocket_manager.send_room_message(route_room_id, ws_message)
            
            logger.debug(f"Updated location for bus {bus_id}")
            
        except Exception as e:
            logger.error(f"Error updating bus location for {bus_id}: {e}")
    
    @staticmethod
    async def subscribe_to_bus(user_id: str, bus_id: str):
        """Subscribe user to bus tracking updates"""
        room_id = f"bus_tracking:{bus_id}"
        await websocket_manager.join_room_user(user_id, room_id)

        # Send initial location if available
        message = {
            "type": "bus_tracking_subscribed",
            "bus_id": str(bus_id),
            "room_id": room_id,
            "message": f"Subscribed to bus {bus_id} tracking"
        }

        await websocket_manager.send_personal_message(user_id, message)
        logger.info(f"User {user_id} subscribed to bus {bus_id} tracking")
    
    @staticmethod
    async def subscribe_to_route(user_id: str, route_id: str):
        """Subscribe user to all buses on a route"""
        room_id = f"route_tracking:{route_id}"
        await websocket_manager.join_room_user(user_id, room_id)

        message = {
            "type": "route_tracking_subscribed",
            "route_id": str(route_id),
            "room_id": room_id,
            "message": f"Subscribed to route {route_id} tracking"
        }

        await websocket_manager.send_personal_message(user_id, message)
        logger.info(f"User {user_id} subscribed to route {route_id} tracking")
    
    @staticmethod
    async def unsubscribe_from_bus(user_id: str, bus_id: str):
        """Unsubscribe user from bus tracking"""
        room_id = f"bus_tracking:{bus_id}"
        await websocket_manager.leave_room_user(user_id, room_id)
        logger.info(f"User {user_id} unsubscribed from bus {bus_id} tracking")

    @staticmethod
    async def unsubscribe_from_route(user_id: str, route_id: str):
        """Unsubscribe user from route tracking"""
        room_id = f"route_tracking:{route_id}"
        await websocket_manager.leave_room_user(user_id, room_id)
        logger.info(f"User {user_id} unsubscribed from route {route_id} tracking")

    @staticmethod
    async def broadcast_all_bus_locations(app_state=None):
        """Broadcast all active bus locations for map display"""
        try:
            if not app_state or not app_state.mongodb:
                return

            # Get all active buses with their current locations
            buses = await app_state.mongodb.buses.find({
                "status": "ACTIVE",
                "current_location": {"$exists": True}
            }).to_list(length=None)

            bus_locations = []
            for bus in buses:
                location = bus.get("current_location")
                if location and location.get("latitude") and location.get("longitude"):
                    bus_data = {
                        "bus_id": bus["id"],
                        "license_plate": bus.get("license_plate"),
                        "location": {
                            "latitude": location["latitude"],
                            "longitude": location["longitude"]
                        },
                        "heading": bus.get("heading"),
                        "speed": bus.get("speed"),
                        "route_id": bus.get("assigned_route_id"),
                        "last_update": bus.get("last_location_update"),
                        "status": bus.get("status", "ACTIVE")
                    }
                    bus_locations.append(bus_data)

            # Broadcast to all users subscribed to general bus tracking
            message = {
                "type": "all_bus_locations",
                "buses": bus_locations,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Convert to WebSocket message format
            ws_message = {
                "type": "all_bus_locations",
                **message
            }
            await websocket_manager.broadcast_message(ws_message)
            logger.debug(f"Broadcasted {len(bus_locations)} bus locations")

        except Exception as e:
            logger.error(f"Error broadcasting all bus locations: {e}")

    @staticmethod
    async def get_route_shape_with_buses(route_id: str, app_state=None) -> Optional[Dict[str, Any]]:
        """Get route shape with current bus positions for Mapbox display"""
        try:
            if not app_state or not app_state.mongodb:
                return None

            # Get route details
            route = await app_state.mongodb.routes.find_one({"id": route_id})
            if not route:
                return None

            # Get buses on this route
            buses = await app_state.mongodb.buses.find({
                "assigned_route_id": route_id,
                "status": "ACTIVE",
                "current_location": {"$exists": True}
            }).to_list(length=None)

            bus_positions = []
            for bus in buses:
                location = bus.get("current_location")
                if location and location.get("latitude") and location.get("longitude"):
                    bus_positions.append({
                        "bus_id": bus["id"],
                        "license_plate": bus.get("license_plate"),
                        "location": {
                            "latitude": location["latitude"],
                            "longitude": location["longitude"]
                        },
                        "heading": bus.get("heading"),
                        "speed": bus.get("speed")
                    })

            route_data = {
                "route_id": route_id,
                "route_name": route.get("name"),
                "route_shape": route.get("route_shape"),  # GeoJSON for Mapbox
                "start_location": route.get("start_location"),
                "end_location": route.get("end_location"),
                "bus_stops": route.get("bus_stops", []),
                "active_buses": bus_positions,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            return route_data

        except Exception as e:
            logger.error(f"Error getting route shape with buses for route {route_id}: {e}")
            return None

    @staticmethod
    async def calculate_eta_for_bus(bus_id: str, target_stop_id: str, app_state=None) -> Optional[Dict[str, Any]]:
        """Calculate ETA for a bus to reach a specific stop"""
        try:
            if not app_state or not app_state.mongodb:
                return None

            # Get bus details
            bus = await app_state.mongodb.buses.find_one({"id": bus_id})
            if not bus or not bus.get("current_location"):
                return None

            # Get target bus stop
            bus_stop = await app_state.mongodb.bus_stops.find_one({"id": target_stop_id})
            if not bus_stop or not bus_stop.get("location"):
                return None

            # Get route information if bus is on a route
            route_id = bus.get("assigned_route_id")
            if not route_id:
                return None

            route = await app_state.mongodb.routes.find_one({"id": route_id})
            if not route:
                return None

            # Simple distance-based ETA calculation
            # In a real implementation, you'd use route service with traffic data
            bus_location = bus["current_location"]
            stop_location = bus_stop["location"]

            # Calculate straight-line distance
            distance_km = BusTrackingService._calculate_distance(
                bus_location["latitude"], bus_location["longitude"],
                stop_location["latitude"], stop_location["longitude"]
            ) / 1000

            # Estimate speed (use current speed or default to 30 km/h in city)
            current_speed = bus.get("speed", 30)  # km/h
            if current_speed < 5:  # If bus is stopped or moving very slowly
                current_speed = 25  # Use average city speed

            # Calculate ETA in minutes
            eta_minutes = max(1, round((distance_km / current_speed) * 60))

            eta_data = {
                "bus_id": bus_id,
                "target_stop_id": target_stop_id,
                "eta_minutes": eta_minutes,
                "distance_km": round(distance_km, 2),
                "current_speed_kmh": current_speed,
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }

            return eta_data

        except Exception as e:
            logger.error(f"Error calculating ETA for bus {bus_id} to stop {target_stop_id}: {e}")
            return None

    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        import math

        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in meters
        r = 6371000
        return c * r


# Global bus tracking service instance
bus_tracking_service = BusTrackingService()
