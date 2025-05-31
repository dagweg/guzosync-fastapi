from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum
from .base import DateTimeModelMixin, Location

class AttendanceType(str, Enum):
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"

class CreateAttendanceRecordRequest(BaseModel):
    type: AttendanceType
    location: Optional[Location] = None

class AttendanceRecordResponse(BaseModel):
    id: UUID
    user_id: UUID
    timestamp: datetime
    type: AttendanceType
    location: Optional[Location] = None