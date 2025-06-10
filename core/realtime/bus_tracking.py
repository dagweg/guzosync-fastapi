"""
Real-time bus tracking service
"""
from datetime import datetime
from typing import Optional

from core.socketio_manager import socketio_manager
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
                "last_location_update": datetime.utcnow()
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
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await socketio_manager.send_room_message(room_id, "bus_location_update", message)

            # Also broadcast to route subscribers if bus is on a route
            if app_state and app_state.mongodb:
                bus = await app_state.mongodb.buses.find_one({"id": bus_id})
                if bus and bus.get("assigned_route_id"):
                    route_room_id = f"route_tracking:{bus['assigned_route_id']}"
                    await socketio_manager.send_room_message(route_room_id, "bus_location_update", message)
            
            logger.debug(f"Updated location for bus {bus_id}")
            
        except Exception as e:
            logger.error(f"Error updating bus location for {bus_id}: {e}")
    
    @staticmethod
    async def subscribe_to_bus(user_id: str, bus_id: str):
        """Subscribe user to bus tracking updates"""
        room_id = f"bus_tracking:{bus_id}"
        await socketio_manager.join_room_user(user_id, room_id)

        # Send initial location if available
        message = {
            "bus_id": str(bus_id),
            "room_id": room_id,
            "message": f"Subscribed to bus {bus_id} tracking"
        }

        await socketio_manager.send_personal_message(user_id, "bus_tracking_subscribed", message)
        logger.info(f"User {user_id} subscribed to bus {bus_id} tracking")
    
    @staticmethod
    async def subscribe_to_route(user_id: str, route_id: str):
        """Subscribe user to all buses on a route"""
        room_id = f"route_tracking:{route_id}"
        await socketio_manager.join_room_user(user_id, room_id)

        message = {
            "route_id": str(route_id),
            "room_id": room_id,
            "message": f"Subscribed to route {route_id} tracking"
        }

        await socketio_manager.send_personal_message(user_id, "route_tracking_subscribed", message)
        logger.info(f"User {user_id} subscribed to route {route_id} tracking")
    
    @staticmethod
    async def unsubscribe_from_bus(user_id: str, bus_id: str):
        """Unsubscribe user from bus tracking"""
        room_id = f"bus_tracking:{bus_id}"
        await socketio_manager.leave_room_user(user_id, room_id)
        logger.info(f"User {user_id} unsubscribed from bus {bus_id} tracking")

    @staticmethod
    async def unsubscribe_from_route(user_id: str, route_id: str):
        """Unsubscribe user from route tracking"""
        room_id = f"route_tracking:{route_id}"
        await socketio_manager.leave_room_user(user_id, room_id)
        logger.info(f"User {user_id} unsubscribed from route {route_id} tracking")


# Global bus tracking service instance
bus_tracking_service = BusTrackingService()
