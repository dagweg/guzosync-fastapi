from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional


from core.dependencies import get_current_user
from models import User, Notification
from schemas.notification import BroadcastNotificationRequest, NotificationResponse
from core.realtime.notifications import notification_service

from core import transform_mongo_doc

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    
    
    notifications = await request.app.state.mongodb.notifications.find(
        {"user_id": current_user.id}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(notification, NotificationResponse) for notification in notifications]

@router.post("/mark-read/{notification_id}")
async def mark_notification_read(
    request: Request,
    notification_id: str, 
    current_user: User = Depends(get_current_user)
):
    
    
    result = await request.app.state.mongodb.notifications.update_one(
        {"_id": notification_id, "user_id": current_user.id},
        {"$set": {"is_read": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already marked as read"
        )
    
    return {"message": "Notification marked as read"}

@router.post("/broadcast")
async def broadcast_notification(
    request: Request,
    notification_req: BroadcastNotificationRequest, 
    current_user: User = Depends(get_current_user)
):
    # Check if user has admin privileges
    if current_user.role not in ["CONTROL_CENTER_ADMIN", "REGULATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can broadcast notifications"
        )
    
    # Determine target users
    target_users = []
    
    if notification_req.target_user_ids:
        # Send to specific users
        target_users = await request.app.state.mongodb.users.find(
            {"_id": {"$in": notification_req.target_user_ids}}
        ).to_list(length=None)
    elif notification_req.target_roles:
        # Send to users with specific roles
        target_users = await request.app.state.mongodb.users.find(
            {"role": {"$in": notification_req.target_roles}}
        ).to_list(length=None)
    else:
        # Send to all users
        target_users = await request.app.state.mongodb.users.find({}).to_list(length=None)
    
    # Create notifications for each target user
    notifications = []
    for user in target_users:
        notification = {
            "user_id": user["id"],
            "title": notification_req.title,
            "message": notification_req.message,
            "type": notification_req.type.value if hasattr(notification_req.type, 'value') else notification_req.type,
            "related_entity": notification_req.related_entity.dict() if notification_req.related_entity else None
        }
        notifications.append(notification)
    
    if notifications:
        await request.app.state.mongodb.notifications.insert_many(notifications)
    
    # Send real-time notifications
    await notification_service.broadcast_notification(
        title=notification_req.title,
        message=notification_req.message,
        notification_type=notification_req.type.value if hasattr(notification_req.type, 'value') else notification_req.type,
        target_user_ids=notification_req.target_user_ids,
        target_roles=notification_req.target_roles,
        related_entity=notification_req.related_entity.dict() if notification_req.related_entity else None,
        app_state=request.app.state
    )
    
    return {"message": f"Notification sent to {len(notifications)} users"}