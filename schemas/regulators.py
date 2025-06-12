from typing import Optional
from pydantic import BaseModel
from enum import Enum

from .base import DateTimeModelMixin
from models.base import Location

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
    requested_route_id: Optional[str] = None
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

class ReallocationHistoryResponse(DateTimeModelMixin):
    id: str
    bus_id: str
    bus_number: Optional[str] = None  # Bus license plate/number for display
    old_route_id: Optional[str] = None
    old_route_name: Optional[str] = None
    new_route_id: Optional[str] = None
    new_route_name: Optional[str] = None
    reason: Optional[ReallocationReason] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: ReallocationStatus
    requested_by_user_id: Optional[str] = None  # For formal requests
    requested_by_name: Optional[str] = None
    reallocated_by: Optional[str] = None  # For direct reallocations
    reallocated_by_name: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[str] = None
    reallocated_at: Optional[str] = None  # For direct reallocations
    review_notes: Optional[str] = None
    reallocation_type: Optional[str] = None  # "FORMAL_REQUEST" or "DIRECT_REALLOCATION"

class ReallocationAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    PENDING = "PENDING"

class ReviewReallocationRequest(BaseModel):
    action: ReallocationAction
    route_id: Optional[str] = None  # Required for APPROVE action
    reason: Optional[str] = None  # Optional reason/notes for any action
    reallocated_at: Optional[str] = None  # For direct reallocations
    review_notes: Optional[str] = None
    reallocation_type: str  # "FORMAL_REQUEST" or "DIRECT_REALLOCATION"
