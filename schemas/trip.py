from typing import Optional, List
from pydantic import BaseModel
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
    id: str
    bus_id: str
    route_id: str
    driver_id: Optional[str] = None
    estimated_arrival_time: Optional[datetime] = None
    status: TripStatus

class TripResponse(DateTimeModelMixin):
    id: str
    bus_id: str
    route_id: str
    driver_id: Optional[str] = None
    schedule_id: Optional[str] = None
    actual_departure_time: Optional[datetime] = None
    actual_arrival_time: Optional[datetime] = None
    estimated_arrival_time: Optional[datetime] = None
    status: TripStatus
    passenger_ids: Optional[List[str]] = None
    feedback_ids: Optional[List[str]] = None