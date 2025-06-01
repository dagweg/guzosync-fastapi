from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
from enum import Enum
from datetime import datetime
from .base import DateTimeModelMixin, Location

class BusType(str, Enum):
    STANDARD = "STANDARD"
    ARTICULATED = "ARTICULATED"
    MINIBUS = "MINIBUS"

class BusStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    BREAKDOWN = "BREAKDOWN"
    IDLE = "IDLE"

class CreateBusRequest(BaseModel):
    license_plate: str
    bus_type: BusType
    capacity: int
    manufacture_year: Optional[int] = None
    bus_model: Optional[str] = None
    bus_status: BusStatus

class UpdateBusRequest(BaseModel):
    license_plate: Optional[str] = None
    bus_type: Optional[BusType] = None
    capacity: Optional[int] = None
    current_location: Optional[Location] = None
    last_location_update: Optional[datetime] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    location_accuracy: Optional[float] = None
    current_address: Optional[str] = None
    assigned_route_id: Optional[UUID] = None
    assigned_driver_id: Optional[UUID] = None
    bus_status: Optional[BusStatus] = None
    manufacture_year: Optional[int] = None
    bus_model: Optional[str] = None

class BusResponse(DateTimeModelMixin):
    id: str
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

class CreateBusStopRequest(BaseModel):
    name: str
    location: Location
    capacity: Optional[int] = None
    is_active: bool

class UpdateBusStopRequest(BaseModel):
    name: Optional[str] = None
    location: Optional[Location] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None

class BusStopResponse(DateTimeModelMixin):
    id: UUID
    name: str
    location: Location
    capacity: Optional[int] = None
    is_active: bool