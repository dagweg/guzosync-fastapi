"""
Socket.IO connection manager for real-time features
"""
from typing import Dict, List, Set, Optional, Any, Union
import socketio
from core.logger import get_logger
import json
from uuid import UUID
from datetime import datetime
import asyncio

logger = get_logger(__name__)


class SocketIOManager:
    """Manages Socket.IO connections for real-time features"""
    
    def __init__(self) -> None:
        # Create Socket.IO server instance
        self.sio: socketio.AsyncServer = socketio.AsyncServer(
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False
        )
        
        # Store user sessions by session ID
        self.user_sessions: Dict[str, str] = {}  # session_id -> user_id
        # Store user connections by user ID
        self.user_connections: Dict[str, str] = {}  # user_id -> session_id
        # Store room subscriptions
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> set of user_ids
        
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
                        await self.sio.leave_room(session_id, room_id)
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
            await self.sio.enter_room(session_id, room_id)
            
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
            await self.sio.leave_room(session_id, room_id)
            
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


# Global Socket.IO manager instance
socketio_manager = SocketIOManager()
