from typing import Optional, List
from pydantic import BaseModel, Field

from datetime import datetime, date
from enum import Enum
from .base import DateTimeModelMixin, Location


class AttendanceType(str, Enum):
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"


class CreateAttendanceRecordRequest(BaseModel):
    type: AttendanceType
    location: Optional[Location] = None


class AttendanceRecordResponse(BaseModel):
    id: str
    user_id: str
    timestamp: datetime
    type: AttendanceType
    location: Optional[Location] = None


class MarkDailyAttendanceRequest(BaseModel):
    """Request to mark daily attendance status"""
    user_id: str
    date: date
    status: AttendanceStatus
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    location: Optional[Location] = None
    notes: Optional[str] = None


class BulkAttendanceRequest(BaseModel):
    """Request to mark attendance for multiple users"""
    date: date
    attendance_records: List[MarkDailyAttendanceRequest]


class DailyAttendanceResponse(BaseModel):
    """Response for daily attendance record"""
    id: str
    user_id: str
    date: date
    status: AttendanceStatus
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    location: Optional[Location] = None
    notes: Optional[str] = None
    marked_by: Optional[str] = None
    marked_at: datetime


class AttendanceSummaryResponse(BaseModel):
    """Summary of attendance for a user over a period"""
    user_id: str
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    attendance_percentage: float
    records: List[DailyAttendanceResponse]


class UpdateAttendanceStatusRequest(BaseModel):
    """Request to update attendance status"""
    status: AttendanceStatus
    notes: Optional[str] = None