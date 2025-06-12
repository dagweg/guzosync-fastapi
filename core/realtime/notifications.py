"""
Real-time notifications service
"""
from datetime import datetime, timezone
from typing import List, Optional

from core.websocket_manager import websocket_manager
from core.logger import get_logger
# Import UserRole as string to avoid circular import
# from models.users import UserRole

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
            logger.info(f"🔔 STARTING notification send to user {user_id}")
            logger.info(f"🔔 Notification details: title='{title}', type='{notification_type}'")

            # Check if user is connected to WebSocket
            is_connected = websocket_manager.is_user_connected(user_id)
            logger.info(f"🔌 User {user_id} WebSocket connection status: {'CONNECTED' if is_connected else 'NOT CONNECTED'}")

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

            if app_state and app_state.mongodb is not None:
                logger.debug(f"💾 Saving notification to database for user {user_id}")
                result = await app_state.mongodb.notifications.insert_one(notification_data)
                notification_data["id"] = str(result.inserted_id)
                logger.debug(f"💾 Notification saved with ID: {notification_data['id']}")
            else:
                logger.warning(f"⚠️ No database connection - notification not saved to DB")

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

            logger.info(f"📤 Attempting to send WebSocket message to user {user_id}")
            logger.debug(f"📤 WebSocket message content: {ws_message}")

            success = await websocket_manager.send_personal_message(str(user_id), ws_message)

            if success:
                logger.info(f"✅ Successfully sent real-time notification to user {user_id}: {title}")
            else:
                logger.error(f"❌ Failed to send real-time notification to user {user_id}: {title}")

        except Exception as e:
            logger.error(f"💥 Error sending real-time notification to user {user_id}: {e}", exc_info=True)
    
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
            
            if app_state and app_state.mongodb is not None:
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
            if app_state and app_state.mongodb is not None:
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

    @staticmethod
    async def send_route_reallocation_notification(
        bus_id: str,
        old_route_id: str,
        new_route_id: str,
        reallocated_by_user_id: str,
        app_state=None,
        requesting_regulator_id: Optional[str] = None  # Add parameter for requesting regulator
    ):
        """Send notifications when a route is reallocated"""
        try:
            if not app_state or app_state.mongodb is None:
                logger.warning("No database connection for route reallocation notification")
                return

            # Get bus and route information - Use id field for queries
            bus = await app_state.mongodb.buses.find_one({"id": bus_id})
            old_route = await app_state.mongodb.routes.find_one({"id": old_route_id}) if old_route_id else None
            new_route = await app_state.mongodb.routes.find_one({"id": new_route_id})
            reallocated_by = await app_state.mongodb.users.find_one({"id": reallocated_by_user_id})

            if not bus or not new_route:
                logger.warning(f"Bus {bus_id} or new route {new_route_id} not found for reallocation notification")
                return

            # Prepare notification data
            old_route_name = old_route.get("name", "Unknown Route") if old_route else "No Previous Route"
            new_route_name = new_route.get("name", "Unknown Route")
            reallocated_by_name = reallocated_by.get("full_name", "System") if reallocated_by else "System"

            related_entity = {
                "entity_type": "route_reallocation",
                "bus_id": bus_id,
                "old_route_id": old_route_id,
                "new_route_id": new_route_id,
                "reallocated_by": reallocated_by_user_id
            }

            # 1. Notify the bus driver
            driver_id = bus.get("assigned_driver_id")
            if driver_id:
                await NotificationService.send_real_time_notification(
                    user_id=driver_id,
                    title="Route Reallocation",
                    message=f"Your bus has been reallocated from {old_route_name} to {new_route_name} by {reallocated_by_name}",
                    notification_type="ROUTE_REALLOCATION",
                    related_entity=related_entity,
                    app_state=app_state
                )
                logger.info(f"Sent route reallocation notification to driver {driver_id}")

            # 2. Notify the requesting regulator (most important!)
            if requesting_regulator_id:
                logger.info(f"🎯 CRITICAL: Sending approval notification to requesting regulator {requesting_regulator_id}")
                logger.info(f"🎯 Bus: {bus.get('license_plate', bus_id)}, Old Route: {old_route_name}, New Route: {new_route_name}")

                await NotificationService.send_real_time_notification(
                    user_id=requesting_regulator_id,
                    title="Reallocation Request Approved",
                    message=f"Your reallocation request has been approved! Bus {bus.get('license_plate', bus_id)} has been reallocated from {old_route_name} to {new_route_name}",
                    notification_type="REALLOCATION_REQUEST_APPROVED",
                    related_entity=related_entity,
                    app_state=app_state
                )
                logger.info(f"✅ Completed sending reallocation approval notification to requesting regulator {requesting_regulator_id}")
            else:
                logger.warning(f"⚠️ No requesting_regulator_id provided - cannot send approval notification!")

            # 3. Notify the queue regulator of the previous route (if exists)
            if old_route_id:
                # Find queue regulators assigned to the old route
                old_route_regulators = await app_state.mongodb.users.find({
                    "role": "QUEUE_REGULATOR",
                    "assigned_route_ids": old_route_id
                }).to_list(length=None)

                for regulator in old_route_regulators:
                    # Don't double-notify the requesting regulator
                    if regulator.get("id") != requesting_regulator_id:
                        await NotificationService.send_real_time_notification(
                            user_id=regulator["id"],  # Use id field
                            title="Bus Removed from Route",
                            message=f"Bus {bus.get('license_plate', bus_id)} has been reallocated from your route {old_route_name} to {new_route_name}",
                            notification_type="ROUTE_REALLOCATION",
                            related_entity=related_entity,
                            app_state=app_state
                        )
                        logger.info(f"Sent route reallocation notification to old route regulator {regulator['id']}")

            # 4. Notify the queue regulator of the new route
            new_route_regulators = await app_state.mongodb.users.find({
                "role": "QUEUE_REGULATOR",
                "assigned_route_ids": new_route_id
            }).to_list(length=None)

            for regulator in new_route_regulators:
                # Don't double-notify the requesting regulator
                if regulator.get("id") != requesting_regulator_id:
                    await NotificationService.send_real_time_notification(
                        user_id=regulator["id"],  # Use id field
                        title="Bus Added to Route",
                        message=f"Bus {bus.get('license_plate', bus_id)} has been allocated to your route {new_route_name}",
                        notification_type="ROUTE_REALLOCATION",
                        related_entity=related_entity,
                        app_state=app_state
                    )
                    logger.info(f"Sent route reallocation notification to new route regulator {regulator['id']}")

            logger.info(f"Route reallocation notifications sent for bus {bus_id}")

        except Exception as e:
            logger.error(f"Error sending route reallocation notifications: {e}")

    @staticmethod
    async def send_reallocation_request_discarded_notification(
        request_id: str,
        requesting_regulator_id: str,
        reason: str,
        app_state=None
    ):
        """Send notification when a reallocation request is discarded"""
        try:
            logger.info(f"🚫 STARTING rejection notification for request {request_id} to regulator {requesting_regulator_id}")
            logger.info(f"🚫 Rejection reason: {reason}")

            if not app_state or app_state.mongodb is None:
                logger.warning("No database connection for reallocation request discarded notification")
                return

            # Get the reallocation request details - Use id field for query
            logger.debug(f"🔍 Looking up reallocation request {request_id} in database")
            request = await app_state.mongodb.reallocation_requests.find_one({"id": request_id})
            if not request:
                logger.warning(f"⚠️ Reallocation request {request_id} not found in database")
                return

            logger.debug(f"📋 Found reallocation request: bus_id={request.get('bus_id')}")

            related_entity = {
                "entity_type": "reallocation_request",
                "request_id": request_id,
                "bus_id": request.get("bus_id"),
                "status": "DISCARDED"
            }

            # Notify the requesting regulator
            logger.info(f"🎯 CRITICAL: Sending rejection notification to requesting regulator {requesting_regulator_id}")
            await NotificationService.send_real_time_notification(
                user_id=requesting_regulator_id,
                title="Reallocation Request Discarded",
                message=f"Your reallocation request for bus {request.get('bus_id', 'Unknown')} has been discarded. Reason: {reason}",
                notification_type="REALLOCATION_REQUEST_DISCARDED",
                related_entity=related_entity,
                app_state=app_state
            )

            logger.info(f"✅ Completed sending reallocation request discarded notification to regulator {requesting_regulator_id}")

        except Exception as e:
            logger.error(f"💥 Error sending reallocation request discarded notification: {e}", exc_info=True)

    @staticmethod
    async def send_incident_reported_notification(
        incident_id: str,
        reported_by_user_id: str,
        incident_type: str,
        severity: str,
        app_state=None
    ):
        """Send notification to control center when an incident is reported"""
        try:
            if not app_state or app_state.mongodb is None:
                logger.warning("No database connection for incident reported notification")
                return

            # Get incident details - Use id field for queries
            incident = await app_state.mongodb.incidents.find_one({"id": incident_id})
            reporter = await app_state.mongodb.users.find_one({"id": reported_by_user_id})

            if not incident:
                logger.warning(f"Incident {incident_id} not found")
                return

            reporter_name = reporter.get("full_name", "Unknown User") if reporter else "Unknown User"
            reporter_role = reporter.get("role", "Unknown Role") if reporter else "Unknown Role"

            related_entity = {
                "entity_type": "incident",
                "incident_id": incident_id,
                "incident_type": incident_type,
                "severity": severity,
                "reported_by": reported_by_user_id
            }

            # Prepare notification message
            message = f"New {severity.lower()} severity {incident_type.replace('_', ' ').lower()} incident reported by {reporter_name} ({reporter_role})"
            if incident.get("related_bus_id"):
                message += f" involving bus {incident['related_bus_id']}"
            if incident.get("related_route_id"):
                route = await app_state.mongodb.routes.find_one({"id": incident["related_route_id"]})
                route_name = route.get("name", incident["related_route_id"]) if route else incident["related_route_id"]
                message += f" on route {route_name}"

            # Send to control center staff - Use string instead of UserRole enum
            await NotificationService.broadcast_notification(
                title="Incident Reported",
                message=message,
                notification_type="INCIDENT_REPORTED",
                target_roles=["CONTROL_ADMIN", "CONTROL_STAFF"],  # Use strings instead of enum
                related_entity=related_entity,
                app_state=app_state
            )

            logger.info(f"Sent incident reported notification for incident {incident_id}")

        except Exception as e:
            logger.error(f"Error sending incident reported notification: {e}")

    @staticmethod
    async def send_reallocation_request_submitted_notification(
        request_id: str,
        requesting_regulator_id: str,
        bus_id: str,
        current_route_id: str,
        reason: str,
        priority: str,
        description: str,
        app_state=None
    ):
        """Send notification to control center when a new reallocation request is submitted"""
        try:
            logger.info(f"📝 STARTING reallocation request submission notification for request {request_id}")
            logger.info(f"📝 Request details: bus={bus_id}, reason={reason}, priority={priority}")

            if not app_state or app_state.mongodb is None:
                logger.warning("No database connection for reallocation request submitted notification")
                return

            # Get request details
            regulator = await app_state.mongodb.users.find_one({"id": requesting_regulator_id})
            bus = await app_state.mongodb.buses.find_one({"id": bus_id})
            current_route = await app_state.mongodb.routes.find_one({"id": current_route_id}) if current_route_id else None

            regulator_name = regulator.get("full_name", "Unknown Regulator") if regulator else "Unknown Regulator"
            bus_info = bus.get("license_plate", bus_id) if bus else bus_id
            current_route_name = current_route.get("name", current_route_id) if current_route else current_route_id

            related_entity = {
                "entity_type": "reallocation_request",
                "request_id": request_id,
                "bus_id": bus_id,
                "current_route_id": current_route_id,
                "requesting_regulator_id": requesting_regulator_id,
                "reason": reason,
                "priority": priority
            }

            # Prepare notification message
            priority_text = f" ({priority.lower()} priority)" if priority != "NORMAL" else ""
            message = f"New{priority_text} reallocation request submitted by {regulator_name} for bus {bus_info} on route {current_route_name}. Reason: {reason.replace('_', ' ').lower()}"
            if description:
                message += f". Details: {description[:100]}{'...' if len(description) > 100 else ''}"

            # Send to control center staff
            logger.info(f"🎯 CRITICAL: Sending reallocation request notification to control center")
            await NotificationService.broadcast_notification(
                title="New Reallocation Request",
                message=message,
                notification_type="REALLOCATION_REQUEST_SUBMITTED",
                target_roles=["CONTROL_ADMIN", "CONTROL_STAFF"],
                related_entity=related_entity,
                app_state=app_state
            )

            logger.info(f"✅ Completed sending reallocation request submitted notification for request {request_id}")

        except Exception as e:
            logger.error(f"💥 Error sending reallocation request submitted notification: {e}", exc_info=True)


# Global notification service instance
notification_service = NotificationService()
