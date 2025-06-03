"""
Real-time WebSocket endpoints
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from core.websocket_manager import websocket_manager
from core.dependencies import get_current_user_websocket
from core.logger import get_logger
import json

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for authentication")
):
    """Main WebSocket endpoint for real-time communication"""
    try:
        # Authenticate user using token
        user = await get_current_user_websocket(token, websocket.app.state)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return
        
        user_id = str(user.id)
        
        # Connect user to WebSocket
        await websocket_manager.connect(websocket, user_id)
        
        try:
            while True:
                # Listen for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "join_room":
                    room_id = message.get("room_id")
                    if room_id:
                        websocket_manager.join_room(user_id, room_id)
                        await websocket.send_text(json.dumps({
                            "type": "room_joined",
                            "room_id": room_id,
                            "message": f"Joined room {room_id}"
                        }))
                
                elif message_type == "leave_room":
                    room_id = message.get("room_id")
                    if room_id:
                        websocket_manager.leave_room(user_id, room_id)
                        await websocket.send_text(json.dumps({
                            "type": "room_left",
                            "room_id": room_id,
                            "message": f"Left room {room_id}"
                        }))
                
                elif message_type == "ping":
                    # Keep connection alive
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }))
                
                logger.debug(f"Received message from user {user_id}: {message_type}")
                
        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        finally:
            websocket_manager.disconnect(user_id)
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=4002, reason="Connection error")
