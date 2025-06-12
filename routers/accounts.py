from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse

from datetime import datetime, timedelta
import secrets

from core.dependencies import get_current_user
from core.mongo_utils import transform_mongo_doc, model_to_mongo_doc
from core.email_service import send_password_reset_email, send_password_reset_email_token, send_welcome_email
from core.security import get_password_hash, verify_password
from models import User, ApprovalRequest
from models.user import UserRole as ModelUserRole
from models.approval import ApprovalStatus
from schemas.user import (
    UserResponse, RegisterUserRequest, LoginRequest, 
    ForgotPasswordRequest, ResetPasswordRequest
)
from schemas.approval import ApprovalRequestResponse
import os
from core import create_access_token, get_logger, transform_mongo_doc

logger = get_logger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
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
        )
    
    # Check if there's already a pending approval request for this email
    existing_request = await request.app.state.mongodb.approval_requests.find_one({
        "email": user_data.email, 
        "status": ApprovalStatus.PENDING.value
    })
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is already a pending approval request for this email"
        )
      # If registering as CONTROL_STAFF, create approval request instead of user
    if user_data.role.value == "CONTROL_STAFF":
        approval_request = ApprovalRequest(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            phone_number=user_data.phone_number,
            profile_image=user_data.profile_image,
            role="CONTROL_STAFF",
            status=ApprovalStatus.PENDING,
            requested_at=datetime.utcnow()
        )
        
        try:
            # Convert model to MongoDB document
            request_doc = model_to_mongo_doc(approval_request)
            result = await request.app.state.mongodb.approval_requests.insert_one(request_doc)
            
            # Retrieve the created approval request
            created_request = await request.app.state.mongodb.approval_requests.find_one({"id": approval_request.id})
            
            logger.info("Approval request created for CONTROL_STAFF", extra={"email": user_data.email})
            return {
                "message": "Registration request submitted successfully. Please wait for admin approval.",
                "request_id": approval_request.id,
                "status": "PENDING_APPROVAL"
            }
        except Exception as e:
            logger.error("Error creating approval request", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating approval request"
            )
      # For all other roles (including CONTROL_ADMIN), proceed with normal registration
    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password=get_password_hash(user_data.password),  # Hash the password
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
        created_user = await request.app.state.mongodb.users.find_one({"id": user.id})
        
        # Send welcome email
        full_name = f"{user_data.first_name} {user_data.last_name}"
        email_sent = await send_welcome_email(user_data.email, full_name)
        if not email_sent:
            logger.warning("Failed to send welcome email", extra={"email": user_data.email})
        
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
    if not user or not verify_password(user_data.password, user.get("password", "")) or not user.get("is_active", True):
        logger.warning(f"Login failed for email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        print(user)
        user_id = user.get("id") or str(user.get("_id"))
        access_token = create_access_token(data={"sub": str(user_id),"role": user.get("role")})
        
        # Create response data
        response_data = {
            "access_token": access_token, 
            "token_type": "bearer", 
            "role": user.get("role", "user")
        }
        
        # Create JSON response
        response = JSONResponse(
            content=response_data,
            status_code=status.HTTP_200_OK
        )
        
        # Set access token in the response cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 1440)) * 60
        )
        
        logger.info(f"Successful login for user: {user_data.email}")
        return response
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

        # Get client URL from environment variable
        client_url = os.getenv("CLIENT_URL", "http://localhost:3000")

        # Create reset link or send token based on user role
        if user["role"] == "CONTROL_ADMIN" or user["role"] == "CONTROL_STAFF":
            # For control center users, send reset link to control center frontend
            reset_link = f"{client_url}/control-center/password/reset?token={reset_token}"
            email_sent = await send_password_reset_email(reset_data.email, reset_link)
        else:
            # For regular users (passengers, drivers, etc.), send token only for mobile/web app
            email_sent = await send_password_reset_email_token(reset_data.email, reset_token)
        
        # Send password reset email
        if not email_sent:
            logger.warning("Failed to send password reset email", extra={"email": reset_data.email})
        
        logger.info("Password reset token generated and email sent", extra={"email": reset_data.email})
        
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
                "$set": {"password": get_password_hash(reset_data.new_password)},  # Hash the new password
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