from typing import Optional
from pydantic import BaseModel
from enum import Enum

from .base import DateTimeModelMixin, Location

class ReallocationReason(str, Enum):
    OVERCROWDING = "OVERCROWDING"
    ROUTE_DISRUPTION = "ROUTE_DISRUPTION"
    MAINTENANCE_REQUIRED = "MAINTENANCE_REQUIRED"
    EMERGENCY = "EMERGENCY"
    SCHEDULE_OPTIMIZATION = "SCHEDULE_OPTIMIZATION"
    OTHER = "OTHER"

class ReallocationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"

class OvercrowdingSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RequestReallocationRequest(BaseModel):
    bus_id: str
    current_route_id: Optional[str]
    requested_route_id: Optional[str]
    reason: ReallocationReason
    description: str
    priority: Optional[str] = "NORMAL"  # NORMAL, HIGH, URGENT

class ReallocationRequestResponse(DateTimeModelMixin):
    id: str
    requested_by_user_id: str
    bus_id: str
    current_route_id: str
    requested_route_id: str
    reason: ReallocationReason
    description: str
    priority: str
    status: ReallocationStatus

class ReportOvercrowdingRequest(BaseModel):
    bus_stop_id: str
    bus_id: Optional[str] = None
    route_id: Optional[str] = None
    severity: OvercrowdingSeverity
    passenger_count: Optional[int] = None
    description: str
    location: Optional[Location] = None

class OvercrowdingReportResponse(DateTimeModelMixin):
    id: str
    reported_by_user_id: str
    bus_stop_id: str
    bus_id: Optional[str] = None
    route_id: Optional[str] = None
    severity: OvercrowdingSeverity
    passenger_count: Optional[int] = None
    description: str
    location: Optional[Location] = None
    is_resolved: bool = False
    resolution_notes: Optional[str] = None
