from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List
from uuid import UUID
from datetime import datetime, time

from models import User
from schemas.attendance import CreateAttendanceRecordRequest, AttendanceRecordResponse
from core.dependencies import get_current_user

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

@router.post("", response_model=AttendanceRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_attendance_record(
    request: Request,
    attendance_request: CreateAttendanceRecordRequest, 
    current_user: User = Depends(get_current_user)
):
    # Create attendance record
    attendance_data = {
        "user_id": current_user.id,
        "timestamp": datetime.utcnow(),
        "type": attendance_request.type,
        "location": attendance_request.location.dict() if attendance_request.location else None
    }
    
    result = await request.app.state.mongodb.attendance.insert_one(attendance_data)
    created_attendance = await request.app.state.mongodb.attendance.find_one({"_id": result.inserted_id})
    
    return AttendanceRecordResponse(**created_attendance)

@router.get("/today", response_model=List[AttendanceRecordResponse])
async def get_today_attendance(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # Get today's date range
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)
    
    # Query attendance records for today
    attendance_records = await request.app.state.mongodb.attendance.find({
        "user_id": current_user.id,
        "timestamp": {"$gte": start_of_day, "$lte": end_of_day}
    }).to_list(length=None)
    
    return [AttendanceRecordResponse(**record) for record in attendance_records]