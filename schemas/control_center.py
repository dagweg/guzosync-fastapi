from typing import Literal, Optional
from pydantic import BaseModel, EmailStr

from models.user import UserRole

class RegisterPersonnelRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    role: Literal[UserRole.BUS_DRIVER, UserRole.QUEUE_REGULATOR]
    phone_number: str
    profile_image: Optional[str] = None

class RegisterControlStaffRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    profile_image: Optional[str] = None