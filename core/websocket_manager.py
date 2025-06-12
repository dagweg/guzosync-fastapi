"""
WebSocket connection manager for real-time features
"""
from typing import Dict, List, Set, Optional, Any, Union
from fastapi import WebSocket, WebSocketDisconnect
from core.logger import get_logger
import json
from uuid import UUID
from datetime import datetime, timezone
import asyncio

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time features"""
    
    def __init__(self) -> None:
        # Store user sessions by connection ID
        self.user_sessions: Dict[str, str] = {}  # connection_id -> user_id
        # Store user connections by user ID
        self.user_connections: Dict[str, WebSocket] = {}  # user_id -> websocket
        # Store connection IDs by user ID
        self.user_connection_ids: Dict[str, str] = {}  # user_id -> connection_id
        # Store room subscriptions
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> set of user_ids
        # Store proximity alert preferences
        self.proximity_preferences: Dict[str, Dict[str, Any]] = {}  # user_id -> preferences
        # Store app state for authentication
        self.app_state: Optional[Any] = None

    def set_app_state(self, app_state: Any) -> None:
        """Set the app state for authentication"""
        self.app_state = app_state
        logger.info("WebSocket manager app state set")

    async def connect_user(self, websocket: WebSocket, user_id: str) -> str:
        """Connect a user and return connection ID"""
        connection_id = f"ws_{user_id}_{datetime.now().timestamp()}"

        # Store the connection
        self.user_connections[user_id] = websocket
        self.user_connection_ids[user_id] = connection_id
        self.user_sessions[connection_id] = user_id

        total_connections = len(self.user_connections)
        logger.info(f"🔌 User {user_id} connected via WebSocket with connection {connection_id} (Total connections: {total_connections})")
        logger.debug(f"🔌 Connection stored: user_connections[{user_id}] = {websocket}")
        logger.debug(f"🔌 All connected users: {list(self.user_connections.keys())}")
        return connection_id

    async def disconnect_user(self, user_id: str) -> None:
        """Disconnect a user and clean up"""
        if user_id in self.user_connections:
            # Remove from all rooms
            rooms_to_clean = []
            rooms_left = []
            for room_id, users in self.rooms.items():
                if user_id in users:
                    users.discard(user_id)
                    rooms_left.append(room_id)
                    if len(users) == 0:
                        rooms_to_clean.append(room_id)

            # Clean up empty rooms
            for room_id in rooms_to_clean:
                del self.rooms[room_id]

            # Remove connection tracking
            connection_id = self.user_connection_ids.get(user_id)
            if connection_id:
                self.user_sessions.pop(connection_id, None)

            self.user_connections.pop(user_id, None)
            self.user_connection_ids.pop(user_id, None)
            self.proximity_preferences.pop(user_id, None)

            remaining_connections = len(self.user_connections)
            logger.info(f"🔌 User {user_id} disconnected and cleaned up (Remaining connections: {remaining_connections})")
            if rooms_left:
                logger.debug(f"🔌 User {user_id} was removed from rooms: {rooms_left}")
            if rooms_to_clean:
                logger.debug(f"🔌 Cleaned up empty rooms: {rooms_to_clean}")

    async def join_room_user(self, user_id: str, room_id: str) -> bool:
        """Add user to a room for group communications"""
        # Debug: Check connection state
        logger.debug(f"🔍 Checking connection for user {user_id} to join room {room_id}")
        logger.debug(f"🔍 Connected users: {list(self.user_connections.keys())}")
        logger.debug(f"🔍 User {user_id} in connections: {user_id in self.user_connections}")

        if user_id not in self.user_connections:
            logger.warning(f"🔌 User {user_id} not connected, cannot join room {room_id}")
            logger.warning(f"🔌 Currently connected users: {list(self.user_connections.keys())}")
            return False

        try:
            # Track in our room management
            if room_id not in self.rooms:
                self.rooms[room_id] = set()
                logger.debug(f"🏠 Created new room: {room_id}")

            self.rooms[room_id].add(user_id)
            room_size = len(self.rooms[room_id])

            logger.info(f"🏠 User {user_id} joined room {room_id} (Room size: {room_size})")
            return True
        except Exception as e:
            logger.error(f"💥 Error joining room {room_id} for user {user_id}: {e}")
            return False

    async def leave_room_user(self, user_id: str, room_id: str) -> bool:
        """Remove user from a room"""
        if room_id not in self.rooms:
            logger.debug(f"🏠 Room {room_id} doesn't exist, cannot remove user {user_id}")
            return False

        self.rooms[room_id].discard(user_id)
        remaining_users = len(self.rooms[room_id])

        if remaining_users == 0:
            del self.rooms[room_id]
            logger.info(f"🏠 User {user_id} left room {room_id} (Room deleted - was empty)")
        else:
            logger.info(f"🏠 User {user_id} left room {room_id} (Room size: {remaining_users})")

        return True

    def get_connection_count(self) -> int:
        """Get number of connected users"""
        return len(self.user_connections)

    def get_room_count(self) -> int:
        """Get number of active rooms"""
        return len(self.rooms)

    def get_users_in_room(self, room_id: str) -> Set[str]:
        """Get list of users in a room"""
        return self.rooms.get(room_id, set()).copy()

    def is_user_connected(self, user_id: str) -> bool:
        """Check if user is connected"""
        is_connected = user_id in self.user_connections
        logger.debug(f"🔍 Checking connection for user {user_id}: {'CONNECTED' if is_connected else 'NOT CONNECTED'}")
        logger.debug(f"🔍 Currently connected users: {list(self.user_connections.keys())}")
        logger.debug(f"🔍 Total connections: {len(self.user_connections)}")
        return is_connected

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific user"""
        if user_id not in self.user_connections:
            logger.warning(f"🔌 User {user_id} not connected, cannot send message")
            return False

        websocket = self.user_connections[user_id]
        message_type = message.get('type', 'unknown')

        try:
            message_json = json.dumps(message)
            await websocket.send_text(message_json)

            # Log successful message send
            logger.info(f"📤 SENT WebSocket Message: {message_type} to user {user_id}")
            logger.debug(f"📤 Message Data: {message}")

            return True
        except Exception as e:
            logger.error(f"💥 Error sending WebSocket message {message_type} to user {user_id}: {e}")
            # Remove disconnected connection
            await self.disconnect_user(user_id)
            return False

    async def send_room_message(self, room_id: str, message: Dict[str, Any], exclude_user: str = "") -> bool:
        """Send message to all users in a room"""
        if room_id not in self.rooms:
            logger.warning(f"🏠 Room {room_id} does not exist")
            return False

        users_to_notify = self.rooms[room_id].copy()
        if exclude_user:
            users_to_notify.discard(exclude_user)

        message_type = message.get('type', 'unknown')
        logger.info(f"📡 BROADCASTING to room {room_id}: {message_type} to {len(users_to_notify)} users")
        if exclude_user:
            logger.debug(f"📡 Excluding user {exclude_user} from broadcast")

        success_count = 0
        for user_id in users_to_notify:
            if await self.send_personal_message(user_id, message):
                success_count += 1

        if success_count > 0:
            logger.info(f"✅ Successfully broadcasted {message_type} to {success_count}/{len(users_to_notify)} users in room {room_id}")
        else:
            logger.warning(f"❌ Failed to broadcast {message_type} to any users in room {room_id}")

        return success_count > 0

    async def broadcast_message(self, message: Dict[str, Any]) -> bool:
        """Send message to all connected users"""
        message_type = message.get('type', 'unknown')
        total_users = len(self.user_connections)

        logger.info(f"🌐 GLOBAL BROADCAST: {message_type} to {total_users} connected users")

        success_count = 0
        for user_id in list(self.user_connections.keys()):
            if await self.send_personal_message(user_id, message):
                success_count += 1

        if success_count > 0:
            logger.info(f"✅ Global broadcast {message_type} successful: {success_count}/{total_users} users")
        else:
            logger.warning(f"❌ Global broadcast {message_type} failed: 0/{total_users} users")

        return success_count > 0

    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any], exclude_user: str = "") -> bool:
        """Alias for send_room_message to maintain compatibility"""
        return await self.send_room_message(room_id, message, exclude_user)

    def set_proximity_preferences(self, user_id: str, preferences: Dict[str, Any]) -> None:
        """Set proximity alert preferences for a user"""
        self.proximity_preferences[user_id] = preferences
        logger.debug(f"Set proximity preferences for user {user_id}")

    def get_proximity_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get proximity alert preferences for a user"""
        return self.proximity_preferences.get(user_id, {})


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
