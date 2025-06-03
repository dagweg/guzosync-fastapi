"""
WebSocket connection manager for real-time features
"""
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from core.logger import get_logger
import json
from uuid import UUID
from datetime import datetime

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time features"""
    
    def __init__(self):
        # Store active connections by user ID
        self.active_connections: Dict[str, WebSocket] = {}
        # Store room subscriptions (e.g., bus tracking, conversations)
        self.rooms: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a user to WebSocket"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected to WebSocket")
        
    def disconnect(self, user_id: str):
        """Disconnect a user from WebSocket"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            # Remove user from all rooms
            for room_id in list(self.rooms.keys()):
                if user_id in self.rooms[room_id]:
                    self.rooms[room_id].remove(user_id)
                    if not self.rooms[room_id]:  # Remove empty rooms
                        del self.rooms[room_id]
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    def join_room(self, user_id: str, room_id: str):
        """Add user to a room for group communications"""
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(user_id)
        logger.info(f"User {user_id} joined room {room_id}")
    
    def leave_room(self, user_id: str, room_id: str):
        """Remove user from a room"""
        if room_id in self.rooms and user_id in self.rooms[room_id]:
            self.rooms[room_id].remove(user_id)
            if not self.rooms[room_id]:  # Remove empty rooms
                del self.rooms[room_id]
            logger.info(f"User {user_id} left room {room_id}")
    
    async def send_personal_message(self, user_id: str, message: dict):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
                logger.debug(f"Sent message to user {user_id}: {message.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                # Remove disconnected connection
                self.disconnect(user_id)
    
    async def send_room_message(self, room_id: str, message: dict, exclude_user: str = ""):
        """Send message to all users in a room"""
        if room_id in self.rooms:
            users_to_notify = self.rooms[room_id].copy()
            if exclude_user:
                users_to_notify.discard(exclude_user)
            
            for user_id in users_to_notify:
                await self.send_personal_message(user_id, message)
    
    async def broadcast_message(self, message: dict):
        """Send message to all connected users"""
        disconnected_users = []
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)
    
    def get_room_users(self, room_id: str) -> Set[str]:
        """Get all users in a room"""
        return self.rooms.get(room_id, set()).copy()
    
    def get_connected_users(self) -> List[str]:
        """Get list of all connected user IDs"""
        return list(self.active_connections.keys())


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
