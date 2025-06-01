from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from enum import Enum
from .base import DateTimeModelMixin, Location

class SubmitFeedbackRequest(BaseModel):
    content: str
    rating: Optional[float] = None
    related_trip_id: Optional[UUID] = None
    related_bus_id: Optional[UUID] = None

class FeedbackResponse(DateTimeModelMixin):
    id: str
    submitted_by_user_id: UUID
    content: str
    rating: Optional[float] = None
    related_trip_id: Optional[UUID] = None
    related_bus_id: Optional[UUID] = None

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ReportIncidentRequest(BaseModel):
    description: str
    location: Optional[Location] = None
    related_bus_id: Optional[UUID] = None
    related_route_id: Optional[UUID] = None
    severity: IncidentSeverity

class UpdateIncidentRequest(BaseModel):
    description: Optional[str] = None
    location: Optional[Location] = None
    related_bus_id: Optional[UUID] = None
    related_route_id: Optional[UUID] = None
    is_resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None
    severity: Optional[IncidentSeverity] = None

class IncidentResponse(DateTimeModelMixin):
    id: UUID
    reported_by_user_id: UUID
    description: str
    location: Optional[Location] = None
    related_bus_id: Optional[UUID] = None
    related_route_id: Optional[UUID] = None
    is_resolved: bool
    resolution_notes: Optional[str] = None
    severity: IncidentSeverity