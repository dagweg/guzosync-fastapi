from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional, Dict, Any

from datetime import datetime, time, date, timedelta

from core.dependencies import get_current_user
from models import User, AttendanceRecord, AttendanceType, AttendanceStatus, DailyAttendance, Location
from schemas.attendance import (
    CreateAttendanceRecordRequest, AttendanceRecordResponse,
    MarkDailyAttendanceRequest, BulkAttendanceRequest, DailyAttendanceResponse,
    AttendanceSummaryResponse, UpdateAttendanceStatusRequest
)

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


# ===== NEW STATUS-BASED ATTENDANCE ENDPOINTS =====

@router.post("/daily", response_model=DailyAttendanceResponse, status_code=status.HTTP_201_CREATED)
async def mark_daily_attendance(
    request: Request,
    attendance_request: MarkDailyAttendanceRequest,
    current_user: User = Depends(get_current_user)
):
    """Mark daily attendance status for a user"""

    # Check if user has permission to mark attendance for others
    if attendance_request.user_id != str(current_user.id):
        if current_user.role not in ["CONTROL_ADMIN", "QUEUE_REGULATOR"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only mark your own attendance"
            )

    # Check if attendance already exists for this date
    existing_attendance = await request.app.state.mongodb.daily_attendance.find_one({
        "user_id": attendance_request.user_id,
        "date": attendance_request.date
    })

    if existing_attendance:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attendance already marked for {attendance_request.date}"
        )

    # Create daily attendance record
    daily_attendance = DailyAttendance(
        user_id=attendance_request.user_id,
        date=attendance_request.date,
        status=AttendanceStatus(attendance_request.status.value),
        check_in_time=attendance_request.check_in_time,
        check_out_time=attendance_request.check_out_time,
        location=Location(
            latitude=attendance_request.location.latitude,
            longitude=attendance_request.location.longitude
        ) if attendance_request.location else None,
        notes=attendance_request.notes,
        marked_by=str(current_user.id),
        marked_at=datetime.utcnow()
    )

    # Convert model to MongoDB document
    attendance_doc = model_to_mongo_doc(daily_attendance)
    result = await request.app.state.mongodb.daily_attendance.insert_one(attendance_doc)
    created_attendance = await request.app.state.mongodb.daily_attendance.find_one({"_id": result.inserted_id})

    return transform_mongo_doc(created_attendance, DailyAttendanceResponse)


@router.get("/daily", response_model=List[DailyAttendanceResponse])
async def get_daily_attendance(
    request: Request,
    user_id: Optional[str] = Query(None, description="User ID (admin only)"),
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    attendance_status: Optional[AttendanceStatus] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user)
):
    """Get daily attendance records"""

    # Build query
    query: Dict[str, Any] = {}

    # User filter
    if user_id:
        if current_user.role not in ["CONTROL_ADMIN", "QUEUE_REGULATOR"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own attendance"
            )
        query["user_id"] = user_id
    else:
        query["user_id"] = str(current_user.id)

    # Date range filter
    if date_from or date_to:
        date_filter: Dict[str, Any] = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        query["date"] = date_filter

    # Status filter
    if attendance_status:
        query["status"] = attendance_status

    # Get records
    attendance_records = await request.app.state.mongodb.daily_attendance.find(query).sort("date", -1).to_list(length=None)

    return [transform_mongo_doc(record, DailyAttendanceResponse) for record in attendance_records]


