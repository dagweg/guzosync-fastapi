"""
Analytics and reporting endpoints for the control center.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional
from datetime import datetime, timedelta

from core.dependencies import get_current_user
from models import User
from models.user import UserRole
from schemas.analytics import (
    AnalyticsSummaryResponse, OperationalMetricsResponse, FinancialMetricsResponse,
    PerformanceMetricsResponse, ReportRequest, ReportResponse
)
from core.analytics_service import AnalyticsService
from core import transform_mongo_doc

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

def require_control_admin_or_staff(current_user: User = Depends(get_current_user)):
    """Require user to be control admin or staff."""
    if current_user.role not in [UserRole.CONTROL_ADMIN, "CONTROL_STAFF"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center staff can access analytics"
        )
    return current_user

@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_summary_analytics(
    request: Request,
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get summary analytics for the main dashboard."""
    analytics_service = AnalyticsService(request.app.state.mongodb)
    summary = await analytics_service.generate_summary_analytics()
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate analytics summary"
        )
    
    return AnalyticsSummaryResponse(**summary)

@router.get("/operational", response_model=OperationalMetricsResponse)
async def get_operational_metrics(
    request: Request,
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get operational performance metrics."""
    # Default to last 7 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=7)
    
    analytics_service = AnalyticsService(request.app.state.mongodb)
    metrics = await analytics_service.generate_operational_metrics(start_date, end_date)
    
    return OperationalMetricsResponse(**metrics)

@router.get("/financial", response_model=FinancialMetricsResponse)
async def get_financial_metrics(
    request: Request,
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get financial metrics."""
    # Default to current month if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date.replace(day=1)  # First day of current month
    
    analytics_service = AnalyticsService(request.app.state.mongodb)
    metrics = await analytics_service.generate_financial_metrics(start_date, end_date)
    
    return FinancialMetricsResponse(**metrics)

@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    request: Request,
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get performance metrics."""
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    analytics_service = AnalyticsService(request.app.state.mongodb)
    metrics = await analytics_service.generate_performance_metrics(start_date, end_date)
    
    return PerformanceMetricsResponse(**metrics)

@router.get("/routes")
async def get_route_analytics(
    request: Request,
    route_id: Optional[str] = Query(None, description="Specific route ID"),
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get route-specific analytics."""
    analytics_service = AnalyticsService(request.app.state.mongodb)
    analytics = await analytics_service.generate_route_analytics(route_id)
    
    return {"routes": analytics}

@router.get("/time-series")
async def get_time_series_data(
    request: Request,
    metric: str = Query(..., description="Metric name (trip_count, revenue, incidents)"),
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    granularity: str = Query("daily", description="Time granularity (hourly, daily, weekly, monthly)"),
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get time series data for charts."""
    analytics_service = AnalyticsService(request.app.state.mongodb)
    time_series = await analytics_service.generate_time_series_data(
        metric, start_date, end_date, granularity
    )
    
    return {"time_series": time_series}

@router.get("/reports")
async def get_reports(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get list of generated reports."""
    query = {}
    if report_type:
        query["report_type"] = report_type
    
    reports = await request.app.state.mongodb.analytics_reports.find(query)\
        .sort("created_at", -1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(length=limit)
    
    return {"reports": [transform_mongo_doc(report, ReportResponse) for report in reports]}

@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: Request,
    report_request: ReportRequest,
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Generate a new analytics report."""
    try:
        analytics_service = AnalyticsService(request.app.state.mongodb)
        
        # Generate report data based on type
        if report_request.report_type == "OPERATIONAL":
            data = await analytics_service.generate_operational_metrics(
                report_request.start_date, report_request.end_date
            )
        elif report_request.report_type == "FINANCIAL":
            data = await analytics_service.generate_financial_metrics(
                report_request.start_date, report_request.end_date
            )
        elif report_request.report_type == "PERFORMANCE":
            data = await analytics_service.generate_performance_metrics(
                report_request.start_date, report_request.end_date
            )
        else:
            data = await analytics_service.generate_summary_analytics()
        
        # Create report document
        report_doc = {
            "title": report_request.title,
            "report_type": report_request.report_type,
            "period": report_request.period,
            "start_date": report_request.start_date,
            "end_date": report_request.end_date,
            "generated_by": current_user.id,
            "data": data,
            "filters": report_request.filters,
            "status": "COMPLETED",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await request.app.state.mongodb.analytics_reports.insert_one(report_doc)
        created_report = await request.app.state.mongodb.analytics_reports.find_one(
            {"_id": result.inserted_id}
        )
        
        return transform_mongo_doc(created_report, ReportResponse)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )

@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    request: Request,
    report_id: str,
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get a specific report by ID."""
    report = await request.app.state.mongodb.analytics_reports.find_one({"_id": report_id})
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    return transform_mongo_doc(report, ReportResponse)

@router.delete("/reports/{report_id}")
async def delete_report(
    request: Request,
    report_id: str,
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Delete a specific report."""
    result = await request.app.state.mongodb.analytics_reports.delete_one({"_id": report_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    return {"message": "Report deleted successfully"}

@router.get("/kpis")
async def get_kpi_metrics(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by KPI category"),
    period: Optional[str] = Query(None, description="Filter by time period"),
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get KPI metrics."""
    query = {}
    if category:
        query["category"] = category
    if period:
        query["period"] = period
    
    kpis = await request.app.state.mongodb.kpi_metrics.find(query)\
        .sort("date_range_end", -1)\
        .to_list(length=50)
    
    return {"kpis": kpis}

@router.get("/dashboard-config")
async def get_dashboard_config(
    request: Request,
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get dashboard configuration for the current user."""
    # Get user's custom dashboards
    dashboards = await request.app.state.mongodb.custom_dashboards.find({
        "$or": [
            {"created_by": current_user.id},
            {"is_shared": True},
            {"access_roles": {"$in": [current_user.role]}}
        ]
    }).to_list(length=None)
    
    # Get default dashboard configuration
    default_config = {
        "widgets": [
            {"type": "summary_metrics", "position": {"x": 0, "y": 0, "w": 12, "h": 4}},
            {"type": "route_chart", "position": {"x": 0, "y": 4, "w": 6, "h": 6}},
            {"type": "performance_chart", "position": {"x": 6, "y": 4, "w": 6, "h": 6}},
            {"type": "alerts_table", "position": {"x": 0, "y": 10, "w": 12, "h": 4}}
        ]
    }
    
    return {
        "dashboards": dashboards,
        "default_config": default_config
    }

@router.get("/dashboard/real-time")
async def get_realtime_dashboard_data(
    request: Request,
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Get real-time dashboard data for live updates."""
    analytics_service = AnalyticsService(request.app.state.mongodb)
    
    # Get current live metrics
    live_metrics = await analytics_service.generate_summary_analytics()
    
    # Get recent alerts
    recent_alerts = await request.app.state.mongodb.alerts.find({
        "is_active": True,
        "severity": {"$in": ["HIGH", "CRITICAL"]}
    }).sort("created_at", -1).limit(5).to_list(length=5)
    
    # Get pending reallocation requests
    pending_requests = await request.app.state.mongodb.reallocation_requests.find({
        "status": "PENDING"
    }).sort("created_at", -1).limit(10).to_list(length=10)
    
    # Get recent incidents
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    recent_incidents = await request.app.state.mongodb.incidents.find({
        "created_at": {"$gte": today}
    }).sort("created_at", -1).limit(5).to_list(length=5)
    
    return {
        "live_metrics": live_metrics,
        "recent_alerts": recent_alerts,
        "pending_requests": pending_requests,
        "recent_incidents": recent_incidents,
        "last_updated": datetime.utcnow().isoformat()
    }

@router.get("/export/csv")
async def export_analytics_csv(
    request: Request,
    report_type: str = Query(..., description="Type of report to export"),
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    current_user: User = Depends(require_control_admin_or_staff)
):
    """Export analytics data as CSV."""
    try:
        import csv
        import io
        from fastapi.responses import StreamingResponse
        
        analytics_service = AnalyticsService(request.app.state.mongodb)
        
        # Generate data based on report type
        if report_type == "operational":
            data = await analytics_service.generate_operational_metrics(start_date, end_date)
            csv_data = _format_operational_csv(data)
        elif report_type == "financial":
            data = await analytics_service.generate_financial_metrics(start_date, end_date)
            csv_data = _format_financial_csv(data)
        elif report_type == "performance":
            data = await analytics_service.generate_performance_metrics(start_date, end_date)
            csv_data = _format_performance_csv(data)
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        # Create CSV response
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        if csv_data:
            writer.writerow(csv_data[0].keys())
            # Write data
            for row in csv_data:
                writer.writerow(row.values())
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={report_type}_report_{start_date.date()}_{end_date.date()}.csv"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export CSV: {str(e)}"
        )

def _format_operational_csv(data: dict) -> List[dict]:
    """Format operational data for CSV export."""
    return [{
        "Metric": "On-Time Performance",
        "Value": f"{data.get('on_time_performance', 0)}%",
        "Category": "Operational"
    }, {
        "Metric": "Average Trip Duration",
        "Value": f"{data.get('average_trip_duration', 0)} minutes",
        "Category": "Operational"
    }, {
        "Metric": "Bus Utilization Rate",
        "Value": f"{data.get('bus_utilization_rate', 0)}%",
        "Category": "Operational"
    }, {
        "Metric": "Service Reliability",
        "Value": f"{data.get('service_reliability', 0)}%",
        "Category": "Operational"
    }, {
        "Metric": "Breakdown Incidents",
        "Value": str(data.get('breakdown_incidents', 0)),
        "Category": "Operational"
    }]

def _format_financial_csv(data: dict) -> List[dict]:
    """Format financial data for CSV export."""
    return [{
        "Metric": "Daily Revenue",
        "Value": f"${data.get('daily_revenue', 0):.2f}",
        "Category": "Financial"
    }, {
        "Metric": "Monthly Revenue",
        "Value": f"${data.get('monthly_revenue', 0):.2f}",
        "Category": "Financial"
    }, {
        "Metric": "Operating Costs",
        "Value": f"${data.get('operating_costs', 0):.2f}",
        "Category": "Financial"
    }, {
        "Metric": "Profit Margin",
        "Value": f"{data.get('profit_margin', 0):.2f}%",
        "Category": "Financial"
    }]

def _format_performance_csv(data: dict) -> List[dict]:
    """Format performance data for CSV export."""
    return [{
        "Metric": "Driver Performance Average",
        "Value": f"{data.get('driver_performance_avg', 0):.2f}",
        "Category": "Performance"
    }, {
        "Metric": "Regulator Response Time",
        "Value": f"{data.get('regulator_response_time', 0):.2f} minutes",
        "Category": "Performance"
    }, {
        "Metric": "Customer Complaint Resolution",
        "Value": f"{data.get('customer_complaint_resolution', 0):.2f}%",
        "Category": "Performance"
    }, {
        "Metric": "Safety Score",
        "Value": f"{data.get('safety_score', 0):.2f}",
        "Category": "Performance"
    }]
