"""
Analytics and reporting models for the control center dashboard.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .base import BaseDBModel

class ReportType(str, Enum):
    """Types of reports that can be generated."""
    OPERATIONAL = "OPERATIONAL"
    FINANCIAL = "FINANCIAL"
    PERFORMANCE = "PERFORMANCE"
    USAGE = "USAGE"
    MAINTENANCE = "MAINTENANCE"
    SAFETY = "SAFETY"
    CUSTOMER_SATISFACTION = "CUSTOMER_SATISFACTION"

class MetricPeriod(str, Enum):
    """Time periods for metrics aggregation."""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    CUSTOM = "CUSTOM"

class AnalyticsReport(BaseDBModel):
    """Analytics report model."""
    title: str
    report_type: ReportType
    period: MetricPeriod
    start_date: datetime
    end_date: datetime
    generated_by: str  # User ID
    data: Dict[str, Any]  # Report data in JSON format
    filters: Optional[Dict[str, Any]] = None
    status: str = "COMPLETED"  # PENDING, COMPLETED, FAILED
    file_path: Optional[str] = None  # Path to generated file if exported

class KPIMetric(BaseDBModel):
    """Key Performance Indicator model."""
    name: str
    category: str  # Operational, Financial, Performance, etc.
    value: float
    unit: str  # percentage, minutes, count, currency, etc.
    target_value: Optional[float] = None
    previous_value: Optional[float] = None
    trend: str = "STABLE"  # UP, DOWN, STABLE
    period: MetricPeriod
    date_range_start: datetime
    date_range_end: datetime
    metadata: Optional[Dict[str, Any]] = None

class DashboardWidget(BaseDBModel):
    """Dashboard widget configuration."""
    name: str
    widget_type: str  # chart, table, metric, map, etc.
    position: Dict[str, int]  # x, y, width, height
    config: Dict[str, Any]  # Chart configuration, data source, etc.
    user_id: str  # User who created/owns this widget
    is_shared: bool = False
    dashboard_id: str

class CustomDashboard(BaseDBModel):
    """Custom dashboard configuration."""
    name: str
    description: Optional[str] = None
    created_by: str  # User ID
    widgets: List[str] = []  # Widget IDs
    is_default: bool = False
    is_shared: bool = False
    access_roles: List[str] = []  # Roles that can access this dashboard

class AlertRule(BaseDBModel):
    """Alert rule for automated notifications."""
    name: str
    metric_name: str
    condition: str  # "greater_than", "less_than", "equals", "not_equals"
    threshold_value: float
    is_active: bool = True
    notification_channels: List[str] = []  # email, sms, webhook, etc.
    created_by: str
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
