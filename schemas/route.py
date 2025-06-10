from typing import Optional, List, Dict, Any
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

    # Mapbox integration fields
    route_geometry: Optional[Dict[str, Any]] = None  # GeoJSON LineString
    route_shape_data: Optional[Dict[str, Any]] = None  # Full Mapbox route response
    last_shape_update: Optional[datetime] = None

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

# ETA and route shape schemas
class ETAResponse(BaseModel):
    """ETA calculation response"""
    stop_id: str
    stop_name: Optional[str] = None
    duration_seconds: float
    duration_minutes: float
    distance_meters: float
    distance_km: float
    estimated_arrival: str  # ISO datetime string
    traffic_aware: bool = True
    current_speed_kmh: Optional[float] = None
    calculated_at: str  # ISO datetime string
    fallback_calculation: bool = False

class RouteShapeResponse(BaseModel):
    """Route shape data response"""
    route_id: str
    geometry: Dict[str, Any]  # GeoJSON LineString
    distance_meters: float
    duration_seconds: float
    profile: str  # driving, walking, cycling
    created_at: str  # ISO datetime string

class BusETAResponse(BaseModel):
    """Bus ETA to all stops on route"""
    bus_id: str
    route_id: str
    current_location: Dict[str, float]  # lat, lng
    current_speed_kmh: Optional[float] = None
    stop_etas: List[ETAResponse]
    calculated_at: str  # ISO datetime string