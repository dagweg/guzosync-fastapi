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
        
        logger.info(f"User {user_id} connected via WebSocket with connection {connection_id}")
        return connection_id

    async def disconnect_user(self, user_id: str) -> None:
        """Disconnect a user and clean up"""
        if user_id in self.user_connections:
            # Remove from all rooms
            rooms_to_clean = []
            for room_id, users in self.rooms.items():
                if user_id in users:
                    users.discard(user_id)
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
            
            logger.info(f"User {user_id} disconnected and cleaned up")

    async def join_room_user(self, user_id: str, room_id: str) -> bool:
        """Add user to a room for group communications"""
        if user_id not in self.user_connections:
            logger.warning(f"User {user_id} not connected, cannot join room {room_id}")
            return False
            
        try:
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
        if room_id not in self.rooms:
            return False
            
        self.rooms[room_id].discard(user_id)
        if len(self.rooms[room_id]) == 0:
            del self.rooms[room_id]
            
        logger.info(f"User {user_id} left room {room_id}")
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
        return user_id in self.user_connections

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific user"""
        if user_id not in self.user_connections:
            logger.warning(f"User {user_id} not connected, cannot send message")
            return False

        websocket = self.user_connections[user_id]

        try:
            await websocket.send_text(json.dumps(message))
            logger.debug(f"Sent message to user {user_id}: {message.get('type', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            # Remove disconnected connection
            await self.disconnect_user(user_id)
            return False

    async def send_room_message(self, room_id: str, message: Dict[str, Any], exclude_user: str = "") -> bool:
        """Send message to all users in a room"""
        if room_id not in self.rooms:
            logger.warning(f"Room {room_id} does not exist")
            return False

        users_to_notify = self.rooms[room_id].copy()
        if exclude_user:
            users_to_notify.discard(exclude_user)

        success_count = 0
        for user_id in users_to_notify:
            if await self.send_personal_message(user_id, message):
                success_count += 1

        logger.debug(f"Sent message to {success_count}/{len(users_to_notify)} users in room {room_id}")
        return success_count > 0

    async def broadcast_message(self, message: Dict[str, Any]) -> bool:
        """Send message to all connected users"""
        success_count = 0
        for user_id in list(self.user_connections.keys()):
            if await self.send_personal_message(user_id, message):
                success_count += 1

        logger.debug(f"Broadcasted message to {success_count} users")
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
