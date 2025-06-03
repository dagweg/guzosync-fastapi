from typing import Optional
from pydantic import BaseModel

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
    id: str
    user_id: str
    timestamp: datetime
    type: AttendanceType
    location: Optional[Location] = None

    