from typing import Optional
from pydantic import BaseModel

from enum import Enum
from .base import DateTimeModelMixin, Location

class SubmitFeedbackRequest(BaseModel):
    content: str
    rating: Optional[float] = None
    related_trip_id: Optional[str] = None
    related_bus_id: Optional[str] = None

class FeedbackResponse(DateTimeModelMixin):
    id: str
    submitted_by_user_id: str
    content: str
    rating: Optional[float] = None
    related_trip_id: Optional[str] = None
    related_bus_id: Optional[str] = None

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentType(str, Enum):
    VEHICLE_ISSUE = "VEHICLE_ISSUE"
    SAFETY_CONCERN = "SAFETY_CONCERN"
    OTHER = "OTHER"

class ReportIncidentRequest(BaseModel):
    description: str
    incident_type: IncidentType
    location: Optional[Location] = None
    related_bus_id: Optional[str] = None
    related_route_id: Optional[str] = None
    severity: IncidentSeverity

class UpdateIncidentRequest(BaseModel):
    description: Optional[str] = None
    incident_type: Optional[IncidentType] = None
    location: Optional[Location] = None
    related_bus_id: Optional[str] = None
    related_route_id: Optional[str] = None
    is_resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None
    severity: Optional[IncidentSeverity] = None

class IncidentResponse(DateTimeModelMixin):
    id: str
    reported_by_user_id: str
    description: str
    incident_type: IncidentType
    location: Optional[Location] = None
    related_bus_id: Optional[str] = None
    related_route_id: Optional[str] = None
    is_resolved: bool
    resolution_notes: Optional[str] = None
    severity: IncidentSeverity