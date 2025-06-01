from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from uuid import UUID

from models import User, NotificationSettings
from schemas.user import UserResponse, UpdateUserRequest
from schemas.notification import NotificationSettingsResponse, UpdateNotificationSettingsRequest
from core.dependencies import get_current_user

router = APIRouter(prefix="/api/account", tags=["account"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_user_info(
    request: Request,
    update_request: UpdateUserRequest, 
    current_user: User = Depends(get_current_user)
):
    # Update only provided fields
    update_data = {k: v for k, v in update_request.dict().items() if v is not None}
    
    if update_data:
        await request.app.state.mongodb.users.update_one(
            {"id": current_user.id},
            {"$set": update_data}
        )
    
    updated_user = await request.app.state.mongodb.users.find_one({"id": current_user.id})
    return UserResponse(**updated_user)

@router.put("/notification-settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    request: Request,
    settings_request: UpdateNotificationSettingsRequest, 
    current_user: User = Depends(get_current_user)
):
    # Check if settings exist
    settings = await request.app.state.mongodb.notification_settings.find_one({"user_id": current_user.id})
    
    if settings:
        # Update existing settings
        await request.app.state.mongodb.notification_settings.update_one(
            {"user_id": current_user.id},
            {"$set": {"email_enabled": settings_request.email_enabled}}
        )
    else:
        # Create new settings
        settings = NotificationSettings(user_id=current_user.id, email_enabled=settings_request.email_enabled)
        await request.app.state.mongodb.notification_settings.insert_one(settings.dict())
    
    updated_settings = await request.app.state.mongodb.notification_settings.find_one({"user_id": current_user.id})
    return NotificationSettingsResponse(**updated_settings)

@router.put("/language")
async def update_preferred_language(
    request: Request,
    language: str, 
    current_user: User = Depends(get_current_user)
):
    # Check if user is a passenger
    if current_user.role != "PASSENGER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only passengers can update preferred language"
        )
    
    # Update user's language preference
    await request.app.state.mongodb.users.update_one(
        {"id": current_user.id},
        {"$set": {"preferred_language": language}}
    )
    
    return {"message": "Language preference updated successfully"}