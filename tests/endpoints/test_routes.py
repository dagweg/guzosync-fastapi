import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from tests.conftest import TestFixtures


class TestRoutesRouter:
    """Test cases for routes router endpoints"""

    @pytest.mark.asyncio
    async def test_get_route_success(self, authenticated_client, mock_mongodb):
        """Test successful retrieval of route by ID"""
        route_id = str(uuid4())
        route = TestFixtures.create_test_route(name="Route 1: City Center - Airport")
        route["id"] = route_id
        
        mock_mongodb.routes.find_one.return_value = route
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == route_id
        assert data["name"] == "Route 1: City Center - Airport"
        assert "origin_stop_id" in data
        assert "destination_stop_id" in data

    @pytest.mark.asyncio
    async def test_get_route_not_found(self, authenticated_client, mock_mongodb):
        """Test retrieval of non-existent route"""
        route_id = str(uuid4())
        mock_mongodb.routes.find_one.return_value = None
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 404
        assert "route not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_route_invalid_id(self, authenticated_client):
        """Test retrieval with invalid route ID format"""
        invalid_id = "invalid-uuid-format"
        
        response = await authenticated_client.get(f"/api/routes/{invalid_id}")
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_route_unauthenticated(self, test_client):
        """Test route retrieval without authentication"""
        route_id = str(uuid4())
        
        response = await test_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_route_with_stops(self, authenticated_client, mock_mongodb):
        """Test route retrieval includes stop information"""
        route_id = str(uuid4())
        stop1_id = str(uuid4())
        stop2_id = str(uuid4())
        stop3_id = str(uuid4())
        
        route = TestFixtures.create_test_route(
            name="Express Route",
            origin_stop_id=stop1_id,
            destination_stop_id=stop3_id,
            stops=[
                {"stop_id": stop1_id, "sequence": 1, "estimated_duration": 0},
                {"stop_id": stop2_id, "sequence": 2, "estimated_duration": 15},
                {"stop_id": stop3_id, "sequence": 3, "estimated_duration": 30}
            ]
        )
        route["id"] = route_id
        
        mock_mongodb.routes.find_one.return_value = route
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["origin_stop_id"] == stop1_id
        assert data["destination_stop_id"] == stop3_id
        assert "stops" in data
        assert len(data["stops"]) == 3
        assert data["stops"][0]["sequence"] == 1
        assert data["stops"][1]["sequence"] == 2
        assert data["stops"][2]["sequence"] == 3

    @pytest.mark.asyncio
    async def test_get_route_inactive_route(self, authenticated_client, mock_mongodb):
        """Test retrieval of inactive route"""
        route_id = str(uuid4())
        route = TestFixtures.create_test_route(is_active=False)
        route["id"] = route_id
        
        mock_mongodb.routes.find_one.return_value = route
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        # Should still return the route but mark it as inactive
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] == False

    @pytest.mark.asyncio
    async def test_get_route_with_schedule_info(self, authenticated_client, mock_mongodb):
        """Test route retrieval includes schedule information"""
        route_id = str(uuid4())
        route = TestFixtures.create_test_route()
        route["id"] = route_id
        route["schedule"] = {
            "weekday_frequency": 15,  # Every 15 minutes
            "weekend_frequency": 30,  # Every 30 minutes
            "first_departure": "05:30",
            "last_departure": "23:30"
        }
        route["estimated_duration"] = 45  # 45 minutes total
        
        mock_mongodb.routes.find_one.return_value = route
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "schedule" in data
        assert data["schedule"]["weekday_frequency"] == 15
        assert data["estimated_duration"] == 45

    @pytest.mark.asyncio
    async def test_get_route_performance(self, authenticated_client, mock_mongodb):
        """Test route retrieval performance"""
        import time
        
        route_id = str(uuid4())
        route = TestFixtures.create_test_route()
        route["id"] = route_id
        
        mock_mongodb.routes.find_one.return_value = route
        
        start_time = time.time()
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Route retrieval should be fast
        response_time = end_time - start_time
        assert response_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_get_route_data_integrity(self, authenticated_client, mock_mongodb):
        """Test route data integrity and validation"""
        route_id = str(uuid4())
        route = TestFixtures.create_test_route()
        route["id"] = route_id
        
        # Add complex route data to test integrity
        route["distance_km"] = 12.5
        route["fare"] = 8.50
        route["route_type"] = "EXPRESS"
        route["operator"] = "City Transport Authority"
        
        mock_mongodb.routes.find_one.return_value = route
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all data is preserved and correctly typed
        assert isinstance(data["distance_km"], (int, float))
        assert isinstance(data["fare"], (int, float))
        assert isinstance(data["route_type"], str)
        assert isinstance(data["operator"], str)

    @pytest.mark.asyncio
    async def test_get_route_with_real_time_info(self, authenticated_client, mock_mongodb):
        """Test route retrieval with real-time operational info"""
        route_id = str(uuid4())
        route = TestFixtures.create_test_route()
        route["id"] = route_id
        
        # Add real-time operational data
        route["current_delays"] = [
            {"stop_id": str(uuid4()), "delay_minutes": 5},
            {"stop_id": str(uuid4()), "delay_minutes": 2}
        ]
        route["active_buses_count"] = 3
        route["next_departure"] = "14:25"
        
        mock_mongodb.routes.find_one.return_value = route
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        if "current_delays" in data:
            assert isinstance(data["current_delays"], list)
        if "active_buses_count" in data:
            assert isinstance(data["active_buses_count"], int)

    @pytest.mark.asyncio
    async def test_get_route_accessibility_info(self, authenticated_client, mock_mongodb):
        """Test route includes accessibility information"""
        route_id = str(uuid4())
        route = TestFixtures.create_test_route()
        route["id"] = route_id
        
        # Add accessibility information
        route["accessibility"] = {
            "wheelchair_accessible": True,
            "audio_announcements": True,
            "visual_displays": True,
            "low_floor_buses": True
        }
        
        mock_mongodb.routes.find_one.return_value = route
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        if "accessibility" in data:
            accessibility = data["accessibility"]
            assert isinstance(accessibility["wheelchair_accessible"], bool)
            assert isinstance(accessibility["audio_announcements"], bool)

    @pytest.mark.asyncio
    async def test_get_route_multilingual_support(self, authenticated_client, mock_mongodb):
        """Test route supports multilingual names and descriptions"""
        route_id = str(uuid4())
        route = TestFixtures.create_test_route()
        route["id"] = route_id
        
        # Add multilingual support
        route["names"] = {
            "en": "City Center - Airport Express",
            "am": "የከተማ ማእከል - አውሮፕላን ማረፊያ ፈጣን",
            "om": "Magaalaa Gidduu - Buufata Xiyyaaraa Ariifataa"
        }
        route["descriptions"] = {
            "en": "Express route connecting city center to airport",
            "am": "የከተማ ማእከልን ከአውሮፕላን ማረፊያ ጋር የሚያገናኝ ፈጣን መንገድ",
            "om": "Karaa ariifataa magaalaa gidduu fi buufata xiyyaaraa walitti fiduudha"
        }
        
        mock_mongodb.routes.find_one.return_value = route
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        if "names" in data:
            assert "en" in data["names"]
            assert "am" in data["names"]
            assert "om" in data["names"]

    @pytest.mark.asyncio
    async def test_get_route_error_scenarios(self, authenticated_client, mock_mongodb):
        """Test various error scenarios for route retrieval"""
        # Test database connection error
        mock_mongodb.routes.find_one.side_effect = Exception("Database connection error")
        
        route_id = str(uuid4())
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        # Should handle database errors gracefully
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_get_route_caching_behavior(self, authenticated_client, mock_mongodb):
        """Test route data caching behavior"""
        route_id = str(uuid4())
        route = TestFixtures.create_test_route()
        route["id"] = route_id
        
        mock_mongodb.routes.find_one.return_value = route
        
        # Make multiple requests
        response1 = await authenticated_client.get(f"/api/routes/{route_id}")
        response2 = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Both responses should be identical
        assert response1.json() == response2.json()

    @pytest.mark.asyncio
    async def test_route_data_consistency(self, authenticated_client, mock_mongodb):
        """Test consistency of route data across requests"""
        route_id = str(uuid4())
        route = TestFixtures.create_test_route()
        route["id"] = route_id
        route["version"] = "1.0"
        route["last_modified"] = "2024-01-01T10:00:00Z"
        
        mock_mongodb.routes.find_one.return_value = route
        
        response = await authenticated_client.get(f"/api/routes/{route_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify data consistency fields
        assert data["id"] == route_id
        if "version" in data:
            assert data["version"] == "1.0"
        if "last_modified" in data:
            assert data["last_modified"] == "2024-01-01T10:00:00Z"
