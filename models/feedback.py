from typing import Optional

from enum import Enum

from models.transport import Location
from .base import BaseDBModel

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentType(str, Enum):
    VEHICLE_ISSUE = "VEHICLE_ISSUE"
    SAFETY_CONCERN = "SAFETY_CONCERN"
    OTHER = "OTHER"

class Feedback(BaseDBModel):
    submitted_by_user_id: str
    content: str
    rating: Optional[float] = None
    related_trip_id: Optional[str] = None
    related_bus_id: Optional[str] = None

class Incident(BaseDBModel):
    reported_by_user_id: str
    description: str
    incident_type: IncidentType
    location: Optional[Location] = None
    related_bus_id: Optional[str] = None
    related_route_id: Optional[str] = None
    is_resolved: bool = False
    resolution_notes: Optional[str] = None
    severity: IncidentSeverity