from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from .base import BaseDBModel

class UserRole(str, Enum):
    PASSENGER = "PASSENGER"
    BUS_DRIVER = "BUS_DRIVER"
    QUEUE_REGULATOR = "QUEUE_REGULATOR"
    CONTROL_CENTER_ADMIN = "CONTROL_CENTER_ADMIN"
    REGULATOR = "REGULATOR"

class User(BaseDBModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: UserRole
    phone_number: str
    profile_image: Optional[str] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    is_active: bool = True