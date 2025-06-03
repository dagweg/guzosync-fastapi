from typing import Optional, List
from pydantic import BaseModel

from datetime import datetime
from .base import DateTimeModelMixin

class CreateRouteRequest(BaseModel):
    name: str
    description: Optional[str] = None
    stop_ids: List[str]
    total_distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    is_active: bool

    

class UpdateRouteRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    stop_ids: Optional[List[str]] = None
    total_distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    is_active: Optional[bool] = None

    

class RouteResponse(DateTimeModelMixin):
    id: str
    name: str
    description: Optional[str] = None
    stop_ids: List[str]
    total_distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    is_active: bool

class ScheduleResponse(DateTimeModelMixin):
    id: str
    route_id: str
    schedule_pattern: str
    departure_times: List[str]
    assigned_bus_id: Optional[str] = None
    assigned_driver_id: Optional[str] = None
    valid_from: datetime
    valid_until: Optional[datetime] = None
    is_active: bool

# Route change request schemas
class RouteChangeRequestRequest(BaseModel):
    current_route_id: str
    requested_route_id: str
    reason: str

    

class RouteChangeResponse(DateTimeModelMixin):
    id: str
    driver_id: str
    current_route_id: str
    requested_route_id: str
    reason: str
    status: str  # PENDING, APPROVED, REJECTED
    requested_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None