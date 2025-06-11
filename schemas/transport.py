from typing import Optional, List
from pydantic import BaseModel

from enum import Enum
from datetime import datetime
from .base import DateTimeModelMixin
from models.base import Location
from .user import UserResponse

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
    assigned_route_id: Optional[str] = None
    assigned_driver_id: Optional[str] = None
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
    assigned_route_id: Optional[str] = None
    assigned_driver_id: Optional[str] = None
    assigned_driver: Optional[UserResponse] = None  # Populated driver information
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
    id: str
    name: str
    location: Location
    capacity: Optional[int] = None
    is_active: bool

# Alert schemas
class AlertType(str, Enum):
    TRAFFIC = "TRAFFIC"
    WEATHER = "WEATHER"
    MAINTENANCE = "MAINTENANCE"
    EMERGENCY = "EMERGENCY"
    ROUTE_CHANGE = "ROUTE_CHANGE"
    SERVICE_UPDATE = "SERVICE_UPDATE"

class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class CreateAlertRequest(BaseModel):
    title: str
    message: str
    alert_type: AlertType
    severity: AlertSeverity
    affected_routes: Optional[List[str]] = None
    affected_bus_stops: Optional[List[str]] = None

    

class UpdateAlertRequest(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    alert_type: Optional[AlertType] = None
    severity: Optional[AlertSeverity] = None
    affected_routes: Optional[List[str]] = None
    affected_bus_stops: Optional[List[str]] = None
    is_active: Optional[bool] = None

    

class AlertResponse(DateTimeModelMixin):
    id: str
    title: str
    message: str
    alert_type: AlertType
    severity: AlertSeverity
    affected_routes: Optional[List[str]] = None
    affected_bus_stops: Optional[List[str]] = None
    is_active: bool
    created_by: str

# Instruction schemas
class InstructionType(str, Enum):
    ROUTE_CHANGE = "ROUTE_CHANGE"
    SPEED_LIMIT = "SPEED_LIMIT"
    MAINTENANCE = "MAINTENANCE"
    EMERGENCY = "EMERGENCY"
    GENERAL = "GENERAL"

class InstructionResponse(DateTimeModelMixin):
    id: str
    title: str
    content: str
    instruction_type: InstructionType
    target_driver_id: str
    priority: str
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None

# Detailed bus information for when a bus is clicked
class RouteInfo(BaseModel):
    """Route information for detailed bus response"""
    id: str
    name: str
    description: Optional[str] = None
    total_distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    start_destination: Optional[BusStopResponse] = None  # First stop
    end_destination: Optional[BusStopResponse] = None    # Last stop
    total_stops: int = 0

class CurrentTripInfo(BaseModel):
    """Current trip information for detailed bus response"""
    id: str
    status: str  # SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED, DELAYED
    actual_departure_time: Optional[datetime] = None
    estimated_arrival_time: Optional[datetime] = None
    passenger_count: Optional[int] = None

class BusDetailedResponse(DateTimeModelMixin):
    """Comprehensive bus information returned when a bus is clicked"""
    # Basic bus information
    id: str
    license_plate: str
    bus_type: BusType
    capacity: int
    bus_status: BusStatus
    manufacture_year: Optional[int] = None
    bus_model: Optional[str] = None

    # Location and movement data
    current_location: Optional[Location] = None
    last_location_update: Optional[datetime] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    location_accuracy: Optional[float] = None
    current_address: Optional[str] = None

    # Driver information
    assigned_driver: Optional[UserResponse] = None

    # Route and trip information
    current_route: Optional[RouteInfo] = None
    current_trip: Optional[CurrentTripInfo] = None

    # Real-time status
    is_tracking_active: bool = False
    last_ping: Optional[datetime] = None

    # Operational metrics
    total_trips_today: Optional[int] = None
    average_speed_today: Optional[float] = None
    distance_covered_today: Optional[float] = None

# Driver assignment schemas
class DriverAssignmentResponse(BaseModel):
    """Response for driver assignment operations"""
    message: str
    bus_id: str
    driver_id: Optional[str] = None
    driver_name: Optional[str] = None
    assignment_timestamp: datetime
    previous_driver_id: Optional[str] = None