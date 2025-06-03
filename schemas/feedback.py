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

class ReportIncidentRequest(BaseModel):
    description: str
    location: Optional[Location] = None
    related_bus_id: Optional[str] = None
    related_route_id: Optional[str] = None
    severity: IncidentSeverity

class UpdateIncidentRequest(BaseModel):
    description: Optional[str] = None
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
    location: Optional[Location] = None
    related_bus_id: Optional[str] = None
    related_route_id: Optional[str] = None
    is_resolved: bool
    resolution_notes: Optional[str] = None
    severity: IncidentSeverity