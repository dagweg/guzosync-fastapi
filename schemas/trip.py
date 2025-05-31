from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum
from .base import DateTimeModelMixin

class TripStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DELAYED = "DELAYED"

class SimplifiedTripResponse(BaseModel):
    id: UUID
    bus_id: UUID
    route_id: UUID
    driver_id: Optional[UUID] = None
    estimated_arrival_time: Optional[datetime] = None
    status: TripStatus

class TripResponse(DateTimeModelMixin):
    id: UUID
    bus_id: UUID
    route_id: UUID
    driver_id: Optional[UUID] = None
    schedule_id: Optional[UUID] = None
    actual_departure_time: Optional[datetime] = None
    actual_arrival_time: Optional[datetime] = None
    estimated_arrival_time: Optional[datetime] = None
    status: TripStatus
    passenger_ids: Optional[List[UUID]] = None
    feedback_ids: Optional[List[UUID]] = None