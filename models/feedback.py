from typing import Optional

from enum import Enum

from models.transport import Location
from .base import BaseDBModel
from core.custom_types import UUID

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Feedback(BaseDBModel):
    submitted_by_user_id: UUID
    content: str
    rating: Optional[float] = None
    related_trip_id: Optional[UUID] = None
    related_bus_id: Optional[UUID] = None

class Incident(BaseDBModel):
    reported_by_user_id: UUID
    description: str
    location: Optional[Location] = None
    related_bus_id: Optional[UUID] = None
    related_route_id: Optional[UUID] = None
    is_resolved: bool = False
    resolution_notes: Optional[str] = None
    severity: IncidentSeverity