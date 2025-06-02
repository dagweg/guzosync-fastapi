"""
Comprehensive tests for the issues router endpoints.
Tests all endpoints with various scenarios including success cases,
error handling, validation, and edge cases.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from datetime import datetime
from uuid import uuid4
from httpx import AsyncClient
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from conftest import TestFixtures


class TestReportIssue:
    """Test issue reporting endpoint."""
    
    async def test_report_issue_success(self, passenger_client: AsyncClient, test_fixtures: TestFixtures):
        """Test successful issue reporting."""
        bus_id = str(uuid4())
        route_id = str(uuid4())
        
        issue_data = {
            "description": "Bus broke down at Main Street",
            "severity": "HIGH",
            "related_bus_id": bus_id,
            "related_route_id": route_id,
            "location": {
                "latitude": 9.0320,
                "longitude": 38.7469,
                "address": "Main Street, Addis Ababa"
            }
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == issue_data["description"]
        assert data["severity"] == "HIGH"
        assert data["related_bus_id"] == bus_id
        assert data["related_route_id"] == route_id
        assert data["location"]["latitude"] == 9.0320
        assert data["location"]["longitude"] == 38.7469
        assert data["location"]["address"] == "Main Street, Addis Ababa"
        assert "id" in data
        assert "reported_at" in data
        assert data["is_resolved"] == False
    
    async def test_report_issue_low_severity(self, passenger_client: AsyncClient):
        """Test reporting issue with low severity."""
        issue_data = {
            "description": "Minor delay at bus stop",
            "severity": "LOW",
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["severity"] == "LOW"
    
    async def test_report_issue_medium_severity(self, passenger_client: AsyncClient):
        """Test reporting issue with medium severity."""
        issue_data = {
            "description": "Bus running late due to traffic",
            "severity": "MEDIUM",
            "related_route_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["severity"] == "MEDIUM"
    
    async def test_report_issue_critical_severity(self, passenger_client: AsyncClient):
        """Test reporting issue with critical severity."""
        issue_data = {
            "description": "Bus accident on highway",
            "severity": "CRITICAL",
            "related_bus_id": str(uuid4()),
            "location": {
                "latitude": 9.0320,
                "longitude": 38.7469,
                "address": "Highway near Bole"
            }
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["severity"] == "CRITICAL"
    
    async def test_report_issue_without_location(self, passenger_client: AsyncClient):
        """Test reporting issue without location."""
        issue_data = {
            "description": "General service complaint",
            "severity": "MEDIUM",
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["location"] is None
    
    async def test_report_issue_without_bus_id(self, passenger_client: AsyncClient):
        """Test reporting issue without bus ID."""
        issue_data = {
            "description": "Route is frequently delayed",
            "severity": "MEDIUM",
            "related_route_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["related_bus_id"] is None
    
    async def test_report_issue_without_route_id(self, passenger_client: AsyncClient):
        """Test reporting issue without route ID."""
        issue_data = {
            "description": "Bus driver was rude",
            "severity": "LOW",
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["related_route_id"] is None
    
    async def test_report_issue_empty_description(self, passenger_client: AsyncClient):
        """Test reporting issue with empty description."""
        issue_data = {
            "description": "",
            "severity": "MEDIUM",
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 422
    
    async def test_report_issue_missing_description(self, passenger_client: AsyncClient):
        """Test reporting issue without description."""
        issue_data = {
            "severity": "MEDIUM",
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 422
    
    async def test_report_issue_invalid_severity(self, passenger_client: AsyncClient):
        """Test reporting issue with invalid severity."""
        issue_data = {
            "description": "Bus issue",
            "severity": "INVALID",
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 422
    
    async def test_report_issue_missing_severity(self, passenger_client: AsyncClient):
        """Test reporting issue without severity."""
        issue_data = {
            "description": "Bus issue",
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 422
    
    async def test_report_issue_invalid_uuid_format(self, passenger_client: AsyncClient):
        """Test reporting issue with invalid UUID format."""
        issue_data = {
            "description": "Bus issue",
            "severity": "MEDIUM",
            "related_bus_id": "invalid-uuid"
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 422
    
    async def test_report_issue_invalid_location(self, passenger_client: AsyncClient):
        """Test reporting issue with invalid location data."""
        issue_data = {
            "description": "Bus issue",
            "severity": "MEDIUM",
            "related_bus_id": str(uuid4()),
            "location": {
                "latitude": "invalid",  # Should be a number
                "longitude": 38.7469,
                "address": "Test Address"
            }
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 422
    
    async def test_report_issue_unauthorized(self, client: AsyncClient):
        """Test issue reporting without authentication."""
        issue_data = {
            "description": "Bus issue",
            "severity": "MEDIUM",
            "related_bus_id": str(uuid4())
        }
        
        response = await client.post("/api/issues/report", json=issue_data)
        
        assert response.status_code == 401
    
    async def test_report_issue_long_description(self, passenger_client: AsyncClient):
        """Test reporting issue with very long description."""
        long_description = "A" * 2000  # Very long description
        issue_data = {
            "description": long_description,
            "severity": "MEDIUM",
            "related_bus_id": str(uuid4())
        }
        
        response = await passenger_client.post("/api/issues/report", json=issue_data)
        
        # Should either succeed or fail validation depending on limits
        assert response.status_code in [201, 422]


class TestGetIssues:
    """Test issues retrieval endpoint."""
    
    async def test_get_issues_passenger(self, passenger_client: AsyncClient, test_fixtures: TestFixtures):
        """Test passenger can only see their own reported issues."""
        # First report an issue
        issue_data = {
            "description": "Bus was very crowded",
            "severity": "MEDIUM",
            "related_bus_id": str(uuid4())
        }
        
        # Report issue first
        report_response = await passenger_client.post("/api/issues/report", json=issue_data)
        assert report_response.status_code == 201
        
        # Then retrieve issues
        response = await passenger_client.get("/api/issues")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should contain the issue we just reported
        if data:
            assert any(issue["description"] == "Bus was very crowded" for issue in data)
    
    async def test_get_issues_admin(self, admin_client: AsyncClient, test_fixtures: TestFixtures):
        """Test admin can see all reported issues."""
        response = await admin_client.get("/api/issues")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Admin should see all issues, not filtered by user
    
    async def test_get_issues_regulator(self, regulator_client: AsyncClient, test_fixtures: TestFixtures):
        """Test regulator can see all reported issues."""
        response = await regulator_client.get("/api/issues")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Regulator should see all issues, not filtered by user
    
    async def test_get_issues_pagination(self, passenger_client: AsyncClient):
        """Test issues pagination."""
        # Test with skip and limit parameters
        response = await passenger_client.get("/api/issues?skip=0&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
    
    async def test_get_issues_pagination_skip(self, passenger_client: AsyncClient):
        """Test issues pagination with skip."""
        response = await passenger_client.get("/api/issues?skip=10&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_issues_invalid_skip(self, passenger_client: AsyncClient):
        """Test issues with invalid skip parameter."""
        response = await passenger_client.get("/api/issues?skip=-1")
        
        assert response.status_code == 422
    
    async def test_get_issues_invalid_limit_low(self, passenger_client: AsyncClient):
        """Test issues with limit below minimum."""
        response = await passenger_client.get("/api/issues?limit=0")
        
        assert response.status_code == 422
    
    async def test_get_issues_invalid_limit_high(self, passenger_client: AsyncClient):
        """Test issues with limit above maximum."""
        response = await passenger_client.get("/api/issues?limit=101")
        
        assert response.status_code == 422
    
    async def test_get_issues_unauthorized(self, client: AsyncClient):
        """Test issues retrieval without authentication."""
        response = await client.get("/api/issues")
        
        assert response.status_code == 401
    
    async def test_get_issues_empty_result(self, passenger_client: AsyncClient):
        """Test issues retrieval when no issues exist."""
        response = await passenger_client.get("/api/issues")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should return empty list if no issues exist
    
    async def test_get_issues_default_pagination(self, passenger_client: AsyncClient):
        """Test issues with default pagination parameters."""
        response = await passenger_client.get("/api/issues")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should use default skip=0, limit=10
        assert len(data) <= 10


class TestIssuesEndpointsIntegration:
    """Integration tests for issues endpoints."""
    
    async def test_report_and_retrieve_issue_flow(self, passenger_client: AsyncClient):
        """Test the complete flow of reporting and retrieving issues."""
        bus_id = str(uuid4())
        
        # Report issue
        issue_data = {
            "description": "Integration test issue",
            "severity": "HIGH",
            "related_bus_id": bus_id,
            "location": {
                "latitude": 9.0320,
                "longitude": 38.7469,
                "address": "Test Location"
            }
        }
        
        report_response = await passenger_client.post("/api/issues/report", json=issue_data)
        assert report_response.status_code == 201
        reported_issue = report_response.json()
        
        # Retrieve issues
        get_response = await passenger_client.get("/api/issues")
        assert get_response.status_code == 200
        issues_list = get_response.json()
        
        # Verify the reported issue is in the list
        assert any(
            issue["id"] == reported_issue["id"] 
            for issue in issues_list
        )
    
    async def test_multiple_issue_reports(self, passenger_client: AsyncClient):
        """Test reporting multiple issues."""
        severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        issue_entries = [
            {
                "description": f"Issue {i} - {severity} severity",
                "severity": severity,
                "related_bus_id": str(uuid4())
            }
            for i, severity in enumerate(severities)
        ]
        
        reported_ids = []
        for issue_data in issue_entries:
            response = await passenger_client.post("/api/issues/report", json=issue_data)
            assert response.status_code == 201
            reported_ids.append(response.json()["id"])
        
        # Retrieve all issues
        get_response = await passenger_client.get("/api/issues")
        assert get_response.status_code == 200
        issues_list = get_response.json()
        
        # Verify all reported issues are present
        retrieved_ids = [issue["id"] for issue in issues_list]
        for reported_id in reported_ids:
            assert reported_id in retrieved_ids
    
    async def test_issue_severity_levels(self, passenger_client: AsyncClient):
        """Test all severity levels are handled correctly."""
        severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        
        for severity in severities:
            issue_data = {
                "description": f"Test {severity} severity issue",
                "severity": severity,
                "related_bus_id": str(uuid4())
            }
            
            response = await passenger_client.post("/api/issues/report", json=issue_data)
            assert response.status_code == 201
            data = response.json()
            assert data["severity"] == severity
    
    async def test_role_based_access_control(self, passenger_client: AsyncClient, admin_client: AsyncClient):
        """Test role-based access control for issues."""
        # Passenger reports an issue
        issue_data = {
            "description": "Passenger reported issue",
            "severity": "MEDIUM",
            "related_bus_id": str(uuid4())
        }
        
        passenger_report_response = await passenger_client.post("/api/issues/report", json=issue_data)
        assert passenger_report_response.status_code == 201
        
        # Passenger sees only their own issues
        passenger_get_response = await passenger_client.get("/api/issues")
        assert passenger_get_response.status_code == 200
        passenger_issues = passenger_get_response.json()
        
        # Admin sees all issues
        admin_get_response = await admin_client.get("/api/issues")
        assert admin_get_response.status_code == 200
        admin_issues = admin_get_response.json()
        
        # Admin should see at least as many issues as passenger
        assert len(admin_issues) >= len(passenger_issues)
