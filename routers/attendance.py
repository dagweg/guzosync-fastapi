from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime, time
from uuid import UUID

from models import User
from schemas.attendance import CreateAttendanceRecordRequest, AttendanceRecordResponse
from routers.accounts import get_current_user

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

@router.post("", response_model=AttendanceRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_attendance_record(request: CreateAttendanceRecordRequest, current_user: User = Depends(get_current_user)):
    from fastapi import Request
    request_obj = Request
    
    # Create attendance record
    attendance = {
        "user_id": current_user.id,
        "timestamp": datetime.utcnow(),
        "type": request.type,
        "location": request.location.dict() if request.location else None
    }
    
    result = await request_obj.app.mongodb.attendance.insert_one(attendance)
    created_attendance = await request_obj.app.mongodb.attendance.find_one({"_id": result.inserted_id})
    
    return AttendanceRecordResponse(**created_attendance)

@router.get("/today", response_model=List[AttendanceRecordResponse])
async def get_today_attendance(current_user: User = Depends(get_current_user)):
    
    
    # Get today's date range
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)
    
    # Query attendance records for today
    attendance_records = await request.app.mongodb.attendance.find({
        "user_id": current_user.id,
        "timestamp": {"$gte": start_of_day, "$lte": end_of_day}
    }).to_list(length=None)
    
    return [AttendanceRecordResponse(**record) for record in attendance_records]