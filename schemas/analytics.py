"""
Analytics and reporting schemas for API requests and responses.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from .base import DateTimeModelMixin

class ReportRequest(BaseModel):
    """Request schema for generating reports."""
    title: str
    report_type: str  # OPERATIONAL, FINANCIAL, PERFORMANCE, etc.
    period: str  # DAILY, WEEKLY, MONTHLY, etc.
    start_date: datetime
    end_date: datetime
    filters: Optional[Dict[str, Any]] = None

class ReportResponse(DateTimeModelMixin):
    """Response schema for reports."""
    id: str
    title: str
    report_type: str
    period: str
    start_date: datetime
    end_date: datetime
    generated_by: str
    data: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None
    status: str
    file_path: Optional[str] = None

class KPIMetricRequest(BaseModel):
    """Request schema for creating KPI metrics."""
    name: str
    category: str
    value: float
    unit: str
    target_value: Optional[float] = None
    previous_value: Optional[float] = None
    trend: str = "STABLE"
    period: str
    date_range_start: datetime
    date_range_end: datetime
    metadata: Optional[Dict[str, Any]] = None

class KPIMetricResponse(DateTimeModelMixin):
    """Response schema for KPI metrics."""
    id: str
    name: str
    category: str
    value: float
    unit: str
    target_value: Optional[float] = None
    previous_value: Optional[float] = None
    trend: str
    period: str
    date_range_start: datetime
    date_range_end: datetime
    metadata: Optional[Dict[str, Any]] = None

class DashboardWidgetRequest(BaseModel):
    """Request schema for creating dashboard widgets."""
    name: str
    widget_type: str
    position: Dict[str, int]
    config: Dict[str, Any]
    dashboard_id: str
    is_shared: bool = False

class DashboardWidgetResponse(DateTimeModelMixin):
    """Response schema for dashboard widgets."""
    id: str
    name: str
    widget_type: str
    position: Dict[str, int]
    config: Dict[str, Any]
    user_id: str
    is_shared: bool
    dashboard_id: str

class CustomDashboardRequest(BaseModel):
    """Request schema for creating custom dashboards."""
    name: str
    description: Optional[str] = None
    widgets: List[str] = []
    is_default: bool = False
    is_shared: bool = False
    access_roles: List[str] = []

class CustomDashboardResponse(DateTimeModelMixin):
    """Response schema for custom dashboards."""
    id: str
    name: str
    description: Optional[str] = None
    created_by: str
    widgets: List[str] = []
    is_default: bool
    is_shared: bool
    access_roles: List[str] = []

class AlertRuleRequest(BaseModel):
    """Request schema for creating alert rules."""
    name: str
    metric_name: str
    condition: str
    threshold_value: float
    is_active: bool = True
    notification_channels: List[str] = []

class AlertRuleResponse(DateTimeModelMixin):
    """Response schema for alert rules."""
    id: str
    name: str
    metric_name: str
    condition: str
    threshold_value: float
    is_active: bool
    notification_channels: List[str]
    created_by: str
    last_triggered: Optional[datetime] = None
    trigger_count: int

class AnalyticsSummaryResponse(BaseModel):
    """Summary analytics response."""
    total_buses: int
    active_buses: int
    total_routes: int
    active_routes: int
    total_trips_today: int
    completed_trips_today: int
    average_delay_minutes: float
    passenger_satisfaction_score: float
    fuel_efficiency_score: float
    maintenance_alerts: int
    safety_incidents: int
    revenue_today: float

class OperationalMetricsResponse(BaseModel):
    """Operational metrics response."""
    on_time_performance: float
    average_trip_duration: float
    bus_utilization_rate: float
    route_efficiency_score: float
    passenger_load_factor: float
    service_reliability: float
    breakdown_incidents: int
    maintenance_compliance: float

class FinancialMetricsResponse(BaseModel):
    """Financial metrics response."""
    daily_revenue: float
    monthly_revenue: float
    operating_costs: float
    profit_margin: float
    cost_per_kilometer: float
    revenue_per_passenger: float
    fuel_costs: float
    maintenance_costs: float

class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response."""
    driver_performance_avg: float
    regulator_response_time: float
    customer_complaint_resolution: float
    safety_score: float
    service_quality_index: float
    operational_efficiency: float
