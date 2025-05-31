from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum
from uuid import UUID
from .base import BaseDBModel

class Location(BaseModel):
    latitude: float
    longitude: float

class BusType(str, Enum):
    STANDARD = "STANDARD"
    ARTICULATED = "ARTICULATED"
    MINIBUS = "MINIBUS"

class BusStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    BREAKDOWN = "BREAKDOWN"
    IDLE = "IDLE"

class Bus(BaseDBModel):
    license_plate: str
    bus_type: BusType
    capacity: int
    current_location: Optional[Location] = None
    last_location_update: Optional[datetime] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    location_accuracy: Optional[float] = None
    current_address: Optional[str] = None
    assigned_route_id: Optional[UUID] = None
    assigned_driver_id: Optional[UUID] = None
    bus_status: BusStatus
    manufacture_year: Optional[int] = None
    bus_model: Optional[str] = None

class BusStop(BaseDBModel):
    name: str
    location: Location
    capacity: Optional[int] = None
    is_active: bool = True

class Route(BaseDBModel):
    name: str
    description: Optional[str] = None
    stop_ids: List[UUID]
    total_distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    is_active: bool = True