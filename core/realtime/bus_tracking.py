"""
Real-time bus tracking service with enhanced Mapbox integration
"""
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from core.websocket_manager import websocket_manager
from core.logger import get_logger
from models.base import Location
from core.mongo_utils import model_to_mongo_doc
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
            logger.info(f"🚌 Updating bus {bus_id} location: {latitude}, {longitude}")

            # Update bus location in database
            # Create Location model instance
            location = Location(
                latitude=latitude,
                longitude=longitude
            )

            # Convert to MongoDB document format
            location_doc = model_to_mongo_doc(location)

            update_data = {
                "current_location": location_doc,
                "last_location_update": datetime.now(timezone.utc)
            }

            if heading is not None:
                update_data["heading"] = heading
            if speed is not None:
                update_data["speed"] = speed

            if app_state is not None and app_state.mongodb is not None:
                await app_state.mongodb.buses.update_one(
                    {"id": bus_id},
                    {"$set": update_data}
                )
                logger.debug(f"🚌 Bus {bus_id} location updated in database")
            
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

            logger.info(f"📡 Broadcasting bus {bus_id} location to room {room_id}")
            await websocket_manager.send_room_message(room_id, ws_message)

            # Also broadcast to global bus tracking room (all subscribers)
            global_room_id = "all_bus_tracking"
            logger.debug(f"📡 Broadcasting bus {bus_id} location to global room {global_room_id}")
            await websocket_manager.send_room_message(global_room_id, ws_message)

            # Also broadcast to route subscribers if bus is on a route
            if app_state is not None and app_state.mongodb is not None:
                bus = await app_state.mongodb.buses.find_one({"id": bus_id})
                if bus and bus.get("assigned_route_id"):
                    route_room_id = f"route_tracking:{bus['assigned_route_id']}"
                    logger.info(f"📡 Broadcasting bus {bus_id} location to route room {route_room_id}")
                    await websocket_manager.send_room_message(route_room_id, ws_message)

            logger.info(f"✅ Bus {bus_id} location broadcast completed")
            
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
            if app_state is None or app_state.mongodb is None:
                return

            # Get all buses and filter manually (more reliable than complex MongoDB queries)
            all_buses = await app_state.mongodb.buses.find({}).to_list(length=None)

            bus_locations = []
            for bus in all_buses:
                # Check if bus is trackable (exclude only BREAKDOWN status)
                bus_status = bus.get("bus_status")
                if bus_status == "BREAKDOWN":
                    continue

                # Check if bus has valid location
                location = bus.get("current_location")
                if (location is None or
                    not isinstance(location, dict) or
                    not location.get("latitude") or
                    not location.get("longitude")):
                    continue

                # Bus meets criteria - add to broadcast list
                last_update = bus.get("last_location_update")
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
                    "last_update": last_update.isoformat() if last_update else None,
                    "status": bus.get("bus_status", "OPERATIONAL")
                }
                bus_locations.append(bus_data)

            # Broadcast to users subscribed to all bus tracking room
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

            # Send to the specific room that clients join when they subscribe_all_buses
            room_id = "all_bus_tracking"

            # Check if room has subscribers before broadcasting
            from core.websocket_manager import websocket_manager
            room_size = len(websocket_manager.rooms.get(room_id, set()))

            if room_size > 0:
                await websocket_manager.send_room_message(room_id, ws_message)
                logger.info(f"📡 Broadcasted {len(bus_locations)} bus locations to {room_size} subscribers in {room_id} room")
            else:
                logger.debug(f"📡 No subscribers in {room_id} room, skipping broadcast of {len(bus_locations)} bus locations")

        except Exception as e:
            logger.error(f"Error broadcasting all bus locations: {e}")

    @staticmethod
    async def get_route_shape_with_buses(route_id: str, app_state=None) -> Optional[Dict[str, Any]]:
        """Get route shape with current bus positions for Mapbox display"""
        try:
            if app_state is None or app_state.mongodb is None:
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
            logger.info(f"🧮 Starting ETA calculation for bus {bus_id} to stop {target_stop_id}")

            if app_state is None or app_state.mongodb is None:
                logger.error("❌ No app_state or mongodb available for ETA calculation")
                return None

            # Get bus details
            bus = await app_state.mongodb.buses.find_one({"id": bus_id})
            if not bus:
                logger.error(f"❌ Bus {bus_id} not found in database")
                return None

            if not bus.get("current_location"):
                logger.error(f"❌ Bus {bus_id} has no current_location set")
                return None

            logger.info(f"✅ Found bus {bus_id} with location: {bus.get('current_location')}")

            # Get target bus stop
            bus_stop = await app_state.mongodb.bus_stops.find_one({"id": target_stop_id})
            if not bus_stop:
                logger.error(f"❌ Bus stop {target_stop_id} not found in database")
                return None

            if not bus_stop.get("location"):
                logger.error(f"❌ Bus stop {target_stop_id} has no location set")
                return None

            logger.info(f"✅ Found bus stop {target_stop_id}: {bus_stop.get('name')} at {bus_stop.get('location')}")

            # Get route information if bus is on a route
            route_id = bus.get("assigned_route_id")
            if not route_id:
                logger.warning(f"⚠️ Bus {bus_id} has no assigned_route_id - using direct distance calculation")
                # Continue without route - we can still calculate direct distance
            else:
                route = await app_state.mongodb.routes.find_one({"id": route_id})
                if not route:
                    logger.warning(f"⚠️ Route {route_id} not found - using direct distance calculation")
                else:
                    logger.info(f"✅ Found route {route_id}: {route.get('name')}")

            # Simple distance-based ETA calculation
            # In a real implementation, you'd use route service with traffic data
            bus_location = bus["current_location"]
            stop_location = bus_stop["location"]

            logger.info(f"🧮 Calculating distance from bus at ({bus_location['latitude']}, {bus_location['longitude']}) to stop at ({stop_location['latitude']}, {stop_location['longitude']})")

            # Calculate straight-line distance
            distance_km = BusTrackingService._calculate_distance(
                bus_location["latitude"], bus_location["longitude"],
                stop_location["latitude"], stop_location["longitude"]
            ) / 1000

            logger.info(f"📏 Distance calculated: {distance_km:.2f} km")

            # Estimate speed (use current speed or default to 30 km/h in city)
            current_speed = bus.get("speed", 30)  # km/h
            if current_speed < 5:  # If bus is stopped or moving very slowly
                current_speed = 25  # Use average city speed

            logger.info(f"🚗 Using speed: {current_speed} km/h")

            # Calculate ETA in minutes
            eta_minutes = max(1, round((distance_km / current_speed) * 60))

            logger.info(f"⏰ Calculated ETA: {eta_minutes} minutes")

            eta_data = {
                "bus_id": bus_id,
                "target_stop_id": target_stop_id,
                "eta_minutes": eta_minutes,
                "distance_km": round(distance_km, 2),
                "current_speed_kmh": current_speed,
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"✅ ETA calculation completed successfully: {eta_data}")
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

    @staticmethod
    async def check_proximity_notifications(
        bus_id: str,
        latitude: float,
        longitude: float,
        app_state=None
    ):
        """Check for passengers within 500m of bus stops when bus approaches and notify them"""
        try:
            logger.info(f"🔔 Checking proximity notifications for bus {bus_id} at {latitude}, {longitude}")

            if app_state is None or app_state.mongodb is None:
                logger.warning("❌ No app_state or mongodb available for proximity checks")
                return

            # Get all active bus stops
            bus_stops = await app_state.mongodb.bus_stops.find({
                "is_active": True
            }).to_list(length=None)

            logger.info(f"🔔 Found {len(bus_stops)} active bus stops to check")
            proximity_threshold = 500  # 500 meters as requested
            nearby_stops = 0

            for bus_stop in bus_stops:
                stop_location = bus_stop.get("location")
                if not stop_location:
                    continue

                # Calculate distance between bus and bus stop
                bus_to_stop_distance = BusTrackingService._calculate_distance(
                    latitude, longitude,
                    stop_location["latitude"], stop_location["longitude"]
                )

                # If bus is approaching this bus stop (within 500m), find passengers near this stop
                if bus_to_stop_distance <= proximity_threshold:
                    nearby_stops += 1
                    stop_name = bus_stop.get("name", "Unknown Stop")
                    logger.info(f"🔔 Bus {bus_id} is {bus_to_stop_distance:.1f}m from stop '{stop_name}' - checking for nearby passengers")

                    await BusTrackingService._notify_passengers_near_bus_stop(
                        bus_id=bus_id,
                        bus_stop=bus_stop,
                        bus_to_stop_distance=bus_to_stop_distance,
                        bus_latitude=latitude,
                        bus_longitude=longitude,
                        app_state=app_state
                    )

            if nearby_stops == 0:
                logger.debug(f"🔔 Bus {bus_id} is not near any bus stops (>500m)")
            else:
                logger.info(f"🔔 Proximity check completed for bus {bus_id}: {nearby_stops} nearby stops")

        except Exception as e:
            logger.error(f"💥 Error checking proximity notifications for bus {bus_id}: {e}")

    @staticmethod
    async def _notify_passengers_near_bus_stop(
        bus_id: str,
        bus_stop: dict,
        bus_to_stop_distance: float,
        bus_latitude: float,
        bus_longitude: float,
        app_state=None
    ):
        """Find passengers within 500m of bus stop and notify them about approaching bus"""
        try:
            bus_stop_id = bus_stop["id"]
            bus_stop_name = bus_stop.get("name", "Unknown Stop")
            stop_location = bus_stop.get("location")

            logger.info(f"👥 Checking passengers near bus stop '{bus_stop_name}' for bus {bus_id}")

            if not stop_location:
                logger.warning(f"❌ Bus stop '{bus_stop_name}' has no location data")
                return

            # Get all passengers with location sharing enabled and current location
            if app_state is None or app_state.mongodb is None:
                logger.warning("❌ No app_state or mongodb available for passenger lookup")
                return

            passengers = await app_state.mongodb.users.find({
                "role": "PASSENGER",
                "location_sharing_enabled": True,
                "current_location": {"$exists": True, "$ne": None}
            }).to_list(length=None)

            logger.info(f"👥 Found {len(passengers)} passengers with location sharing enabled")

            proximity_threshold = 500  # 500 meters for passenger-to-bus-stop distance
            notified_passengers = []

            # Check each passenger's distance to this bus stop
            for passenger in passengers:
                passenger_location = passenger.get("current_location")
                if not passenger_location:
                    continue

                # Calculate distance between passenger and bus stop
                passenger_to_stop_distance = BusTrackingService._calculate_distance(
                    passenger_location["latitude"], passenger_location["longitude"],
                    stop_location["latitude"], stop_location["longitude"]
                )

                logger.debug(f"👤 Passenger {passenger['id']} is {passenger_to_stop_distance:.1f}m from stop '{bus_stop_name}'")

                # If passenger is within 500m of the bus stop, notify them
                if passenger_to_stop_distance <= proximity_threshold:
                    logger.info(f"🔔 Notifying passenger {passenger['id']} - within {passenger_to_stop_distance:.1f}m of stop '{bus_stop_name}'")

                    await BusTrackingService._send_passenger_proximity_notification(
                        passenger_id=passenger["id"],
                        bus_id=bus_id,
                        bus_stop=bus_stop,
                        bus_to_stop_distance=bus_to_stop_distance,
                        passenger_to_stop_distance=passenger_to_stop_distance,
                        app_state=app_state
                    )
                    notified_passengers.append(passenger["id"])

            if len(notified_passengers) > 0:
                logger.info(f"✅ Notified {len(notified_passengers)} passengers near bus stop '{bus_stop_name}' about approaching bus {bus_id}")
            else:
                logger.debug(f"👥 No passengers within 500m of bus stop '{bus_stop_name}'")

        except Exception as e:
            logger.error(f"💥 Error notifying passengers near bus stop for bus {bus_id}: {e}")

    @staticmethod
    async def _send_passenger_proximity_notification(
        passenger_id: str,
        bus_id: str,
        bus_stop: dict,
        bus_to_stop_distance: float,
        passenger_to_stop_distance: float,
        app_state=None
    ):
        """Send proximity notification to a specific passenger"""
        try:
            from core.realtime.notifications import notification_service

            bus_stop_id = bus_stop["id"]
            bus_stop_name = bus_stop.get("name", "Unknown Stop")

            logger.info(f"📤 Sending proximity alert to passenger {passenger_id} for bus {bus_id} approaching '{bus_stop_name}'")

            # Calculate estimated arrival time based on bus distance to stop
            # Assume average city speed of 25 km/h when approaching stops
            estimated_arrival_minutes = max(1, round((bus_to_stop_distance / 1000) / 25 * 60))

            # Get bus information for notification
            bus_info = None
            if app_state is not None and app_state.mongodb is not None:
                bus = await app_state.mongodb.buses.find_one({"id": bus_id})
                if bus:
                    bus_info = {
                        "license_plate": bus.get("license_plate", "Unknown"),
                        "route_id": bus.get("assigned_route_id")
                    }

            # Create proximity alert message for WebSocket
            proximity_message = {
                "type": "proximity_alert",
                "bus_id": bus_id,
                "bus_stop_id": bus_stop_id,
                "bus_stop_name": bus_stop_name,
                "bus_distance_to_stop_meters": round(bus_to_stop_distance, 1),
                "passenger_distance_to_stop_meters": round(passenger_to_stop_distance, 1),
                "estimated_arrival_minutes": estimated_arrival_minutes,
                "bus_info": bus_info,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Send WebSocket message to passenger
            logger.info(f"📤 Sending WebSocket proximity alert to passenger {passenger_id}")
            await websocket_manager.send_personal_message(passenger_id, proximity_message)

            # Also send database notification
            notification_title = f"Bus Approaching {bus_stop_name}"
            bus_identifier = bus_info.get('license_plate', bus_id) if bus_info else bus_id
            notification_message = f"Bus {bus_identifier} is approaching {bus_stop_name} ({round(bus_to_stop_distance)}m away, ~{estimated_arrival_minutes} min). You are {round(passenger_to_stop_distance)}m from the stop."

            logger.info(f"📤 Saving proximity notification to database for passenger {passenger_id}")
            await notification_service.send_real_time_notification(
                user_id=passenger_id,
                title=notification_title,
                message=notification_message,
                notification_type="PROXIMITY_ALERT",
                related_entity={
                    "entity_type": "bus_proximity",
                    "entity_id": bus_id,
                    "bus_stop_id": bus_stop_id,
                    "bus_distance_meters": bus_to_stop_distance,
                    "passenger_distance_meters": passenger_to_stop_distance
                },
                app_state=app_state
            )

            logger.info(f"✅ Proximity notification sent successfully to passenger {passenger_id} for bus {bus_id}")

        except Exception as e:
            logger.error(f"💥 Error sending proximity notification to passenger {passenger_id}: {e}")


# Global bus tracking service instance
bus_tracking_service = BusTrackingService()
