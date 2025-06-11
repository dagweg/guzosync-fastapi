"""
Basic Socket.IO functionality tests
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from core.socketio_manager import SocketIOManager
from tests.realtime.conftest import RealtimeTestFixtures


class TestSocketIOBasic:
    """Basic Socket.IO functionality tests"""
    
    @pytest.mark.asyncio
    async def test_socketio_manager_initialization(self):
        """Test Socket.IO manager initializes correctly"""
        manager = SocketIOManager()
        
        assert manager.sio is not None
        assert isinstance(manager.user_sessions, dict)
        assert isinstance(manager.user_connections, dict)
        assert isinstance(manager.rooms, dict)
        assert isinstance(manager.proximity_preferences, dict)
    
    @pytest.mark.asyncio
    async def test_user_connection_and_disconnection(self, socketio_manager_mock, realtime_fixtures):
        """Test user connection and disconnection flow"""
        user_id = str(uuid4())
        session_id = f"session_{user_id}"
        
        # Test connection
        await socketio_manager_mock.connect_user(session_id, user_id)
        
        assert user_id in socketio_manager_mock.user_connections
        assert session_id in socketio_manager_mock.user_sessions
        assert socketio_manager_mock.user_sessions[session_id] == user_id
        assert socketio_manager_mock.user_connections[user_id] == session_id
        
        # Test disconnection
        await socketio_manager_mock.disconnect_user(session_id)
        
        assert user_id not in socketio_manager_mock.user_connections
        assert session_id not in socketio_manager_mock.user_sessions
    
    @pytest.mark.asyncio
    async def test_room_management(self, socketio_manager_mock, realtime_fixtures):
        """Test joining and leaving rooms"""
        user_id = str(uuid4())
        session_id = f"session_{user_id}"
        room_id = "test_room"
        
        # Connect user first
        await socketio_manager_mock.connect_user(session_id, user_id)
        
        # Test joining room
        await socketio_manager_mock.join_room_user(user_id, room_id)
        
        assert room_id in socketio_manager_mock.rooms
        assert user_id in socketio_manager_mock.rooms[room_id]
        assert socketio_manager_mock.is_user_in_room(user_id, room_id)
        
        # Test leaving room
        await socketio_manager_mock.leave_room_user(user_id, room_id)
        
        assert user_id not in socketio_manager_mock.rooms.get(room_id, set())
        assert not socketio_manager_mock.is_user_in_room(user_id, room_id)
    
    @pytest.mark.asyncio
    async def test_personal_message_sending(self, socketio_manager_mock, realtime_fixtures):
        """Test sending personal messages to users"""
        user_id = str(uuid4())
        session_id = f"session_{user_id}"
        
        # Connect user
        session = socketio_manager_mock.sio.add_session(session_id)
        await socketio_manager_mock.connect_user(session_id, user_id)
        
        # Send personal message
        event_name = "test_event"
        message_data = {"message": "Hello World", "timestamp": datetime.now(timezone.utc).isoformat()}
        
        await socketio_manager_mock.send_personal_message(user_id, event_name, message_data)
        
        # Verify message was sent to user's session
        sent_events = session.get_events_by_name(event_name)
        assert len(sent_events) > 0
        assert sent_events[0]['data'] == message_data
    
    @pytest.mark.asyncio
    async def test_room_message_broadcasting(self, socketio_manager_mock, realtime_fixtures):
        """Test broadcasting messages to rooms"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        user3_id = str(uuid4())
        room_id = "broadcast_room"
        
        # Connect users
        session1 = socketio_manager_mock.sio.add_session(f"session_{user1_id}")
        session2 = socketio_manager_mock.sio.add_session(f"session_{user2_id}")
        session3 = socketio_manager_mock.sio.add_session(f"session_{user3_id}")
        
        await socketio_manager_mock.connect_user(f"session_{user1_id}", user1_id)
        await socketio_manager_mock.connect_user(f"session_{user2_id}", user2_id)
        await socketio_manager_mock.connect_user(f"session_{user3_id}", user3_id)
        
        # Add users 1 and 2 to room, leave user 3 out
        await socketio_manager_mock.join_room_user(user1_id, room_id)
        await socketio_manager_mock.join_room_user(user2_id, room_id)
        
        # Broadcast message to room
        event_name = "room_broadcast"
        broadcast_data = {"announcement": "Room announcement", "room": room_id}
        
        await socketio_manager_mock.send_room_message(room_id, event_name, broadcast_data)
        
        # Verify users in room received the message
        events1 = session1.get_events_by_name(event_name)
        events2 = session2.get_events_by_name(event_name)
        events3 = session3.get_events_by_name(event_name)
        
        assert len(events1) > 0  # User 1 should receive
        assert len(events2) > 0  # User 2 should receive
        assert len(events3) == 0  # User 3 should not receive (not in room)
        
        assert events1[0]['data'] == broadcast_data
        assert events2[0]['data'] == broadcast_data
    
    @pytest.mark.asyncio
    async def test_global_message_broadcasting(self, socketio_manager_mock, realtime_fixtures):
        """Test broadcasting messages to all connected users"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        
        # Connect users
        session1 = socketio_manager_mock.sio.add_session(f"session_{user1_id}")
        session2 = socketio_manager_mock.sio.add_session(f"session_{user2_id}")
        
        await socketio_manager_mock.connect_user(f"session_{user1_id}", user1_id)
        await socketio_manager_mock.connect_user(f"session_{user2_id}", user2_id)
        
        # Broadcast global message
        event_name = "global_announcement"
        global_data = {"message": "System maintenance in 10 minutes", "priority": "HIGH"}
        
        await socketio_manager_mock.broadcast_message(event_name, global_data)
        
        # Verify all users received the message
        events1 = session1.get_events_by_name(event_name)
        events2 = session2.get_events_by_name(event_name)
        
        assert len(events1) > 0
        assert len(events2) > 0
        assert events1[0]['data'] == global_data
        assert events2[0]['data'] == global_data
    
    @pytest.mark.asyncio
    async def test_connection_count_and_room_count(self, socketio_manager_mock, realtime_fixtures):
        """Test connection and room counting functionality"""
        # Initially no connections
        assert socketio_manager_mock.get_connection_count() == 0
        assert socketio_manager_mock.get_room_count() == 0
        
        # Connect users
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        
        await socketio_manager_mock.connect_user(f"session_{user1_id}", user1_id)
        await socketio_manager_mock.connect_user(f"session_{user2_id}", user2_id)
        
        assert socketio_manager_mock.get_connection_count() == 2
        
        # Create rooms
        await socketio_manager_mock.join_room_user(user1_id, "room1")
        await socketio_manager_mock.join_room_user(user2_id, "room1")
        await socketio_manager_mock.join_room_user(user1_id, "room2")
        
        assert socketio_manager_mock.get_room_count() == 2  # room1 and room2
        
        # Disconnect one user
        await socketio_manager_mock.disconnect_user(f"session_{user1_id}")
        
        assert socketio_manager_mock.get_connection_count() == 1
        # room1 should still exist (user2 still in it), room2 should be gone
        assert socketio_manager_mock.get_room_count() == 1
    
    @pytest.mark.asyncio
    async def test_proximity_preferences_management(self, socketio_manager_mock, realtime_fixtures):
        """Test proximity alert preferences management"""
        user_id = str(uuid4())
        bus_stop_id = str(uuid4())
        
        # Set proximity preferences
        preferences = {
            'bus_stop_id': bus_stop_id,
            'radius_meters': 150,
            'subscribed_at': datetime.now(timezone.utc)
        }
        
        socketio_manager_mock.proximity_preferences[user_id] = preferences
        
        # Verify preferences are stored
        assert user_id in socketio_manager_mock.proximity_preferences
        stored_prefs = socketio_manager_mock.proximity_preferences[user_id]
        assert stored_prefs['bus_stop_id'] == bus_stop_id
        assert stored_prefs['radius_meters'] == 150
        
        # Test distance calculation
        # Bus stop at (9.0200, 38.7530), bus at (9.0195, 38.7528) - should be close
        distance = socketio_manager_mock._calculate_distance(9.0195, 38.7528, 9.0200, 38.7530)
        assert distance < 100  # Should be less than 100 meters
        
        # Test farther distance
        far_distance = socketio_manager_mock._calculate_distance(9.0100, 38.7400, 9.0200, 38.7530)
        assert far_distance > 1000  # Should be more than 1km
    
    @pytest.mark.asyncio
    async def test_app_state_integration(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test Socket.IO manager integration with app state"""
        # Set app state
        socketio_manager_mock.set_app_state(mock_app_state)
        
        assert socketio_manager_mock.app_state == mock_app_state
        assert socketio_manager_mock.app_state.mongodb is not None
        
        # Verify app state is accessible in manager
        assert hasattr(socketio_manager_mock.app_state, 'mongodb')
        assert hasattr(socketio_manager_mock.app_state.mongodb, 'users')
        assert hasattr(socketio_manager_mock.app_state.mongodb, 'buses')
        assert hasattr(socketio_manager_mock.app_state.mongodb, 'conversations')
