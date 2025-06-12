"""
Comprehensive WebSocket event handlers for GuzoSync real-time features
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from core.websocket_manager import websocket_manager
from core.realtime.bus_tracking import bus_tracking_service
from core.realtime.chat import chat_service
from core.realtime.notifications import notification_service
from core.logger import get_logger
from models.base import Location
from core.mongo_utils import model_to_mongo_doc

logger = get_logger(__name__)


class WebSocketEventHandlers:
    """Centralized WebSocket event handlers for all real-time features"""
    
    @staticmethod
    async def handle_message(user_id: str, message_type: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Handle incoming WebSocket messages by routing to appropriate handlers"""

        # Log incoming message
        logger.info(f"📨 RECEIVED WebSocket Event: {message_type} from user {user_id}")
        logger.debug(f"📨 Event Data: {data}")

        try:
            result = None

            if message_type == "subscribe_all_buses":
                result = await WebSocketEventHandlers.handle_subscribe_all_buses(user_id, data, app_state)
            elif message_type == "get_route_with_buses":
                route_id = data.get("route_id")
                if not route_id:
                    result = {"success": False, "error": "Route ID required"}
                else:
                    result = await WebSocketEventHandlers.handle_get_route_with_buses(user_id, route_id, app_state)
            elif message_type == "calculate_eta":
                bus_id = data.get("bus_id")
                stop_id = data.get("stop_id")
                if not bus_id or not stop_id:
                    result = {"success": False, "error": "Bus ID and Stop ID required"}
                else:
                    result = await WebSocketEventHandlers.handle_calculate_eta(user_id, bus_id, stop_id, app_state)
            elif message_type == "bus_location_update":
                result = await WebSocketEventHandlers.handle_bus_location_update(user_id, data, app_state)
            elif message_type == "passenger_location_update":
                result = await WebSocketEventHandlers.handle_passenger_location_update(user_id, data, app_state)
            elif message_type == "subscribe_proximity_alerts":
                result = await WebSocketEventHandlers.handle_subscribe_proximity_alerts(user_id, data, app_state)
            elif message_type == "toggle_location_sharing":
                result = await WebSocketEventHandlers.handle_toggle_location_sharing(user_id, data, app_state)
            elif message_type == "admin_broadcast":
                result = await WebSocketEventHandlers.handle_admin_broadcast(user_id, data, app_state)
            elif message_type == "emergency_alert":
                result = await WebSocketEventHandlers.handle_emergency_alert(user_id, data, app_state)
            elif message_type == "join_conversation":
                conversation_id = data.get("conversation_id")
                if not conversation_id:
                    result = {"success": False, "error": "Conversation ID required"}
                else:
                    result = await WebSocketEventHandlers.handle_join_conversation_room(user_id, conversation_id, app_state)
            elif message_type == "typing_indicator":
                conversation_id = data.get("conversation_id")
                is_typing = data.get("is_typing", False)
                if not conversation_id:
                    result = {"success": False, "error": "Conversation ID required"}
                else:
                    result = await WebSocketEventHandlers.handle_typing_indicator(user_id, conversation_id, is_typing)
            elif message_type == "mark_message_read":
                conversation_id = data.get("conversation_id")
                message_id = data.get("message_id")
                if not conversation_id or not message_id:
                    result = {"success": False, "error": "Conversation ID and Message ID required"}
                else:
                    result = await WebSocketEventHandlers.handle_mark_message_read(user_id, conversation_id, message_id)
            else:
                logger.warning(f"❓ Unknown WebSocket message type: {message_type} from user {user_id}")
                result = {"success": False, "error": f"Unknown message type: {message_type}"}

            # Log response
            if result.get("success", True):
                logger.info(f"✅ WebSocket Event {message_type} handled successfully for user {user_id}")
            else:
                logger.warning(f"❌ WebSocket Event {message_type} failed for user {user_id}: {result.get('error', 'Unknown error')}")

            logger.debug(f"📤 Event Response: {result}")
            return result

        except Exception as e:
            logger.error(f"💥 Error handling WebSocket message type {message_type} from user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_subscribe_all_buses(user_id: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Subscribe user to all bus location updates"""
        try:
            logger.info(f"🚌 Processing subscribe_all_buses request from user {user_id}")

            # Join global bus tracking room
            room_id = "all_bus_tracking"
            success = await websocket_manager.join_room_user(user_id, room_id)

            if success:
                logger.info(f"✅ User {user_id} successfully joined {room_id} room")

                # Send initial bus locations
                logger.info(f"📡 Sending initial bus locations to user {user_id}")
                await bus_tracking_service.broadcast_all_bus_locations(app_state)

                return {
                    "success": True,
                    "message": "Subscribed to all bus tracking",
                    "room_id": room_id
                }
            else:
                logger.error(f"❌ Failed to join user {user_id} to {room_id} room")
                return {"success": False, "error": "Failed to join bus tracking room"}

        except Exception as e:
            logger.error(f"Error subscribing user {user_id} to all buses: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_get_route_with_buses(user_id: str, route_id: str, app_state=None) -> Dict[str, Any]:
        """Get route shape with current bus positions for Mapbox"""
        try:
            route_data = await bus_tracking_service.get_route_shape_with_buses(route_id, app_state)
            if route_data:
                return {
                    "success": True,
                    "route_data": route_data
                }
            else:
                return {"success": False, "error": "Route not found or no data available"}
        except Exception as e:
            logger.error(f"Error getting route data for user {user_id}, route {route_id}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_calculate_eta(user_id: str, bus_id: str, stop_id: str, app_state=None) -> Dict[str, Any]:
        """Calculate ETA for bus to reach specific stop"""
        try:
            eta_data = await bus_tracking_service.calculate_eta_for_bus(bus_id, stop_id, app_state)
            if eta_data:
                return {
                    "success": True,
                    "eta_data": eta_data
                }
            else:
                return {"success": False, "error": "ETA calculation failed"}
        except Exception as e:
            logger.error(f"Error calculating ETA for user {user_id}, bus {bus_id}, stop {stop_id}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def handle_bus_location_update(user_id: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Handle bus location updates from drivers and broadcast to all subscribers"""
        try:
            logger.info(f"🚌 Processing bus location update from driver {user_id}")

            # Verify user is a bus driver
            if app_state is not None and app_state.mongodb is not None:
                user = await app_state.mongodb.users.find_one({"id": user_id})
                if not user or user.get("role") != "BUS_DRIVER":
                    logger.warning(f"❌ Non-driver user {user_id} attempted bus location update")
                    return {"success": False, "error": "Only bus drivers can update bus locations"}

            # Extract location data
            bus_id = data.get("bus_id")
            latitude = data.get("latitude")
            longitude = data.get("longitude")   
            heading = data.get("heading")
            speed = data.get("speed")

            logger.info(f"🚌 Bus {bus_id} location: {latitude}, {longitude} (heading: {heading}°, speed: {speed} km/h)")

            if not bus_id or latitude is None or longitude is None:
                logger.warning(f"❌ Missing required location data from driver {user_id}")
                return {"success": False, "error": "Bus ID, latitude, and longitude are required"}

            # Verify driver is assigned to this bus
            if app_state is not None and app_state.mongodb is not None:
                bus = await app_state.mongodb.buses.find_one({"id": bus_id})
                if not bus:
                    logger.warning(f"❌ Bus {bus_id} not found for driver {user_id}")
                    return {"success": False, "error": "Bus not found"}
                if bus.get("assigned_driver_id") != user_id:
                    logger.warning(f"❌ Driver {user_id} not assigned to bus {bus_id}")
                    return {"success": False, "error": "Driver not assigned to this bus"}

            # Update bus location and broadcast to all subscribers
            logger.info(f"🚌 Updating bus {bus_id} location in database and broadcasting...")
            await bus_tracking_service.update_bus_location(
                bus_id=bus_id,
                latitude=float(latitude),
                longitude=float(longitude),
                heading=float(heading) if heading is not None else None,
                speed=float(speed) if speed is not None else None,
                app_state=app_state
            )

            # Check for proximity alerts and notify passengers
            logger.info(f"🔔 Checking proximity notifications for bus {bus_id}...")
            await bus_tracking_service.check_proximity_notifications(
                bus_id=bus_id,
                latitude=float(latitude),
                longitude=float(longitude),
                app_state=app_state
            )

            logger.info(f"✅ Bus {bus_id} location successfully updated by driver {user_id}")

            return {
                "success": True,
                "message": "Location updated successfully",
                "bus_id": bus_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error handling bus location update from user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def handle_passenger_location_update(user_id: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Handle passenger location updates for proximity notifications"""
        try:
            logger.info(f"👤 Processing passenger location update from {user_id}")

            # Verify user is a passenger
            if app_state is not None and app_state.mongodb is not None:
                user = await app_state.mongodb.users.find_one({"id": user_id})
                if not user or user.get("role") != "PASSENGER":
                    logger.warning(f"❌ Non-passenger user {user_id} attempted location update")
                    return {"success": False, "error": "Only passengers can update their location"}

                # Check if location sharing is enabled
                if not user.get("location_sharing_enabled", False):
                    logger.warning(f"❌ Passenger {user_id} has location sharing disabled")
                    return {"success": False, "error": "Location sharing is disabled. Enable it in settings to receive proximity alerts."}

            # Extract location data
            latitude = data.get("latitude")
            longitude = data.get("longitude")

            logger.info(f"👤 Passenger {user_id} location: {latitude}, {longitude}")

            if latitude is None or longitude is None:
                logger.warning(f"❌ Missing location coordinates from passenger {user_id}")
                return {"success": False, "error": "Latitude and longitude are required"}

            # Update passenger location in database
            if app_state is not None and app_state.mongodb is not None:
                # Create Location model instance
                location = Location(
                    latitude=float(latitude),
                    longitude=float(longitude)
                )

                # Convert to MongoDB document format
                location_doc = model_to_mongo_doc(location)

                update_data = {
                    "current_location": location_doc,
                    "last_location_update": datetime.now(timezone.utc)
                }

                logger.debug(f"👤 Updating passenger {user_id} location in database...")
                await app_state.mongodb.users.update_one(
                    {"id": user_id},
                    {"$set": update_data}
                )

            logger.info(f"✅ Passenger {user_id} location successfully updated")

            return {
                "success": True,
                "message": "Location updated successfully",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error handling passenger location update from user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def handle_toggle_location_sharing(user_id: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Toggle location sharing for passengers to enable/disable proximity notifications"""
        try:
            # Verify user is a passenger
            if app_state is not None and app_state.mongodb is not None:
                user = await app_state.mongodb.users.find_one({"id": user_id})
                if not user or user.get("role") != "PASSENGER":
                    return {"success": False, "error": "Only passengers can toggle location sharing"}

            # Get the desired state
            enabled = data.get("enabled", True)

            # Update location sharing setting
            if app_state is not None and app_state.mongodb is not None:
                await app_state.mongodb.users.update_one(
                    {"id": user_id},
                    {"$set": {"location_sharing_enabled": bool(enabled)}}
                )

            status = "enabled" if enabled else "disabled"
            logger.info(f"Location sharing {status} for passenger {user_id}")

            return {
                "success": True,
                "message": f"Location sharing {status}",
                "location_sharing_enabled": bool(enabled)
            }

        except Exception as e:
            logger.error(f"Error toggling location sharing for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def handle_subscribe_proximity_alerts(user_id: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Subscribe passenger to proximity alerts for specific bus stops"""
        try:
            # Verify user is a passenger
            if app_state is not None and app_state.mongodb is not None:
                user = await app_state.mongodb.users.find_one({"id": user_id})
                if not user or user.get("role") != "PASSENGER":
                    return {"success": False, "error": "Only passengers can subscribe to proximity alerts"}

            bus_stop_ids = data.get("bus_stop_ids", [])
            radius_meters = data.get("radius_meters", 500)  # Default 500m threshold

            if not bus_stop_ids:
                return {"success": False, "error": "At least one bus stop ID is required"}

            # Validate bus stops exist
            if app_state is not None and app_state.mongodb is not None:
                existing_stops = await app_state.mongodb.bus_stops.find(
                    {"id": {"$in": bus_stop_ids}, "is_active": True}
                ).to_list(length=None)

                if len(existing_stops) != len(bus_stop_ids):
                    return {"success": False, "error": "One or more bus stops not found or inactive"}

            # Subscribe user to proximity alert rooms for each bus stop
            subscribed_stops = []
            for stop_id in bus_stop_ids:
                room_id = f"proximity_alerts:{stop_id}"
                success = await websocket_manager.join_room_user(user_id, room_id)
                if success:
                    subscribed_stops.append(stop_id)

            logger.info(f"User {user_id} subscribed to proximity alerts for {len(subscribed_stops)} bus stops")

            return {
                "success": True,
                "message": f"Subscribed to proximity alerts for {len(subscribed_stops)} bus stops",
                "subscribed_stops": subscribed_stops,
                "radius_meters": radius_meters
            }

        except Exception as e:
            logger.error(f"Error subscribing user {user_id} to proximity alerts: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_admin_broadcast(user_id: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Handle admin/control staff broadcasting messages to drivers/regulators"""
        try:
            # Verify user has admin/control staff permissions
            if app_state is not None and app_state.mongodb is not None:
                user = await app_state.mongodb.users.find_one({"id": user_id})
                if not user or user.get("role") not in ["ADMIN", "CONTROL_STAFF"]:
                    return {"success": False, "error": "Insufficient permissions"}
            
            message = data.get("message", "")
            target_roles = data.get("target_roles", ["BUS_DRIVER", "QUEUE_REGULATOR"])
            priority = data.get("priority", "NORMAL")
            
            if not message:
                return {"success": False, "error": "Message content required"}
            
            # Create notification
            notification = {
                "id": str(datetime.now().timestamp()),
                "type": "ADMIN_BROADCAST",
                "title": "Admin Broadcast",
                "message": message,
                "priority": priority,
                "sender_id": user_id,
                "target_roles": target_roles,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to all users with target roles
            await notification_service.broadcast_notification(
                title=notification["title"],
                message=notification["message"],
                notification_type=notification["type"],
                target_roles=target_roles,
                app_state=app_state
            )
            
            return {
                "success": True,
                "message": "Broadcast sent successfully",
                "notification_id": notification["id"]
            }
        except Exception as e:
            logger.error(f"Error handling admin broadcast from user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_emergency_alert(user_id: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Handle emergency alerts from drivers/regulators"""
        try:
            # Verify user has appropriate role
            if app_state is not None and app_state.mongodb is not None:
                user = await app_state.mongodb.users.find_one({"id": user_id})
                if not user or user.get("role") not in ["BUS_DRIVER", "QUEUE_REGULATOR", "ADMIN", "CONTROL_STAFF"]:
                    return {"success": False, "error": "Insufficient permissions"}
            
            alert_type = data.get("alert_type", "GENERAL")
            message = data.get("message", "")
            location = data.get("location")  # Optional GPS coordinates
            
            if not message:
                return {"success": False, "error": "Alert message required"}
            
            # Create emergency alert
            alert = {
                "id": str(datetime.now().timestamp()),
                "type": "EMERGENCY_ALERT",
                "alert_type": alert_type,
                "title": f"Emergency Alert - {alert_type}",
                "message": message,
                "location": location,
                "sender_id": user_id,
                "priority": "HIGH",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to control staff and admins
            await notification_service.broadcast_notification(
                title=alert["title"],
                message=alert["message"],
                notification_type=alert["type"],
                target_roles=["ADMIN", "CONTROL_STAFF"],
                app_state=app_state
            )
            
            # Also broadcast to emergency response room
            await websocket_manager.send_room_message(
                "emergency_alerts",
                {
                    "type": "emergency_alert",
                    **alert
                }
            )
            
            return {
                "success": True,
                "message": "Emergency alert sent successfully",
                "alert_id": alert["id"]
            }
        except Exception as e:
            logger.error(f"Error handling emergency alert from user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_join_conversation_room(user_id: str, conversation_id: str, app_state=None) -> Dict[str, Any]:
        """Join user to a conversation room for real-time messaging"""
        try:
            success = await chat_service.join_conversation(user_id, conversation_id, app_state)
            if success:
                return {
                    "success": True,
                    "message": f"Joined conversation {conversation_id}",
                    "conversation_id": conversation_id
                }
            else:
                return {"success": False, "error": "Failed to join conversation"}
        except Exception as e:
            logger.error(f"Error joining conversation for user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_typing_indicator(user_id: str, conversation_id: str, is_typing: bool) -> Dict[str, Any]:
        """Handle typing indicators in conversations"""
        try:
            await chat_service.notify_typing(conversation_id, user_id, is_typing)
            return {"success": True}
        except Exception as e:
            logger.error(f"Error handling typing indicator for user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_mark_message_read(user_id: str, conversation_id: str, message_id: str) -> Dict[str, Any]:
        """Mark message as read and notify other participants"""
        try:
            await chat_service.notify_message_read(conversation_id, user_id, message_id)
            return {"success": True}
        except Exception as e:
            logger.error(f"Error marking message as read for user {user_id}: {e}")
            return {"success": False, "error": str(e)}


# Global event handlers instance
websocket_event_handlers = WebSocketEventHandlers()
