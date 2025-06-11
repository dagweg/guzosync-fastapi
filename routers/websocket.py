"""
WebSocket endpoints for real-time communication
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
from core.websocket_manager import websocket_manager
from core.dependencies import get_current_user, get_current_user_websocket
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


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


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """Main WebSocket connection endpoint"""
    await websocket.accept()
    
    user = None
    user_id = None
    
    try:
        # Authenticate user
        if not websocket_manager.app_state:
            await websocket.send_text(json.dumps({
                "type": "auth_error",
                "message": "Server not ready"
            }))
            await websocket.close(code=4002)
            return
        
        user = await get_current_user_websocket(token, websocket_manager.app_state)
        if not user:
            await websocket.send_text(json.dumps({
                "type": "auth_error", 
                "message": "Invalid token"
            }))
            await websocket.close(code=4001)
            return
        
        user_id = str(user.id)
        
        # Connect user
        connection_id = await websocket_manager.connect_user(websocket, user_id)
        
        # Send authentication success
        await websocket.send_text(json.dumps({
            "type": "authenticated",
            "user_id": user_id,
            "connection_id": connection_id,
            "message": "Authentication successful"
        }))
        
        logger.info(f"WebSocket user {user.email} authenticated successfully")
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_websocket_message(user_id, message, websocket)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message from user {user_id}: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Internal server error"
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Connection error"
            }))
        except:
            pass
    finally:
        if user_id:
            await websocket_manager.disconnect_user(user_id)


async def handle_websocket_message(user_id: str, message: Dict[str, Any], websocket: WebSocket):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if not message_type:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Message type required"
        }))
        return
    
    try:
        if message_type == "ping":
            await websocket.send_text(json.dumps({
                "type": "pong",
                "timestamp": message.get("timestamp"),
                "server_time": str(datetime.now(timezone.utc).isoformat())
            }))
            
        elif message_type == "join_room":
            room_id = message.get("room_id")
            if not room_id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Room ID required"
                }))
                return
            
            success = await websocket_manager.join_room_user(user_id, room_id)
            if success:
                await websocket.send_text(json.dumps({
                    "type": "room_joined",
                    "room_id": room_id,
                    "message": f"Joined room {room_id}"
                }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Failed to join room"
                }))
                
        elif message_type == "leave_room":
            room_id = message.get("room_id")
            if not room_id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Room ID required"
                }))
                return
            
            success = await websocket_manager.leave_room_user(user_id, room_id)
            await websocket.send_text(json.dumps({
                "type": "room_left",
                "room_id": room_id,
                "message": f"Left room {room_id}"
            }))
            
        elif message_type == "send_message":
            # Handle direct messaging
            recipient_id = message.get("recipient_id")
            message_content = message.get("message")
            
            if not recipient_id or not message_content:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Recipient ID and message required"
                }))
                return
            
            # Import here to avoid circular imports
            from core.realtime.chat import chat_service
            from uuid import uuid4

            # Generate message ID
            message_id = str(uuid4())

            # For direct messages, we need to create/find a conversation first
            # This is a simplified approach - in production you'd want proper conversation management
            conversation_id = f"direct_{min(user_id, recipient_id)}_{max(user_id, recipient_id)}"

            result = await chat_service.send_real_time_message(
                conversation_id=conversation_id,
                sender_id=user_id,
                content=message_content,
                message_id=message_id,
                message_type=message.get("message_type", "TEXT")
            )
            
            if result:
                await websocket.send_text(json.dumps({
                    "type": "message_sent",
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                    "recipient_id": recipient_id
                }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Failed to send message"
                }))
                
        else:
            # Handle other message types through event handlers
            from core.realtime.websocket_events import websocket_event_handlers
            await websocket_event_handlers.handle_message(user_id, message_type, message, websocket_manager.app_state)
            
    except Exception as e:
        logger.error(f"Error handling message type {message_type} from user {user_id}: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Error handling {message_type}"
        }))


# HTTP endpoints for WebSocket functionality
@router.get("/status")
async def get_websocket_status():
    """Get WebSocket server status"""
    return {
        "status": "active",
        "connected_users": websocket_manager.get_connection_count(),
        "active_rooms": websocket_manager.get_room_count(),
        "server_info": {
            "transport_methods": ["websocket"]
        }
    }


@router.get("/info")
async def websocket_info():
    """Get WebSocket connection information"""
    return {
        "endpoint": "/ws/connect",
        "transport": ["websocket"],
        "connected_users": websocket_manager.get_connection_count(),
        "active_rooms": websocket_manager.get_room_count(),
        "features": [
            "Real-time chat messaging",
            "Bus location tracking", 
            "Push notifications",
            "Live analytics updates"
        ]
    }


# Import datetime for ping/pong
from datetime import datetime, timezone
