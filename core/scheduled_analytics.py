"""
Scheduled analytics tasks for automated reporting.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from core.analytics_service import AnalyticsService
from core.email_service import EmailService

logger = logging.getLogger(__name__)

class ScheduledAnalyticsService:
    """Service for scheduled analytics tasks."""
    
    def __init__(self, mongodb_client):
        self.db = mongodb_client
        self.analytics_service = AnalyticsService(mongodb_client)
        self.email_service = EmailService()
        self.is_running = False
        self._tasks = []
    
    async def start(self):
        """Start scheduled analytics tasks."""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting scheduled analytics service...")
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._daily_report_generator()),
            asyncio.create_task(self._weekly_report_generator()),
            asyncio.create_task(self._monthly_report_generator()),
            asyncio.create_task(self._alert_digest_generator())
        ]
    
    async def stop(self):
        """Stop scheduled analytics tasks."""
        self.is_running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("Scheduled analytics service stopped")
    
    async def _daily_report_generator(self):
        """Generate daily reports at 6 AM."""
        while self.is_running:
            try:
                now = datetime.now(timezone.utc)
                # Schedule for 6 AM UTC
                next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                # Wait until next scheduled time
                wait_seconds = (next_run - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                if self.is_running:
                    await self._generate_daily_report()
                
            except Exception as e:
                logger.error(f"Error in daily report generator: {str(e)}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _weekly_report_generator(self):
        """Generate weekly reports on Mondays at 7 AM."""
        while self.is_running:
            try:
                now = datetime.now(timezone.utc)
                
                # Find next Monday at 7 AM
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0 and now.hour >= 7:
                    days_until_monday = 7
                
                next_monday = now + timedelta(days=days_until_monday)
                next_run = next_monday.replace(hour=7, minute=0, second=0, microsecond=0)
                
                wait_seconds = (next_run - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                if self.is_running:
                    await self._generate_weekly_report()
                
            except Exception as e:
                logger.error(f"Error in weekly report generator: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _monthly_report_generator(self):
        """Generate monthly reports on the 1st at 8 AM."""
        while self.is_running:
            try:
                now = datetime.now(timezone.utc)
                
                # Find next 1st of month at 8 AM
                if now.day == 1 and now.hour < 8:
                    next_run = now.replace(hour=8, minute=0, second=0, microsecond=0)
                else:
                    # Next month
                    if now.month == 12:
                        next_run = now.replace(year=now.year + 1, month=1, day=1, hour=8, minute=0, second=0, microsecond=0)
                    else:
                        next_run = now.replace(month=now.month + 1, day=1, hour=8, minute=0, second=0, microsecond=0)
                
                wait_seconds = (next_run - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                if self.is_running:
                    await self._generate_monthly_report()
                
            except Exception as e:
                logger.error(f"Error in monthly report generator: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _alert_digest_generator(self):
        """Generate alert digest every 4 hours."""
        while self.is_running:
            try:
                await asyncio.sleep(14400)  # 4 hours
                
                if self.is_running:
                    await self._generate_alert_digest()
                
            except Exception as e:
                logger.error(f"Error in alert digest generator: {str(e)}")
                await asyncio.sleep(1800)  # Wait 30 minutes before retry
    
    async def _generate_daily_report(self):
        """Generate and save daily report."""
        try:
            yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
            start_date = datetime.combine(yesterday, datetime.min.time())
            end_date = datetime.combine(yesterday, datetime.max.time())
            
            logger.info(f"Generating daily report for {yesterday}")
            
            # Generate metrics
            operational = await self.analytics_service.generate_operational_metrics(start_date, end_date)
            financial = await self.analytics_service.generate_financial_metrics(start_date, end_date)
            performance = await self.analytics_service.generate_performance_metrics(start_date, end_date)
            
            # Combine data
            report_data = {
                "operational": operational,
                "financial": financial,
                "performance": performance,
                "summary": await self.analytics_service.generate_summary_analytics()
            }
            
            # Save report
            report_doc = {
                "title": f"Daily Report - {yesterday}",
                "report_type": "OPERATIONAL",
                "period": "DAILY",
                "start_date": start_date,
                "end_date": end_date,
                "generated_by": "system",
                "data": report_data,
                "status": "COMPLETED",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            result = await self.db.analytics_reports.insert_one(report_doc)
            logger.info(f"Daily report saved with ID: {result.inserted_id}")
            
            # Send email notification to control center staff
            await self._send_report_notification("daily", report_data)
            
        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}")
    
    async def _generate_weekly_report(self):
        """Generate and save weekly report."""
        try:
            # Last week (Monday to Sunday)
            today = datetime.now(timezone.utc).date()
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6)
            
            start_date = datetime.combine(last_monday, datetime.min.time())
            end_date = datetime.combine(last_sunday, datetime.max.time())
            
            logger.info(f"Generating weekly report for {last_monday} to {last_sunday}")
            
            # Generate comprehensive metrics
            operational = await self.analytics_service.generate_operational_metrics(start_date, end_date)
            financial = await self.analytics_service.generate_financial_metrics(start_date, end_date)
            performance = await self.analytics_service.generate_performance_metrics(start_date, end_date)
            route_analytics = await self.analytics_service.generate_route_analytics()
            
            report_data = {
                "operational": operational,
                "financial": financial,
                "performance": performance,
                "route_analytics": route_analytics,
                "period_summary": f"Week of {last_monday} to {last_sunday}"
            }
            
            # Save report
            report_doc = {
                "title": f"Weekly Report - Week of {last_monday}",
                "report_type": "PERFORMANCE",
                "period": "WEEKLY",
                "start_date": start_date,
                "end_date": end_date,
                "generated_by": "system",
                "data": report_data,
                "status": "COMPLETED",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            result = await self.db.analytics_reports.insert_one(report_doc)
            logger.info(f"Weekly report saved with ID: {result.inserted_id}")
            
            await self._send_report_notification("weekly", report_data)
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {str(e)}")
    
    async def _generate_monthly_report(self):
        """Generate and save monthly report."""
        try:
            # Last month
            today = datetime.now(timezone.utc).date()
            if today.month == 1:
                last_month = today.replace(year=today.year - 1, month=12, day=1)
            else:
                last_month = today.replace(month=today.month - 1, day=1)
            
            # Last day of last month
            if last_month.month == 12:
                next_month = last_month.replace(year=last_month.year + 1, month=1, day=1)
            else:
                next_month = last_month.replace(month=last_month.month + 1, day=1)
            
            last_day = next_month - timedelta(days=1)
            
            start_date = datetime.combine(last_month, datetime.min.time())
            end_date = datetime.combine(last_day, datetime.max.time())
            
            logger.info(f"Generating monthly report for {last_month.strftime('%B %Y')}")
            
            # Generate comprehensive metrics
            operational = await self.analytics_service.generate_operational_metrics(start_date, end_date)
            financial = await self.analytics_service.generate_financial_metrics(start_date, end_date)
            performance = await self.analytics_service.generate_performance_metrics(start_date, end_date)
            route_analytics = await self.analytics_service.generate_route_analytics()
            
            # Generate time series data for trends
            trip_trends = await self.analytics_service.generate_time_series_data(
                "trip_count", start_date, end_date, "daily"
            )
            revenue_trends = await self.analytics_service.generate_time_series_data(
                "revenue", start_date, end_date, "daily"
            )
            
            report_data = {
                "operational": operational,
                "financial": financial,
                "performance": performance,
                "route_analytics": route_analytics,
                "trends": {
                    "trip_trends": trip_trends,
                    "revenue_trends": revenue_trends
                },
                "period_summary": f"{last_month.strftime('%B %Y')}"
            }
            
            # Save report
            report_doc = {
                "title": f"Monthly Report - {last_month.strftime('%B %Y')}",
                "report_type": "FINANCIAL",
                "period": "MONTHLY",
                "start_date": start_date,
                "end_date": end_date,
                "generated_by": "system",
                "data": report_data,
                "status": "COMPLETED",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            result = await self.db.analytics_reports.insert_one(report_doc)
            logger.info(f"Monthly report saved with ID: {result.inserted_id}")
            
            await self._send_report_notification("monthly", report_data)
            
        except Exception as e:
            logger.error(f"Error generating monthly report: {str(e)}")
    
    async def _generate_alert_digest(self):
        """Generate alert digest for the last 4 hours."""
        try:
            four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=4)
            
            # Get recent alerts
            recent_alerts = await self.db.alerts.find({
                "created_at": {"$gte": four_hours_ago},
                "is_active": True
            }).to_list(length=None)
            
            # Get recent incidents
            recent_incidents = await self.db.incidents.find({
                "created_at": {"$gte": four_hours_ago}
            }).to_list(length=None)
            
            # Get new reallocation requests
            new_requests = await self.db.reallocation_requests.find({
                "created_at": {"$gte": four_hours_ago}
            }).to_list(length=None)
            
            if recent_alerts or recent_incidents or new_requests:
                digest_data = {
                    "alerts": recent_alerts,
                    "incidents": recent_incidents,
                    "reallocation_requests": new_requests,
                    "period": "Last 4 hours",
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                
                await self._send_alert_digest(digest_data)
                logger.info(f"Alert digest sent - {len(recent_alerts)} alerts, {len(recent_incidents)} incidents")
            
        except Exception as e:
            logger.error(f"Error generating alert digest: {str(e)}")
    
    async def _send_report_notification(self, report_type: str, data: Dict[str, Any]):
        """Send report notification email."""
        try:
            # Get control center users
            control_users = await self.db.users.find({
                "role": {"$in": ["CONTROL_ADMIN", "CONTROL_STAFF"]},
                "is_active": True
            }).to_list(length=None)
            
            if not control_users:
                return
            
            # Prepare email content
            subject = f"GuzoSync {report_type.title()} Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
            
            # Format key metrics
            if "operational" in data:
                op_metrics = data["operational"]
                metrics_summary = f"""
                • On-Time Performance: {op_metrics.get('on_time_performance', 0):.1f}%
                • Bus Utilization: {op_metrics.get('bus_utilization_rate', 0):.1f}%
                • Service Reliability: {op_metrics.get('service_reliability', 0):.1f}%
                """
            else:
                metrics_summary = "Metrics data not available"
            
            body = f"""
            Dear Control Center Team,

            Your {report_type} GuzoSync analytics report is ready.

            Key Metrics Summary:
            {metrics_summary}

            You can view the full report in the GuzoSync dashboard under Analytics > Reports.            Best regards,
            GuzoSync Analytics System
            """
            
            # Send to all control users
            for user in control_users:
                if user.get("email"):
                    await self.email_service.send_notification_email(
                        email=user["email"],
                        subject=subject,
                        message=body
                    )
            
        except Exception as e:
            logger.error(f"Error sending report notification: {str(e)}")
    
    async def _send_alert_digest(self, digest_data: Dict[str, Any]):
        """Send alert digest email."""
        try:
            # Get control center users
            control_users = await self.db.users.find({
                "role": {"$in": ["CONTROL_ADMIN", "CONTROL_STAFF"]},
                "is_active": True
            }).to_list(length=None)
            
            if not control_users:
                return
            
            alerts_count = len(digest_data.get("alerts", []))
            incidents_count = len(digest_data.get("incidents", []))
            requests_count = len(digest_data.get("reallocation_requests", []))
            
            if alerts_count == 0 and incidents_count == 0 and requests_count == 0:
                return  # No need to send empty digest
            
            subject = f"GuzoSync Alert Digest - {alerts_count} alerts, {incidents_count} incidents"
            
            body = f"""
            Control Center Alert Digest - {digest_data['period']}

            Summary:
            • New Alerts: {alerts_count}
            • New Incidents: {incidents_count}
            • New Reallocation Requests: {requests_count}

            Please check the GuzoSync dashboard for details and take appropriate action.

            This is an automated digest sent every 4 hours.            GuzoSync Monitoring System
            """
            
            # Send to all control users
            for user in control_users:
                if user.get("email"):
                    await self.email_service.send_notification_email(
                        email=user["email"],
                        subject=subject,
                        message=body
                    )
            
        except Exception as e:
            logger.error(f"Error sending alert digest: {str(e)}")

# Global instance (will be initialized in main.py)
scheduled_analytics_service: ScheduledAnalyticsService | None = None
