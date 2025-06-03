from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum

from .base import BaseDBModel


class TripStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DELAYED = "DELAYED"

class Trip(BaseDBModel):
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

class Schedule(BaseDBModel):
    route_id: str
    schedule_pattern: str
    departure_times: List[str]
    assigned_bus_id: Optional[str] = None
    assigned_driver_id: Optional[str] = None
    valid_from: datetime
    valid_until: Optional[datetime] = None
    is_active: bool = True