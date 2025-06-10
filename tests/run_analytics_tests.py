"""
Simple test runner for analytics feature.
This script runs basic functionality tests without requiring pytest setup.
"""

import asyncio
import sys
import traceback
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock

# Add the project root to Python path
sys.path.append('.')

try:
    from core.analytics_service import AnalyticsService
    from core.realtime_analytics import RealTimeAnalyticsService
    from core.scheduled_analytics import ScheduledAnalyticsService
    print("✅ Successfully imported analytics modules")
except ImportError as e:
    print(f"❌ Failed to import analytics modules: {e}")
    sys.exit(1)

class AnalyticsTestRunner:
    """Simple test runner for analytics functionality."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run_test(self, test_name, test_func):
        """Run a single test and track results."""
        try:
            print(f"  Running {test_name}...", end=" ")
            if asyncio.iscoroutinefunction(test_func):
                asyncio.run(test_func())
            else:
                test_func()
            print("✅ PASSED")
            self.passed += 1
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.failed += 1
            self.errors.append(f"{test_name}: {str(e)}")
    
    def create_mock_db(self):
        """Create a mock database for testing."""
        db = MagicMock()

        # Mock all collections with proper async behavior
        for collection in ['buses', 'routes', 'trips', 'feedback', 'alerts',
                          'incidents', 'payments', 'users', 'reallocation_requests',
                          'overcrowding_reports', 'analytics_reports', 'kpi_metrics']:

            # Create collection mock
            collection_mock = AsyncMock()

            # Mock the find method to return a mock with to_list
            find_mock = MagicMock()
            find_mock.to_list = AsyncMock(return_value=[])
            find_mock.sort = MagicMock(return_value=find_mock)
            find_mock.skip = MagicMock(return_value=find_mock)
            find_mock.limit = MagicMock(return_value=find_mock)
            collection_mock.find = MagicMock(return_value=find_mock)

            # Mock count_documents
            collection_mock.count_documents = AsyncMock(return_value=0)

            # Mock insert_one
            insert_result = MagicMock()
            insert_result.inserted_id = "mock_id"
            collection_mock.insert_one = AsyncMock(return_value=insert_result)

            setattr(db, collection, collection_mock)

        return db
    
    async def test_analytics_service_basic(self):
        """Test basic analytics service functionality."""
        mock_db = self.create_mock_db()

        # Setup mock data with proper async returns
        mock_db.buses.count_documents = AsyncMock(side_effect=[50, 45])
        mock_db.routes.count_documents = AsyncMock(side_effect=[20, 18])

        # Mock trips data
        trips_data = [
            {"status": "COMPLETED", "delay_minutes": 3},
            {"status": "COMPLETED", "delay_minutes": 8}
        ]
        mock_db.trips.find.return_value.to_list = AsyncMock(return_value=trips_data)

        # Mock feedback data
        feedback_data = [{"rating": 4.5}, {"rating": 3.8}]
        mock_db.feedback.find.return_value.to_list = AsyncMock(return_value=feedback_data)

        # Mock other counts
        mock_db.alerts.count_documents = AsyncMock(return_value=3)
        mock_db.incidents.count_documents = AsyncMock(return_value=1)

        # Mock payments data
        payments_data = [{"amount": 25.50}, {"amount": 18.75}]
        mock_db.payments.find.return_value.to_list = AsyncMock(return_value=payments_data)

        # Test analytics service
        service = AnalyticsService(mock_db)
        result = await service.generate_summary_analytics()

        # Basic assertions
        assert result["total_buses"] == 50
        assert result["active_buses"] == 45
        assert result["total_routes"] == 20
        assert result["active_routes"] == 18
        assert result["revenue_today"] == 44.25
    
    async def test_operational_metrics(self):
        """Test operational metrics calculation."""
        mock_db = self.create_mock_db()

        # Mock trips with various delays
        mock_trips = [
            {"delay_minutes": 3, "duration_minutes": 45},
            {"delay_minutes": 12, "duration_minutes": 52},
            {"delay_minutes": 2, "duration_minutes": 38},
            {"delay_minutes": 8, "duration_minutes": 41}
        ]
        mock_db.trips.find.return_value.to_list = AsyncMock(return_value=mock_trips)
        mock_db.buses.count_documents = AsyncMock(return_value=10)
        mock_db.incidents.count_documents = AsyncMock(return_value=2)

        service = AnalyticsService(mock_db)
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        result = await service.generate_operational_metrics(start_date, end_date)

        # Verify calculations
        assert result["on_time_performance"] == 50.0  # 2 out of 4 trips on time
        assert result["average_trip_duration"] == 44.0
        assert result["breakdown_incidents"] == 2
    
    async def test_financial_metrics(self):
        """Test financial metrics calculation."""
        mock_db = self.create_mock_db()

        mock_payments = [
            {"amount": 100.0},
            {"amount": 150.0},
            {"amount": 75.0}
        ]
        mock_db.payments.find.return_value.to_list = AsyncMock(return_value=mock_payments)

        service = AnalyticsService(mock_db)
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        result = await service.generate_financial_metrics(start_date, end_date)

        # Verify basic financial calculations
        assert result["profit_margin"] == 25.0  # Based on 75% cost ratio
        assert "daily_revenue" in result
        assert "operating_costs" in result
    
    async def test_realtime_analytics(self):
        """Test real-time analytics service."""
        mock_db = self.create_mock_db()
        mock_websocket = AsyncMock()

        # Setup mock data with proper async returns
        mock_db.buses.count_documents = AsyncMock(return_value=25)
        mock_db.trips.count_documents = AsyncMock(return_value=150)
        mock_db.alerts.count_documents = AsyncMock(return_value=5)
        mock_db.reallocation_requests.count_documents = AsyncMock(return_value=3)
        mock_db.incidents.count_documents = AsyncMock(return_value=2)

        payments_data = [{"amount": 50.0}, {"amount": 75.0}]
        mock_db.payments.find.return_value.to_list = AsyncMock(return_value=payments_data)

        service = RealTimeAnalyticsService(mock_db, mock_websocket)
        result = await service._get_live_metrics()

        # Verify live metrics
        assert result["active_buses"] == 25
        assert result["trips_today"] == 150
        assert result["revenue_today"] == 125.0
        assert "last_updated" in result
    
    async def test_kpi_thresholds(self):
        """Test KPI threshold detection."""
        mock_db = self.create_mock_db()
        mock_websocket = AsyncMock()

        # Mock trips with high delay rate
        mock_trips = [
            {"delay_minutes": 15},  # Delayed
            {"delay_minutes": 20},  # Delayed
            {"delay_minutes": 3},   # On time
            {"delay_minutes": 25}   # Delayed
        ]
        mock_db.trips.find.return_value.to_list = AsyncMock(return_value=mock_trips)
        mock_db.buses.count_documents = AsyncMock(return_value=10)

        service = RealTimeAnalyticsService(mock_db, mock_websocket)
        result = await service._check_kpi_thresholds()

        # Should detect high delay rate (75% > 25% threshold)
        delay_breach = next((b for b in result if b["metric"] == "delay_percentage"), None)
        assert delay_breach is not None
        assert delay_breach["value"] == 75.0
    
    def test_service_imports(self):
        """Test that all analytics services can be imported."""
        # This test already passed if we got here
        assert AnalyticsService is not None
        assert RealTimeAnalyticsService is not None
        assert ScheduledAnalyticsService is not None
    
    def run_all_tests(self):
        """Run all analytics tests."""
        print("🚀 Starting Analytics Feature Tests")
        print("=" * 50)
        
        # List of tests to run
        tests = [
            ("Service Imports", self.test_service_imports),
            ("Analytics Service Basic", self.test_analytics_service_basic),
            ("Operational Metrics", self.test_operational_metrics),
            ("Financial Metrics", self.test_financial_metrics),
            ("Real-time Analytics", self.test_realtime_analytics),
            ("KPI Thresholds", self.test_kpi_thresholds),
        ]
        
        print(f"\n📊 Running {len(tests)} tests...\n")
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📈 TEST RESULTS SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        
        if self.failed > 0:
            print(f"\n❌ Failed Tests:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print(f"\n✅ All tests passed!")
        
        success_rate = (self.passed / (self.passed + self.failed)) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        return self.failed == 0


def main():
    """Main test runner function."""
    print("🔍 Analytics Feature Test Suite")
    print("Testing GuzoSync Analytics Implementation")
    print("=" * 60)
    
    runner = AnalyticsTestRunner()
    success = runner.run_all_tests()
    
    if success:
        print("\n🎉 Analytics feature is working correctly!")
        print("\n📋 Verified Features:")
        print("  • Summary Analytics Generation")
        print("  • Operational Metrics Calculation")
        print("  • Financial Metrics Processing")
        print("  • Real-time Data Updates")
        print("  • KPI Threshold Monitoring")
        print("  • Service Architecture")
        
        print("\n💡 Next Steps:")
        print("  • Run with real database for integration testing")
        print("  • Test API endpoints with authentication")
        print("  • Verify WebSocket real-time updates")
        print("  • Test scheduled report generation")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
