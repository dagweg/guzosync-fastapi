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

logger = get_logger(__name__)


class WebSocketEventHandlers:
    """Centralized WebSocket event handlers for all real-time features"""
    
    @staticmethod
    async def handle_message(user_id: str, message_type: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Handle incoming WebSocket messages by routing to appropriate handlers"""
        try:
            if message_type == "subscribe_all_buses":
                return await WebSocketEventHandlers.handle_subscribe_all_buses(user_id, data, app_state)
            elif message_type == "get_route_with_buses":
                route_id = data.get("route_id")
                if not route_id:
                    return {"success": False, "error": "Route ID required"}
                return await WebSocketEventHandlers.handle_get_route_with_buses(user_id, route_id, app_state)
            elif message_type == "calculate_eta":
                bus_id = data.get("bus_id")
                stop_id = data.get("stop_id")
                if not bus_id or not stop_id:
                    return {"success": False, "error": "Bus ID and Stop ID required"}
                return await WebSocketEventHandlers.handle_calculate_eta(user_id, bus_id, stop_id, app_state)
            elif message_type == "admin_broadcast":
                return await WebSocketEventHandlers.handle_admin_broadcast(user_id, data, app_state)
            elif message_type == "emergency_alert":
                return await WebSocketEventHandlers.handle_emergency_alert(user_id, data, app_state)
            elif message_type == "join_conversation":
                conversation_id = data.get("conversation_id")
                if not conversation_id:
                    return {"success": False, "error": "Conversation ID required"}
                return await WebSocketEventHandlers.handle_join_conversation_room(user_id, conversation_id, app_state)
            elif message_type == "typing_indicator":
                conversation_id = data.get("conversation_id")
                is_typing = data.get("is_typing", False)
                if not conversation_id:
                    return {"success": False, "error": "Conversation ID required"}
                return await WebSocketEventHandlers.handle_typing_indicator(user_id, conversation_id, is_typing)
            elif message_type == "mark_message_read":
                conversation_id = data.get("conversation_id")
                message_id = data.get("message_id")
                if not conversation_id or not message_id:
                    return {"success": False, "error": "Conversation ID and Message ID required"}
                return await WebSocketEventHandlers.handle_mark_message_read(user_id, conversation_id, message_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                return {"success": False, "error": f"Unknown message type: {message_type}"}
        except Exception as e:
            logger.error(f"Error handling message type {message_type} from user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_subscribe_all_buses(user_id: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Subscribe user to all bus location updates"""
        try:
            # Join global bus tracking room
            room_id = "all_bus_tracking"
            await websocket_manager.join_room_user(user_id, room_id)
            
            # Send initial bus locations
            await bus_tracking_service.broadcast_all_bus_locations(app_state)
            
            return {
                "success": True,
                "message": "Subscribed to all bus tracking",
                "room_id": room_id
            }
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
    async def handle_admin_broadcast(user_id: str, data: Dict[str, Any], app_state=None) -> Dict[str, Any]:
        """Handle admin/control staff broadcasting messages to drivers/regulators"""
        try:
            # Verify user has admin/control staff permissions
            if app_state and app_state.mongodb:
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
            if app_state and app_state.mongodb:
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
