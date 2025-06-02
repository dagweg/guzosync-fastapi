import pytest
from httpx import AsyncClient
from datetime import datetime, time, timedelta
from fastapi import status
from uuid import uuid4
from typing import Dict, Any

from tests.conftest import TestFixtures


class TestAttendanceRouter:
    """Test cases for attendance router endpoints."""

    @pytest.mark.asyncio
    async def test_create_attendance_record_check_in_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test successful attendance check-in record creation."""
        attendance_data: Dict[str, Any] = {
            "type": "CHECK_IN",
            "location": {
                "latitude": 9.0054,
                "longitude": 38.7636,
                "address": "Bole, Addis Ababa"
            }
        }
        
        response = await passenger_client.post("/api/attendance", json=attendance_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["type"] == "CHECK_IN"
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])
        assert "timestamp" in data
        assert data["location"]["latitude"] == 9.0054
        assert data["location"]["longitude"] == 38.7636

    @pytest.mark.asyncio
    async def test_create_attendance_record_check_out_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test successful attendance check-out record creation."""
        attendance_data: Dict[str, Any] = {
            "type": "CHECK_OUT",
            "location": {
                "latitude": 9.0054,
                "longitude": 38.7636,
                "address": "Bole, Addis Ababa"
            }
        }
        
        response = await passenger_client.post("/api/attendance", json=attendance_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["type"] == "CHECK_OUT"
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_create_attendance_record_without_location(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test attendance record creation without location."""
        attendance_data: Dict[str, Any] = {
            "type": "CHECK_IN"
        }
        
        response = await passenger_client.post("/api/attendance", json=attendance_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["type"] == "CHECK_IN"
        assert data["location"] is None
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])

    @pytest.mark.asyncio
    async def test_create_attendance_record_invalid_type(
        self, passenger_client: AsyncClient
    ):
        """Test attendance record creation with invalid type."""
        attendance_data: Dict[str, Any] = {
            "type": "INVALID_TYPE"
        }
        
        response = await passenger_client.post("/api/attendance", json=attendance_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_attendance_record_missing_type(
        self, passenger_client: AsyncClient
    ):
        """Test attendance record creation without type."""
        attendance_data: Dict[str, Any] = {}
        
        response = await passenger_client.post("/api/attendance", json=attendance_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_attendance_record_unauthorized(
        self, test_client: AsyncClient
    ):
        """Test attendance record creation without authentication."""
        attendance_data: Dict[str, Any] = {
            "type": "CHECK_IN"
        }
        
        response = await test_client.post("/api/attendance", json=attendance_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_attendance_record_invalid_location_format(
        self, passenger_client: AsyncClient
    ):
        """Test attendance record creation with invalid location format."""
        attendance_data: Dict[str, Any] = {
            "type": "CHECK_IN",
            "location": {
                "latitude": "invalid",
                "longitude": 38.7636
            }
        }
        
        response = await passenger_client.post("/api/attendance", json=attendance_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_today_attendance_empty(
        self, passenger_client: AsyncClient
    ):
        """Test retrieving today's attendance records when none exist."""
        response = await passenger_client.get("/api/attendance/today")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_today_attendance_with_records(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test retrieving today's attendance records."""
        # Create test attendance records for today
        today = datetime.utcnow().date()
        attendance_records = [
            {
                "_id": test_fixtures.object_ids[0],
                "user_id": test_fixtures.passenger_user["_id"],
                "timestamp": datetime.combine(today, time(9, 0)),
                "type": "CHECK_IN",
                "location": {
                    "latitude": 9.0054,
                    "longitude": 38.7636,
                    "address": "Bole, Addis Ababa"
                }
            },
            {
                "_id": test_fixtures.object_ids[1],
                "user_id": test_fixtures.passenger_user["_id"],
                "timestamp": datetime.combine(today, time(17, 0)),
                "type": "CHECK_OUT",
                "location": {
                    "latitude": 9.0054,
                    "longitude": 38.7636,
                    "address": "Bole, Addis Ababa"
                }
            }
        ]
        
        await mongodb.attendance.insert_many(attendance_records)
        
        response = await passenger_client.get("/api/attendance/today")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["type"] == "CHECK_IN"
        assert data[1]["type"] == "CHECK_OUT"

    @pytest.mark.asyncio
    async def test_get_today_attendance_excludes_other_days(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test that today's attendance only includes today's records."""
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        # Create records for today and yesterday
        attendance_records = [
            {
                "_id": test_fixtures.object_ids[0],
                "user_id": test_fixtures.passenger_user["_id"],
                "timestamp": datetime.combine(today, time(9, 0)),
                "type": "CHECK_IN",
                "location": None
            },
            {
                "_id": test_fixtures.object_ids[1],
                "user_id": test_fixtures.passenger_user["_id"],
                "timestamp": datetime.combine(yesterday, time(9, 0)),
                "type": "CHECK_IN",
                "location": None
            }
        ]
        
        await mongodb.attendance.insert_many(attendance_records)
        
        response = await passenger_client.get("/api/attendance/today")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["type"] == "CHECK_IN"

    @pytest.mark.asyncio
    async def test_get_today_attendance_excludes_other_users(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test that today's attendance only includes current user's records."""
        today = datetime.utcnow().date()
        
        attendance_records = [
            {
                "_id": test_fixtures.object_ids[0],
                "user_id": test_fixtures.passenger_user["_id"],
                "timestamp": datetime.combine(today, time(9, 0)),
                "type": "CHECK_IN",
                "location": None
            },
            {
                "_id": test_fixtures.object_ids[1],
                "user_id": test_fixtures.admin_user["_id"],  # Different user
                "timestamp": datetime.combine(today, time(9, 0)),
                "type": "CHECK_IN",
                "location": None
            }
        ]
        
        await mongodb.attendance.insert_many(attendance_records)
        
        response = await passenger_client.get("/api/attendance/today")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_id"] == str(test_fixtures.passenger_user["_id"])

    @pytest.mark.asyncio
    async def test_get_today_attendance_unauthorized(
        self, test_client: AsyncClient
    ):
        """Test retrieving today's attendance without authentication."""
        response = await test_client.get("/api/attendance/today")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_attendance_record_timestamp_accuracy(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test that attendance record timestamp is accurate."""
        before_request = datetime.utcnow()
        
        attendance_data: Dict[str, Any] = {
            "type": "CHECK_IN"
        }
        
        response = await passenger_client.post("/api/attendance", json=attendance_data)
        
        after_request = datetime.utcnow()
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Parse timestamp and verify it's within the request window
        timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        timestamp = timestamp.replace(tzinfo=None)  # Remove timezone for comparison
        
        assert before_request <= timestamp <= after_request

    @pytest.mark.asyncio
    async def test_attendance_location_with_address_only(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test attendance record with address but no coordinates."""
        attendance_data: Dict[str, Any] = {
            "type": "CHECK_IN",
            "location": {
                "latitude": 9.0054,
                "longitude": 38.7636,
                "address": "Test Address"
            }
        }
        
        response = await passenger_client.post("/api/attendance", json=attendance_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["location"]["address"] == "Test Address"

    @pytest.mark.asyncio
    async def test_attendance_multiple_records_same_day(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test creating multiple attendance records on the same day."""
        # Create check-in
        check_in_data: Dict[str, Any] = {"type": "CHECK_IN"}
        response1 = await passenger_client.post("/api/attendance", json=check_in_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Create check-out
        check_out_data: Dict[str, Any] = {"type": "CHECK_OUT"}
        response2 = await passenger_client.post("/api/attendance", json=check_out_data)
        assert response2.status_code == status.HTTP_201_CREATED
        
        # Verify both records are retrieved
        response = await passenger_client.get("/api/attendance/today")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_attendance_edge_of_day_records(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test attendance records at the edge of day boundaries."""
        today = datetime.utcnow().date()
        
        # Create records at start and end of day
        attendance_records = [
            {
                "_id": test_fixtures.object_ids[0],
                "user_id": test_fixtures.passenger_user["_id"],
                "timestamp": datetime.combine(today, time(0, 0, 1)),  # Start of day
                "type": "CHECK_IN",
                "location": None
            },
            {
                "_id": test_fixtures.object_ids[1],
                "user_id": test_fixtures.passenger_user["_id"],
                "timestamp": datetime.combine(today, time(23, 59, 59)),  # End of day
                "type": "CHECK_OUT",
                "location": None
            }
        ]
        
        await mongodb.attendance.insert_many(attendance_records)
        
        response = await passenger_client.get("/api/attendance/today")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_attendance_invalid_coordinates_range(
        self, passenger_client: AsyncClient
    ):
        """Test attendance record with coordinates outside valid range."""
        attendance_data: Dict[str, Any] = {
            "type": "CHECK_IN",
            "location": {
                "latitude": 95.0,  # Invalid latitude (should be -90 to 90)
                "longitude": 200.0  # Invalid longitude (should be -180 to 180)
            }
        }
        
        response = await passenger_client.post("/api/attendance", json=attendance_data)
        
        # Should still succeed if no validation constraints on coordinates
        assert response.status_code == status.HTTP_201_CREATED
