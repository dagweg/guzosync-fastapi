from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from .base import DateTimeModelMixin

class CreateRouteRequest(BaseModel):
    name: str
    description: Optional[str] = None
    stop_ids: List[UUID]
    total_distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    is_active: bool

class UpdateRouteRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    stop_ids: Optional[List[UUID]] = None
    total_distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    is_active: Optional[bool] = None

class RouteResponse(DateTimeModelMixin):
    id: str
    name: str
    description: Optional[str] = None
    stop_ids: List[UUID]
    total_distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    is_active: bool

class ScheduleResponse(DateTimeModelMixin):
    id: UUID
    route_id: UUID
    schedule_pattern: str
    departure_times: List[str]
    assigned_bus_id: Optional[UUID] = None
    assigned_driver_id: Optional[UUID] = None
    valid_from: datetime
    valid_until: Optional[datetime] = None
    is_active: bool