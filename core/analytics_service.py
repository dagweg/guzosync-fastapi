"""
Analytics service for generating reports and metrics.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for analytics and reporting functionality."""
    
    def __init__(self, mongodb_client):
        self.db = mongodb_client
    
    async def generate_summary_analytics(self) -> Dict[str, Any]:
        """Generate summary analytics for the dashboard."""
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get basic counts
            total_buses = await self.db.buses.count_documents({})
            active_buses = await self.db.buses.count_documents({"status": "ACTIVE"})
            total_routes = await self.db.routes.count_documents({})
            active_routes = await self.db.routes.count_documents({"is_active": True})
            
            # Get today's trip metrics
            trips_today = await self.db.trips.find({
                "created_at": {"$gte": today}
            }).to_list(length=None)
            
            total_trips_today = len(trips_today)
            completed_trips_today = len([t for t in trips_today if t.get("status") == "COMPLETED"])
            
            # Calculate average delay
            delays = [t.get("delay_minutes", 0) for t in trips_today if t.get("delay_minutes")]
            average_delay = sum(delays) / len(delays) if delays else 0.0
            
            # Get feedback metrics
            feedback_scores = await self.db.feedback.find({
                "created_at": {"$gte": today}
            }).to_list(length=None)
            
            ratings = [f.get("rating", 0) for f in feedback_scores if f.get("rating")]
            avg_satisfaction = sum(ratings) / len(ratings) if ratings else 0.0
            
            # Get maintenance alerts
            maintenance_alerts = await self.db.alerts.count_documents({
                "alert_type": "MAINTENANCE",
                "is_active": True
            })
            
            # Get safety incidents
            safety_incidents = await self.db.incidents.count_documents({
                "created_at": {"$gte": today},
                "severity": {"$in": ["HIGH", "CRITICAL"]}
            })
            
            # Get revenue (placeholder - would integrate with payment system)
            payments_today = await self.db.payments.find({
                "created_at": {"$gte": today},
                "status": "COMPLETED"
            }).to_list(length=None)
            
            revenue_today = sum([p.get("amount", 0) for p in payments_today])
            
            return {
                "total_buses": total_buses,
                "active_buses": active_buses,
                "total_routes": total_routes,
                "active_routes": active_routes,
                "total_trips_today": total_trips_today,
                "completed_trips_today": completed_trips_today,
                "average_delay_minutes": round(average_delay, 2),
                "passenger_satisfaction_score": round(avg_satisfaction, 2),
                "fuel_efficiency_score": 85.5,  # Placeholder
                "maintenance_alerts": maintenance_alerts,
                "safety_incidents": safety_incidents,
                "revenue_today": revenue_today
            }
            
        except Exception as e:
            logger.error(f"Error generating summary analytics: {str(e)}")
            return {}
    
    async def generate_operational_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate operational performance metrics."""
        try:
            # Get trips in date range
            trips = await self.db.trips.find({
                "created_at": {"$gte": start_date, "$lte": end_date}
            }).to_list(length=None)
            
            if not trips:
                return self._empty_operational_metrics()
            
            # Calculate on-time performance
            on_time_trips = [t for t in trips if t.get("delay_minutes", 0) <= 5]
            on_time_performance = (len(on_time_trips) / len(trips)) * 100
            
            # Calculate average trip duration
            durations = [t.get("duration_minutes", 0) for t in trips if t.get("duration_minutes")]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Bus utilization (placeholder calculation)
            total_buses = await self.db.buses.count_documents({"status": "ACTIVE"})
            trips_per_bus = len(trips) / total_buses if total_buses > 0 else 0
            bus_utilization = min(100, (trips_per_bus / 10) * 100)  # Assuming 10 trips/day is 100% utilization
            
            # Get breakdown incidents
            breakdowns = await self.db.incidents.count_documents({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "incident_type": "BREAKDOWN"
            })
            
            return {
                "on_time_performance": round(on_time_performance, 2),
                "average_trip_duration": round(avg_duration, 2),
                "bus_utilization_rate": round(bus_utilization, 2),
                "route_efficiency_score": 78.5,  # Placeholder
                "passenger_load_factor": 65.2,   # Placeholder
                "service_reliability": round(100 - (breakdowns / len(trips) * 100), 2),
                "breakdown_incidents": breakdowns,
                "maintenance_compliance": 92.3   # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Error generating operational metrics: {str(e)}")
            return self._empty_operational_metrics()
    
    async def generate_financial_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate financial metrics."""
        try:
            # Get payments in date range
            payments = await self.db.payments.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "status": "COMPLETED"
            }).to_list(length=None)
            
            total_revenue = sum([p.get("amount", 0) for p in payments])
            
            # Calculate daily and monthly revenue
            days_in_range = (end_date - start_date).days + 1
            daily_revenue = total_revenue / days_in_range if days_in_range > 0 else 0
            monthly_revenue = daily_revenue * 30  # Estimated monthly
            
            # Placeholder calculations for costs (would integrate with accounting system)
            operating_costs = total_revenue * 0.75  # Assuming 75% cost ratio
            profit_margin = ((total_revenue - operating_costs) / total_revenue * 100) if total_revenue > 0 else 0
            
            return {
                "daily_revenue": round(daily_revenue, 2),
                "monthly_revenue": round(monthly_revenue, 2),
                "operating_costs": round(operating_costs, 2),
                "profit_margin": round(profit_margin, 2),
                "cost_per_kilometer": 2.45,      # Placeholder
                "revenue_per_passenger": 12.50,  # Placeholder
                "fuel_costs": round(operating_costs * 0.4, 2),  # 40% of operating costs
                "maintenance_costs": round(operating_costs * 0.15, 2)  # 15% of operating costs
            }
            
        except Exception as e:
            logger.error(f"Error generating financial metrics: {str(e)}")
            return {}
    
    async def generate_performance_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate performance metrics."""
        try:
            # Driver performance (placeholder - would integrate with driver evaluation system)
            drivers = await self.db.users.find({"role": "DRIVER"}).to_list(length=None)
            driver_scores = [d.get("performance_score", 75) for d in drivers]
            avg_driver_performance = sum(driver_scores) / len(driver_scores) if driver_scores else 0
            
            # Regulator response time
            reallocation_requests = await self.db.reallocation_requests.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "status": "COMPLETED"
            }).to_list(length=None)
            
            response_times = []
            for req in reallocation_requests:
                if req.get("reviewed_at") and req.get("created_at"):
                    created = datetime.fromisoformat(req["created_at"].replace("Z", "+00:00"))
                    reviewed = datetime.fromisoformat(req["reviewed_at"].replace("Z", "+00:00"))
                    response_times.append((reviewed - created).total_seconds() / 60)  # minutes
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Customer complaint resolution
            feedback_with_issues = await self.db.feedback.find({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "rating": {"$lte": 2}  # Poor ratings
            }).to_list(length=None)
            
            resolved_complaints = len([f for f in feedback_with_issues if f.get("resolved", False)])
            complaint_resolution = (resolved_complaints / len(feedback_with_issues) * 100) if feedback_with_issues else 100
            
            # Safety incidents
            safety_incidents = await self.db.incidents.count_documents({
                "created_at": {"$gte": start_date, "$lte": end_date},
                "severity": {"$in": ["HIGH", "CRITICAL"]}
            })
            
            total_trips = await self.db.trips.count_documents({
                "created_at": {"$gte": start_date, "$lte": end_date}
            })
            
            safety_score = max(0, 100 - (safety_incidents / max(total_trips, 1) * 100))
            
            return {
                "driver_performance_avg": round(avg_driver_performance, 2),
                "regulator_response_time": round(avg_response_time, 2),
                "customer_complaint_resolution": round(complaint_resolution, 2),
                "safety_score": round(safety_score, 2),
                "service_quality_index": 82.5,    # Placeholder
                "operational_efficiency": 78.9    # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Error generating performance metrics: {str(e)}")
            return {}
    
    async def generate_route_analytics(self, route_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate route-specific analytics."""
        try:
            query = {"route_id": route_id} if route_id else {}
            
            # Get route trips
            trips = await self.db.trips.find(query).to_list(length=None)
            
            # Get overcrowding reports
            overcrowding_reports = await self.db.overcrowding_reports.find(query).to_list(length=None)
            
            # Get reallocation requests
            reallocation_requests = await self.db.reallocation_requests.find(
                {"current_route_id": route_id} if route_id else {}
            ).to_list(length=None)
            
            route_analytics = {}
            
            if route_id:
                # Single route analytics
                route = await self.db.routes.find_one({"_id": route_id})
                if route:
                    route_analytics[route_id] = {
                        "route_name": route.get("name", "Unknown"),
                        "total_trips": len(trips),
                        "average_delay": sum([t.get("delay_minutes", 0) for t in trips]) / len(trips) if trips else 0,
                        "overcrowding_reports": len(overcrowding_reports),
                        "reallocation_requests": len(reallocation_requests),
                        "efficiency_score": 85.0  # Placeholder
                    }
            else:
                # All routes analytics
                routes = await self.db.routes.find({}).to_list(length=None)
                for route in routes:
                    route_trips = [t for t in trips if t.get("route_id") == route["_id"]]
                    route_overcrowding = [r for r in overcrowding_reports if r.get("route_id") == route["_id"]]
                    route_reallocations = [r for r in reallocation_requests if r.get("current_route_id") == route["_id"]]
                    
                    route_analytics[route["_id"]] = {
                        "route_name": route.get("name", "Unknown"),
                        "total_trips": len(route_trips),
                        "average_delay": sum([t.get("delay_minutes", 0) for t in route_trips]) / len(route_trips) if route_trips else 0,
                        "overcrowding_reports": len(route_overcrowding),
                        "reallocation_requests": len(route_reallocations),
                        "efficiency_score": 85.0  # Placeholder
                    }
            
            return route_analytics
            
        except Exception as e:
            logger.error(f"Error generating route analytics: {str(e)}")
            return {}
    
    async def generate_time_series_data(self, metric: str, start_date: datetime, end_date: datetime, granularity: str = "daily") -> List[Dict[str, Any]]:
        """Generate time series data for charts."""
        try:
            time_series = []
            current_date = start_date
            
            # Determine time delta based on granularity
            if granularity == "hourly":
                delta = timedelta(hours=1)
            elif granularity == "daily":
                delta = timedelta(days=1)
            elif granularity == "weekly":
                delta = timedelta(weeks=1)
            elif granularity == "monthly":
                delta = timedelta(days=30)
            else:
                delta = timedelta(days=1)
            
            while current_date <= end_date:
                period_end = current_date + delta
                
                # Generate data point based on metric type
                if metric == "trip_count":
                    value = await self.db.trips.count_documents({
                        "created_at": {"$gte": current_date, "$lt": period_end}
                    })
                elif metric == "revenue":
                    payments = await self.db.payments.find({
                        "created_at": {"$gte": current_date, "$lt": period_end},
                        "status": "COMPLETED"
                    }).to_list(length=None)
                    value = sum([p.get("amount", 0) for p in payments])
                elif metric == "incidents":
                    value = await self.db.incidents.count_documents({
                        "created_at": {"$gte": current_date, "$lt": period_end}
                    })
                else:
                    value = 0
                
                time_series.append({
                    "timestamp": current_date.isoformat(),
                    "value": value,
                    "metric": metric
                })
                
                current_date = period_end
            
            return time_series
            
        except Exception as e:
            logger.error(f"Error generating time series data: {str(e)}")
            return []
    
    def _empty_operational_metrics(self) -> Dict[str, Any]:
        """Return empty operational metrics."""
        return {
            "on_time_performance": 0.0,
            "average_trip_duration": 0.0,
            "bus_utilization_rate": 0.0,
            "route_efficiency_score": 0.0,
            "passenger_load_factor": 0.0,
            "service_reliability": 0.0,
            "breakdown_incidents": 0,
            "maintenance_compliance": 0.0
        }
