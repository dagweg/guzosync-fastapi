"""
Socket.IO endpoints and HTTP helpers for real-time communication
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import socketio
from core.socketio_manager import socketio_manager
from core.realtime.socketio_events import websocket_event_handlers
from core.dependencies import get_current_user
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/socket.io", tags=["socketio"])

# Get the Socket.IO server instance from the manager
sio = socketio_manager.sio


# Pydantic models for HTTP endpoints
class BroadcastMessageRequest(BaseModel):
    message: str
    target_roles: List[str] = ["BUS_DRIVER", "QUEUE_REGULATOR"]
    priority: str = "NORMAL"


class EmergencyAlertRequest(BaseModel):
    alert_type: str = "GENERAL"
    message: str
    location: Optional[Dict[str, float]] = None


class ETARequest(BaseModel):
    bus_id: str
    stop_id: str


# HTTP endpoints for Socket.IO functionality
@router.get("/status")
async def get_socketio_status():
    """Get Socket.IO server status"""
    return {
        "status": "active",
        "connected_users": socketio_manager.get_connection_count(),
        "active_rooms": socketio_manager.get_room_count(),
        "server_info": {
            "cors_allowed_origins": "*",
            "transport_methods": ["websocket", "polling"]
        }
    }


@router.get("/rooms")
async def get_active_rooms(current_user=Depends(get_current_user)):
    """Get list of active rooms (admin only)"""
    if current_user.role not in ["ADMIN", "CONTROL_STAFF"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    rooms_info = {}
    for room_id, users in socketio_manager.rooms.items():
        rooms_info[room_id] = {
            "user_count": len(users),
            "users": list(users)
        }

    return {
        "total_rooms": len(rooms_info),
        "rooms": rooms_info
    }


@router.post("/broadcast")
async def broadcast_message(
    request: BroadcastMessageRequest,
    current_user=Depends(get_current_user)
):
    """HTTP endpoint for broadcasting messages (admin/control staff only)"""
    if current_user.role not in ["ADMIN", "CONTROL_STAFF"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        result = await websocket_event_handlers.handle_admin_broadcast(
            str(current_user.id),
            {
                "message": request.message,
                "target_roles": request.target_roles,
                "priority": request.priority
            }
        )

        if result["success"]:
            return {"message": "Broadcast sent successfully", "details": result}
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Broadcast failed"))

    except Exception as e:
        logger.error(f"Error in broadcast endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/emergency-alert")
async def send_emergency_alert(
    request: EmergencyAlertRequest,
    current_user=Depends(get_current_user)
):
    """HTTP endpoint for sending emergency alerts"""
    if current_user.role not in ["BUS_DRIVER", "QUEUE_REGULATOR"]:
        raise HTTPException(status_code=403, detail="Only drivers and regulators can send emergency alerts")

    try:
        result = await websocket_event_handlers.handle_emergency_alert(
            str(current_user.id),
            {
                "alert_type": request.alert_type,
                "message": request.message,
                "location": request.location
            }
        )

        if result["success"]:
            return {"message": "Emergency alert sent", "details": result}
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Alert failed"))

    except Exception as e:
        logger.error(f"Error in emergency alert endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/calculate-eta")
async def calculate_eta(
    request: ETARequest,
    current_user=Depends(get_current_user)
):
    """HTTP endpoint for calculating bus ETA"""
    try:
        result = await websocket_event_handlers.handle_calculate_eta(
            str(current_user.id),
            request.bus_id,
            request.stop_id
        )

        if result["success"]:
            return result["eta_data"]
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "ETA calculation failed"))

    except Exception as e:
        logger.error(f"Error in ETA calculation endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/route/{route_id}/live")
async def get_live_route_data(
    route_id: str,
    current_user=Depends(get_current_user)
):
    """Get live route data with bus positions for Mapbox"""
    try:
        result = await websocket_event_handlers.handle_get_route_with_buses(
            str(current_user.id),
            route_id
        )

        if result["success"]:
            return result["route_data"]
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "Route data not found"))

    except Exception as e:
        logger.error(f"Error getting live route data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# The Socket.IO server will be mounted to the FastAPI app in main.py
# Additional Socket.IO event handlers are defined in the socketio_manager

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
