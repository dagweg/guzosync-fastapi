from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID
from enum import Enum
from .base import DateTimeModelMixin

class UserRole(str, Enum):
    PASSENGER = "PASSENGER"
    BUS_DRIVER = "BUS_DRIVER"
    QUEUE_REGULATOR = "QUEUE_REGULATOR"
    CONTROL_CENTER_ADMIN = "CONTROL_CENTER_ADMIN"
    REGULATOR = "REGULATOR"

class RegisterUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: UserRole
    phone_number: str
    profile_image: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class UpdateUserRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    profile_image: Optional[str] = None

class UserResponse(DateTimeModelMixin):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole
    phone_number: str
    profile_image: Optional[str] = None
    is_active: bool