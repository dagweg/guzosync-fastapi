from typing import Optional
from enum import Enum

from models.transport import Location
from .base import BaseDBModel

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

class ReallocationRequest(BaseDBModel):
    requested_by_user_id: str
    bus_id: str
    current_route_id: str
    requested_route_id: Optional[str] = None  # AI agent will determine optimal route
    reason: ReallocationReason
    description: str
    priority: str = "NORMAL"  # NORMAL, HIGH, URGENT
    status: ReallocationStatus = ReallocationStatus.PENDING
    reviewed_by: Optional[str] = None  # Admin user ID who reviewed
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None

class OvercrowdingReport(BaseDBModel):
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
    resolved_by: Optional[str] = None  # Admin user ID who resolved
    resolved_at: Optional[str] = None
