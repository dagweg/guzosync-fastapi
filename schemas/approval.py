from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime
from enum import Enum
from .base import DateTimeModelMixin

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ApprovalRequestRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    profile_image: Optional[str] = None

class ApprovalActionRequest(BaseModel):
    action: ApprovalStatus  # APPROVED or REJECTED
    review_notes: Optional[str] = None

class ApprovalRequestResponse(DateTimeModelMixin):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    profile_image: Optional[str] = None
    role: str
    status: ApprovalStatus
    requested_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
