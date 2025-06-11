"""
Real-time notifications service
"""
from datetime import datetime, timezone
from typing import List, Optional

from core.websocket_manager import websocket_manager
from core.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Service for real-time notifications"""
    
    @staticmethod
    async def send_real_time_notification(
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "GENERAL",
        related_entity: Optional[dict] = None,
        app_state=None
    ):
        """Send real-time notification to a specific user"""
        try:
            # Save notification to database
            notification_data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "type": notification_type,
                "is_read": False,
                "related_entity": related_entity,
                "created_at": datetime.now(timezone.utc)
            }
            
            if app_state and app_state.mongodb:
                result = await app_state.mongodb.notifications.insert_one(notification_data)
                notification_data["id"] = str(result.inserted_id)
            
            # Send real-time notification via WebSocket
            websocket_message = {
                "type": "notification",
                "notification": {
                    "id": notification_data.get("id"),
                    "title": title,
                    "message": message,
                    "notification_type": notification_type,
                    "related_entity": related_entity,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_read": False
                }
            }
            
            ws_message = {
                "type": "notification",
                **websocket_message
            }
            await websocket_manager.send_personal_message(str(user_id), ws_message)
            logger.info(f"Sent real-time notification to user {user_id}: {title}")
            
        except Exception as e:
            logger.error(f"Error sending real-time notification to user {user_id}: {e}")
    
    @staticmethod
    async def broadcast_notification(
        title: str,
        message: str,
        notification_type: str = "GENERAL",
        target_user_ids: Optional[List[str]] = None,
        target_roles: Optional[List[str]] = None,
        related_entity: Optional[dict] = None,
        app_state=None
    ):
        """Broadcast notification to multiple users"""
        try:
            target_users = []
            
            if app_state and app_state.mongodb:
                if target_user_ids:
                    # Send to specific users
                    target_users = await app_state.mongodb.users.find(
                        {"id": {"$in": target_user_ids}}
                    ).to_list(length=None)
                elif target_roles:
                    # Send to users with specific roles
                    target_users = await app_state.mongodb.users.find(
                        {"role": {"$in": target_roles}}
                    ).to_list(length=None)
                else:
                    # Send to all users
                    target_users = await app_state.mongodb.users.find({}).to_list(length=None)
                
                # Save notifications to database
                notifications = []
                for user in target_users:
                    notification_data = {
                        "user_id": user["id"],
                        "title": title,
                        "message": message,
                        "type": notification_type,
                        "is_read": False,
                        "related_entity": related_entity,
                        "created_at": datetime.now(timezone.utc)
                    }
                    notifications.append(notification_data)
                
                if notifications:
                    await app_state.mongodb.notifications.insert_many(notifications)
            
            # Send real-time notifications via WebSocket
            websocket_message = {
                "type": "notification",
                "notification": {
                    "title": title,
                    "message": message,
                    "notification_type": notification_type,
                    "related_entity": related_entity,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_read": False
                }            }
            
            # Convert to WebSocket message format
            ws_message = {
                "type": "notification",
                **websocket_message
            }

            if target_user_ids:
                # Send to specific users
                for user_id in target_user_ids:
                    await websocket_manager.send_personal_message(str(user_id), ws_message)
            elif target_users:
                # Send to users from database query
                for user in target_users:
                    await websocket_manager.send_personal_message(str(user["id"]), ws_message)
            else:
                # Broadcast to all connected users
                await websocket_manager.broadcast_message(ws_message)
            
            recipient_count = len(target_user_ids) if target_user_ids else len(target_users)
            logger.info(f"Broadcast notification to {recipient_count} users: {title}")
            
        except Exception as e:
            logger.error(f"Error broadcasting notification: {e}")
    
    @staticmethod
    async def send_trip_update_notification(
        trip_id: str,
        message: str,
        delay_minutes: Optional[int] = None,
        app_state=None
    ):
        """Send trip update notification to relevant users"""
        try:
            # Get trip details and passengers
            if app_state and app_state.mongodb:
                trip = await app_state.mongodb.trips.find_one({"id": trip_id})
                if not trip:
                    logger.warning(f"Trip {trip_id} not found for notification")
                    return
                
                # Get trip participants
                participants = trip.get("participants", [])
                  # Find users who might be interested in this trip
                # This could be passengers on the route, or those tracking the bus
                route_id = trip.get("route_id")
                bus_id = trip.get("bus_id")
                
                notification_title = "Trip Update"
                # Note: delay information is included in related_entity, not title
                
                related_entity = {
                    "entity_type": "trip",
                    "entity_id": str(trip_id)
                }
                  # Create WebSocket message
                websocket_message = {
                    "type": "notification",
                    "notification": {
                        "title": notification_title,
                        "message": message,
                        "notification_type": "TRIP_UPDATE",
                        "related_entity": {
                            "entity_type": "trip",
                            "entity_id": str(trip_id),
                            "trip_id": str(trip_id),
                            "delay_minutes": delay_minutes
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "is_read": False
                    }
                }
                
                # Convert to WebSocket message format
                ws_message = {
                    "type": "trip_notification",
                    **websocket_message
                }

                # Send to individual participants
                if participants:
                    for participant_id in participants:
                        await websocket_manager.send_personal_message(str(participant_id), ws_message)

                # Also send to users tracking this specific trip/route
                room_id = f"trip_tracking:{trip_id}"
                await websocket_manager.send_room_message(room_id, ws_message)

                # Also send to route subscribers
                if route_id:
                    route_room_id = f"route_tracking:{route_id}"
                    await websocket_manager.send_room_message(route_room_id, ws_message)
                
                logger.info(f"Sent trip update notification for trip {trip_id}")
            
        except Exception as e:
            logger.error(f"Error sending trip update notification: {e}")


# Global notification service instance
notification_service = NotificationService()
