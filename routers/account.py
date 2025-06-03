from fastapi import APIRouter, Depends, HTTPException, status, Request, Body


from core.dependencies import get_current_user
from models import User, NotificationSettings
from schemas.user import UserResponse, UpdateUserRequest
from schemas.notification import NotificationSettingsResponse, UpdateNotificationSettingsRequest
from core import transform_mongo_doc

router = APIRouter(prefix="/api/account", tags=["account"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    # Convert User model to dict and ensure id is a string
    user_dict = current_user.model_dump()
    user_dict["id"] = str(user_dict["id"])
    return UserResponse(**user_dict)

@router.put("/me", response_model=UserResponse)
async def update_user_info(
    request: Request,
    update_request: UpdateUserRequest, 
    current_user: User = Depends(get_current_user)
):
    # Update only provided fields
    update_data = {k: v for k, v in update_request.model_dump().items() if v is not None}
    
    if update_data:
        # Update user in MongoDB using built-in driver
        await request.app.state.mongodb.users.update_one(
            {"_id": current_user.id},
            {"$set": update_data}
        )
    
    # Find the updated user
    updated_user = await request.app.state.mongodb.users.find_one({"_id": current_user.id})
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    return transform_mongo_doc(updated_user, UserResponse)

@router.put("/notification-settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    request: Request,
    settings_request: dict = Body(...),
    current_user: User = Depends(get_current_user)
):
    # Map incoming fields to the normalized email_enabled field
    email_enabled = settings_request.get("email_notifications")
    if email_enabled is None:
        email_enabled = settings_request.get("email_enabled")
    
    if email_enabled is None:
        raise HTTPException(status_code=422, detail="email_notifications or email_enabled field is required")
      
    # Prepare update data with normalized field name
    update_data = {"email_enabled": email_enabled}
    
    # Find existing settings
    settings = await request.app.state.mongodb.notification_settings.find_one(
        {"user_id": current_user.id}
    )
    
    if settings:
        # Update existing settings
        await request.app.state.mongodb.notification_settings.update_one(
            {"user_id": current_user.id},
            {"$set": update_data}
        )
    else:
        # Create new settings document
        new_settings = {"user_id": current_user.id, **update_data}
        await request.app.state.mongodb.notification_settings.insert_one(new_settings)
    
    # Get updated settings
    updated_settings = await request.app.state.mongodb.notification_settings.find_one(
        {"user_id": current_user.id}
    )
    
    # Return a properly formatted response matching the schema
    if updated_settings:
        return {
            "id": str(updated_settings.get("_id", "")),
            "user_id": current_user.id,
            "email_enabled": updated_settings.get("email_enabled", False)
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to create or retrieve notification settings")

@router.put("/language")
async def update_preferred_language(
    request: Request,
    language: dict,  # Accept JSON body
    current_user: User = Depends(get_current_user)
):
    # Check if user is a passenger
    if current_user.role != "PASSENGER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only passengers can update preferred language"
        )
    
    # Validate language
    allowed_languages = {"en", "am", "om", "ti"}
    lang = language.get("language")
    if lang not in allowed_languages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid language code"
        )
    
    # Update user's language preference
    await request.app.state.mongodb.users.update_one(
        {"_id": current_user.id},
        {"$set": {"preferred_language": lang}}
    )
    
    return {"message": "Language updated successfully"}