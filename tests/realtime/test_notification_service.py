"""
Tests for real-time notification service functionality
"""
import pytest
import json
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.realtime.notifications import notification_service, NotificationService
from core.websocket_manager import websocket_manager
from tests.realtime.conftest import MockWebSocket


class TestNotificationService:
    """Test cases for notification service functionality"""
    
    @pytest.mark.asyncio
    async def test_send_real_time_notification_success(self, websocket_manager_mock, mock_app_state):
        """Test sending a real-time notification successfully"""
        user_id = str(uuid4())
        title = "Test Notification"
        message = "This is a test notification"
        notification_type = "GENERAL"
        
        # Mock database insert
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "notification_id_123"
        mock_app_state.mongodb.notifications.insert_one.return_value = mock_insert_result
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Send notification
        await notification_service.send_real_time_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            app_state=mock_app_state
        )
        
        # Verify database insert was called
        mock_app_state.mongodb.notifications.insert_one.assert_called_once()
        insert_call = mock_app_state.mongodb.notifications.insert_one.call_args[0][0]
        assert insert_call["user_id"] == user_id
        assert insert_call["title"] == title
        assert insert_call["message"] == message
        assert insert_call["type"] == notification_type
        assert insert_call["is_read"] is False
        
        # Verify WebSocket message was sent
        messages = user_ws.get_sent_messages()
        assert len(messages) == 1
        
        ws_message = messages[0]
        assert ws_message["type"] == "notification"
        notification_data = ws_message["notification"]
        assert notification_data["id"] == "notification_id_123"
        assert notification_data["title"] == title
        assert notification_data["message"] == message
        assert notification_data["notification_type"] == notification_type
        assert notification_data["is_read"] is False
    
    @pytest.mark.asyncio
    async def test_send_notification_with_related_entity(self, websocket_manager_mock, mock_app_state):
        """Test sending notification with related entity data"""
        user_id = str(uuid4())
        title = "Trip Update"
        message = "Your trip has been delayed"
        related_entity = {
            "type": "trip",
            "id": "trip_123",
            "delay_minutes": 15
        }
        
        # Mock database
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "notification_id_456"
        mock_app_state.mongodb.notifications.insert_one.return_value = mock_insert_result
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Send notification with related entity
        await notification_service.send_real_time_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type="TRIP_UPDATE",
            related_entity=related_entity,
            app_state=mock_app_state
        )
        
        # Verify related entity was saved
        insert_call = mock_app_state.mongodb.notifications.insert_one.call_args[0][0]
        assert insert_call["related_entity"] == related_entity
        
        # Verify WebSocket message includes related entity
        messages = user_ws.get_sent_messages()
        ws_message = messages[0]
        assert ws_message["notification"]["related_entity"] == related_entity
    
    @pytest.mark.asyncio
    async def test_send_notification_to_offline_user(self, websocket_manager_mock, mock_app_state):
        """Test sending notification to user who is not connected"""
        user_id = str(uuid4())  # User not connected
        title = "Offline Notification"
        message = "This user is offline"
        
        # Mock database
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "notification_id_789"
        mock_app_state.mongodb.notifications.insert_one.return_value = mock_insert_result
        
        # Send notification to offline user
        await notification_service.send_real_time_notification(
            user_id=user_id,
            title=title,
            message=message,
            app_state=mock_app_state
        )
        
        # Verify database insert still happened
        mock_app_state.mongodb.notifications.insert_one.assert_called_once()
        
        # WebSocket manager should attempt to send but fail gracefully
        # (the mock WebSocket manager will handle this)
        assert True  # Test completes without error
    
    @pytest.mark.asyncio
    async def test_send_notification_without_database(self, websocket_manager_mock):
        """Test sending notification when database is not available"""
        user_id = str(uuid4())
        title = "No DB Notification"
        message = "Database not available"
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
          # Send notification without app_state (no database)
        await notification_service.send_real_time_notification(
            user_id=user_id,
            title=title,
            message=message,
            app_state=None
        )
        
        # Should still send WebSocket message
        messages = user_ws.get_sent_messages()
        assert len(messages) == 1
        
        ws_message = messages[0]
        assert ws_message["type"] == "notification"
        assert ws_message["notification"]["title"] == title
        assert ws_message["notification"]["message"] == message
        # Should not have database ID
        assert ws_message["notification"]["id"] is None
    
    @pytest.mark.asyncio
    async def test_broadcast_notification_to_all_users(self, websocket_manager_mock, mock_app_state):
        """Test broadcasting notification to all connected users"""
        title = "System Announcement"
        message = "System maintenance scheduled"
        notification_type = "SYSTEM"
        
        # Mock multiple users
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        user3_id = str(uuid4())
        
        user1_ws = MockWebSocket()
        user2_ws = MockWebSocket()
        user3_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(user1_ws, user1_id)
        await websocket_manager_mock.connect(user2_ws, user2_id)
        await websocket_manager_mock.connect(user3_ws, user3_id)
        
        # Mock database responses for finding all users
        mock_users = [
            {"id": user1_id, "email": "user1@test.com"},
            {"id": user2_id, "email": "user2@test.com"},
            {"id": user3_id, "email": "user3@test.com"}
        ]
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_users)
        mock_app_state.mongodb.users.find.return_value = mock_cursor
        
        # Mock database inserts
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "broadcast_notification_id"
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        # Broadcast notification
        await notification_service.broadcast_notification(
            title=title,
            message=message,
            notification_type=notification_type,
            app_state=mock_app_state
        )
        
        # Verify all users received the notification
        user1_messages = user1_ws.get_sent_messages()
        user2_messages = user2_ws.get_sent_messages()
        user3_messages = user3_ws.get_sent_messages()
        
        assert len(user1_messages) == 1
        assert len(user2_messages) == 1
        assert len(user3_messages) == 1
        
        # Verify message content
        for messages in [user1_messages, user2_messages, user3_messages]:
            ws_message = messages[0]
            assert ws_message["type"] == "notification"
            assert ws_message["notification"]["title"] == title
            assert ws_message["notification"]["message"] == message
            assert ws_message["notification"]["notification_type"] == notification_type
    
    @pytest.mark.asyncio
    async def test_broadcast_notification_to_specific_users(self, websocket_manager_mock, mock_app_state):
        """Test broadcasting notification to specific target users"""
        title = "Group Notification"
        message = "Message for specific users"
        
        # Mock users
        target_user1_id = str(uuid4())
        target_user2_id = str(uuid4())
        other_user_id = str(uuid4())  # Should not receive notification
        
        target_user_ids = [target_user1_id, target_user2_id]
        
        target1_ws = MockWebSocket()
        target2_ws = MockWebSocket()
        other_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(target1_ws, target_user1_id)
        await websocket_manager_mock.connect(target2_ws, target_user2_id)
        await websocket_manager_mock.connect(other_ws, other_user_id)
        
        # Mock database responses for specific users query
        mock_users = [
            {"id": target_user1_id, "email": "target1@test.com"},
            {"id": target_user2_id, "email": "target2@test.com"}
        ]
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_users)
        mock_app_state.mongodb.users.find.return_value = mock_cursor
        
        # Mock database
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        # Broadcast to specific users
        await notification_service.broadcast_notification(
            title=title,
            message=message,
            target_user_ids=target_user_ids,
            app_state=mock_app_state
        )
        
        # Verify only target users received notification
        target1_messages = target1_ws.get_sent_messages()
        target2_messages = target2_ws.get_sent_messages()
        other_messages = other_ws.get_sent_messages()
        
        assert len(target1_messages) == 1
        assert len(target2_messages) == 1
        assert len(other_messages) == 0  # Other user should not receive
        
        # Verify message content
        assert target1_messages[0]["notification"]["title"] == title
        assert target2_messages[0]["notification"]["title"] == title
    
    @pytest.mark.asyncio
    async def test_broadcast_notification_to_roles(self, websocket_manager_mock, mock_app_state):
        """Test broadcasting notification to users with specific roles"""
        title = "Admin Notification"
        message = "Message for administrators"
        target_roles = ["admin", "super_admin"]
        
        # Mock users with different roles
        admin_user_id = str(uuid4())
        regular_user_id = str(uuid4())
        
        admin_ws = MockWebSocket()
        regular_ws = MockWebSocket()
        await websocket_manager_mock.connect(admin_ws, admin_user_id)
        await websocket_manager_mock.connect(regular_ws, regular_user_id)
          # Mock database responses for role-based query - should only return admin users
        admin_users = [
            {"id": admin_user_id, "role": "admin"}
        ]
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=admin_users)
        mock_app_state.mongodb.users.find.return_value = mock_cursor
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        # Broadcast to specific roles
        await notification_service.broadcast_notification(
            title=title,
            message=message,
            target_roles=target_roles,
            app_state=mock_app_state
        )
        
        # Verify only admin user received notification
        admin_messages = admin_ws.get_sent_messages()
        regular_messages = regular_ws.get_sent_messages()
        
        assert len(admin_messages) == 1
        assert len(regular_messages) == 0  # Regular user should not receive
        
        assert admin_messages[0]["notification"]["title"] == title
    
    @pytest.mark.asyncio
    async def test_send_trip_update_notification(self, websocket_manager_mock, mock_app_state):
        """Test sending trip update notification"""
        trip_id = str(uuid4())
        message = "Your trip has been delayed by 10 minutes"
        delay_minutes = 10
        
        # Mock trip participants
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        
        mock_trip = {
            "id": trip_id,
            "participants": [user1_id, user2_id]
        }
        mock_app_state.mongodb.trips.find_one.return_value = mock_trip
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        # Mock WebSocket connections
        user1_ws = MockWebSocket()
        user2_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(user1_ws, user1_id)
        await websocket_manager_mock.connect(user2_ws, user2_id)
        
        # Send trip update notification
        await notification_service.send_trip_update_notification(
            trip_id=trip_id,
            message=message,
            delay_minutes=delay_minutes,
            app_state=mock_app_state
        )
        
        # Verify both participants received notification
        user1_messages = user1_ws.get_sent_messages()
        user2_messages = user2_ws.get_sent_messages()
        
        assert len(user1_messages) == 1
        assert len(user2_messages) == 1
        
        # Verify notification content
        for messages in [user1_messages, user2_messages]:
            ws_message = messages[0]
            assert ws_message["type"] == "notification"
            notification_data = ws_message["notification"]
            assert notification_data["title"] == "Trip Update"
            assert notification_data["message"] == message
            assert notification_data["notification_type"] == "TRIP_UPDATE"
            assert notification_data["related_entity"]["trip_id"] == trip_id
            assert notification_data["related_entity"]["delay_minutes"] == delay_minutes
    
    @pytest.mark.asyncio
    async def test_trip_update_notification_no_participants(self, websocket_manager_mock, mock_app_state):
        """Test trip update notification when trip has no participants"""
        trip_id = str(uuid4())
        message = "Trip update with no participants"
        
        # Mock trip with no participants
        mock_trip = {
            "id": trip_id,
            "participants": []
        }
        mock_app_state.mongodb.trips.find_one.return_value = mock_trip
        
        # Should not raise error
        await notification_service.send_trip_update_notification(
            trip_id=trip_id,
            message=message,
            app_state=mock_app_state
        )
        
        # Test completes without error
        assert True
    
    @pytest.mark.asyncio
    async def test_trip_update_notification_trip_not_found(self, websocket_manager_mock, mock_app_state):
        """Test trip update notification when trip is not found"""
        trip_id = str(uuid4())
        message = "Update for non-existent trip"
        
        # Mock trip not found
        mock_app_state.mongodb.trips.find_one.return_value = None
        
        # Should not raise error
        await notification_service.send_trip_update_notification(
            trip_id=trip_id,
            message=message,
            app_state=mock_app_state
        )
        
        # Test completes without error
        assert True
    
    @pytest.mark.asyncio
    async def test_notification_types(self, websocket_manager_mock, mock_app_state):
        """Test different notification types"""
        user_id = str(uuid4())
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Mock database
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "test_id"
        mock_app_state.mongodb.notifications.insert_one.return_value = mock_insert_result
        
        notification_types = [
            "GENERAL",
            "TRIP_UPDATE",
            "BUS_DELAY",
            "ROUTE_CHANGE",
            "SYSTEM",
            "EMERGENCY"
        ]
        
        for notification_type in notification_types:
            user_ws.clear_messages()
            
            await notification_service.send_real_time_notification(
                user_id=user_id,
                title=f"{notification_type} Notification",
                message=f"This is a {notification_type.lower()} notification",
                notification_type=notification_type,
                app_state=mock_app_state
            )
            
            messages = user_ws.get_sent_messages()
            assert len(messages) == 1
            assert messages[0]["notification"]["notification_type"] == notification_type
    
    @pytest.mark.asyncio
    async def test_error_handling_in_send_notification(self, websocket_manager_mock, mock_app_state):
        """Test error handling when sending notification fails"""
        user_id = str(uuid4())
        
        # Mock database error
        mock_app_state.mongodb.notifications.insert_one.side_effect = Exception("Database error")
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Should not raise exception, should handle error gracefully
        await notification_service.send_real_time_notification(
            user_id=user_id,
            title="Error Test",
            message="This should handle errors gracefully",
            app_state=mock_app_state
        )
        
        # Test should complete without raising exception
        assert True
    
    @pytest.mark.asyncio
    async def test_error_handling_in_broadcast_notification(self, websocket_manager_mock, mock_app_state):
        """Test error handling when broadcasting notification fails"""
        # Mock database error
        mock_app_state.mongodb.users.find.side_effect = Exception("Database error")
        
        # Should not raise exception, should handle error gracefully
        await notification_service.broadcast_notification(
            title="Broadcast Error Test",
            message="This should handle errors gracefully",
            app_state=mock_app_state
        )
        
        # Test should complete without raising exception
        assert True
    
    @pytest.mark.asyncio
    async def test_concurrent_notifications(self, websocket_manager_mock, mock_app_state):
        """Test sending multiple notifications concurrently"""
        import asyncio
        
        user_id = str(uuid4())
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Mock database
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "concurrent_id"
        mock_app_state.mongodb.notifications.insert_one.return_value = mock_insert_result
        
        # Send multiple notifications concurrently
        tasks = []
        for i in range(5):
            task = notification_service.send_real_time_notification(
                user_id=user_id,
                title=f"Concurrent Notification {i}",
                message=f"This is concurrent notification {i}",
                app_state=mock_app_state
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all notifications were sent
        messages = user_ws.get_sent_messages()
        assert len(messages) == 5
        
        # Verify unique titles
        titles = [msg["notification"]["title"] for msg in messages]
        assert len(set(titles)) == 5  # All titles should be unique


class TestNotificationServiceIntegration:
    """Integration tests for notification service with WebSocket manager"""
    
    @pytest.mark.asyncio
    async def test_full_notification_workflow(self, mock_app_state):
        """Test complete notification workflow"""
        user_id = str(uuid4())
        title = "Integration Test"
        message = "Full workflow test"
        
        # Mock database
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "integration_id"
        mock_app_state.mongodb.notifications.insert_one.return_value = mock_insert_result
          # Use real WebSocket manager for integration test
        with patch('core.realtime.notifications.websocket_manager') as mock_manager:
            mock_manager.send_personal_message = AsyncMock()
            mock_manager.get_connected_users.return_value = [user_id]
            
            # Mock database responses for broadcast notification
            mock_users = [{"id": user_id, "email": "test@test.com"}]
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=mock_users)
            mock_app_state.mongodb.users.find.return_value = mock_cursor
            mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
            
            # Send individual notification
            await notification_service.send_real_time_notification(
                user_id=user_id,
                title=title,
                message=message,
                app_state=mock_app_state
            )
            
            assert mock_manager.send_personal_message.called
            
            # Send broadcast notification
            await notification_service.broadcast_notification(
                title="Broadcast Test",
                message="Broadcast message",
                app_state=mock_app_state
            )
            
            # Should be called multiple times (once for individual, once for broadcast)
            assert mock_manager.send_personal_message.call_count >= 2
