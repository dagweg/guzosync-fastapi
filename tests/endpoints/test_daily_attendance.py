import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import date, datetime
from typing import Dict, Any

from tests.conftest import TestFixtures


class TestDailyAttendance:
    """Test cases for daily attendance endpoints"""

    @pytest.mark.asyncio
    async def test_mark_daily_attendance_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test successful daily attendance marking."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": date.today().isoformat(),
            "status": "PRESENT",
            "check_in_time": datetime.now().isoformat(),
            "location": {
                "latitude": 9.0054,
                "longitude": 38.7636
            },
            "notes": "On time arrival"
        }
        
        response = await passenger_client.post("/api/attendance/daily", json=attendance_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "PRESENT"
        assert data["user_id"] == str(test_fixtures.passenger_user["_id"])
        assert data["notes"] == "On time arrival"
        assert "marked_at" in data

    @pytest.mark.asyncio
    async def test_mark_daily_attendance_late_status(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test marking attendance with late status."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": "2024-01-15",
            "status": "LATE",
            "check_in_time": "2024-01-15T09:30:00",
            "notes": "Traffic delay"
        }
        
        response = await passenger_client.post("/api/attendance/daily", json=attendance_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "LATE"
        assert data["notes"] == "Traffic delay"

    @pytest.mark.asyncio
    async def test_mark_daily_attendance_absent_status(
        self, admin_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test marking attendance as absent (admin only)."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": "2024-01-16",
            "status": "ABSENT",
            "notes": "Sick leave"
        }
        
        response = await admin_client.post("/api/attendance/daily", json=attendance_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "ABSENT"
        assert data["notes"] == "Sick leave"

    @pytest.mark.asyncio
    async def test_mark_daily_attendance_duplicate_date(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test that duplicate attendance for same date is rejected."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": "2024-01-17",
            "status": "PRESENT"
        }
        
        # First request should succeed
        response1 = await passenger_client.post("/api/attendance/daily", json=attendance_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Second request should fail
        response2 = await passenger_client.post("/api/attendance/daily", json=attendance_data)
        assert response2.status_code == status.HTTP_409_CONFLICT
        assert "already marked" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_mark_attendance_for_other_user_forbidden(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test that regular users cannot mark attendance for others."""
        attendance_data: Dict[str, Any] = {
            "user_id": str(test_fixtures.driver_user["_id"]),  # Different user
            "date": date.today().isoformat(),
            "status": "PRESENT"
        }
        
        response = await passenger_client.post("/api/attendance/daily", json=attendance_data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "only mark your own attendance" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_daily_attendance_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test retrieving daily attendance records."""
        # First create some attendance records
        attendance_data = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": "2024-01-18",
            "status": "PRESENT"
        }
        await passenger_client.post("/api/attendance/daily", json=attendance_data)
        
        # Get attendance records
        response = await passenger_client.get("/api/attendance/daily")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["status"] == "PRESENT"

    @pytest.mark.asyncio
    async def test_get_daily_attendance_with_filters(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test retrieving daily attendance with date filters."""
        # Create attendance records for different dates
        dates = ["2024-01-19", "2024-01-20", "2024-01-21"]
        for i, test_date in enumerate(dates):
            attendance_data = {
                "user_id": str(test_fixtures.passenger_user["_id"]),
                "date": test_date,
                "status": "PRESENT" if i % 2 == 0 else "LATE"
            }
            await passenger_client.post("/api/attendance/daily", json=attendance_data)
        
        # Get attendance with date range filter
        response = await passenger_client.get(
            "/api/attendance/daily",
            params={"date_from": "2024-01-19", "date_to": "2024-01-20"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_update_daily_attendance_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test updating daily attendance status."""
        # First create an attendance record
        attendance_data = {
            "user_id": str(test_fixtures.passenger_user["_id"]),
            "date": "2024-01-22",
            "status": "PRESENT"
        }
        create_response = await passenger_client.post("/api/attendance/daily", json=attendance_data)
        attendance_id = create_response.json()["id"]
        
        # Update the attendance
        update_data = {
            "status": "LATE",
            "notes": "Updated to late due to verification"
        }
        response = await passenger_client.put(f"/api/attendance/daily/{attendance_id}", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "LATE"
        assert data["notes"] == "Updated to late due to verification"

    @pytest.mark.asyncio
    async def test_attendance_summary_success(
        self, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test getting attendance summary."""
        # Create some attendance records
        test_dates = ["2024-01-23", "2024-01-24", "2024-01-25"]
        statuses = ["PRESENT", "LATE", "ABSENT"]
        
        for test_date, status_val in zip(test_dates, statuses):
            attendance_data = {
                "user_id": str(test_fixtures.passenger_user["_id"]),
                "date": test_date,
                "status": status_val
            }
            await passenger_client.post("/api/attendance/daily", json=attendance_data)
        
        # Get summary
        response = await passenger_client.get(
            "/api/attendance/summary",
            params={"date_from": "2024-01-23", "date_to": "2024-01-25"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_days"] >= 3
        assert data["present_days"] >= 1
        assert data["late_days"] >= 1
        assert data["absent_days"] >= 1
        assert "attendance_percentage" in data
        assert isinstance(data["records"], list)

    @pytest.mark.asyncio
    async def test_bulk_attendance_admin_only(
        self, admin_client: AsyncClient, passenger_client: AsyncClient, test_fixtures: TestFixtures
    ):
        """Test bulk attendance marking (admin only)."""
        bulk_data = {
            "date": "2024-01-26",
            "attendance_records": [
                {
                    "user_id": str(test_fixtures.passenger_user["_id"]),
                    "date": "2024-01-26",
                    "status": "PRESENT"
                },
                {
                    "user_id": str(test_fixtures.driver_user["_id"]),
                    "date": "2024-01-26",
                    "status": "LATE"
                }
            ]
        }
        
        # Admin should succeed
        admin_response = await admin_client.post("/api/attendance/bulk", json=bulk_data)
        assert admin_response.status_code == status.HTTP_200_OK
        
        # Regular user should fail
        passenger_response = await passenger_client.post("/api/attendance/bulk", json=bulk_data)
        assert passenger_response.status_code == status.HTTP_403_FORBIDDEN
