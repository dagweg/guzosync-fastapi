import pytest
from httpx import AsyncClient
from datetime import datetime
from fastapi import status
from uuid import uuid4

from tests.conftest import TestFixtures


class TestAlertsRouter:
    """Test cases for alerts router endpoints."""

    @pytest.mark.asyncio
    async def test_get_alerts_empty(
        self, passenger_client: AsyncClient
    ):
        """Test retrieving alerts when none exist."""
        response = await passenger_client.get("/api/alerts")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_alerts_with_data(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test retrieving alerts with data."""
        # Create test alerts
        alerts = [
            {
                "_id": test_fixtures.object_ids[0],
                "id": test_fixtures.uuids[0],
                "title": "Traffic Alert",
                "message": "Heavy traffic on Route 1",
                "alert_type": "TRAFFIC",
                "severity": "HIGH",
                "affected_routes": [test_fixtures.object_ids[0]],
                "affected_bus_stops": [test_fixtures.object_ids[1]],
                "is_active": True,
                "created_by": test_fixtures.admin_user["_id"],
                "created_at": datetime.utcnow()
            },
            {
                "_id": test_fixtures.object_ids[1],
                "id": test_fixtures.uuids[1],
                "title": "Weather Alert",
                "message": "Heavy rain expected",
                "alert_type": "WEATHER",
                "severity": "MEDIUM",
                "affected_routes": [],
                "affected_bus_stops": [],
                "is_active": True,
                "created_by": test_fixtures.admin_user["_id"],
                "created_at": datetime.utcnow()
            }
        ]
        
        await mongodb.alerts.insert_many(alerts)
        
        response = await passenger_client.get("/api/alerts")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Traffic Alert"
        assert data[1]["title"] == "Weather Alert"

    @pytest.mark.asyncio
    async def test_get_alerts_only_active(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test that only active alerts are returned."""
        alerts = [
            {
                "_id": test_fixtures.object_ids[0],
                "id": test_fixtures.uuids[0],
                "title": "Active Alert",
                "message": "This is active",
                "alert_type": "TRAFFIC",
                "severity": "HIGH",
                "is_active": True,
                "created_by": test_fixtures.admin_user["_id"],
                "created_at": datetime.utcnow()
            },
            {
                "_id": test_fixtures.object_ids[1],
                "id": test_fixtures.uuids[1],
                "title": "Inactive Alert",
                "message": "This is inactive",
                "alert_type": "WEATHER",
                "severity": "MEDIUM",
                "is_active": False,
                "created_by": test_fixtures.admin_user["_id"],
                "created_at": datetime.utcnow()
            }
        ]
        
        await mongodb.alerts.insert_many(alerts)
        
        response = await passenger_client.get("/api/alerts")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Active Alert"

    @pytest.mark.asyncio
    async def test_get_alerts_pagination(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test alerts pagination."""
        # Create multiple alerts
        alerts = []
        for i in range(15):
            alerts.append({
                "_id": test_fixtures.object_ids[i % len(test_fixtures.object_ids)],
                "id": test_fixtures.uuids[i % len(test_fixtures.uuids)],
                "title": f"Alert {i}",
                "message": f"Message {i}",
                "alert_type": "TRAFFIC",
                "severity": "LOW",
                "is_active": True,
                "created_by": test_fixtures.admin_user["_id"],
                "created_at": datetime.utcnow()
            })
        
        await mongodb.alerts.insert_many(alerts)
        
        # Test first page
        response = await passenger_client.get("/api/alerts?skip=0&limit=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 5
          # Test second page
        response = await passenger_client.get("/api/alerts?skip=5&limit=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_get_alerts_unauthorized(
        self, test_client: AsyncClient
    ):
        """Test retrieving alerts without authentication."""
        response = await test_client.get("/api/alerts")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_alert_success_admin(
        self, admin_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test successful alert creation by admin."""
        alert_data = {
            "title": "Emergency Alert",
            "message": "Emergency situation on Route 1",
            "alert_type": "EMERGENCY",
            "severity": "CRITICAL",
            "affected_routes": [str(test_fixtures.object_ids[0])],
            "affected_bus_stops": [str(test_fixtures.object_ids[1])]
        }
        
        response = await admin_client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Emergency Alert"
        assert data["alert_type"] == "EMERGENCY"
        assert data["severity"] == "CRITICAL"
        assert data["is_active"] is True
        assert data["created_by"] == str(test_fixtures.admin_user["_id"])

    @pytest.mark.asyncio
    async def test_create_alert_success_regulator(
        self, regulator_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test successful alert creation by regulator."""
        alert_data = {
            "title": "Route Change",
            "message": "Route 2 temporarily closed",
            "alert_type": "ROUTE_CHANGE",
            "severity": "HIGH"
        }
        
        response = await regulator_client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Route Change"
        assert data["created_by"] == str(test_fixtures.regulator_user["_id"])

    @pytest.mark.asyncio
    async def test_create_alert_forbidden_passenger(
        self, passenger_client: AsyncClient
    ):
        """Test alert creation forbidden for passengers."""
        alert_data = {
            "title": "Test Alert",
            "message": "Test message",
            "alert_type": "TRAFFIC",
            "severity": "LOW"
        }
        
        response = await passenger_client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_alert_forbidden_driver(
        self, driver_client: AsyncClient
    ):
        """Test alert creation forbidden for drivers."""
        alert_data = {
            "title": "Test Alert",
            "message": "Test message",
            "alert_type": "TRAFFIC",
            "severity": "LOW"
        }
        
        response = await driver_client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_alert_invalid_data(
        self, admin_client: AsyncClient
    ):
        """Test alert creation with invalid data."""
        alert_data = {
            "title": "",  # Empty title
            "message": "Valid message",
            "alert_type": "INVALID_TYPE",
            "severity": "LOW"
        }
        
        response = await admin_client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_alert_missing_required_fields(
        self, admin_client: AsyncClient
    ):
        """Test alert creation with missing required fields."""
        alert_data = {
            "title": "Test Alert"
            # Missing message, alert_type, severity
        }
        
        response = await admin_client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_alert_success(
        self, admin_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test successful alert update."""
        # Create test alert
        alert = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "title": "Original Title",
            "message": "Original message",
            "alert_type": "TRAFFIC",
            "severity": "LOW",
            "is_active": True,
            "created_by": test_fixtures.admin_user["_id"],
            "created_at": datetime.utcnow()
        }
        
        await mongodb.alerts.insert_one(alert)
        
        update_data = {
            "title": "Updated Title",
            "severity": "HIGH"
        }
        
        response = await admin_client.put(f"/api/alerts/{test_fixtures.uuids[0]}", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["severity"] == "HIGH"
        assert data["message"] == "Original message"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_alert_not_found(
        self, admin_client: AsyncClient
    ):
        """Test updating non-existent alert."""
        update_data = {
            "title": "Updated Title"
        }
        
        response = await admin_client.put(f"/api/alerts/{uuid4()}", json=update_data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_alert_forbidden_passenger(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test alert update forbidden for passengers."""
        # Create test alert
        alert = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "title": "Test Alert",
            "message": "Test message",
            "alert_type": "TRAFFIC",
            "severity": "LOW",
            "is_active": True,
            "created_by": test_fixtures.admin_user["_id"],
            "created_at": datetime.utcnow()
        }
        
        await mongodb.alerts.insert_one(alert)
        
        update_data = {"title": "Updated Title"}
        
        response = await passenger_client.put(f"/api/alerts/{test_fixtures.uuids[0]}", json=update_data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_alert_success(
        self, admin_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test successful alert deletion."""
        # Create test alert
        alert = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "title": "Test Alert",
            "message": "Test message",
            "alert_type": "TRAFFIC",
            "severity": "LOW",
            "is_active": True,
            "created_by": test_fixtures.admin_user["_id"],
            "created_at": datetime.utcnow()
        }
        
        await mongodb.alerts.insert_one(alert)
        
        response = await admin_client.delete(f"/api/alerts/{test_fixtures.uuids[0]}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Alert deleted successfully"

    @pytest.mark.asyncio
    async def test_delete_alert_not_found(
        self, admin_client: AsyncClient
    ):
        """Test deleting non-existent alert."""
        response = await admin_client.delete(f"/api/alerts/{uuid4()}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_alert_forbidden_passenger(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test alert deletion forbidden for passengers."""
        # Create test alert
        alert = {
            "_id": test_fixtures.object_ids[0],
            "id": test_fixtures.uuids[0],
            "title": "Test Alert",
            "message": "Test message",
            "alert_type": "TRAFFIC",
            "severity": "LOW",
            "is_active": True,
            "created_by": test_fixtures.admin_user["_id"],
            "created_at": datetime.utcnow()
        }
        
        await mongodb.alerts.insert_one(alert)
        
        response = await passenger_client.delete(f"/api/alerts/{test_fixtures.uuids[0]}")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_alert_all_severity_levels(
        self, admin_client: AsyncClient
    ):
        """Test creating alerts with all severity levels."""
        severity_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        
        for severity in severity_levels:
            alert_data = {
                "title": f"{severity} Alert",
                "message": f"This is a {severity} alert",
                "alert_type": "TRAFFIC",
                "severity": severity
            }
            
            response = await admin_client.post("/api/alerts", json=alert_data)
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["severity"] == severity

    @pytest.mark.asyncio
    async def test_alert_all_types(
        self, admin_client: AsyncClient
    ):
        """Test creating alerts with all types."""
        alert_types = ["TRAFFIC", "WEATHER", "MAINTENANCE", "EMERGENCY", "ROUTE_CHANGE", "SERVICE_UPDATE"]
        
        for alert_type in alert_types:
            alert_data = {
                "title": f"{alert_type} Alert",
                "message": f"This is a {alert_type} alert",
                "alert_type": alert_type,
                "severity": "MEDIUM"
            }
            
            response = await admin_client.post("/api/alerts", json=alert_data)
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["alert_type"] == alert_type

    @pytest.mark.asyncio
    async def test_alert_with_affected_routes_and_stops(
        self, admin_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test creating alert with affected routes and bus stops."""
        alert_data = {
            "title": "Route Specific Alert",
            "message": "Alert affecting specific routes and stops",
            "alert_type": "MAINTENANCE",
            "severity": "HIGH",
            "affected_routes": [str(test_fixtures.object_ids[0]), str(test_fixtures.object_ids[1])],
            "affected_bus_stops": [str(test_fixtures.object_ids[2]), str(test_fixtures.object_ids[3])]
        }
        
        response = await admin_client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["affected_routes"]) == 2
        assert len(data["affected_bus_stops"]) == 2

    @pytest.mark.asyncio
    async def test_alerts_sorted_by_creation_date(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test that alerts are sorted by creation date (newest first)."""
        base_time = datetime.utcnow()
        
        alerts = [
            {
                "_id": test_fixtures.object_ids[0],
                "id": test_fixtures.uuids[0],
                "title": "First Alert",
                "message": "Created first",
                "alert_type": "TRAFFIC",
                "severity": "LOW",
                "is_active": True,
                "created_by": test_fixtures.admin_user["_id"],
                "created_at": base_time
            },
            {
                "_id": test_fixtures.object_ids[1],
                "id": test_fixtures.uuids[1],
                "title": "Second Alert",
                "message": "Created second",
                "alert_type": "WEATHER",
                "severity": "MEDIUM",
                "is_active": True,
                "created_by": test_fixtures.admin_user["_id"],
                "created_at": base_time.replace(second=base_time.second + 1)
            }
        ]
        
        await mongodb.alerts.insert_many(alerts)
        
        response = await passenger_client.get("/api/alerts")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        # Newest first
        assert data[0]["title"] == "Second Alert"
        assert data[1]["title"] == "First Alert"
