from typing import Optional
from datetime import datetime
from enum import Enum

from .base import BaseDBModel
from .transport import Location


class AttendanceType(str, Enum):
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"


class AttendanceRecord(BaseDBModel):
    user_id: str
    timestamp: datetime
    type: AttendanceType
    location: Optional[Location] = None
