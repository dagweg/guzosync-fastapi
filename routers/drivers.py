from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from core.dependencies import get_current_user
from models import User
from schemas.attendance import CreateAttendanceRecordRequest, AttendanceRecordResponse
from schemas.feedback import ReportIncidentRequest, IncidentResponse
from schemas.route import RouteChangeRequestRequest, RouteChangeResponse
from schemas.transport import InstructionResponse

from core import transform_mongo_doc

router = APIRouter(prefix="/api/drivers", tags=["drivers"])

@router.post("/attendance", response_model=AttendanceRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_driver_attendance(
    request: Request,
    attendance_request: CreateAttendanceRecordRequest, 
    current_user: User = Depends(get_current_user)
):
    """Create driver attendance record"""
    if current_user.role != "DRIVER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can create attendance records"
        )
    
    attendance_data = {
        "user_id": current_user.id,
        "type": attendance_request.type,
        "location": attendance_request.location,
        "timestamp": datetime.utcnow()
    }
    
    result = await request.app.state.mongodb.attendance.insert_one(attendance_data)
    created_attendance = await request.app.state.mongodb.attendance.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_attendance, AttendanceRecordResponse)

@router.get("/attendance/today", response_model=List[AttendanceRecordResponse])
async def get_driver_attendance_today(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get driver's attendance records for today"""
    if current_user.role != "DRIVER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view their attendance"
        )
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    attendance_records = await request.app.state.mongodb.attendance.find({
        "user_id": current_user.id,
        "timestamp": {"$gte": today_start, "$lte": today_end}
    }).sort("timestamp", -1).to_list(length=None)
    
    return [transform_mongo_doc(record, AttendanceRecordResponse) for record in attendance_records]

@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def report_driver_incident(
    request: Request,
    incident_request: ReportIncidentRequest, 
    current_user: User = Depends(get_current_user)
):
    """Report an incident as a driver"""
    if current_user.role != "DRIVER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can report incidents"
        )
    
    incident_data = {
        "reported_by_user_id": current_user.id,
        "description": incident_request.description,
        "severity": incident_request.severity,
        "location": incident_request.location,
        "related_bus_id": incident_request.related_bus_id,
        "related_route_id": incident_request.related_route_id,
        "status": "REPORTED",
        "reported_at": datetime.utcnow()
    }
    
    result = await request.app.state.mongodb.incidents.insert_one(incident_data)
    created_incident = await request.app.state.mongodb.incidents.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_incident, IncidentResponse)

@router.get("/incidents", response_model=List[IncidentResponse])
async def get_driver_incidents(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get incidents reported by the driver"""
    if current_user.role != "DRIVER":
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
    if current_user.role != "DRIVER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can request route changes"
        )
    
    request_data = {
        "driver_id": current_user.id,
        "current_route_id": route_change_request.current_route_id,
        "requested_route_id": route_change_request.requested_route_id,
        "reason": route_change_request.reason,
        "status": "PENDING",
        "requested_at": datetime.utcnow()
    }
    
    result = await request.app.state.mongodb.route_change_requests.insert_one(request_data)
    created_request = await request.app.state.mongodb.route_change_requests.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_request, RouteChangeResponse)

@router.get("/route-change-requests", response_model=List[RouteChangeResponse])
async def get_driver_route_change_requests(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get driver's route change requests"""
    if current_user.role != "DRIVER":
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
    if current_user.role != "DRIVER":
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
    route_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get schedule for a specific route"""
    if current_user.role != "DRIVER":
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
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get instructions for the driver"""
    if current_user.role != "DRIVER":
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
    instruction_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Acknowledge an instruction"""
    if current_user.role != "DRIVER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can acknowledge instructions"
        )
    
    result = await request.app.state.mongodb.instructions.update_one(
        {"id": instruction_id, "target_driver_id": current_user.id},
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
