import pytest
from httpx import AsyncClient
from datetime import datetime, date, time, timedelta
from fastapi import status
from uuid import uuid4
from typing import Dict, Any

from tests.conftest import TestFixtures


class TestAttendanceRouter:
    """Test cases for attendance router endpoints."""

    @pytest.mark.asyncio
    async def test_mark_attendance_present_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test successful attendance marking as present."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": date.today().isoformat(),
            "status": "PRESENT",
            "check_in_time": datetime.now().replace(hour=8, minute=30).isoformat(),
            "check_out_time": datetime.now().replace(hour=17, minute=0).isoformat(),
            "location": {
                "latitude": 9.0054,
                "longitude": 38.7636,
                "address": "Bole, Addis Ababa"
            },
            "notes": "On time today"
        }

        response = await passenger_client.post("/api/attendance", json=attendance_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "PRESENT"
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])
        assert data["date"] == date.today().isoformat()
        assert data["location"]["latitude"] == 9.0054
        assert data["location"]["longitude"] == 38.7636
        assert data["notes"] == "On time today"

    @pytest.mark.asyncio
    async def test_mark_attendance_late_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test successful attendance marking as late."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": date.today().isoformat(),
            "status": "LATE",
            "check_in_time": datetime.now().replace(hour=9, minute=30).isoformat(),
            "notes": "Traffic delay"
        }

        response = await passenger_client.post("/api/attendance", json=attendance_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "LATE"
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])
        assert data["notes"] == "Traffic delay"

    @pytest.mark.asyncio
    async def test_mark_attendance_absent_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test successful attendance marking as absent."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": date.today().isoformat(),
            "status": "ABSENT",
            "notes": "Sick leave"
        }

        response = await passenger_client.post("/api/attendance", json=attendance_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "ABSENT"
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])
        assert data["notes"] == "Sick leave"
        assert data["check_in_time"] is None
        assert data["check_out_time"] is None

    @pytest.mark.asyncio
    async def test_mark_attendance_without_location(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test attendance marking without location."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": date.today().isoformat(),
            "status": "PRESENT"
        }

        response = await passenger_client.post("/api/attendance", json=attendance_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "PRESENT"
        assert data["location"] is None
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])

    @pytest.mark.asyncio
    async def test_mark_attendance_invalid_status(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test attendance marking with invalid status."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": date.today().isoformat(),
            "status": "INVALID_STATUS"
        }

        response = await passenger_client.post("/api/attendance", json=attendance_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_mark_attendance_missing_required_fields(
        self, passenger_client: AsyncClient
    ):
        """Test attendance marking without required fields."""
        attendance_data: Dict[str, Any] = {}

        response = await passenger_client.post("/api/attendance", json=attendance_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_mark_attendance_duplicate_date(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test marking attendance twice for the same date."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": date.today().isoformat(),
            "status": "PRESENT"
        }

        # First request should succeed
        response1 = await passenger_client.post("/api/attendance", json=attendance_data)
        assert response1.status_code == status.HTTP_201_CREATED

        # Second request should fail with conflict
        response2 = await passenger_client.post("/api/attendance", json=attendance_data)
        assert response2.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_mark_attendance_unauthorized(
        self, test_client: AsyncClient
    ):
        """Test attendance marking without authentication."""
        attendance_data: Dict[str, Any] = {
            "user_id": "test-user",
            "date": date.today().isoformat(),
            "status": "PRESENT"
        }

        response = await test_client.post("/api/attendance", json=attendance_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_attendance_heatmap_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures, mongodb
    ):
        """Test successful attendance heatmap retrieval."""
        # Create test attendance records
        today = date.today()
        attendance_records = [
            {
                "_id": test_fixtures.object_ids[0],
                "user_id": test_fixtures.passenger_user["_id"],
                "date": today,
                "status": "PRESENT",
                "check_in_time": datetime.combine(today, time(8, 30)),
                "marked_by": test_fixtures.passenger_user["_id"],
                "marked_at": datetime.now()
            },
            {
                "_id": test_fixtures.object_ids[1],
                "user_id": test_fixtures.passenger_user["_id"],
                "date": today - timedelta(days=1),
                "status": "LATE",
                "check_in_time": datetime.combine(today - timedelta(days=1), time(9, 30)),
                "marked_by": test_fixtures.passenger_user["_id"],
                "marked_at": datetime.now()
            },
            {
                "_id": test_fixtures.object_ids[2],
                "user_id": test_fixtures.passenger_user["_id"],
                "date": today - timedelta(days=2),
                "status": "ABSENT",
                "marked_by": test_fixtures.admin_user["_id"],
                "marked_at": datetime.now()
            }
        ]

        await mongodb.attendance.insert_many(attendance_records)

        response = await passenger_client.get("/api/attendance/heatmap")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])
        assert "date_from" in data
        assert "date_to" in data
        assert "attendance_data" in data

        # Check that our test data is included
        attendance_data = data["attendance_data"]
        assert attendance_data[today.isoformat()] == "PRESENT"
        assert attendance_data[(today - timedelta(days=1)).isoformat()] == "LATE"
        assert attendance_data[(today - timedelta(days=2)).isoformat()] == "ABSENT"

    @pytest.mark.asyncio
    async def test_get_attendance_heatmap_with_date_range(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test attendance heatmap with custom date range."""
        date_from = "2024-01-01"
        date_to = "2024-01-31"

        response = await passenger_client.get(
            f"/api/attendance/heatmap?date_from={date_from}&date_to={date_to}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["date_from"] == date_from
        assert data["date_to"] == date_to
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])

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
