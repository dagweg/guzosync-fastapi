from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from models import User, Notification
from schemas.notification import BroadcastNotificationRequest, NotificationResponse
from routers.accounts import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    
    
    notifications = await request.app.mongodb.notifications.find(
        {"user_id": current_user.id}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [NotificationResponse(**notification) for notification in notifications]

@router.post("/mark-read/{notification_id}")
async def mark_notification_read(notification_id: UUID, current_user: User = Depends(get_current_user)):
    
    
    result = await request.app.mongodb.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"is_read": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already marked as read"
        )
    
    return {"message": "Notification marked as read"}

@router.post("/broadcast")
async def broadcast_notification(request: BroadcastNotificationRequest, current_user: User = Depends(get_current_user)):
    from fastapi import Request
    request_obj = Request
    
    # Check if user has admin privileges
    if current_user.role not in ["CONTROL_CENTER_ADMIN", "REGULATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can broadcast notifications"
        )
    
    # Determine target users
    target_users = []
    
    if request.target_user_ids:
        # Send to specific users
        target_users = await request_obj.app.mongodb.users.find(
            {"id": {"$in": request.target_user_ids}}
        ).to_list(length=None)
    elif request.target_roles:
        # Send to users with specific roles
        target_users = await request_obj.app.mongodb.users.find(
            {"role": {"$in": request.target_roles}}
        ).to_list(length=None)
    else:
        # Send to all users
        target_users = await request_obj.app.mongodb.users.find({}).to_list(length=None)
    
    # Create notifications for each target user
    notifications = []
    for user in target_users:
        notification = Notification(
            user_id=user["id"],
            title=request.title,
            message=request.message,
            type=request.type,
            related_entity=request.related_entity
        )
        notifications.append(notification.dict())
    
    if notifications:
        await request_obj.app.mongodb.notifications.insert_many(notifications)
    
    return {"message": f"Notification sent to {len(notifications)} users"}