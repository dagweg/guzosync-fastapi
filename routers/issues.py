from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List


from core.dependencies import get_current_user
from models import User, Incident, Location, IncidentSeverity, IncidentType
from schemas.feedback import ReportIncidentRequest, IncidentResponse

from core import transform_mongo_doc
from core.mongo_utils import model_to_mongo_doc

router = APIRouter(prefix="/api/issues", tags=["issues"])

@router.post("/report", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def report_issue(
    request: Request,
    incident_request: ReportIncidentRequest, 
    current_user: User = Depends(get_current_user)
):
    """Report a new incident"""
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
    
    # Convert model to MongoDB document
    incident_doc = model_to_mongo_doc(incident)
    result = await request.app.state.mongodb.incidents.insert_one(incident_doc)
    created_incident = await request.app.state.mongodb.incidents.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_incident, IncidentResponse)

@router.get("", response_model=List[IncidentResponse])
async def get_issues(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    # For regular users, only show their own reported incidents
    query = {"reported_by_user_id": current_user.id}
      # For admins, show all incidents
    if current_user.role in ["CONTROL_CENTER_ADMIN", "REGULATOR"]:
        query = {}
    
    incidents = await request.app.state.mongodb.incidents.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(incident, IncidentResponse) for incident in incidents]