"""
Tests for the regulators router endpoints.
Tests the new /request-reallocation and /report-overcrowding endpoints.
"""

import pytest
import pytest_asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from datetime import datetime
from uuid import uuid4
from httpx import AsyncClient
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from conftest import TestFixtures


class TestRequestReallocation:
    """Test bus reallocation request endpoint."""
    
    async def test_request_reallocation_success(self, regulator_client: AsyncClient, test_fixtures: TestFixtures, mock_mongodb):
        """Test successful reallocation request."""
        bus_id = str(uuid4())
        current_route_id = str(uuid4())
        requested_route_id = str(uuid4())

        # Mock bus and routes existence
        mock_mongodb.buses.find_one.return_value = {"_id": bus_id}
        mock_mongodb.routes.find_one.side_effect = [
            {"_id": current_route_id},  # current route
            {"_id": requested_route_id}  # requested route
        ]

        # Mock insert operation
        mock_mongodb.reallocation_requests.insert_one.return_value.inserted_id = "test_id"
        mock_mongodb.reallocation_requests.find_one.return_value = {
            "_id": "test_id",
            "id": "test_id",
            "requested_by_user_id": "test_user_id",
            "bus_id": bus_id,
            "current_route_id": current_route_id,
            "requested_route_id": requested_route_id,
            "reason": "OVERCROWDING",
            "description": "Bus is overcrowded on current route, need reallocation",
            "priority": "HIGH",
            "status": "PENDING",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        reallocation_data = {
            "bus_id": bus_id,
            "current_route_id": current_route_id,
            "requested_route_id": requested_route_id,
            "reason": "OVERCROWDING",
            "description": "Bus is overcrowded on current route, need reallocation",
            "priority": "HIGH"
        }
        
        response = await regulator_client.post("/api/regulators/request-reallocation", json=reallocation_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["bus_id"] == bus_id
        assert data["current_route_id"] == current_route_id
        assert data["requested_route_id"] == requested_route_id
        assert data["reason"] == "OVERCROWDING"
        assert data["description"] == reallocation_data["description"]
        assert data["priority"] == "HIGH"
        assert data["status"] == "PENDING"
        assert "id" in data
        assert "created_at" in data
    
    async def test_request_reallocation_bus_not_found(self, regulator_client: AsyncClient, mock_mongodb):
        """Test reallocation request with non-existent bus."""
        bus_id = str(uuid4())

        # Mock bus not found
        mock_mongodb.buses.find_one.return_value = None
        
        reallocation_data = {
            "bus_id": bus_id,
            "current_route_id": str(uuid4()),
            "requested_route_id": str(uuid4()),
            "reason": "OVERCROWDING",
            "description": "Test description"
        }
        
        response = await regulator_client.post("/api/regulators/request-reallocation", json=reallocation_data)
        
        assert response.status_code == 404
        assert "Bus not found" in response.json()["detail"]
    
    async def test_request_reallocation_unauthorized(self, test_client: AsyncClient):
        """Test reallocation request without authentication."""
        reallocation_data = {
            "bus_id": str(uuid4()),
            "current_route_id": str(uuid4()),
            "requested_route_id": str(uuid4()),
            "reason": "OVERCROWDING",
            "description": "Test description"
        }
        
        response = await test_client.post("/api/regulators/request-reallocation", json=reallocation_data)
        
        assert response.status_code == 401


class TestReportOvercrowding:
    """Test overcrowding report endpoint."""
    
    async def test_report_overcrowding_success(self, regulator_client: AsyncClient, test_fixtures: TestFixtures, mock_mongodb):
        """Test successful overcrowding report."""
        bus_stop_id = str(uuid4())
        bus_id = str(uuid4())
        route_id = str(uuid4())

        # Mock bus stop, bus, and route existence
        mock_mongodb.bus_stops.find_one.return_value = {"_id": bus_stop_id}
        mock_mongodb.buses.find_one.return_value = {"_id": bus_id}
        mock_mongodb.routes.find_one.return_value = {"_id": route_id}

        # Mock insert operation
        mock_mongodb.overcrowding_reports.insert_one.return_value.inserted_id = "test_id"
        mock_mongodb.overcrowding_reports.find_one.return_value = {
            "_id": "test_id",
            "id": "test_id",
            "reported_by_user_id": "test_user_id",
            "bus_stop_id": bus_stop_id,
            "bus_id": bus_id,
            "route_id": route_id,
            "severity": "HIGH",
            "passenger_count": 150,
            "description": "Bus stop is severely overcrowded during rush hour",
            "location": {"latitude": 9.0320, "longitude": 38.7469},
            "is_resolved": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        overcrowding_data = {
            "bus_stop_id": bus_stop_id,
            "bus_id": bus_id,
            "route_id": route_id,
            "severity": "HIGH",
            "passenger_count": 150,
            "description": "Bus stop is severely overcrowded during rush hour",
            "location": {
                "latitude": 9.0320,
                "longitude": 38.7469
            }
        }
        
        response = await regulator_client.post("/api/regulators/report-overcrowding", json=overcrowding_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["bus_stop_id"] == bus_stop_id
        assert data["bus_id"] == bus_id
        assert data["route_id"] == route_id
        assert data["severity"] == "HIGH"
        assert data["passenger_count"] == 150
        assert data["description"] == overcrowding_data["description"]
        assert data["location"]["latitude"] == 9.0320
        assert data["location"]["longitude"] == 38.7469
        assert data["is_resolved"] == False
        assert "id" in data
        assert "created_at" in data
    
    async def test_report_overcrowding_bus_stop_not_found(self, regulator_client: AsyncClient, mock_mongodb):
        """Test overcrowding report with non-existent bus stop."""
        bus_stop_id = str(uuid4())

        # Mock bus stop not found
        mock_mongodb.bus_stops.find_one.return_value = None
        
        overcrowding_data = {
            "bus_stop_id": bus_stop_id,
            "severity": "MEDIUM",
            "description": "Test description"
        }
        
        response = await regulator_client.post("/api/regulators/report-overcrowding", json=overcrowding_data)
        
        assert response.status_code == 404
        assert "Bus stop not found" in response.json()["detail"]
    
    async def test_report_overcrowding_without_optional_fields(self, regulator_client: AsyncClient, mock_mongodb):
        """Test overcrowding report with only required fields."""
        bus_stop_id = str(uuid4())

        # Mock bus stop existence
        mock_mongodb.bus_stops.find_one.return_value = {"_id": bus_stop_id}

        # Mock insert operation
        mock_mongodb.overcrowding_reports.insert_one.return_value.inserted_id = "test_id"
        mock_mongodb.overcrowding_reports.find_one.return_value = {
            "_id": "test_id",
            "id": "test_id",
            "reported_by_user_id": "test_user_id",
            "bus_stop_id": bus_stop_id,
            "bus_id": None,
            "route_id": None,
            "severity": "LOW",
            "passenger_count": None,
            "description": "Minor overcrowding issue",
            "location": None,
            "is_resolved": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        overcrowding_data = {
            "bus_stop_id": bus_stop_id,
            "severity": "LOW",
            "description": "Minor overcrowding issue"
        }
        
        response = await regulator_client.post("/api/regulators/report-overcrowding", json=overcrowding_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["bus_stop_id"] == bus_stop_id
        assert data["bus_id"] is None
        assert data["route_id"] is None
        assert data["passenger_count"] is None
        assert data["location"] is None
        assert data["severity"] == "LOW"
    
    async def test_report_overcrowding_unauthorized(self, test_client: AsyncClient):
        """Test overcrowding report without authentication."""
        overcrowding_data = {
            "bus_stop_id": str(uuid4()),
            "severity": "MEDIUM",
            "description": "Test description"
        }
        
        response = await test_client.post("/api/regulators/report-overcrowding", json=overcrowding_data)
        
        assert response.status_code == 401


class TestRegulatorsEndpointsIntegration:
    """Integration tests for regulators endpoints."""
    
    async def test_regulator_workflow(self, regulator_client: AsyncClient, mock_mongodb):
        """Test complete regulator workflow."""
        bus_id = str(uuid4())
        bus_stop_id = str(uuid4())
        current_route_id = str(uuid4())
        requested_route_id = str(uuid4())

        # Mock all required entities
        mock_mongodb.buses.find_one.return_value = {"_id": bus_id}
        mock_mongodb.bus_stops.find_one.return_value = {"_id": bus_stop_id}
        mock_mongodb.routes.find_one.side_effect = [
            {"_id": current_route_id},
            {"_id": requested_route_id}
        ]

        # Mock insert operations
        mock_mongodb.overcrowding_reports.insert_one.return_value.inserted_id = "overcrowding_id"
        mock_mongodb.overcrowding_reports.find_one.return_value = {
            "_id": "overcrowding_id",
            "id": "overcrowding_id",
            "reported_by_user_id": "test_user_id",
            "bus_stop_id": bus_stop_id,
            "bus_id": bus_id,
            "severity": "CRITICAL",
            "description": "Severe overcrowding at main terminal",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        mock_mongodb.reallocation_requests.insert_one.return_value.inserted_id = "reallocation_id"
        mock_mongodb.reallocation_requests.find_one.return_value = {
            "_id": "reallocation_id",
            "id": "reallocation_id",
            "requested_by_user_id": "test_user_id",
            "bus_id": bus_id,
            "current_route_id": current_route_id,
            "requested_route_id": requested_route_id,
            "reason": "OVERCROWDING",
            "description": "Need to reallocate due to overcrowding report",
            "status": "PENDING",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # First report overcrowding
        overcrowding_data = {
            "bus_stop_id": bus_stop_id,
            "bus_id": bus_id,
            "severity": "CRITICAL",
            "description": "Severe overcrowding at main terminal"
        }
        
        overcrowding_response = await regulator_client.post("/api/regulators/report-overcrowding", json=overcrowding_data)
        assert overcrowding_response.status_code == 201
        
        # Then request reallocation
        reallocation_data = {
            "bus_id": bus_id,
            "current_route_id": current_route_id,
            "requested_route_id": requested_route_id,
            "reason": "OVERCROWDING",
            "description": "Need to reallocate due to overcrowding report"
        }
        
        reallocation_response = await regulator_client.post("/api/regulators/request-reallocation", json=reallocation_data)
        assert reallocation_response.status_code == 201
        
        # Verify both requests were created successfully
        overcrowding_result = overcrowding_response.json()
        reallocation_result = reallocation_response.json()
        
        assert overcrowding_result["bus_id"] == reallocation_result["bus_id"]
        assert reallocation_result["reason"] == "OVERCROWDING"
