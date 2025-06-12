from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from datetime import datetime, date
from enum import Enum
from .base import DateTimeModelMixin
from models.base import Location


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"


class MarkAttendanceRequest(BaseModel):
    """Request to mark attendance status"""
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
    attendance_records: List[MarkAttendanceRequest]


class AttendanceResponse(BaseModel):
    """Response for attendance record"""
    id: str
    user_id: str
    date: date
    status: AttendanceStatus
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    location: Optional[Location] = None
    notes: Optional[str] = None
    marked_at: datetime


class AttendanceSummaryResponse(BaseModel):
    """Summary of attendance for a user over a period"""
    user_id: str
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    attendance_percentage: float
    records: List[AttendanceResponse]


class UpdateAttendanceStatusRequest(BaseModel):
    """Request to update attendance status"""
    status: AttendanceStatus
    notes: Optional[str] = None


class AttendanceHeatmapResponse(BaseModel):
    """Response for attendance heatmap data"""
    user_id: str
    date_from: date
    date_to: date
    attendance_data: Dict[str, str]  # date string -> status string mapping