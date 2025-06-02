from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from uuid import UUID
from datetime import datetime, timedelta
import secrets

from core.dependencies import get_current_user
from core.mongo_utils import transform_mongo_doc, model_to_mongo_doc
from models import User
from models.user import UserRole as ModelUserRole
from schemas.user import (
    UserResponse, RegisterUserRequest, LoginRequest, 
    ForgotPasswordRequest, ResetPasswordRequest
)

from core import create_access_token, get_logger, transform_mongo_doc

logger = get_logger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request, 
    user_data: RegisterUserRequest
):
    logger.info("Registration attempt", extra={"email": user_data.email})
    
    # Check if user with email already exists
    existing_user = await request.app.state.mongodb.users.find_one({"email": user_data.email})
    if existing_user:
        logger.warning("Registration failed - email exists", extra={"email": user_data.email})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )    # Create new user model
    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password=user_data.password,  # In production, hash this password
        role=ModelUserRole(user_data.role.value),  # Convert schema enum to model enum
        phone_number=user_data.phone_number,
        profile_image=user_data.profile_image,
        is_active=True
    )
    
    try:
        # Convert model to MongoDB document
        user_doc = model_to_mongo_doc(user)
        result = await request.app.state.mongodb.users.insert_one(user_doc)
        
        # Retrieve and return the created user
        created_user = await request.app.state.mongodb.users.find_one({"_id": result.inserted_id})
        logger.info("User registered successfully", extra={"email": user_data.email})
        return transform_mongo_doc(created_user, UserResponse)
    except Exception as e:
        logger.error("Error during user registration", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )

@router.post("/login")
async def login(
    request: Request, 
    user_data: LoginRequest
):
    logger.info(f"Login attempt for email: {user_data.email}")
    
    user = await request.app.state.mongodb.users.find_one({"email": user_data.email})
    if not user or user.get("password") != user_data.password:  # In production, verify hashed password
        logger.warning(f"Login failed for email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = user.get("id") or str(user.get("_id"))
        access_token = create_access_token(data={"sub": str(user_id)})
        logger.info(f"Successful login for user: {user_data.email}")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Error generating token for user {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating access token"
        )

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (invalidate token)"""
    # In a real implementation, you would invalidate the token
    # For now, we'll just return a success message since JWT tokens
    # are stateless and would need to be blacklisted
    logger.info(f"User logout: {current_user.email}")
    return {"message": "Logged out successfully"}

@router.post("/password/reset/request")
async def request_password_reset(
    request: Request, 
    reset_data: ForgotPasswordRequest
):
    logger.info("Password reset request", extra={"email": reset_data.email})
    
    try:
        # Check if user exists
        user = await request.app.state.mongodb.users.find_one({"email": reset_data.email})
        if not user:
            # Security: Don't reveal if email exists
            logger.info("Password reset request for unknown email")
            return {"message": "If your email is registered, you will receive a password reset link"}
        
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        reset_expires = datetime.utcnow() + timedelta(hours=1)
        
        # Store token in database
        await request.app.state.mongodb.users.update_one(
            {"email": reset_data.email},
            {"$set": {
                "password_reset_token": reset_token,
                "password_reset_expires": reset_expires
            }}
        )
        
        # Create reset link
        reset_link = f"{request.base_url}password/reset?token={reset_token}"
        
        # TODO: Send email with reset link
        logger.info("Password reset token generated", extra={"email": reset_data.email})
        
        return {"message": "Password reset instructions sent to your email"}
    except Exception as e:
        logger.error("Error processing password reset request", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing password reset request"
        )

@router.post("/password/reset/confirm")
async def confirm_password_reset(
    request: Request, 
    reset_data: ResetPasswordRequest
):
    logger.info("Password reset confirmation attempt")
    
    # Find user with valid reset token
    user = await request.app.state.mongodb.users.find_one({
        "password_reset_token": reset_data.token,
        "password_reset_expires": {"$gt": datetime.utcnow()}
    })
    
    if not user:
        logger.warning("Invalid or expired password reset token used")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    try:
        # Update password and clear reset token
        await request.app.state.mongodb.users.update_one(
            {"password_reset_token": reset_data.token},
            {
                "$set": {"password": reset_data.new_password},  # In production, hash this password
                "$unset": {"password_reset_token": "", "password_reset_expires": ""}
            }
        )
        logger.info(f"Successfully reset password for user: {user['email']}")
        return {"message": "Password has been reset successfully"}
    except Exception as e:
        logger.error("Error updating password", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating password"
        )