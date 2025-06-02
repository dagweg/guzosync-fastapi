import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime
from uuid import uuid4

from tests.conftest import TestFixtures
from models.notifications import NotificationType
from models.user import UserRole


class TestNotificationsRouter:
    """Test cases for notifications router endpoints"""

    @pytest.mark.asyncio
    async def test_get_notifications_success(self, authenticated_client, mock_mongodb):
        """Test successful retrieval of notifications"""
        # Mock notifications for the user
        notifications = [
            TestFixtures.create_test_notification(
                user_id=authenticated_client.test_user.id,
                title="Test Notification 1",
                message="Test message 1"
            ),
            TestFixtures.create_test_notification(
                user_id=authenticated_client.test_user.id,
                title="Test Notification 2",
                message="Test message 2",
                is_read=True
            )
        ]
        
        # Mock async iterator for MongoDB cursor
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = notifications
        mock_mongodb.notifications.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/notifications")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["title"] == "Test Notification 1"
        assert data[1]["title"] == "Test Notification 2"
        assert data[1]["is_read"] == True

    @pytest.mark.asyncio
    async def test_get_notifications_pagination(self, authenticated_client, mock_mongodb):
        """Test notifications pagination"""
        # Create multiple notifications
        notifications = [TestFixtures.create_test_notification(
            user_id=authenticated_client.test_user.id,
            title=f"Notification {i}"
        ) for i in range(5)]
        
        # Mock async iterator
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = notifications[:2]  # Return first 2
        mock_mongodb.notifications.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/notifications?skip=0&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Verify pagination parameters were used
        mock_cursor.skip.assert_called_with(0)
        mock_cursor.limit.assert_called_with(2)

    @pytest.mark.asyncio
    async def test_get_notifications_empty(self, authenticated_client, mock_mongodb):
        """Test getting notifications when none exist"""
        # Mock empty result
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = []
        mock_mongodb.notifications.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/notifications")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_notifications_unauthenticated(self, test_client):
        """Test getting notifications without authentication"""
        response = await test_client.get("/api/notifications")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_mark_notification_read_success(self, authenticated_client, mock_mongodb):
        """Test successfully marking notification as read"""
        notification_id = str(uuid4())
        
        # Mock successful update
        mock_mongodb.notifications.update_one.return_value = AsyncMock(modified_count=1)
        
        response = await authenticated_client.post(f"/api/notifications/mark-read/{notification_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "marked as read" in data["message"].lower()
        
        # Verify correct update query
        mock_mongodb.notifications.update_one.assert_called_once()
        call_args = mock_mongodb.notifications.update_one.call_args
        assert call_args[0][0]["id"] == notification_id
        assert call_args[0][0]["user_id"] == authenticated_client.test_user.id
        assert call_args[0][1]["$set"]["is_read"] == True

    @pytest.mark.asyncio
    async def test_mark_notification_read_not_found(self, authenticated_client, mock_mongodb):
        """Test marking non-existent notification as read"""
        notification_id = str(uuid4())
        
        # Mock no documents modified (notification not found)
        mock_mongodb.notifications.update_one.return_value = AsyncMock(modified_count=0)
        
        response = await authenticated_client.post(f"/api/notifications/mark-read/{notification_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_mark_notification_read_unauthorized(self, authenticated_client, mock_mongodb):
        """Test marking another user's notification as read"""
        notification_id = str(uuid4())
        
        # Mock no documents modified (notification belongs to different user)
        mock_mongodb.notifications.update_one.return_value = AsyncMock(modified_count=0)
        
        response = await authenticated_client.post(f"/api/notifications/mark-read/{notification_id}")
        
        assert response.status_code == 404
        # Should return 404 instead of 403 to not leak information about notification existence

    @pytest.mark.asyncio
    async def test_mark_notification_read_invalid_id(self, authenticated_client):
        """Test marking notification with invalid ID format"""
        invalid_id = "invalid-uuid"
        
        response = await authenticated_client.post(f"/api/notifications/mark-read/{invalid_id}")
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_mark_notification_read_unauthenticated(self, test_client):
        """Test marking notification as read without authentication"""
        notification_id = str(uuid4())
        
        response = await test_client.post(f"/api/notifications/mark-read/{notification_id}")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_broadcast_notification_success(self, admin_client, mock_mongodb):
        """Test successful notification broadcast by admin"""
        # Mock user list for broadcasting
        users = [
            TestFixtures.create_test_user(),
            TestFixtures.create_test_user(),
            TestFixtures.create_test_user()
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = users
        mock_mongodb.users.find.return_value = mock_cursor
        
        # Mock successful notification insertion
        mock_mongodb.notifications.insert_many.return_value = AsyncMock(
            inserted_ids=["id1", "id2", "id3"]
        )
        
        broadcast_data = {
            "title": "System Maintenance",
            "message": "The system will be under maintenance from 2-4 AM",
            "type": "SYSTEM_ALERT",
            "target_roles": ["PASSENGER", "BUS_DRIVER"]
        }
        
        response = await admin_client.post("/api/notifications/broadcast", json=broadcast_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "broadcast successful" in data["message"].lower()
        assert data["recipients_count"] == 3

    @pytest.mark.asyncio
    async def test_broadcast_notification_unauthorized(self, authenticated_client):
        """Test broadcast notification by non-admin user"""
        broadcast_data = {
            "title": "Test Broadcast",
            "message": "Test message",
            "type": "GENERAL"
        }
        
        response = await authenticated_client.post("/api/notifications/broadcast", json=broadcast_data)
        
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_broadcast_notification_invalid_data(self, admin_client):
        """Test broadcast with invalid data"""
        invalid_data = {
            "title": "",  # Empty title
            "message": "",  # Empty message
            "type": "INVALID_TYPE"  # Invalid notification type
        }
        
        response = await admin_client.post("/api/notifications/broadcast", json=invalid_data)
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_broadcast_notification_specific_roles(self, admin_client, mock_mongodb):
        """Test broadcasting to specific roles only"""
        # Mock drivers only
        drivers = [
            TestFixtures.create_test_user(role=UserRole.BUS_DRIVER),
            TestFixtures.create_test_user(role=UserRole.BUS_DRIVER)
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = drivers
        mock_mongodb.users.find.return_value = mock_cursor
        
        mock_mongodb.notifications.insert_many.return_value = AsyncMock(
            inserted_ids=["id1", "id2"]
        )
        
        broadcast_data = {
            "title": "Driver Alert",
            "message": "Important message for drivers",
            "type": "ROLE_SPECIFIC",
            "target_roles": ["BUS_DRIVER"]
        }
        
        response = await admin_client.post("/api/notifications/broadcast", json=broadcast_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["recipients_count"] == 2
        
        # Verify query filtered by role
        mock_mongodb.users.find.assert_called_once()
        call_args = mock_mongodb.users.find.call_args[0][0]
        assert "role" in call_args
        assert call_args["role"]["$in"] == ["BUS_DRIVER"]

    @pytest.mark.asyncio
    async def test_notifications_filtering_by_type(self, authenticated_client, mock_mongodb):
        """Test filtering notifications by type"""
        notifications = [
            TestFixtures.create_test_notification(
                user_id=authenticated_client.test_user.id,
                type=NotificationType.TRIP_UPDATE.value
            ),
            TestFixtures.create_test_notification(
                user_id=authenticated_client.test_user.id,
                type=NotificationType.SERVICE_ALERT.value
            )
        ]
        
        mock_cursor = AsyncMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.to_list.return_value = [notifications[0]]  # Only trip updates
        mock_mongodb.notifications.find.return_value = mock_cursor
        
        response = await authenticated_client.get("/api/notifications?type=TRIP_UPDATE")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["type"] == NotificationType.TRIP_UPDATE.value

    @pytest.mark.asyncio
    async def test_notification_system_load(self, authenticated_client, mock_mongodb):
        """Test system behavior with large number of notifications"""
        # Test with maximum pagination limit
        response = await authenticated_client.get("/api/notifications?limit=100")
        
        # Should not exceed maximum limit
        assert response.status_code == 200
        
        # Test with invalid pagination parameters
        response = await authenticated_client.get("/api/notifications?limit=0")
        assert response.status_code == 422
        
        response = await authenticated_client.get("/api/notifications?skip=-1")
        assert response.status_code == 422
