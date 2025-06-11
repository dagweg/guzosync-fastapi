"""
Socket.IO connection manager for real-time features
"""
from typing import Dict, List, Set, Optional, Any, Union
import socketio
from core.logger import get_logger
import json
from uuid import UUID
from datetime import datetime, timezone
import asyncio

logger = get_logger(__name__)


class SocketIOManager:
    """Manages Socket.IO connections for real-time features"""
    
    def __init__(self) -> None:
        # Create Socket.IO server instance
        self.sio: socketio.AsyncServer = socketio.AsyncServer(
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
            
        )

        # Store user sessions by session ID
        self.user_sessions: Dict[str, str] = {}  # session_id -> user_id
        # Store user connections by user ID
        self.user_connections: Dict[str, str] = {}  # user_id -> session_id
        # Store room subscriptions
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> set of user_ids
        # Store proximity alert preferences
        self.proximity_preferences: Dict[str, Dict[str, Any]] = {}  # user_id -> preferences

        # Store app state for authentication
        self.app_state: Optional[Any] = None

        # Register event handlers
        self._register_handlers()
        
    def set_app_state(self, app_state: Any) -> None:
        """Set the FastAPI app state for authentication"""
        self.app_state = app_state
        
    def _register_handlers(self) -> None:
        """Register Socket.IO event handlers"""
        
        @self.sio.event
        async def connect(sid: str, environ: Dict[str, Any], auth: Optional[Dict[str, Any]] = None) -> bool:
            """Handle client connection"""
            logger.info(f"Socket.IO client {sid} attempting to connect")
            
            # Authentication will be handled separately via token
            # For now, accept all connections
            return True
            
        @self.sio.event
        async def disconnect(sid: str) -> None:
            """Handle client disconnection"""
            if sid in self.user_sessions:
                user_id = self.user_sessions[sid]
                await self.disconnect_user(user_id)
                logger.info(f"User {user_id} disconnected from Socket.IO")
            else:
                logger.info(f"Unknown client {sid} disconnected")
                
        @self.sio.event
        async def authenticate(sid: str, data: Dict[str, Any]) -> None:
            """Handle user authentication"""
            try:
                token = data.get('token')
                if not token:
                    await self.sio.emit('auth_error', {'message': 'Token required'}, room=sid)
                    return
                
                # Import here to avoid circular imports
                from core.dependencies import get_current_user_websocket

                # Check if app state is available
                if not self.app_state:
                    await self.sio.emit('auth_error', {'message': 'Server not ready'}, room=sid)
                    return

                # Verify token and get user
                user = await get_current_user_websocket(token, self.app_state)
                if not user:
                    await self.sio.emit('auth_error', {'message': 'Invalid token'}, room=sid)
                    return
                
                # Store user session
                user_id = str(user.id)
                await self.connect_user(sid, user_id)
                
                await self.sio.emit('authenticated', {
                    'user_id': user_id,
                    'message': 'Successfully authenticated'
                }, room=sid)
                
                logger.info(f"User {user_id} authenticated via Socket.IO")
                
            except Exception as e:
                logger.error(f"Authentication error for session {sid}: {e}")
                await self.sio.emit('auth_error', {'message': 'Authentication failed'}, room=sid)
                
        @self.sio.event
        async def join_room(sid: str, data: Dict[str, Any]) -> None:
            """Handle room join requests"""
            try:
                if sid not in self.user_sessions:
                    await self.sio.emit('error', {'message': 'Not authenticated'}, room=sid)
                    return
                
                user_id = self.user_sessions[sid]
                room_id = data.get('room_id')
                
                if not room_id:
                    await self.sio.emit('error', {'message': 'Room ID required'}, room=sid)
                    return
                
                await self.join_room_user(user_id, room_id)
                await self.sio.emit('room_joined', {
                    'room_id': room_id,
                    'message': f'Joined room {room_id}'
                }, room=sid)
                
            except Exception as e:
                logger.error(f"Error joining room for session {sid}: {e}")
                await self.sio.emit('error', {'message': 'Failed to join room'}, room=sid)
                
        @self.sio.event
        async def leave_room(sid: str, data: Dict[str, Any]) -> None:
            """Handle room leave requests"""
            try:
                if sid not in self.user_sessions:
                    await self.sio.emit('error', {'message': 'Not authenticated'}, room=sid)
                    return
                
                user_id = self.user_sessions[sid]
                room_id = data.get('room_id')
                
                if not room_id:
                    await self.sio.emit('error', {'message': 'Room ID required'}, room=sid)
                    return
                
                await self.leave_room_user(user_id, room_id)
                await self.sio.emit('room_left', {
                    'room_id': room_id,
                    'message': f'Left room {room_id}'
                }, room=sid)
                
            except Exception as e:
                logger.error(f"Error leaving room for session {sid}: {e}")
                await self.sio.emit('error', {'message': 'Failed to leave room'}, room=sid)
                
        @self.sio.event
        async def ping(sid: str, data: Dict[str, Any]) -> None:
            """Handle ping requests for keepalive"""
            await self.sio.emit('pong', {
                'timestamp': data.get('timestamp', datetime.utcnow().isoformat())
            }, room=sid)

        # Enhanced event handlers for messaging, notifications, and bus tracking
        @self.sio.event
        async def send_message(sid: str, data: Dict[str, Any]) -> None:
            """Handle direct messaging between users"""
            try:
                if sid not in self.user_sessions:
                    await self.sio.emit('error', {'message': 'Not authenticated'}, room=sid)
                    return

                sender_id = self.user_sessions[sid]
                recipient_id = data.get('recipient_id')
                message_content = data.get('message')
                message_type = data.get('message_type', 'TEXT')

                if not recipient_id or not message_content:
                    await self.sio.emit('error', {'message': 'Recipient ID and message required'}, room=sid)
                    return

                # Import here to avoid circular imports
                from core.realtime.chat import chat_service

                # Create or get conversation between users
                if self.app_state and self.app_state.mongodb:
                    # Find existing conversation between these users
                    conversation = await self.app_state.mongodb.conversations.find_one({
                        "participants": {"$all": [sender_id, recipient_id]},
                        "type": "DIRECT"
                    })

                    if not conversation:
                        # Create new conversation
                        from uuid import uuid4
                        conversation_id = str(uuid4())
                        conversation_data = {
                            "id": conversation_id,
                            "type": "DIRECT",
                            "participants": [sender_id, recipient_id],
                            "created_at": datetime.utcnow(),
                            "last_message_at": datetime.utcnow()
                        }
                        await self.app_state.mongodb.conversations.insert_one(conversation_data)
                    else:
                        conversation_id = conversation["id"]

                    # Save message to database
                    from uuid import uuid4
                    message_id = str(uuid4())
                    message_data = {
                        "id": message_id,
                        "conversation_id": conversation_id,
                        "sender_id": sender_id,
                        "content": message_content,
                        "message_type": message_type,
                        "sent_at": datetime.utcnow(),
                        "is_read": False
                    }
                    await self.app_state.mongodb.messages.insert_one(message_data)

                    # Send real-time message
                    await chat_service.send_real_time_message(
                        conversation_id, sender_id, message_content, message_id, message_type, self.app_state
                    )

                    # Confirm to sender
                    await self.sio.emit('message_sent', {
                        'message_id': message_id,
                        'conversation_id': conversation_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=sid)

            except Exception as e:
                logger.error(f"Error handling send_message for session {sid}: {e}")
                await self.sio.emit('error', {'message': 'Failed to send message'}, room=sid)

        @self.sio.event
        async def subscribe_bus_tracking(sid: str, data: Dict[str, Any]) -> None:
            """Subscribe to bus location updates"""
            try:
                if sid not in self.user_sessions:
                    await self.sio.emit('error', {'message': 'Not authenticated'}, room=sid)
                    return

                user_id = self.user_sessions[sid]
                bus_id = data.get('bus_id')

                if not bus_id:
                    await self.sio.emit('error', {'message': 'Bus ID required'}, room=sid)
                    return

                from core.realtime.bus_tracking import bus_tracking_service
                await bus_tracking_service.subscribe_to_bus(user_id, bus_id)

            except Exception as e:
                logger.error(f"Error handling subscribe_bus_tracking for session {sid}: {e}")
                await self.sio.emit('error', {'message': 'Failed to subscribe to bus tracking'}, room=sid)

        @self.sio.event
        async def subscribe_route_tracking(sid: str, data: Dict[str, Any]) -> None:
            """Subscribe to route updates (all buses on route)"""
            try:
                if sid not in self.user_sessions:
                    await self.sio.emit('error', {'message': 'Not authenticated'}, room=sid)
                    return

                user_id = self.user_sessions[sid]
                route_id = data.get('route_id')

                if not route_id:
                    await self.sio.emit('error', {'message': 'Route ID required'}, room=sid)
                    return

                from core.realtime.bus_tracking import bus_tracking_service
                await bus_tracking_service.subscribe_to_route(user_id, route_id)

            except Exception as e:
                logger.error(f"Error handling subscribe_route_tracking for session {sid}: {e}")
                await self.sio.emit('error', {'message': 'Failed to subscribe to route tracking'}, room=sid)

        @self.sio.event
        async def subscribe_proximity_alerts(sid: str, data: Dict[str, Any]) -> None:
            """Subscribe to proximity alerts for bus stops"""
            try:
                if sid not in self.user_sessions:
                    await self.sio.emit('error', {'message': 'Not authenticated'}, room=sid)
                    return

                user_id = self.user_sessions[sid]
                bus_stop_id = data.get('bus_stop_id')
                radius_meters = data.get('radius_meters', 100)  # Default 100m radius

                if not bus_stop_id:
                    await self.sio.emit('error', {'message': 'Bus stop ID required'}, room=sid)
                    return

                # Join proximity alert room for this bus stop
                room_id = f"proximity_alerts:{bus_stop_id}"
                await self.join_room_user(user_id, room_id)

                # Store user's proximity preferences
                self.proximity_preferences[user_id] = {
                    'bus_stop_id': bus_stop_id,
                    'radius_meters': radius_meters,
                    'subscribed_at': datetime.now(timezone.utc)
                }

                await self.sio.emit('proximity_alerts_subscribed', {
                    'bus_stop_id': bus_stop_id,
                    'radius_meters': radius_meters,
                    'message': f'Subscribed to proximity alerts for bus stop {bus_stop_id}'
                }, room=sid)

                logger.info(f"User {user_id} subscribed to proximity alerts for bus stop {bus_stop_id}")

            except Exception as e:
                logger.error(f"Error handling subscribe_proximity_alerts for session {sid}: {e}")
                await self.sio.emit('error', {'message': 'Failed to subscribe to proximity alerts'}, room=sid)

        @self.sio.event
        async def update_bus_location(sid: str, data: Dict[str, Any]) -> None:
            """Handle bus location updates from drivers"""
            try:
                if sid not in self.user_sessions:
                    await self.sio.emit('error', {'message': 'Not authenticated'}, room=sid)
                    return

                user_id = self.user_sessions[sid]

                # Verify user is a bus driver
                if self.app_state and self.app_state.mongodb:
                    user = await self.app_state.mongodb.users.find_one({"id": user_id})
                    if not user or user.get("role") != "BUS_DRIVER":
                        await self.sio.emit('error', {'message': 'Only bus drivers can update bus locations'}, room=sid)
                        return

                bus_id = data.get('bus_id')
                latitude = data.get('latitude')
                longitude = data.get('longitude')
                heading = data.get('heading')
                speed = data.get('speed')

                if not bus_id or latitude is None or longitude is None:
                    await self.sio.emit('error', {'message': 'Bus ID, latitude, and longitude required'}, room=sid)
                    return

                # Type validation
                try:
                    latitude = float(latitude)
                    longitude = float(longitude)
                    if heading is not None:
                        heading = float(heading)
                    if speed is not None:
                        speed = float(speed)
                except (ValueError, TypeError):
                    await self.sio.emit('error', {'message': 'Invalid numeric values for location data'}, room=sid)
                    return

                from core.realtime.bus_tracking import bus_tracking_service
                await bus_tracking_service.update_bus_location(
                    str(bus_id), latitude, longitude, heading, speed, self.app_state
                )

                # Check for proximity alerts
                await self._check_proximity_alerts(str(bus_id), latitude, longitude)

                await self.sio.emit('location_updated', {
                    'bus_id': bus_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, room=sid)

            except Exception as e:
                logger.error(f"Error handling update_bus_location for session {sid}: {e}")
                await self.sio.emit('error', {'message': 'Failed to update bus location'}, room=sid)

        @self.sio.event
        async def get_bus_details(sid: str, data: Dict[str, Any]) -> None:
            """Get comprehensive bus details for map display"""
            try:
                if sid not in self.user_sessions:
                    await self.sio.emit('error', {'message': 'Not authenticated'}, room=sid)
                    return

                bus_id = data.get('bus_id')
                if not bus_id:
                    await self.sio.emit('error', {'message': 'Bus ID required'}, room=sid)
                    return

                if self.app_state and self.app_state.mongodb:
                    # Get bus details
                    bus = await self.app_state.mongodb.buses.find_one({"id": bus_id})
                    if not bus:
                        await self.sio.emit('error', {'message': 'Bus not found'}, room=sid)
                        return

                    # Get route details if bus is assigned to a route
                    route_details = None
                    if bus.get('assigned_route_id'):
                        route = await self.app_state.mongodb.routes.find_one({"id": bus['assigned_route_id']})
                        if route:
                            route_details = {
                                'id': route['id'],
                                'name': route.get('name'),
                                'start_location': route.get('start_location'),
                                'end_location': route.get('end_location'),
                                'route_shape': route.get('route_shape'),  # GeoJSON for Mapbox
                                'bus_stops': route.get('bus_stops', [])
                            }

                    # Calculate ETA if possible (this would need route service integration)
                    eta_info = None
                    if route_details and bus.get('current_location'):
                        # This would integrate with your route service for ETA calculation
                        # For now, we'll provide a placeholder
                        eta_info = {
                            'next_stop_eta': None,  # Would be calculated
                            'end_destination_eta': None  # Would be calculated
                        }

                    bus_details = {
                        'id': bus['id'],
                        'license_plate': bus.get('license_plate'),
                        'current_location': bus.get('current_location'),
                        'heading': bus.get('heading'),
                        'speed': bus.get('speed'),
                        'last_location_update': bus.get('last_location_update'),
                        'route': route_details,
                        'eta_info': eta_info,
                        'status': bus.get('status', 'ACTIVE')
                    }

                    await self.sio.emit('bus_details', bus_details, room=sid)

            except Exception as e:
                logger.error(f"Error handling get_bus_details for session {sid}: {e}")
                await self.sio.emit('error', {'message': 'Failed to get bus details'}, room=sid)
    
    async def connect_user(self, session_id: str, user_id: str) -> None:
        """Connect a user to Socket.IO"""
        # Remove any existing connection for this user
        if user_id in self.user_connections:
            old_session = self.user_connections[user_id]
            if old_session in self.user_sessions:
                del self.user_sessions[old_session]
        
        # Store new connection
        self.user_sessions[session_id] = user_id
        self.user_connections[user_id] = session_id
        
        logger.info(f"User {user_id} connected to Socket.IO with session {session_id}")
        
    async def disconnect_user(self, user_id: str) -> None:
        """Disconnect a user from Socket.IO"""
        if user_id in self.user_connections:
            session_id = self.user_connections[user_id]
            
            # Remove from sessions
            if session_id in self.user_sessions:
                del self.user_sessions[session_id]
            del self.user_connections[user_id]
            
            # Remove user from all rooms
            for room_id in list(self.rooms.keys()):
                if user_id in self.rooms[room_id]:
                    self.rooms[room_id].remove(user_id)
                    try:
                        self.sio.leave_room(session_id, room_id)
                    except Exception as e:
                        logger.warning(f"Error leaving room {room_id} for session {session_id}: {e}")
                    if not self.rooms[room_id]:  # Remove empty rooms
                        del self.rooms[room_id]
            
            logger.info(f"User {user_id} disconnected from Socket.IO")
    
    async def join_room_user(self, user_id: str, room_id: str) -> bool:
        """Add user to a room for group communications"""
        if user_id not in self.user_connections:
            logger.warning(f"User {user_id} not connected, cannot join room {room_id}")
            return False
            
        session_id = self.user_connections[user_id]
        
        try:
            # Add to Socket.IO room
            self.sio.enter_room(session_id, room_id)

            # Track in our room management
            if room_id not in self.rooms:
                self.rooms[room_id] = set()
            self.rooms[room_id].add(user_id)
            
            logger.info(f"User {user_id} joined room {room_id}")
            return True
        except Exception as e:
            logger.error(f"Error joining room {room_id} for user {user_id}: {e}")
            return False
    
    async def leave_room_user(self, user_id: str, room_id: str) -> bool:
        """Remove user from a room"""
        if user_id not in self.user_connections:
            return False
            
        session_id = self.user_connections[user_id]
        
        try:
            # Remove from Socket.IO room
            self.sio.leave_room(session_id, room_id)

            # Remove from our tracking
            if room_id in self.rooms and user_id in self.rooms[room_id]:
                self.rooms[room_id].remove(user_id)
                if not self.rooms[room_id]:  # Remove empty rooms
                    del self.rooms[room_id]
                
            logger.info(f"User {user_id} left room {room_id}")
            return True
        except Exception as e:
            logger.error(f"Error leaving room {room_id} for user {user_id}: {e}")
            return False

    async def send_personal_message(self, user_id: str, event: str, data: Dict[str, Any]) -> bool:
        """Send message to a specific user"""
        if user_id not in self.user_connections:
            logger.warning(f"User {user_id} not connected, cannot send message")
            return False

        session_id = self.user_connections[user_id]

        try:
            await self.sio.emit(event, data, room=session_id)
            logger.debug(f"Sent {event} to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            # Remove disconnected connection
            await self.disconnect_user(user_id)
            return False

    async def send_room_message(self, room_id: str, event: str, data: Dict[str, Any], exclude_user: str = "") -> bool:
        """Send message to all users in a room"""
        if room_id not in self.rooms:
            logger.warning(f"Room {room_id} does not exist")
            return False

        users_to_notify = self.rooms[room_id].copy()
        if exclude_user:
            users_to_notify.discard(exclude_user)

        success_count = 0
        for user_id in users_to_notify:
            if await self.send_personal_message(user_id, event, data):
                success_count += 1

        logger.debug(f"Sent {event} to {success_count}/{len(users_to_notify)} users in room {room_id}")
        return success_count > 0

    async def broadcast_message(self, event: str, data: Dict[str, Any]) -> bool:
        """Send message to all connected users"""
        try:
            await self.sio.emit(event, data)
            logger.debug(f"Broadcasted {event} to all users")
            return True
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return False

    async def broadcast_to_room(self, room_id: str, event: str, data: Dict[str, Any], exclude_user: str = "") -> bool:
        """Alias for send_room_message to maintain compatibility"""
        return await self.send_room_message(room_id, event, data, exclude_user)

    def get_user_rooms(self, user_id: str) -> List[str]:
        """Get all rooms that a user is subscribed to"""
        user_rooms = []
        for room_id, users in self.rooms.items():
            if user_id in users:
                user_rooms.append(room_id)
        return user_rooms

    def get_connection_count(self) -> int:
        """Get the total number of active connections"""
        return len(self.user_connections)

    def get_room_count(self) -> int:
        """Get the total number of active rooms"""
        return len(self.rooms)

    def get_room_users(self, room_id: str) -> Set[str]:
        """Get all users in a room"""
        return self.rooms.get(room_id, set()).copy()

    def get_connected_users(self) -> List[str]:
        """Get list of all connected user IDs"""
        return list(self.user_connections.keys())

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user is currently connected"""
        return user_id in self.user_connections

    def is_user_in_room(self, user_id: str, room_id: str) -> bool:
        """Check if a user is in a specific room"""
        return room_id in self.rooms and user_id in self.rooms[room_id]

    async def _check_proximity_alerts(self, bus_id: str, latitude: float, longitude: float) -> None:
        """Check if bus is near any bus stops and send proximity alerts"""
        try:
            if not self.app_state or not self.app_state.mongodb:
                return

            # Get all bus stops
            bus_stops = await self.app_state.mongodb.bus_stops.find({}).to_list(length=None)

            for bus_stop in bus_stops:
                stop_location = bus_stop.get('location')
                if not stop_location:
                    continue

                stop_lat = stop_location.get('latitude')
                stop_lng = stop_location.get('longitude')
                if stop_lat is None or stop_lng is None:
                    continue

                # Calculate distance using simple Haversine formula
                distance_meters = self._calculate_distance(latitude, longitude, stop_lat, stop_lng)

                # Check if any users are subscribed to proximity alerts for this stop
                room_id = f"proximity_alerts:{bus_stop['id']}"
                if room_id in self.rooms:
                    for user_id in self.rooms[room_id]:
                        user_prefs = self.proximity_preferences.get(user_id)
                        if user_prefs and distance_meters <= user_prefs.get('radius_meters', 100):
                            # Send proximity alert
                            alert_message = {
                                'type': 'proximity_alert',
                                'bus_id': bus_id,
                                'bus_stop_id': bus_stop['id'],
                                'bus_stop_name': bus_stop.get('name', 'Unknown Stop'),
                                'distance_meters': round(distance_meters, 1),
                                'estimated_arrival_minutes': max(1, round(distance_meters / 200)),  # Rough estimate
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            }

                            await self.send_personal_message(user_id, 'proximity_alert', alert_message)
                            logger.info(f"Sent proximity alert to user {user_id} for bus {bus_id} near stop {bus_stop['id']}")

        except Exception as e:
            logger.error(f"Error checking proximity alerts: {e}")

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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


# Global Socket.IO manager instance
socketio_manager = SocketIOManager()
