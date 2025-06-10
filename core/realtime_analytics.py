"""
Real-time analytics service for live dashboard updates.
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from core.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

class RealTimeAnalyticsService:
    """Service for real-time analytics and dashboard updates."""
    
    def __init__(self, mongodb_client, websocket_manager: WebSocketManager):
        self.db = mongodb_client
        self.websocket_manager = websocket_manager
        self.is_running = False
        self.update_interval = 30  # seconds
        self._tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Start real-time analytics updates."""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting real-time analytics service...")
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._live_metrics_updater()),
            asyncio.create_task(self._alert_monitor()),
            asyncio.create_task(self._performance_tracker())
        ]
    
    async def stop(self):
        """Stop real-time analytics updates."""
        self.is_running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("Real-time analytics service stopped")
    
    async def _live_metrics_updater(self):
        """Update live metrics every 30 seconds."""
        while self.is_running:
            try:
                # Generate current metrics
                metrics = await self._get_live_metrics()
                  # Broadcast to all connected control center users
                await self.websocket_manager.broadcast_to_room(
                    room_id="control_center:live_dashboard",
                    message={
                        "type": "live_metrics_update",
                        "data": metrics,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in live metrics updater: {str(e)}")
                await asyncio.sleep(5)  # Short delay before retry
    
    async def _alert_monitor(self):
        """Monitor for new alerts and critical metrics."""
        while self.is_running:
            try:                # Check for new critical alerts
                critical_alerts = await self._check_critical_alerts()
                
                for alert in critical_alerts:
                    await self.websocket_manager.broadcast_to_room(
                        room_id="control_center:alerts",
                        message={
                            "type": "critical_alert",
                            "data": alert,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                  # Check KPI thresholds
                threshold_breaches = await self._check_kpi_thresholds()
                
                for breach in threshold_breaches:
                    await self.websocket_manager.broadcast_to_room(
                        room_id="control_center:kpi_alerts",
                        message={
                            "type": "kpi_threshold_breach",
                            "data": breach,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in alert monitor: {str(e)}")
                await asyncio.sleep(10)
    
    async def _performance_tracker(self):
        """Track performance trends and anomalies."""
        while self.is_running:
            try:
                # Get performance trends
                trends = await self._get_performance_trends()
                  # Detect anomalies
                anomalies = await self._detect_anomalies(trends)
                
                if anomalies:
                    await self.websocket_manager.broadcast_to_room(
                        room_id="control_center:performance_alerts",
                        message={
                            "type": "performance_anomaly",
                            "data": anomalies,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in performance tracker: {str(e)}")
                await asyncio.sleep(30)
    
    async def _get_live_metrics(self) -> Dict[str, Any]:
        """Get current live metrics."""
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Active buses
        active_buses = await self.db.buses.count_documents({"status": "ACTIVE"})
        
        # Trips today
        trips_today = await self.db.trips.count_documents({
            "created_at": {"$gte": today}
        })
        
        # Current alerts
        active_alerts = await self.db.alerts.count_documents({"is_active": True})
        
        # Pending reallocation requests
        pending_reallocations = await self.db.reallocation_requests.count_documents({
            "status": "PENDING"
        })
        
        # Recent incidents (last hour)
        recent_incidents = await self.db.incidents.count_documents({
            "created_at": {"$gte": now - timedelta(hours=1)}
        })
        
        # Revenue today
        payments_today = await self.db.payments.find({
            "created_at": {"$gte": today},
            "status": "COMPLETED"
        }).to_list(length=None)
        
        revenue_today = sum([p.get("amount", 0) for p in payments_today])
        
        return {
            "active_buses": active_buses,
            "trips_today": trips_today,
            "active_alerts": active_alerts,
            "pending_reallocations": pending_reallocations,
            "recent_incidents": recent_incidents,
            "revenue_today": revenue_today,
            "last_updated": now.isoformat()
        }
    
    async def _check_critical_alerts(self) -> List[Dict[str, Any]]:
        """Check for new critical alerts."""        # Get alerts created in the last minute
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        
        critical_alerts = await self.db.alerts.find({
            "severity": {"$in": ["HIGH", "CRITICAL"]},
            "created_at": {"$gte": one_minute_ago},
            "is_active": True
        }).to_list(length=None)
        
        return list(critical_alerts) if critical_alerts else []
    
    async def _check_kpi_thresholds(self) -> List[Dict[str, Any]]:
        """Check for KPI threshold breaches."""
        breaches = []
        
        # Example: Check if delay percentage is too high
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        trips_today = await self.db.trips.find({
            "created_at": {"$gte": today}
        }).to_list(length=None)
        
        if trips_today:
            delayed_trips = [t for t in trips_today if t.get("delay_minutes", 0) > 10]
            delay_percentage = (len(delayed_trips) / len(trips_today)) * 100
            
            if delay_percentage > 25:  # More than 25% delayed
                breaches.append({
                    "metric": "delay_percentage",
                    "value": delay_percentage,
                    "threshold": 25,
                    "severity": "HIGH" if delay_percentage > 40 else "MEDIUM",
                    "description": f"High delay rate: {delay_percentage:.1f}% of trips delayed"
                })
        
        # Example: Check bus utilization
        active_buses = await self.db.buses.count_documents({"status": "ACTIVE"})
        if active_buses > 0 and trips_today:
            utilization = len(trips_today) / active_buses
            if utilization < 3:  # Less than 3 trips per bus
                breaches.append({
                    "metric": "bus_utilization",
                    "value": utilization,
                    "threshold": 3,
                    "severity": "MEDIUM",
                    "description": f"Low bus utilization: {utilization:.1f} trips per bus"
                })
        
        return breaches
    
    async def _get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trends for anomaly detection."""
        # Get data for the last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Daily trip counts
        daily_trips = []
        for i in range(7):
            day_start = week_ago + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            trip_count = await self.db.trips.count_documents({
                "created_at": {"$gte": day_start, "$lt": day_end}
            })
            
            daily_trips.append({
                "date": day_start.date().isoformat(),
                "trip_count": trip_count
            })
        
        # Daily revenue
        daily_revenue = []
        for i in range(7):
            day_start = week_ago + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            payments = await self.db.payments.find({
                "created_at": {"$gte": day_start, "$lt": day_end},
                "status": "COMPLETED"
            }).to_list(length=None)
            
            revenue = sum([p.get("amount", 0) for p in payments])
            
            daily_revenue.append({
                "date": day_start.date().isoformat(),
                "revenue": revenue
            })
        
        return {
            "daily_trips": daily_trips,
            "daily_revenue": daily_revenue
        }
    
    async def _detect_anomalies(self, trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect anomalies in performance trends."""
        anomalies = []
        
        # Check for significant drops in trip count
        daily_trips = trends.get("daily_trips", [])
        if len(daily_trips) >= 3:
            recent_trips = [d["trip_count"] for d in daily_trips[-3:]]
            avg_recent = sum(recent_trips) / len(recent_trips)
            
            earlier_trips = [d["trip_count"] for d in daily_trips[:-3]]
            if earlier_trips:
                avg_earlier = sum(earlier_trips) / len(earlier_trips)
                
                # If recent average is 30% lower than earlier average
                if avg_recent < avg_earlier * 0.7:
                    anomalies.append({
                        "type": "trip_count_drop",
                        "description": f"Significant drop in daily trips: {avg_recent:.0f} vs {avg_earlier:.0f}",
                        "severity": "HIGH",
                        "current_value": avg_recent,
                        "expected_value": avg_earlier
                    })
        
        # Check for revenue anomalies
        daily_revenue = trends.get("daily_revenue", [])
        if len(daily_revenue) >= 3:
            recent_revenue = [d["revenue"] for d in daily_revenue[-3:]]
            avg_recent_revenue = sum(recent_revenue) / len(recent_revenue)
            
            earlier_revenue = [d["revenue"] for d in daily_revenue[:-3]]
            if earlier_revenue:
                avg_earlier_revenue = sum(earlier_revenue) / len(earlier_revenue)
                
                # If recent revenue is 25% lower than earlier
                if avg_recent_revenue < avg_earlier_revenue * 0.75:
                    anomalies.append({
                        "type": "revenue_drop",
                        "description": f"Significant drop in daily revenue",
                        "severity": "HIGH",
                        "current_value": avg_recent_revenue,
                        "expected_value": avg_earlier_revenue
                    })
        
        return anomalies

# Global instance (will be initialized in main.py)
realtime_analytics_service: RealTimeAnalyticsService | None = None
