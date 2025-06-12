from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional, Dict, Any

from datetime import datetime, time, date, timedelta

from core.dependencies import get_current_user
from models import User, Attendance, AttendanceStatus, Location
from schemas.attendance import (
    MarkAttendanceRequest, BulkAttendanceRequest, AttendanceResponse,
    AttendanceSummaryResponse, UpdateAttendanceStatusRequest, AttendanceHeatmapResponse
)

from core import transform_mongo_doc
from core.mongo_utils import model_to_mongo_doc

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def mark_attendance(
    request: Request,
    attendance_request: MarkAttendanceRequest,
    current_user: User = Depends(get_current_user)
):
    """Mark attendance status for a user"""

    # Check if user has permission to mark attendance for others
    if attendance_request.user_id != str(current_user.id):
        if current_user.role not in ["CONTROL_ADMIN", "QUEUE_REGULATOR"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only mark your own attendance"
            )

    # Check if attendance already exists for this date
    existing_attendance = await request.app.state.mongodb.attendance.find_one({
        "user_id": attendance_request.user_id,
        "date": attendance_request.date
    })

    if existing_attendance:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attendance already marked for {attendance_request.date}"
        )

    # Create attendance record
    attendance = Attendance(
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
        marked_at=datetime.utcnow()
    )

    # Convert model to MongoDB document
    attendance_doc = model_to_mongo_doc(attendance)
    result = await request.app.state.mongodb.attendance.insert_one(attendance_doc)
    created_attendance = await request.app.state.mongodb.attendance.find_one({"_id": result.inserted_id})

    return transform_mongo_doc(created_attendance, AttendanceResponse)


@router.get("", response_model=List[AttendanceResponse])
async def get_attendance(
    request: Request,
    user_id: Optional[str] = Query(None, description="User ID (admin only)"),
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    attendance_status: Optional[AttendanceStatus] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user)
):
    """Get attendance records"""

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
    attendance_records = await request.app.state.mongodb.attendance.find(query).sort("date", -1).to_list(length=None)

    return [transform_mongo_doc(record, AttendanceResponse) for record in attendance_records]


@router.get("/heatmap", response_model=AttendanceHeatmapResponse)
async def get_attendance_heatmap(
    request: Request,
    user_id: Optional[str] = Query(None, description="User ID (admin only)"),
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    current_user: User = Depends(get_current_user)
):
    """Get attendance heatmap data for visualization"""

    try:
        # Determine target user
        target_user_id = user_id if user_id else str(current_user.id)

        # Check permissions
        if user_id and user_id != str(current_user.id):
            if current_user.role not in ["CONTROL_ADMIN", "QUEUE_REGULATOR"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own attendance heatmap"
                )

        # Set default date range (last 365 days if not specified)
        if not date_from:
            date_from = date.today() - timedelta(days=365)
        if not date_to:
            date_to = date.today()

        # Build query - MongoDB stores dates as datetime objects, so we need to convert
        # date objects to datetime for proper comparison
        from datetime import datetime as dt
        query = {
            "user_id": target_user_id,
            "date": {
                "$gte": dt.combine(date_from, time.min),
                "$lte": dt.combine(date_to, time.max)
            }
        }

        # Get attendance records
        attendance_records = await request.app.state.mongodb.attendance.find(query).to_list(length=None)

        # Create date-to-status mapping
        attendance_data: Dict[str, str] = {}
        for record in attendance_records:
            # Handle different date formats that might be stored
            record_date = record["date"]
            if hasattr(record_date, 'isoformat'):
                date_str = record_date.isoformat()
            elif isinstance(record_date, str):
                date_str = record_date
            else:
                # Convert to string if it's some other format
                date_str = str(record_date)
            attendance_data[date_str] = record["status"]

        return AttendanceHeatmapResponse(
            user_id=target_user_id,
            date_from=date_from,
            date_to=date_to,
            attendance_data=attendance_data
        )
    except Exception as e:
        # Log the error for debugging
        print(f"Error in attendance heatmap: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.put("/{attendance_id}", response_model=AttendanceResponse)
async def update_attendance(
    request: Request,
    attendance_id: str,
    update_request: UpdateAttendanceStatusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update attendance status"""

    # Find existing attendance record
    existing_attendance = await request.app.state.mongodb.attendance.find_one({"_id": attendance_id})
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
        "marked_at": datetime.utcnow()
    }

    if update_request.notes:
        update_data["notes"] = update_request.notes

    await request.app.state.mongodb.attendance.update_one(
        {"_id": attendance_id},
        {"$set": update_data}
    )

    # Return updated record
    updated_attendance = await request.app.state.mongodb.attendance.find_one({"_id": attendance_id})
    return transform_mongo_doc(updated_attendance, AttendanceResponse)


@router.post("/bulk", response_model=List[AttendanceResponse])
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
            existing = await request.app.state.mongodb.attendance.find_one({
                "user_id": attendance_req.user_id,
                "date": bulk_request.date
            })

            if existing:
                errors.append(f"Attendance already exists for user {attendance_req.user_id} on {bulk_request.date}")
                continue

            # Create attendance record
            attendance = Attendance(
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
                marked_at=datetime.utcnow()
            )

            # Insert record
            attendance_doc = model_to_mongo_doc(attendance)
            result = await request.app.state.mongodb.attendance.insert_one(attendance_doc)
            created_attendance = await request.app.state.mongodb.attendance.find_one({"_id": result.inserted_id})
            created_records.append(transform_mongo_doc(created_attendance, AttendanceResponse))

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
    attendance_records = await request.app.state.mongodb.attendance.find(query).sort("date", -1).to_list(length=None)

    # Calculate summary statistics
    total_days = len(attendance_records)
    present_days = len([r for r in attendance_records if r["status"] == "PRESENT"])
    absent_days = len([r for r in attendance_records if r["status"] == "ABSENT"])
    late_days = len([r for r in attendance_records if r["status"] == "LATE"])

    attendance_percentage = (present_days + late_days) / total_days * 100 if total_days > 0 else 0

    # Transform records
    transformed_records = [transform_mongo_doc(record, AttendanceResponse) for record in attendance_records]

    return AttendanceSummaryResponse(
        user_id=target_user_id,
        total_days=total_days,
        present_days=present_days,
        absent_days=absent_days,
        late_days=late_days,
        attendance_percentage=round(attendance_percentage, 2),
        records=transformed_records
    )


@router.delete("/{attendance_id}")
async def delete_attendance(
    request: Request,
    attendance_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete attendance record (admin only)"""

    # Check admin permissions
    if current_user.role not in ["CONTROL_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete attendance records"
        )

    # Find and delete the record
    result = await request.app.state.mongodb.attendance.delete_one({"_id": attendance_id})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    return {"message": "Attendance record deleted successfully"}

