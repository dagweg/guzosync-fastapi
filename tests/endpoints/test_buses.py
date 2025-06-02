import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime
from uuid import uuid4

from tests.conftest import TestFixtures


class TestBusesRouter:
    """Test cases for buses router endpoints"""

    @pytest.mark.asyncio
    async def test_get_bus_stops_success(self, authenticated_client, mock_mongodb):
        """Test successful retrieval of bus stops"""
        # Mock bus stops
        bus_stops = [
            TestFixtures.create_test_bus_stop(name="Central Station"),
            TestFixtures.create_test_bus_stop(name="Airport Terminal"),
            TestFixtures.create_test_bus_stop(name="University Campus")
        ]
        
        # Mock async iterator
        mock_cursor = AsyncMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = bus_stops
        mock_mongodb.bus_stops.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/buses/stops")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["name"] == "Central Station"
        assert data[1]["name"] == "Airport Terminal"

    @pytest.mark.asyncio
    async def test_get_bus_stops_with_search(self, authenticated_client, mock_mongodb):
        """Test bus stops retrieval with search parameter"""
        # Mock filtered bus stops
        filtered_stops = [
            TestFixtures.create_test_bus_stop(name="Central Station")
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = filtered_stops
        mock_mongodb.bus_stops.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/buses/stops?search=Central")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "Central" in data[0]["name"]

    @pytest.mark.asyncio
    async def test_get_bus_stops_pagination(self, authenticated_client, mock_mongodb):
        """Test bus stops pagination"""
        bus_stops = [TestFixtures.create_test_bus_stop() for _ in range(5)]
        
        mock_cursor = AsyncMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = bus_stops[:2]  # Return first 2
        mock_mongodb.bus_stops.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/buses/stops?pn=1&ps=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Verify pagination was applied
        mock_cursor.skip.assert_called_with(0)  # (page-1) * page_size
        mock_cursor.limit.assert_called_with(2)

    @pytest.mark.asyncio
    async def test_get_bus_stops_unauthenticated(self, test_client):
        """Test bus stops retrieval without authentication"""
        response = await test_client.get("/api/buses/stops")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_bus_stop_by_id_success(self, authenticated_client, mock_mongodb):
        """Test successful retrieval of specific bus stop"""
        bus_stop_id = str(uuid4())
        bus_stop = TestFixtures.create_test_bus_stop(name="Test Stop")
        bus_stop["id"] = bus_stop_id
        
        mock_mongodb.bus_stops.find_one.return_value = bus_stop
        
        response = await authenticated_client.get(f"/api/buses/stops/{bus_stop_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bus_stop_id
        assert data["name"] == "Test Stop"

    @pytest.mark.asyncio
    async def test_get_bus_stop_by_id_not_found(self, authenticated_client, mock_mongodb):
        """Test retrieval of non-existent bus stop"""
        bus_stop_id = str(uuid4())
        mock_mongodb.bus_stops.find_one.return_value = None
        
        response = await authenticated_client.get(f"/api/buses/stops/{bus_stop_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_bus_stop_invalid_id(self, authenticated_client):
        """Test retrieval with invalid bus stop ID"""
        invalid_id = "invalid-uuid"
        
        response = await authenticated_client.get(f"/api/buses/stops/{invalid_id}")
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_incoming_buses_success(self, authenticated_client, mock_mongodb):
        """Test successful retrieval of incoming buses at bus stop"""
        bus_stop_id = str(uuid4())
        
        # Mock bus stop exists
        bus_stop = TestFixtures.create_test_bus_stop()
        bus_stop["id"] = bus_stop_id
        mock_mongodb.bus_stops.find_one.return_value = bus_stop
        
        # Mock incoming trips/buses
        incoming_trips = [
            {
                "_id": "ObjectId1",
                "id": str(uuid4()),
                "bus_id": str(uuid4()),
                "route_id": str(uuid4()),
                "estimated_arrival": datetime.utcnow(),
                "current_stop_index": 2,
                "status": "IN_TRANSIT"
            },
            {
                "_id": "ObjectId2",
                "id": str(uuid4()),
                "bus_id": str(uuid4()),
                "route_id": str(uuid4()),
                "estimated_arrival": datetime.utcnow(),
                "current_stop_index": 1,
                "status": "IN_TRANSIT"
            }
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.to_list.return_value = incoming_trips
        mock_mongodb.trips.find.return_value = mock_cursor
        
        response = await authenticated_client.get(f"/api/buses/stops/{bus_stop_id}/incoming-buses")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_incoming_buses_bus_stop_not_found(self, authenticated_client, mock_mongodb):
        """Test incoming buses for non-existent bus stop"""
        bus_stop_id = str(uuid4())
        mock_mongodb.bus_stops.find_one.return_value = None
        
        response = await authenticated_client.get(f"/api/buses/stops/{bus_stop_id}/incoming-buses")
        
        assert response.status_code == 404
        assert "bus stop not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_incoming_buses_no_incoming(self, authenticated_client, mock_mongodb):
        """Test incoming buses when none are incoming"""
        bus_stop_id = str(uuid4())
        
        # Mock bus stop exists
        bus_stop = TestFixtures.create_test_bus_stop()
        bus_stop["id"] = bus_stop_id
        mock_mongodb.bus_stops.find_one.return_value = bus_stop
        
        # Mock no incoming trips
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.to_list.return_value = []
        mock_mongodb.trips.find.return_value = mock_cursor
        
        response = await authenticated_client.get(f"/api/buses/stops/{bus_stop_id}/incoming-buses")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_bus_by_id_success(self, authenticated_client, mock_mongodb):
        """Test successful retrieval of specific bus"""
        bus_id = str(uuid4())
        bus = TestFixtures.create_test_bus(license_plate="AAA-123")
        bus["id"] = bus_id
        
        mock_mongodb.buses.find_one.return_value = bus
        
        response = await authenticated_client.get(f"/api/buses/{bus_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bus_id
        assert data["license_plate"] == "AAA-123"

    @pytest.mark.asyncio
    async def test_get_bus_by_id_not_found(self, authenticated_client, mock_mongodb):
        """Test retrieval of non-existent bus"""
        bus_id = str(uuid4())
        mock_mongodb.buses.find_one.return_value = None
        
        response = await authenticated_client.get(f"/api/buses/{bus_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_bus_invalid_id(self, authenticated_client):
        """Test retrieval with invalid bus ID"""
        invalid_id = "invalid-uuid"
        
        response = await authenticated_client.get(f"/api/buses/{invalid_id}")
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_request_bus_reallocation_success(self, authenticated_client, mock_mongodb):
        """Test successful bus reallocation request"""
        # Mock successful reallocation request creation
        mock_mongodb.reallocation_requests.insert_one.return_value = AsyncMock(inserted_id="ObjectId")
        
        response = await authenticated_client.post("/api/buses/reallocate")
        
        assert response.status_code == 201
        data = response.json()
        assert "reallocation request submitted" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_request_bus_reallocation_unauthenticated(self, test_client):
        """Test bus reallocation request without authentication"""
        response = await test_client.post("/api/buses/reallocate")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_reallocation_requests_success(self, admin_client, mock_mongodb):
        """Test retrieval of reallocation requests by admin"""
        reallocation_requests = [
            {
                "_id": "ObjectId1",
                "id": str(uuid4()),
                "requested_by_user_id": str(uuid4()),
                "reason": "Route change needed",
                "status": "PENDING",
                "created_at": datetime.utcnow()
            },
            {
                "_id": "ObjectId2", 
                "id": str(uuid4()),
                "requested_by_user_id": str(uuid4()),
                "reason": "Emergency reroute",
                "status": "APPROVED",
                "created_at": datetime.utcnow()
            }
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.to_list.return_value = reallocation_requests
        mock_mongodb.reallocation_requests.find.return_value = mock_cursor
        
        response = await admin_client.get("/api/buses/reallocation/requests")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_reallocation_requests_unauthorized(self, authenticated_client):
        """Test reallocation requests retrieval by non-admin"""
        response = await authenticated_client.get("/api/buses/reallocation/requests")
        
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_bus_stops_filtering(self, authenticated_client, mock_mongodb):
        """Test bus stops filtering functionality"""
        # Test different filter scenarios
        filter_scenarios = [
            {"filter_by": "active", "expected_filter": {"is_active": True}},
            {"filter_by": "inactive", "expected_filter": {"is_active": False}},
            {"filter_by": "region", "expected_filter": {"region": "Addis Ababa"}},
        ]
        
        for scenario in filter_scenarios:
            mock_cursor = AsyncMock()
            mock_cursor.skip.return_value = mock_cursor
            mock_cursor.limit.return_value = mock_cursor
            mock_cursor.to_list.return_value = []
            mock_mongodb.bus_stops.find.return_value = mock_cursor
            
            response = await authenticated_client.get(
                f"/api/buses/stops?filter_by={scenario['filter_by']}"
            )
            
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_bus_stops_edge_cases(self, authenticated_client, mock_mongodb):
        """Test edge cases for bus stops endpoints"""
        # Test with maximum pagination limit
        mock_cursor = AsyncMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = []
        mock_mongodb.bus_stops.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/buses/stops?ps=100")
        assert response.status_code == 200
        
        # Test with invalid pagination parameters
        response = await authenticated_client.get("/api/buses/stops?ps=0")
        assert response.status_code == 422
        
        response = await authenticated_client.get("/api/buses/stops?pn=0")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_buses_real_time_data(self, authenticated_client, mock_mongodb):
        """Test real-time data accuracy for buses"""
        bus_stop_id = str(uuid4())
        
        # Mock bus stop
        bus_stop = TestFixtures.create_test_bus_stop()
        bus_stop["id"] = bus_stop_id
        mock_mongodb.bus_stops.find_one.return_value = bus_stop
        
        # Mock real-time trip data with precise timing
        current_time = datetime.utcnow()
        incoming_trips = [
            {
                "_id": "ObjectId1",
                "id": str(uuid4()),
                "bus_id": str(uuid4()),
                "estimated_arrival": current_time,
                "status": "IN_TRANSIT",
                "last_updated": current_time
            }
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.to_list.return_value = incoming_trips
        mock_mongodb.trips.find.return_value = mock_cursor
        
        response = await authenticated_client.get(f"/api/buses/stops/{bus_stop_id}/incoming-buses")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # Verify real-time data is recent
        assert "estimated_arrival" in data[0]
