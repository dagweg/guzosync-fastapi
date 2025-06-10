from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List

from datetime import datetime, time

from core.dependencies import get_current_user
from models import User, AttendanceRecord, AttendanceType, Location
from schemas.attendance import CreateAttendanceRecordRequest, AttendanceRecordResponse

from core import transform_mongo_doc
from core.mongo_utils import model_to_mongo_doc

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

@router.post("", response_model=AttendanceRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_attendance_record(
    request: Request,
    attendance_request: CreateAttendanceRecordRequest, 
    current_user: User = Depends(get_current_user)
):    # Create AttendanceRecord model instance
    attendance_record = AttendanceRecord(
        user_id=current_user.id,
        timestamp=datetime.utcnow(),
        type=AttendanceType(attendance_request.type.value),
        location=Location(
            latitude=attendance_request.location.latitude,
            longitude=attendance_request.location.longitude
        ) if attendance_request.location else None
    )
    
    # Convert model to MongoDB document
    attendance_doc = model_to_mongo_doc(attendance_record)
    result = await request.app.state.mongodb.attendance.insert_one(attendance_doc)
    created_attendance = await request.app.state.mongodb.attendance.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_attendance, AttendanceRecordResponse)

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
    
    return [transform_mongo_doc(record, AttendanceRecordResponse) for record in attendance_records]