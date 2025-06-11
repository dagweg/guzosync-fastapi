from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional, Dict, Any

from datetime import datetime, date

from core.dependencies import get_current_user
from models import User
from models.user import UserRole
from schemas.attendance import (
    MarkAttendanceRequest, AttendanceResponse, AttendanceStatus
)
from schemas.feedback import ReportIncidentRequest, IncidentResponse
from schemas.route import RouteChangeRequestRequest, RouteChangeResponse
from schemas.transport import InstructionResponse

from core import transform_mongo_doc

router = APIRouter(prefix="/api/drivers", tags=["drivers"])

@router.post("/attendance", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def mark_driver_attendance(
    request: Request,
    attendance_request: MarkAttendanceRequest,
    current_user: User = Depends(get_current_user)
):
    """Mark driver's attendance status"""
    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can mark their attendance"
        )

    # Check if attendance already exists for this date
    existing_attendance = await request.app.state.mongodb.attendance.find_one({
        "user_id": str(current_user.id),
        "date": attendance_request.date
    })

    if existing_attendance:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attendance already marked for {attendance_request.date}"
        )

    # Import here to avoid circular imports
    from models import Attendance, Location, AttendanceStatus as ModelAttendanceStatus
    from core.mongo_utils import model_to_mongo_doc

    # Create attendance record
    attendance = Attendance(
        user_id=str(current_user.id),
        date=attendance_request.date,
        status=ModelAttendanceStatus(attendance_request.status.value),
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
    attendance_doc = model_to_mongo_doc(attendance)
    result = await request.app.state.mongodb.attendance.insert_one(attendance_doc)
    created_attendance = await request.app.state.mongodb.attendance.find_one({"_id": result.inserted_id})

    return transform_mongo_doc(created_attendance, AttendanceResponse)

@router.get("/attendance", response_model=List[AttendanceResponse])
async def get_driver_attendance(
    request: Request,
    date_from: Optional[date] = Query(None, description="Start date"),
    date_to: Optional[date] = Query(None, description="End date"),
    current_user: User = Depends(get_current_user)
):
    """Get driver's attendance records"""

    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view their attendance"
        )

    # Build query
    query: Dict[str, Any] = {"user_id": str(current_user.id)}

    # Date range filter
    if date_from or date_to:
        date_filter: Dict[str, Any] = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        query["date"] = date_filter

    # Get records
    attendance_records = await request.app.state.mongodb.attendance.find(query).sort("date", -1).to_list(length=None)

    return [transform_mongo_doc(record, AttendanceResponse) for record in attendance_records]

@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def report_driver_incident(
    request: Request,
    incident_request: ReportIncidentRequest,
    current_user: User = Depends(get_current_user)
):
    """Report an incident as a driver"""
    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can report incidents"
        )

    # Import here to avoid circular imports
    from models import Incident, Location, IncidentSeverity, IncidentType
    from core.mongo_utils import model_to_mongo_doc

    # Create Incident model instance
    incident = Incident(
        reported_by_user_id=current_user.id,
        description=incident_request.description,
        incident_type=IncidentType(incident_request.incident_type.value),
        location=Location(
            latitude=incident_request.location.latitude,
            longitude=incident_request.location.longitude
        ) if incident_request.location else None,
        related_bus_id=incident_request.related_bus_id,
        related_route_id=incident_request.related_route_id,
        severity=IncidentSeverity(incident_request.severity.value)
    )

    # Convert to MongoDB document
    incident_data = model_to_mongo_doc(incident)

    result = await request.app.state.mongodb.incidents.insert_one(incident_data)
    created_incident = await request.app.state.mongodb.incidents.find_one({"_id": result.inserted_id})

    return transform_mongo_doc(created_incident, IncidentResponse)

@router.get("/incidents", response_model=List[IncidentResponse])
async def get_driver_incidents(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get incidents reported by the driver"""
    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view their incidents"
        )
    
    incidents = await request.app.state.mongodb.incidents.find(
        {"reported_by_user_id": current_user.id}
    ).sort("reported_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(incident, IncidentResponse) for incident in incidents]

@router.post("/route-change-requests", response_model=RouteChangeResponse, status_code=status.HTTP_201_CREATED)
async def create_route_change_request(
    request: Request,
    route_change_request: RouteChangeRequestRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a route change request"""
    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can request route changes"
        )

    # Import here to avoid circular imports
    from models import RouteChangeRequest
    from core.mongo_utils import model_to_mongo_doc

    # Create RouteChangeRequest model instance
    route_change = RouteChangeRequest(
        driver_id=current_user.id,
        current_route_id=route_change_request.current_route_id,
        requested_route_id=route_change_request.requested_route_id,
        reason=route_change_request.reason
    )

    # Convert to MongoDB document
    request_data = model_to_mongo_doc(route_change)

    result = await request.app.state.mongodb.route_change_requests.insert_one(request_data)
    created_request = await request.app.state.mongodb.route_change_requests.find_one({"_id": result.inserted_id})

    return transform_mongo_doc(created_request, RouteChangeResponse)

@router.get("/route-change-requests", response_model=List[RouteChangeResponse])
async def get_driver_route_change_requests(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get driver's route change requests"""
    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view their route change requests"
        )
    
    requests = await request.app.state.mongodb.route_change_requests.find(
        {"driver_id": current_user.id}
    ).sort("requested_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(req, RouteChangeResponse) for req in requests]

@router.get("/schedules", response_model=List[dict])
async def get_driver_schedules(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get driver's schedules"""
    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view their schedules"
        )
    
    schedules = await request.app.state.mongodb.schedules.find(
        {"driver_id": current_user.id}
    ).sort("start_time", 1).to_list(length=None)
    
    return schedules

@router.get("/routes/{route_id}/schedule", response_model=dict)
async def get_route_schedule(
    request: Request,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get schedule for a specific route"""
    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view route schedules"
        )
    
    schedule = await request.app.state.mongodb.schedules.find_one({
        "route_id": route_id,
        "driver_id": current_user.id
    })
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found for this route"
        )
    
    return schedule

@router.get("/instructions", response_model=List[InstructionResponse])
async def get_driver_instructions(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get instructions for the driver"""
    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view their instructions"
        )
    
    instructions = await request.app.state.mongodb.instructions.find(
        {"target_driver_id": current_user.id}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(instruction, InstructionResponse) for instruction in instructions]

@router.put("/instructions/{instruction_id}/acknowledge")
async def acknowledge_instruction(
    request: Request,
    instruction_id: str,
    current_user: User = Depends(get_current_user)
):
    """Acknowledge an instruction"""
    if current_user.role != UserRole.BUS_DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can acknowledge instructions"
        )
    
    result = await request.app.state.mongodb.instructions.update_one(
        {"_id": instruction_id, "target_driver_id": current_user.id},
        {
            "$set": {
                "acknowledged": True,
                "acknowledged_at": datetime.utcnow()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction not found or already acknowledged"
        )
    
    return {"message": "Instruction acknowledged successfully"}
