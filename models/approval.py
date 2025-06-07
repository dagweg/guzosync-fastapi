from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from enum import Enum
from .base import BaseDBModel

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ApprovalRequest(BaseDBModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    profile_image: Optional[str] = None
    role: str  # The role being requested (CONTROL_STAFF)
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: datetime
    reviewed_by: Optional[str] = None  # ID of the admin who reviewed
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
