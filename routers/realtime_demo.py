"""
Real-time demo endpoints for testing
"""
from fastapi import APIRouter, Depends, Request, Body
from uuid import  uuid4
from datetime import datetime

from core.dependencies import get_current_user
from models import User
from core.realtime.bus_tracking import bus_tracking_service
from core.realtime.notifications import notification_service
from core.realtime.chat import chat_service

router = APIRouter(prefix="/api/realtime/demo", tags=["realtime-demo"])


@router.post("/bus-location-update")
async def demo_bus_location_update(
    request: Request,
    demo_data: dict = Body(...),
    current_user: User = Depends(get_current_user)
):
    """Demo endpoint to test real-time bus location updates"""
    
    # Create or get a demo bus
    bus_id = demo_data.get("bus_id", str(uuid4()))
    latitude = demo_data.get("latitude", 9.0317)  # Default to Addis Ababa
    longitude = demo_data.get("longitude", 38.7468)
    heading = demo_data.get("heading", 45.0)
    speed = demo_data.get("speed", 30.0)
    
    # Simulate bus location update
    await bus_tracking_service.update_bus_location(
        bus_id=bus_id,
        latitude=latitude,
        longitude=longitude,
        heading=heading,
        speed=speed,
        app_state=request.app.state
    )
    
    return {
        "message": "Demo bus location updated",
        "bus_id": bus_id,
        "location": {"latitude": latitude, "longitude": longitude},
        "heading": heading,
        "speed": speed
    }


@router.post("/notification")
async def demo_notification(
    request: Request,
    demo_data: dict = Body(...),
    current_user: User = Depends(get_current_user)
):
    """Demo endpoint to test real-time notifications"""
    
    title = demo_data.get("title", "Demo Notification")
    message = demo_data.get("message", "This is a demo real-time notification")
    target_user_id = demo_data.get("target_user_id", str(current_user.id))
    
    # Send real-time notification
    await notification_service.send_real_time_notification(
        user_id=target_user_id,
        title=title,
        message=message,
        notification_type="DEMO",
        app_state=request.app.state
    )
    
    return {
        "message": "Demo notification sent",
        "title": title,
        "content": message,
        "target_user_id": target_user_id
    }


@router.post("/chat-message")
async def demo_chat_message(
    request: Request,
    demo_data: dict = Body(...),
    current_user: User = Depends(get_current_user)
):
    """Demo endpoint to test real-time chat messages"""
    
    conversation_id = demo_data.get("conversation_id", str(uuid4()))
    content = demo_data.get("content", "This is a demo real-time message")
    message_type = demo_data.get("message_type", "TEXT")
    
    # Send real-time chat message
    await chat_service.send_real_time_message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=content,
        message_type=message_type,
        message_id=str(uuid4()),
        app_state=request.app.state
    )
    
    return {
        "message": "Demo chat message sent",
        "conversation_id": conversation_id,
        "content": content,
        "sender_id": str(current_user.id)
    }