@router.put("/daily/{attendance_id}", response_model=DailyAttendanceResponse)
async def update_daily_attendance(
    request: Request,
    attendance_id: str,
    update_request: UpdateAttendanceStatusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update daily attendance status"""

    # Find existing attendance record
    existing_attendance = await request.app.state.mongodb.daily_attendance.find_one({"_id": attendance_id})
    if not existing_attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    # Check permissions
    if existing_attendance["user_id"] != str(current_user.id):
        if current_user.role not in ["CONTROL_ADMIN", "QUEUE_REGULATOR"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own attendance"
            )

    # Update the record
    update_data = {
        "status": update_request.status,
        "marked_by": str(current_user.id),
        "marked_at": datetime.utcnow()
    }

    if update_request.notes:
        update_data["notes"] = update_request.notes

    await request.app.state.mongodb.daily_attendance.update_one(
        {"_id": attendance_id},
        {"$set": update_data}
    )

    # Return updated record
    updated_attendance = await request.app.state.mongodb.daily_attendance.find_one({"_id": attendance_id})
    return transform_mongo_doc(updated_attendance, DailyAttendanceResponse)


@router.post("/bulk", response_model=List[DailyAttendanceResponse])
async def mark_bulk_attendance(
    request: Request,
    bulk_request: BulkAttendanceRequest,
    current_user: User = Depends(get_current_user)
):
    """Mark attendance for multiple users (admin only)"""

    # Check admin permissions
    if current_user.role not in ["CONTROL_ADMIN", "QUEUE_REGULATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can mark bulk attendance"
        )

    created_records = []
    errors = []

    for attendance_req in bulk_request.attendance_records:
        try:
            # Check if attendance already exists
            existing = await request.app.state.mongodb.daily_attendance.find_one({
                "user_id": attendance_req.user_id,
                "date": bulk_request.date
            })

            if existing:
                errors.append(f"Attendance already exists for user {attendance_req.user_id} on {bulk_request.date}")
                continue

            # Create attendance record
            daily_attendance = DailyAttendance(
                user_id=attendance_req.user_id,
                date=bulk_request.date,
                status=AttendanceStatus(attendance_req.status.value),
                check_in_time=attendance_req.check_in_time,
                check_out_time=attendance_req.check_out_time,
                location=Location(
                    latitude=attendance_req.location.latitude,
                    longitude=attendance_req.location.longitude
                ) if attendance_req.location else None,
                notes=attendance_req.notes,
                marked_by=str(current_user.id),
                marked_at=datetime.utcnow()
            )

            # Insert record
            attendance_doc = model_to_mongo_doc(daily_attendance)
            result = await request.app.state.mongodb.daily_attendance.insert_one(attendance_doc)
            created_attendance = await request.app.state.mongodb.daily_attendance.find_one({"_id": result.inserted_id})
            created_records.append(transform_mongo_doc(created_attendance, DailyAttendanceResponse))

        except Exception as e:
            errors.append(f"Error creating attendance for user {attendance_req.user_id}: {str(e)}")

    if errors and not created_records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create any attendance records. Errors: {'; '.join(errors)}"
        )

    return created_records


@router.get("/summary", response_model=AttendanceSummaryResponse)
async def get_attendance_summary(
    request: Request,
    user_id: Optional[str] = Query(None, description="User ID (admin only)"),
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    current_user: User = Depends(get_current_user)
):
    """Get attendance summary for a user over a period"""

    # Determine target user
    target_user_id = user_id if user_id else str(current_user.id)

    # Check permissions
    if user_id and user_id != str(current_user.id):
        if current_user.role not in ["CONTROL_ADMIN", "QUEUE_REGULATOR"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own attendance summary"
            )

    # Set default date range (last 30 days if not specified)
    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()

    # Build query
    query = {
        "user_id": target_user_id,
        "date": {"$gte": date_from, "$lte": date_to}
    }

    # Get attendance records
    attendance_records = await request.app.state.mongodb.daily_attendance.find(query).sort("date", -1).to_list(length=None)

    # Calculate summary statistics
    total_days = len(attendance_records)
    present_days = len([r for r in attendance_records if r["status"] == "PRESENT"])
    absent_days = len([r for r in attendance_records if r["status"] == "ABSENT"])
    late_days = len([r for r in attendance_records if r["status"] == "LATE"])

    attendance_percentage = (present_days + late_days) / total_days * 100 if total_days > 0 else 0

    # Transform records
    transformed_records = [transform_mongo_doc(record, DailyAttendanceResponse) for record in attendance_records]

    return AttendanceSummaryResponse(
        user_id=target_user_id,
        total_days=total_days,
        present_days=present_days,
        absent_days=absent_days,
        late_days=late_days,
        attendance_percentage=round(attendance_percentage, 2),
        records=transformed_records
    )


@router.delete("/daily/{attendance_id}")
async def delete_daily_attendance(
    request: Request,
    attendance_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete daily attendance record (admin only)"""

    # Check admin permissions
    if current_user.role not in ["CONTROL_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete attendance records"
        )

    # Find and delete the record
    result = await request.app.state.mongodb.daily_attendance.delete_one({"_id": attendance_id})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    return {"message": "Attendance record deleted successfully"}


# ===== UTILITY ENDPOINTS =====

@router.post("/auto-mark")
async def auto_mark_attendance_from_checkin(
    request: Request,
    target_date: Optional[date] = Query(None, description="Date to process (default: today)"),
    current_user: User = Depends(get_current_user)
):
    """Automatically mark attendance based on check-in/check-out records"""

    # Check admin permissions
    if current_user.role not in ["CONTROL_ADMIN", "QUEUE_REGULATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can auto-mark attendance"
        )

    process_date = target_date if target_date else date.today()

    # Get all check-in records for the date
    start_of_day = datetime.combine(process_date, time.min)
    end_of_day = datetime.combine(process_date, time.max)

    checkin_records = await request.app.state.mongodb.attendance.find({
        "type": "CHECK_IN",
        "timestamp": {"$gte": start_of_day, "$lte": end_of_day}
    }).to_list(length=None)

    # Define late threshold (e.g., 9:00 AM)
    late_threshold = datetime.combine(process_date, time(9, 0))

    processed_users = []
    errors = []

    for checkin in checkin_records:
        try:
            user_id = checkin["user_id"]
            checkin_time = checkin["timestamp"]

            # Check if daily attendance already exists
            existing = await request.app.state.mongodb.daily_attendance.find_one({
                "user_id": user_id,
                "date": process_date
            })

            if existing:
                continue  # Skip if already marked

            # Determine status based on check-in time
            attendance_status = AttendanceStatus.LATE if checkin_time > late_threshold else AttendanceStatus.PRESENT

            # Look for corresponding check-out
            checkout_record = await request.app.state.mongodb.attendance.find_one({
                "user_id": user_id,
                "type": "CHECK_OUT",
                "timestamp": {"$gte": checkin_time, "$lte": end_of_day}
            })

            # Create daily attendance record
            daily_attendance = DailyAttendance(
                user_id=user_id,
                date=process_date,
                status=attendance_status,
                check_in_time=checkin_time,
                check_out_time=checkout_record["timestamp"] if checkout_record else None,
                location=Location(
                    latitude=checkin["location"]["latitude"],
                    longitude=checkin["location"]["longitude"]
                ) if checkin.get("location") else None,
                notes=f"Auto-marked from check-in record",
                marked_by=str(current_user.id),
                marked_at=datetime.utcnow()
            )

            # Insert record
            attendance_doc = model_to_mongo_doc(daily_attendance)
            await request.app.state.mongodb.daily_attendance.insert_one(attendance_doc)
            processed_users.append(user_id)

        except Exception as e:
            errors.append(f"Error processing user {checkin.get('user_id', 'unknown')}: {str(e)}")

    return {
        "message": f"Auto-marked attendance for {len(processed_users)} users on {process_date}",
        "processed_users": processed_users,
        "errors": errors if errors else None
    }