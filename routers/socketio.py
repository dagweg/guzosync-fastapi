"""
Socket.IO endpoints for real-time communication
"""
from fastapi import APIRouter
import socketio
from core.socketio_manager import socketio_manager
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/socket.io", tags=["socketio"])

# Get the Socket.IO server instance from the manager
sio = socketio_manager.sio

# The Socket.IO server will be mounted to the FastAPI app in main.py
# This router is mainly for documentation and any additional HTTP endpoints
# related to Socket.IO functionality

@router.get("/info")
async def socketio_info():
    """Get Socket.IO connection information"""
    return {
        "endpoint": "/socket.io/",
        "transport": ["websocket", "polling"],
        "connected_users": socketio_manager.get_connection_count(),
        "active_rooms": socketio_manager.get_room_count(),
        "features": [
            "Real-time chat messaging",
            "Bus location tracking", 
            "Push notifications",
            "Live analytics updates"
        ]
    }

@router.get("/stats")
async def socketio_stats():
    """Get Socket.IO connection statistics"""
    return {
        "total_connections": socketio_manager.get_connection_count(),
        "total_rooms": socketio_manager.get_room_count(),
        "connected_users": socketio_manager.get_connected_users(),
        "rooms": {
            room_id: list(users) 
            for room_id, users in socketio_manager.rooms.items()
        }
    }
