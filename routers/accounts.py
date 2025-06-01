from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import os
import jwt   # or keep as just `import jwt` after uninstalling the wrong package
from uuid import UUID
import secrets

# Import centralized logger
from core.logger import get_logger

from models import User
from schemas.user import (
    RegisterUserRequest, LoginRequest, ForgotPasswordRequest,
    ResetPasswordRequest, UpdateUserRequest, UserResponse
)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import socket 

logger = get_logger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/accounts/login")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: Request, user_data: RegisterUserRequest):
    logger.info("Registration attempt", extra={"email": user_data.email})
    
    # Check if user with email already exists
    existing_user = await request.app.mongodb.users.find_one({"email": user_data.email})
    if existing_user:
        logger.warning("Registration failed - email exists", extra={"email": user_data.email})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create new user
    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password=user_data.password,
        role=user_data.role,
        phone_number=user_data.phone_number,
        profile_image=user_data.profile_image
    )
    
    try:
        result = await request.app.mongodb.users.insert_one(user.dict())
        created_user = await request.app.mongodb.users.find_one({"_id": result.inserted_id})
        logger.info("User registered successfully", extra={"email": user_data.email})
        return UserResponse(**created_user)
    except Exception as e:
        logger.error("User registration failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )


@router.post("/login")
async def login(request: Request, user_data: LoginRequest):
    logger.info(f"Login attempt for email: {user_data.email}")
    
    user = await request.app.mongodb.users.find_one({"email": user_data.email})
    if not user or user["password"] != user_data.password:  # In production, verify hashed password
        logger.warning(f"Login failed for email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        access_token = create_access_token(data={"sub": str(user["id"])})
        logger.info(f"Successful login for user: {user_data.email}")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Error generating token for user {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating access token"
        )

@router.post("/logout")
async def logout():
    logger.info("User logged out")
    # In a stateless JWT setup, client-side logout is sufficient
    # Server-side could implement token blacklisting if needed
    return {"message": "Successfully logged out"}

@router.post("/password/reset/request")
async def request_password_reset(request: Request, reset_data: ForgotPasswordRequest):
    logger.info("Password reset request", extra={"email": reset_data.email})
    
    try:
        # Check if user exists
        user = await request.app.mongodb.users.find_one({"email": reset_data.email})
        if not user:
            # Security: Don't reveal if email exists
            logger.info("Password reset request for unknown email")
            return {"message": "If your email is registered, you will receive a password reset link"}
        
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        reset_expires = datetime.utcnow() + timedelta(hours=1)
        
        # Store token in database
        await request.app.mongodb.users.update_one(
            {"email": reset_data.email},
            {"$set": {
                "password_reset_token": reset_token,
                "password_reset_expires": reset_expires
            }}
        )
        
        # Create reset link
        reset_link = f"{request.base_url}password/reset?token={reset_token}"
        
        # Send email (implementation depends on your email service)
        email_sent = await send_password_reset_email(
            email=reset_data.email,
            reset_link=reset_link,
            expiration_hours=1
        )
        
        if not email_sent:
            logger.error("Failed to send password reset email")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error sending password reset email"
            )
        
        logger.info("Password reset email sent successfully")
        return {"message": "Password reset link sent to your email"}
        
    except Exception as e:
        logger.error("Password reset request failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing password reset request"
        )

async def send_password_reset_email(email: str, reset_link: str, expiration_hours: int) -> bool:
    """Improved SMTP email sending with better error handling"""
    smtp_config = {
        'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'port': int(os.getenv('SMTP_PORT', 587)),
        'username': os.getenv('SMTP_USERNAME'),
        'password': os.getenv('SMTP_PASSWORD'),
        'from_email': os.getenv('EMAIL_FROM', 'noreply@yourdomain.com'),
        'timeout': 10
    }

    # Validate config first
    if not smtp_config['server']:
        logger.error("SMTP server not configured (SMTP_SERVER environment variable is empty)")
        return False
        
    if not all([smtp_config['username'], smtp_config['password']]):
        logger.error("SMTP credentials missing (SMTP_USERNAME or SMTP_PASSWORD environment variables are empty)")
        return False

    try:
        # Test DNS resolution first
        # This helps catch issues where the server name itself is unresolvable
        socket.getaddrinfo(smtp_config['server'], smtp_config['port'])
        
        # Proceed with email sending
        msg = MIMEMultipart()
        msg['From'] = smtp_config['from_email']
        msg['To'] = email
        msg['Subject'] = "Password Reset Request"
        
        html = f"""<html><body>
            <p>Hello,</p>
            <p>You have requested a password reset for your account.</p>
            <p>Please click on the following link to reset your password:</p>
            <p><a href="{reset_link}">Reset Your Password</a></p>
            <p>This link will expire in {expiration_hours} hour(s).</p>
            <p>If you did not request a password reset, please ignore this email.</p>
            <p>Best regards,</p>
            <p>The GuzoSync Team</p>
        </body></html>"""
        msg.attach(MIMEText(html, 'html'))

        # --- CRITICAL CHANGE HERE ---
        # Pass host and port directly to the SMTP constructor.
        # This makes the server_hostname available for starttls.
        with smtplib.SMTP(smtp_config['server'], smtp_config['port'], timeout=smtp_config['timeout']) as server:
            # The constructor already connects if host/port are provided.
            # So, server.connect() is no longer needed and should be removed.
            
            server.starttls() # This will now have the correct hostname context
            server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
            
        return True

    except socket.gaierror:
        logger.error(f"Could not resolve SMTP server '{smtp_config['server']}'. Check server address or network connectivity.")
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check SMTP_USERNAME and SMTP_PASSWORD.")
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP connection failed: {e}. Check SMTP_SERVER and SMTP_PORT.")
    except smtplib.SMTPException as e: # Catch all other smtplib errors
        logger.error(f"An SMTP error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during email sending: {str(e)}", exc_info=True)
    
    return False

@router.post("/password/reset/confirm")
async def confirm_password_reset(request: Request, reset_data: ResetPasswordRequest):
    logger.info("Password reset confirmation attempt")
    
    # Find user with valid reset token
    user = await request.app.mongodb.users.find_one({
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
        await request.app.mongodb.users.update_one(
            {"password_reset_token": reset_data.token},
            {
                "$set": {"password": reset_data.new_password},  # In production, hash this password
                "$unset": {"password_reset_token": "", "password_reset_expires": ""}
            }
        )
        logger.info(f"Successfully reset password for user: {user['email']}")
        return {"message": "Password has been reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting password"
        )