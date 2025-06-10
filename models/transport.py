from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

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
    assigned_route_id: Optional[str] = None
    assigned_driver_id: Optional[str] = None
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
    stop_ids: List[str]
    total_distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    is_active: bool = True

    # Mapbox integration fields
    route_geometry: Optional[Dict[str, Any]] = None  # GeoJSON LineString
    route_shape_data: Optional[Dict[str, Any]] = None  # Full Mapbox route response
    last_shape_update: Optional[datetime] = None

    # Performance optimization fields
    shape_cache_key: Optional[str] = None
    geometry_simplified: Optional[Dict[str, Any]] = None  # Simplified geometry for performance

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

class Alert(BaseDBModel):
    title: str
    message: str
    alert_type: AlertType
    severity: AlertSeverity
    affected_routes: Optional[List[str]] = None
    affected_bus_stops: Optional[List[str]] = None
    is_active: bool = True
    created_by: str