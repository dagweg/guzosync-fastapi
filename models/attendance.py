from typing import Optional
from datetime import datetime, date
from enum import Enum

from .base import BaseDBModel, Location


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"


class Attendance(BaseDBModel):
    """Unified attendance model for daily status tracking"""
    user_id: str
    date: date
    status: AttendanceStatus
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    location: Optional[Location] = None
    notes: Optional[str] = None
    marked_at: datetime  # When the attendance was recorded

