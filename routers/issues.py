from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from uuid import UUID

from models import User, Incident
from schemas.feedback import ReportIncidentRequest, IncidentResponse
from routers.accounts import get_current_user

router = APIRouter(prefix="/api/issues", tags=["issues"])

@router.post("/report", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def report_issue(request: ReportIncidentRequest, current_user: User = Depends(get_current_user)):
    from fastapi import Request
    request_obj = Request
    
    incident = Incident(
        reported_by_user_id=current_user.id,
        description=request.description,
        location=request.location,
        related_bus_id=request.related_bus_id,
        related_route_id=request.related_route_id,
        severity=request.severity
    )
    
    result = await request_obj.app.mongodb.incidents.insert_one(incident.dict())
    created_incident = await request_obj.app.mongodb.incidents.find_one({"_id": result.inserted_id})
    
    return IncidentResponse(**created_incident)

@router.get("", response_model=List[IncidentResponse])
async def get_issues(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    from fastapi import Request
    request = Request
    
    # For regular users, only show their own reported incidents
    query = {"reported_by_user_id": current_user.id}
    
    # For admins, show all incidents
    if current_user.role in ["CONTROL_CENTER_ADMIN", "REGULATOR"]:
        query = {}
    
    incidents = await request.app.mongodb.incidents.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    return [IncidentResponse(**incident) for incident in incidents]