"""
Integration tests for real-time functionality end-to-end workflows
"""
import pytest
import json
import asyncio
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.realtime.chat import chat_service
from core.realtime.bus_tracking import bus_tracking_service
from core.realtime.notifications import notification_service
from core.websocket_manager import websocket_manager
from tests.realtime.conftest import MockWebSocket


class TestRealTimeIntegration:
    """Integration tests for complete real-time workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_bus_tracking_workflow(self, websocket_manager_mock, mock_app_state):
        """Test complete bus tracking workflow from subscription to updates"""
        # Setup test data
        user_id = str(uuid4())
        bus_id = str(uuid4())
        route_id = str(uuid4())
        
        # Mock database responses
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {
            "id": bus_id,
            "assigned_route_id": route_id,
            "current_location": {"latitude": 9.0317, "longitude": 38.7468}
        }
        
        # Setup WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Step 1: Subscribe to bus tracking
        await bus_tracking_service.subscribe_to_bus(user_id, bus_id)
        
        # Verify subscription confirmation
        messages = user_ws.get_sent_messages()
        assert len(messages) == 1
        assert messages[0]["type"] == "bus_tracking_subscribed"
        assert messages[0]["bus_id"] == bus_id
        
        user_ws.clear_messages()
        
        # Step 2: Simulate multiple location updates
        locations = [
            {"lat": 9.0320, "lng": 38.7470, "heading": 45.0, "speed": 25.0},
            {"lat": 9.0325, "lng": 38.7475, "heading": 50.0, "speed": 30.0},
            {"lat": 9.0330, "lng": 38.7480, "heading": 55.0, "speed": 35.0}
        ]
        
        for i, location in enumerate(locations):
            await bus_tracking_service.update_bus_location(
                bus_id=bus_id,
                latitude=location["lat"],
                longitude=location["lng"],
                heading=location["heading"],
                speed=location["speed"],
                app_state=mock_app_state
            )
            
            # Verify location update received
            messages = user_ws.get_sent_messages()
            assert len(messages) == i + 1
            
            latest_message = messages[-1]
            assert latest_message["type"] == "bus_location_update"
            assert latest_message["bus_id"] == bus_id
            assert latest_message["location"]["latitude"] == location["lat"]
            assert latest_message["location"]["longitude"] == location["lng"]
        
        # Step 3: Unsubscribe from bus tracking
        bus_tracking_service.unsubscribe_from_bus(user_id, bus_id)
        
        # Verify user is no longer in room
        room_users = websocket_manager_mock.get_room_users(f"bus_tracking:{bus_id}")
        assert user_id not in room_users
        
        # Step 4: Send another location update - user should not receive it
        user_ws.clear_messages()
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=9.0335,
            longitude=38.7485,
            app_state=mock_app_state
        )
        
        # User should not receive this update
        messages = user_ws.get_sent_messages()
        assert len(messages) == 0
    
    @pytest.mark.asyncio
    async def test_complete_chat_workflow(self, websocket_manager_mock, mock_app_state):
        """Test complete chat workflow from join to messaging to notifications"""
        # Setup test data
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        conversation_id = str(uuid4())
        
        # Mock conversation
        mock_conversation = {
            "id": conversation_id,
            "participants": [user1_id, user2_id]
        }
        mock_app_state.mongodb.conversations.find_one.return_value = mock_conversation
        
        # Setup WebSocket connections
        user1_ws = MockWebSocket()
        user2_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(user1_ws, user1_id)
        await websocket_manager_mock.connect(user2_ws, user2_id)
        
        # Step 1: Both users join conversation
        result1 = await chat_service.join_conversation(user1_id, conversation_id, mock_app_state)
        result2 = await chat_service.join_conversation(user2_id, conversation_id, mock_app_state)
        
        assert result1 is True
        assert result2 is True
        
        # Verify join confirmations
        user1_messages = user1_ws.get_sent_messages()
        user2_messages = user2_ws.get_sent_messages()
        
        assert len(user1_messages) == 1
        assert len(user2_messages) == 1
        assert user1_messages[0]["type"] == "conversation_joined"
        assert user2_messages[0]["type"] == "conversation_joined"
        
        # Clear messages
        user1_ws.clear_messages()
        user2_ws.clear_messages()
        
        # Step 2: User1 starts typing
        await chat_service.notify_typing(conversation_id, user1_id, True)
        
        # Only user2 should receive typing notification
        user1_messages = user1_ws.get_sent_messages()
        user2_messages = user2_ws.get_sent_messages()
        
        assert len(user1_messages) == 0  # Sender excluded
        assert len(user2_messages) == 1
        assert user2_messages[0]["type"] == "typing_status"
        assert user2_messages[0]["is_typing"] is True
        
        user2_ws.clear_messages()
        
        # Step 3: User1 stops typing and sends message
        await chat_service.notify_typing(conversation_id, user1_id, False)
        
        message_id = str(uuid4())
        message_content = "Hello, how are you?"
        
        await chat_service.send_real_time_message(
            conversation_id=conversation_id,
            sender_id=user1_id,
            content=message_content,
            message_id=message_id,
            app_state=mock_app_state
        )
        
        # Verify typing stop and message received by user2
        user2_messages = user2_ws.get_sent_messages()
        assert len(user2_messages) == 2
        
        # First message: typing stopped
        assert user2_messages[0]["type"] == "typing_status"
        assert user2_messages[0]["is_typing"] is False
        
        # Second message: new message
        assert user2_messages[1]["type"] == "new_message"
        assert user2_messages[1]["message"]["content"] == message_content
        assert user2_messages[1]["message"]["sender_id"] == user1_id
        
        user2_ws.clear_messages()
        
        # Step 4: User2 reads the message
        await chat_service.notify_message_read(conversation_id, user2_id, message_id)
        
        # Only user1 should receive read notification
        user1_messages = user1_ws.get_sent_messages()
        user2_messages = user2_ws.get_sent_messages()
        
        assert len(user1_messages) == 1
        assert len(user2_messages) == 0  # Reader excluded
        assert user1_messages[0]["type"] == "message_read"
        assert user1_messages[0]["message_id"] == message_id
        
        # Step 5: Both users leave conversation
        chat_service.leave_conversation(user1_id, conversation_id)
        chat_service.leave_conversation(user2_id, conversation_id)
        
        # Verify room is empty
        room_users = websocket_manager_mock.get_room_users(f"conversation:{conversation_id}")
        assert len(room_users) == 0
    
    @pytest.mark.asyncio
    async def test_notification_workflow_with_trip_updates(self, websocket_manager_mock, mock_app_state):
        """Test notification workflow including trip updates"""
        # Setup test data
        trip_id = str(uuid4())
        passenger1_id = str(uuid4())
        passenger2_id = str(uuid4())
        
        # Mock trip data
        mock_trip = {
            "id": trip_id,
            "participants": [passenger1_id, passenger2_id]
        }
        mock_app_state.mongodb.trips.find_one.return_value = mock_trip
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        mock_app_state.mongodb.notifications.insert_one.return_value = MagicMock(inserted_id="notif_id")
        
        # Setup WebSocket connections
        passenger1_ws = MockWebSocket()
        passenger2_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(passenger1_ws, passenger1_id)
        await websocket_manager_mock.connect(passenger2_ws, passenger2_id)
        
        # Step 1: Send individual notification to passenger1
        await notification_service.send_real_time_notification(
            user_id=passenger1_id,
            title="Personal Notification",
            message="Your booking is confirmed",
            notification_type="BOOKING_CONFIRMATION",
            app_state=mock_app_state
        )
        
        # Verify only passenger1 received it
        passenger1_messages = passenger1_ws.get_sent_messages()
        passenger2_messages = passenger2_ws.get_sent_messages()
        
        assert len(passenger1_messages) == 1
        assert len(passenger2_messages) == 0
        assert passenger1_messages[0]["notification"]["title"] == "Personal Notification"
        
        # Clear messages
        passenger1_ws.clear_messages()
        
        # Step 2: Send trip update notification
        await notification_service.send_trip_update_notification(
            trip_id=trip_id,
            message="Your trip has been delayed by 15 minutes due to traffic",
            delay_minutes=15,
            app_state=mock_app_state
        )
        
        # Both passengers should receive trip update
        passenger1_messages = passenger1_ws.get_sent_messages()
        passenger2_messages = passenger2_ws.get_sent_messages()
        
        assert len(passenger1_messages) == 1
        assert len(passenger2_messages) == 1
        
        for messages in [passenger1_messages, passenger2_messages]:
            notification = messages[0]["notification"]
            assert notification["title"] == "Trip Update"
            assert notification["notification_type"] == "TRIP_UPDATE"
            assert notification["related_entity"]["trip_id"] == trip_id
            assert notification["related_entity"]["delay_minutes"] == 15
        
        # Clear messages
        passenger1_ws.clear_messages()
        passenger2_ws.clear_messages()
        
        # Step 3: Broadcast system notification
        await notification_service.broadcast_notification(
            title="System Maintenance",
            message="The system will be under maintenance from 2 AM to 4 AM",
            notification_type="SYSTEM",
            app_state=mock_app_state
        )
        
        # Both passengers should receive broadcast
        passenger1_messages = passenger1_ws.get_sent_messages()
        passenger2_messages = passenger2_ws.get_sent_messages()
        
        assert len(passenger1_messages) == 1
        assert len(passenger2_messages) == 1
        
        for messages in [passenger1_messages, passenger2_messages]:
            notification = messages[0]["notification"]
            assert notification["title"] == "System Maintenance"
            assert notification["notification_type"] == "SYSTEM"
    
    @pytest.mark.asyncio
    async def test_multi_service_real_time_scenario(self, websocket_manager_mock, mock_app_state):
        """Test scenario involving multiple real-time services simultaneously"""
        # Setup test data
        user_id = str(uuid4())
        bus_id = str(uuid4())
        conversation_id = str(uuid4())
        trip_id = str(uuid4())
        
        # Mock database responses
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {"id": bus_id}
        mock_app_state.mongodb.conversations.find_one.return_value = {
            "id": conversation_id,
            "participants": [user_id]
        }
        mock_app_state.mongodb.trips.find_one.return_value = {
            "id": trip_id,
            "participants": [user_id]
        }
        mock_app_state.mongodb.notifications.insert_one.return_value = MagicMock(inserted_id="notif_id")
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        # Setup WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Step 1: Subscribe to bus tracking
        await bus_tracking_service.subscribe_to_bus(user_id, bus_id)
        
        # Step 2: Join conversation
        await chat_service.join_conversation(user_id, conversation_id, mock_app_state)
        
        # Step 3: Simulate concurrent real-time events
        tasks = [
            # Bus location update
            bus_tracking_service.update_bus_location(
                bus_id=bus_id,
                latitude=9.0317,
                longitude=38.7468,
                app_state=mock_app_state
            ),
            # Chat message
            chat_service.send_real_time_message(
                conversation_id=conversation_id,
                sender_id=str(uuid4()),  # Different sender
                content="Hello from another user!",
                message_id=str(uuid4()),
                app_state=mock_app_state
            ),
            # Personal notification
            notification_service.send_real_time_notification(
                user_id=user_id,
                title="Personal Alert",
                message="Your trip is starting soon",
                app_state=mock_app_state
            ),
            # Trip update notification
            notification_service.send_trip_update_notification(
                trip_id=trip_id,
                message="Bus is approaching your stop",
                app_state=mock_app_state
            )
        ]
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        
        # Verify user received all messages
        messages = user_ws.get_sent_messages()
        
        # Should have: bus subscription + conversation join + bus update + chat message + 2 notifications
        assert len(messages) >= 6
        
        # Verify message types
        message_types = [msg["type"] for msg in messages]
        assert "bus_tracking_subscribed" in message_types
        assert "conversation_joined" in message_types
        assert "bus_location_update" in message_types
        assert "new_message" in message_types
        assert message_types.count("notification") == 2  # Two notifications
        
        # Verify bus location update content
        bus_update_msgs = [msg for msg in messages if msg["type"] == "bus_location_update"]
        assert len(bus_update_msgs) == 1
        assert bus_update_msgs[0]["bus_id"] == bus_id
        
        # Verify chat message content
        chat_msgs = [msg for msg in messages if msg["type"] == "new_message"]
        assert len(chat_msgs) == 1
        assert chat_msgs[0]["message"]["content"] == "Hello from another user!"
        
        # Verify notification contents
        notification_msgs = [msg for msg in messages if msg["type"] == "notification"]
        assert len(notification_msgs) == 2
        
        titles = [msg["notification"]["title"] for msg in notification_msgs]
        assert "Personal Alert" in titles
        assert "Trip Update" in titles
    
    @pytest.mark.asyncio
    async def test_user_disconnect_cleanup(self, websocket_manager_mock, mock_app_state):
        """Test proper cleanup when user disconnects"""
        user_id = str(uuid4())
        bus_id = str(uuid4())
        conversation_id = str(uuid4())
        route_id = str(uuid4())
        
        # Mock database
        mock_app_state.mongodb.conversations.find_one.return_value = {
            "id": conversation_id,
            "participants": [user_id]
        }
        
        # Setup WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Subscribe to multiple services
        await bus_tracking_service.subscribe_to_bus(user_id, bus_id)
        await bus_tracking_service.subscribe_to_route(user_id, route_id)
        await chat_service.join_conversation(user_id, conversation_id, mock_app_state)
        
        # Verify user is in all rooms
        assert user_id in websocket_manager_mock.get_room_users(f"bus_tracking:{bus_id}")
        assert user_id in websocket_manager_mock.get_room_users(f"route_tracking:{route_id}")
        assert user_id in websocket_manager_mock.get_room_users(f"conversation:{conversation_id}")
        assert user_id in websocket_manager_mock.get_connected_users()
        
        # Simulate user disconnect
        websocket_manager_mock.disconnect(user_id)
        
        # Verify user is removed from all rooms and connections
        assert user_id not in websocket_manager_mock.get_room_users(f"bus_tracking:{bus_id}")
        assert user_id not in websocket_manager_mock.get_room_users(f"route_tracking:{route_id}")
        assert user_id not in websocket_manager_mock.get_room_users(f"conversation:{conversation_id}")
        assert user_id not in websocket_manager_mock.get_connected_users()
    
    @pytest.mark.asyncio
    async def test_scalability_with_multiple_users(self, websocket_manager_mock, mock_app_state):
        """Test system behavior with multiple concurrent users"""
        # Setup multiple users
        num_users = 10
        users = []
        websockets = []
        
        for i in range(num_users):
            user_id = str(uuid4())
            user_ws = MockWebSocket()
            users.append(user_id)
            websockets.append(user_ws)
            await websocket_manager_mock.connect(user_ws, user_id)
        
        # Mock database
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {"id": "shared_bus"}
        
        # All users subscribe to the same bus
        shared_bus_id = "shared_bus"
        for user_id in users:
            await bus_tracking_service.subscribe_to_bus(user_id, shared_bus_id)
        
        # Send one location update
        await bus_tracking_service.update_bus_location(
            bus_id=shared_bus_id,
            latitude=9.0317,
            longitude=38.7468,
            app_state=mock_app_state
        )
        
        # Verify all users received the update
        for i, user_ws in enumerate(websockets):
            messages = user_ws.get_sent_messages()
            # Should have subscription confirmation + location update
            assert len(messages) == 2
            assert messages[0]["type"] == "bus_tracking_subscribed"
            assert messages[1]["type"] == "bus_location_update"
            assert messages[1]["bus_id"] == shared_bus_id
        
        # Send broadcast notification to all users
        await notification_service.broadcast_notification(
            title="Mass Notification",
            message="Important announcement for all users",
            app_state=mock_app_state
        )
        
        # Verify all users received the broadcast
        for user_ws in websockets:
            # Get only the latest message (the broadcast)
            latest_messages = user_ws.get_sent_messages()[-1:]
            assert len(latest_messages) == 1
            assert latest_messages[0]["notification"]["title"] == "Mass Notification"


class TestRealTimeErrorHandling:
    """Test error handling across real-time services"""
    
    @pytest.mark.asyncio
    async def test_database_failure_resilience(self, websocket_manager_mock, mock_app_state):
        """Test system resilience when database operations fail"""
        user_id = str(uuid4())
        bus_id = str(uuid4())
        
        # Setup WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Mock database failures
        mock_app_state.mongodb.buses.update_one.side_effect = Exception("Database connection failed")
        mock_app_state.mongodb.buses.find_one.side_effect = Exception("Database read failed")
        
        # Subscribe to bus (should work despite database issues)
        await bus_tracking_service.subscribe_to_bus(user_id, bus_id)
        
        # Should still send subscription confirmation
        messages = user_ws.get_sent_messages()
        assert len(messages) == 1
        assert messages[0]["type"] == "bus_tracking_subscribed"
        
        user_ws.clear_messages()
        
        # Try to update bus location (should handle database error gracefully)
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=9.0317,
            longitude=38.7468,
            app_state=mock_app_state
        )
        
        # Should not crash, test completes successfully
        assert True
    
    @pytest.mark.asyncio
    async def test_websocket_failure_resilience(self, websocket_manager_mock, mock_app_state):
        """Test system resilience when WebSocket operations fail"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        conversation_id = str(uuid4())
        
        # Mock conversation
        mock_app_state.mongodb.conversations.find_one.return_value = {
            "id": conversation_id,
            "participants": [user1_id, user2_id]
        }
        
        # Setup connections - user2's WebSocket will fail
        user1_ws = MockWebSocket()
        await websocket_manager_mock.connect(user1_ws, user1_id)
        
        # Join conversation
        await chat_service.join_conversation(user1_id, conversation_id, mock_app_state)
        await chat_service.join_conversation(user2_id, conversation_id, mock_app_state)
        
        # Send message - should handle WebSocket failures gracefully
        await chat_service.send_real_time_message(
            conversation_id=conversation_id,
            sender_id=user1_id,
            content="Test message",
            message_id=str(uuid4()),
            app_state=mock_app_state
        )
        
        # Should not crash, test completes successfully
        assert True
