"""
Tests for Socket.IO messaging features between queue regulators/bus drivers <-> control staff/admin
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from core.realtime.chat import chat_service
from core.realtime.socketio_events import websocket_event_handlers
from tests.realtime.conftest import RealtimeTestFixtures


class TestSocketIOMessaging:
    """Test cases for Socket.IO messaging functionality"""
    
    @pytest.mark.asyncio
    async def test_direct_message_between_driver_and_control_staff(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test direct messaging between bus driver and control staff"""
        # Create test users
        driver_id = str(uuid4())
        control_staff_id = str(uuid4())
        
        driver = realtime_fixtures.create_mock_user(driver_id, "BUS_DRIVER", "John Driver")
        control_staff = realtime_fixtures.create_mock_user(control_staff_id, "CONTROL_STAFF", "Jane Controller")
        
        # Mock database responses
        mock_app_state.mongodb.users.find_one.side_effect = lambda query: {
            driver_id: driver,
            control_staff_id: control_staff
        }.get(query.get("id"))
        
        # Mock conversation creation
        conversation_id = str(uuid4())
        mock_app_state.mongodb.conversations.find_one.return_value = None  # No existing conversation
        mock_app_state.mongodb.conversations.insert_one.return_value = MagicMock(inserted_id=conversation_id)
        
        # Mock message creation
        message_id = str(uuid4())
        mock_app_state.mongodb.messages.insert_one.return_value = MagicMock(inserted_id=message_id)
        
        # Connect users to Socket.IO
        driver_session = socketio_manager_mock.sio.add_session(f"session_{driver_id}")
        control_session = socketio_manager_mock.sio.add_session(f"session_{control_staff_id}")
        
        await socketio_manager_mock.connect_user(f"session_{driver_id}", driver_id)
        await socketio_manager_mock.connect_user(f"session_{control_staff_id}", control_staff_id)
        
        # Driver sends message to control staff
        message_content = "Need assistance with route guidance"
        
        # Simulate the send_message event handler
        data = {
            'recipient_id': control_staff_id,
            'message': message_content,
            'message_type': 'TEXT'
        }
        
        # Test the messaging flow by directly calling the service
        # First, simulate conversation creation
        conversation_data = {
            "id": conversation_id,
            "type": "DIRECT",
            "participants": [driver_id, control_staff_id],
            "created_at": datetime.now(timezone.utc),
            "last_message_at": datetime.now(timezone.utc)
        }

        # Test the real-time message sending
        await chat_service.send_real_time_message(
            conversation_id=conversation_id,
            sender_id=driver_id,
            content=message_content,
            message_id=message_id,
            message_type="TEXT",
            app_state=mock_app_state
        )
        
        # Verify real-time message was sent
        server_events = socketio_manager_mock.sio.emitted_events
        assert len(server_events) > 0
        
        # Check for new_message event
        new_message_events = [e for e in server_events if e['event'] == 'new_message']
        assert len(new_message_events) > 0
        
        message_event = new_message_events[0]
        assert message_event['data']['message']['content'] == message_content
        assert message_event['data']['message']['sender_id'] == driver_id
    
    @pytest.mark.asyncio
    async def test_admin_broadcast_to_drivers(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test admin broadcasting messages to all drivers"""
        # Create test users
        admin_id = str(uuid4())
        driver1_id = str(uuid4())
        driver2_id = str(uuid4())
        regulator_id = str(uuid4())
        
        admin = realtime_fixtures.create_mock_user(admin_id, "ADMIN", "Admin User")
        driver1 = realtime_fixtures.create_mock_user(driver1_id, "BUS_DRIVER", "Driver 1")
        driver2 = realtime_fixtures.create_mock_user(driver2_id, "BUS_DRIVER", "Driver 2")
        regulator = realtime_fixtures.create_mock_user(regulator_id, "QUEUE_REGULATOR", "Regulator 1")
        
        # Mock database responses
        mock_app_state.mongodb.users.find_one.side_effect = lambda query: {
            admin_id: admin,
            driver1_id: driver1,
            driver2_id: driver2,
            regulator_id: regulator
        }.get(query.get("id"))
        
        # Mock finding users by role
        mock_app_state.mongodb.users.find.return_value.to_list.return_value = [driver1, driver2]
        
        # Mock notification insertion
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        # Connect users
        admin_session = socketio_manager_mock.sio.add_session(f"session_{admin_id}")
        driver1_session = socketio_manager_mock.sio.add_session(f"session_{driver1_id}")
        driver2_session = socketio_manager_mock.sio.add_session(f"session_{driver2_id}")
        
        await socketio_manager_mock.connect_user(f"session_{admin_id}", admin_id)
        await socketio_manager_mock.connect_user(f"session_{driver1_id}", driver1_id)
        await socketio_manager_mock.connect_user(f"session_{driver2_id}", driver2_id)
        
        # Admin broadcasts message
        broadcast_message = "All drivers report to dispatch immediately"
        
        result = await websocket_event_handlers.handle_admin_broadcast(
            admin_id,
            {
                "message": broadcast_message,
                "target_roles": ["BUS_DRIVER"],
                "priority": "HIGH"
            },
            mock_app_state
        )
        
        # Verify broadcast was successful
        assert result["success"] is True
        
        # Verify notifications were saved to database
        mock_app_state.mongodb.notifications.insert_many.assert_called_once()
        
        # Verify real-time notifications were sent
        server_events = socketio_manager_mock.sio.emitted_events
        notification_events = [e for e in server_events if e['event'] == 'notification']
        assert len(notification_events) >= 2  # Should send to both drivers
    
    @pytest.mark.asyncio
    async def test_emergency_alert_from_driver(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test emergency alert from driver to control center"""
        # Create test users
        driver_id = str(uuid4())
        control1_id = str(uuid4())
        control2_id = str(uuid4())
        
        driver = realtime_fixtures.create_mock_user(driver_id, "BUS_DRIVER", "Emergency Driver")
        control1 = realtime_fixtures.create_mock_user(control1_id, "CONTROL_STAFF", "Control 1")
        control2 = realtime_fixtures.create_mock_user(control2_id, "ADMIN", "Admin 1")
        
        # Mock database responses
        mock_app_state.mongodb.users.find_one.side_effect = lambda query: {
            driver_id: driver,
            control1_id: control1,
            control2_id: control2
        }.get(query.get("id"))
        
        # Mock finding control staff
        mock_app_state.mongodb.users.find.return_value.to_list.return_value = [control1, control2]
        
        # Mock notification insertion
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        # Connect users
        driver_session = socketio_manager_mock.sio.add_session(f"session_{driver_id}")
        control1_session = socketio_manager_mock.sio.add_session(f"session_{control1_id}")
        control2_session = socketio_manager_mock.sio.add_session(f"session_{control2_id}")
        
        await socketio_manager_mock.connect_user(f"session_{driver_id}", driver_id)
        await socketio_manager_mock.connect_user(f"session_{control1_id}", control1_id)
        await socketio_manager_mock.connect_user(f"session_{control2_id}", control2_id)
        
        # Subscribe control staff to emergency alerts
        await socketio_manager_mock.join_room_user(control1_id, "emergency_alerts")
        await socketio_manager_mock.join_room_user(control2_id, "emergency_alerts")
        
        # Driver sends emergency alert
        alert_data = {
            "alert_type": "VEHICLE_BREAKDOWN",
            "message": "Bus engine failure, need immediate assistance",
            "location": {"latitude": 9.0192, "longitude": 38.7525}
        }
        
        result = await websocket_event_handlers.handle_emergency_alert(
            driver_id,
            alert_data,
            mock_app_state
        )
        
        # Verify alert was successful
        assert result["success"] is True
        
        # Verify emergency notifications were saved
        mock_app_state.mongodb.notifications.insert_many.assert_called_once()
        
        # Verify real-time emergency alerts were sent
        server_events = socketio_manager_mock.sio.emitted_events
        emergency_events = [e for e in server_events if e['event'] == 'emergency_alert']
        assert len(emergency_events) > 0
        
        # Verify emergency alert content
        emergency_event = emergency_events[0]
        assert emergency_event['data']['alert_data']['alert_type'] == "VEHICLE_BREAKDOWN"
        assert emergency_event['data']['alert_data']['sender_id'] == driver_id
    
    @pytest.mark.asyncio
    async def test_conversation_room_management(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test joining and leaving conversation rooms"""
        # Create test users
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        conversation_id = str(uuid4())
        
        user1 = realtime_fixtures.create_mock_user(user1_id, "QUEUE_REGULATOR", "Regulator")
        user2 = realtime_fixtures.create_mock_user(user2_id, "CONTROL_STAFF", "Controller")
        
        # Mock conversation
        mock_conversation = {
            "id": conversation_id,
            "type": "DIRECT",
            "participants": [user1_id, user2_id]
        }
        
        mock_app_state.mongodb.conversations.find_one.return_value = mock_conversation
        
        # Connect users
        user1_session = socketio_manager_mock.sio.add_session(f"session_{user1_id}")
        user2_session = socketio_manager_mock.sio.add_session(f"session_{user2_id}")
        
        await socketio_manager_mock.connect_user(f"session_{user1_id}", user1_id)
        await socketio_manager_mock.connect_user(f"session_{user2_id}", user2_id)
        
        # Test joining conversation
        result1 = await websocket_event_handlers.handle_join_conversation_room(
            user1_id, conversation_id, mock_app_state
        )
        result2 = await websocket_event_handlers.handle_join_conversation_room(
            user2_id, conversation_id, mock_app_state
        )
        
        assert result1["success"] is True
        assert result2["success"] is True
        
        # Verify users are in conversation room
        room_id = f"conversation:{conversation_id}"
        assert user1_id in socketio_manager_mock.rooms.get(room_id, set())
        assert user2_id in socketio_manager_mock.rooms.get(room_id, set())
        
        # Test leaving conversation
        await chat_service.leave_conversation(user1_id, conversation_id)
        
        # Verify user left the room
        assert user1_id not in socketio_manager_mock.rooms.get(room_id, set())
        assert user2_id in socketio_manager_mock.rooms.get(room_id, set())  # Other user still in room
    
    @pytest.mark.asyncio
    async def test_typing_indicators(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test typing indicators in conversations"""
        # Create test users
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        conversation_id = str(uuid4())
        
        # Connect users and join conversation room
        user1_session = socketio_manager_mock.sio.add_session(f"session_{user1_id}")
        user2_session = socketio_manager_mock.sio.add_session(f"session_{user2_id}")
        
        await socketio_manager_mock.connect_user(f"session_{user1_id}", user1_id)
        await socketio_manager_mock.connect_user(f"session_{user2_id}", user2_id)
        
        room_id = f"conversation:{conversation_id}"
        await socketio_manager_mock.join_room_user(user1_id, room_id)
        await socketio_manager_mock.join_room_user(user2_id, room_id)
        
        # Test typing indicator
        result = await websocket_event_handlers.handle_typing_indicator(
            user1_id, conversation_id, True
        )
        
        assert result["success"] is True
        
        # Verify typing status was broadcast
        server_events = socketio_manager_mock.sio.emitted_events
        typing_events = [e for e in server_events if e['event'] == 'typing_status']
        assert len(typing_events) > 0
        
        typing_event = typing_events[0]
        assert typing_event['data']['user_id'] == user1_id
        assert typing_event['data']['is_typing'] is True
        assert typing_event['data']['conversation_id'] == conversation_id
