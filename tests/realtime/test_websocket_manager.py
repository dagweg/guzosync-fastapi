"""
WebSocket Manager Tests
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
from uuid import uuid4
import json

from core.websocket_manager import WebSocketManager
from tests.realtime.conftest import MockWebSocket, RealtimeTestFixtures


class TestWebSocketManager:
    """Test cases for WebSocket manager functionality"""
    
    @pytest.mark.asyncio
    async def test_connect_user(self, websocket_manager_mock, mock_websocket):
        """Test connecting a user to WebSocket"""
        user_id = str(uuid4())
        
        await websocket_manager_mock.connect(mock_websocket, user_id)
        
        assert user_id in websocket_manager_mock.active_connections
        assert websocket_manager_mock.active_connections[user_id] == mock_websocket
        assert mock_websocket.is_connected
    
    @pytest.mark.asyncio
    async def test_disconnect_user(self, websocket_manager_mock, mock_websocket):
        """Test disconnecting a user from WebSocket"""
        user_id = str(uuid4())
        
        # First connect the user
        await websocket_manager_mock.connect(mock_websocket, user_id)
        assert user_id in websocket_manager_mock.active_connections
        
        # Then disconnect
        websocket_manager_mock.disconnect(user_id)
        
        assert user_id not in websocket_manager_mock.active_connections
    
    @pytest.mark.asyncio
    async def test_join_room(self, websocket_manager_mock, mock_websocket):
        """Test user joining a room"""
        user_id = str(uuid4())
        room_id = f"test_room_{uuid4()}"
        
        await websocket_manager_mock.connect(mock_websocket, user_id)
        websocket_manager_mock.join_room(user_id, room_id)
        
        assert room_id in websocket_manager_mock.rooms
        assert user_id in websocket_manager_mock.rooms[room_id]
    
    @pytest.mark.asyncio
    async def test_leave_room(self, websocket_manager_mock, mock_websocket):
        """Test user leaving a room"""
        user_id = str(uuid4())
        room_id = f"test_room_{uuid4()}"
        
        await websocket_manager_mock.connect(mock_websocket, user_id)
        websocket_manager_mock.join_room(user_id, room_id)
        
        # Verify user is in room
        assert user_id in websocket_manager_mock.rooms[room_id]
        
        # Leave room
        websocket_manager_mock.leave_room(user_id, room_id)
        
        # Verify user is no longer in room
        assert user_id not in websocket_manager_mock.rooms.get(room_id, set())
    
    @pytest.mark.asyncio
    async def test_multiple_users_same_room(self, websocket_manager_mock):
        """Test multiple users joining the same room"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        room_id = f"test_room_{uuid4()}"
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        await websocket_manager_mock.connect(websocket1, user1_id)
        await websocket_manager_mock.connect(websocket2, user2_id)
        
        websocket_manager_mock.join_room(user1_id, room_id)
        websocket_manager_mock.join_room(user2_id, room_id)
        
        assert len(websocket_manager_mock.rooms[room_id]) == 2
        assert user1_id in websocket_manager_mock.rooms[room_id]
        assert user2_id in websocket_manager_mock.rooms[room_id]
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_from_all_rooms(self, websocket_manager_mock, mock_websocket):
        """Test that disconnecting a user removes them from all rooms"""
        user_id = str(uuid4())
        room1_id = f"room1_{uuid4()}"
        room2_id = f"room2_{uuid4()}"
        
        await websocket_manager_mock.connect(mock_websocket, user_id)
        websocket_manager_mock.join_room(user_id, room1_id)
        websocket_manager_mock.join_room(user_id, room2_id)
        
        # Verify user is in both rooms
        assert user_id in websocket_manager_mock.rooms[room1_id]
        assert user_id in websocket_manager_mock.rooms[room2_id]
        
        # Disconnect user
        websocket_manager_mock.disconnect(user_id)
        
        # Verify user is removed from all rooms
        assert user_id not in websocket_manager_mock.active_connections
        # Empty rooms should be cleaned up
        assert room1_id not in websocket_manager_mock.rooms
        assert room2_id not in websocket_manager_mock.rooms
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self, websocket_manager_mock, mock_websocket):
        """Test sending a personal message to a specific user"""
        user_id = str(uuid4())
        message = {"type": "test_message", "content": "Hello user!"}
        
        await websocket_manager_mock.connect(mock_websocket, user_id)
        await websocket_manager_mock.send_personal_message(user_id, message)
        
        sent_messages = mock_websocket.get_sent_messages()
        assert len(sent_messages) == 1
        assert sent_messages[0] == message
    
    @pytest.mark.asyncio
    async def test_send_personal_message_user_not_connected(self, websocket_manager_mock):
        """Test sending message to disconnected user"""
        user_id = str(uuid4())
        message = {"type": "test_message", "content": "Hello user!"}
        
        # Should not raise an error, just log and continue
        await websocket_manager_mock.send_personal_message(user_id, message)
        # No assertions needed - just verify it doesn't crash
    
    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, websocket_manager_mock):
        """Test broadcasting a message to all users in a room"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        user3_id = str(uuid4())  # Not in room
        room_id = f"test_room_{uuid4()}"
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        websocket3 = MockWebSocket()
        
        await websocket_manager_mock.connect(websocket1, user1_id)
        await websocket_manager_mock.connect(websocket2, user2_id)
        await websocket_manager_mock.connect(websocket3, user3_id)
        
        websocket_manager_mock.join_room(user1_id, room_id)
        websocket_manager_mock.join_room(user2_id, room_id)
        # user3 is not in the room
        
        message = {"type": "room_broadcast", "content": "Hello room!"}
        await websocket_manager_mock.broadcast_to_room(room_id, message)
        
        # Users in room should receive message
        assert len(websocket1.get_sent_messages()) == 1
        assert len(websocket2.get_sent_messages()) == 1
        assert websocket1.get_sent_messages()[0] == message
        assert websocket2.get_sent_messages()[0] == message
        
        # User not in room should not receive message
        assert len(websocket3.get_sent_messages()) == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_to_empty_room(self, websocket_manager_mock):
        """Test broadcasting to a room with no users"""
        room_id = f"empty_room_{uuid4()}"
        message = {"type": "room_broadcast", "content": "Hello empty room!"}
        
        # Should not raise an error
        await websocket_manager_mock.broadcast_to_room(room_id, message)
    
    @pytest.mark.asyncio
    async def test_get_room_users(self, websocket_manager_mock, mock_websocket):
        """Test getting users in a room"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        room_id = f"test_room_{uuid4()}"
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        await websocket_manager_mock.connect(websocket1, user1_id)
        await websocket_manager_mock.connect(websocket2, user2_id)
        
        websocket_manager_mock.join_room(user1_id, room_id)
        websocket_manager_mock.join_room(user2_id, room_id)
        
        room_users = websocket_manager_mock.get_room_users(room_id)
        
        assert len(room_users) == 2
        assert user1_id in room_users
        assert user2_id in room_users
    
    @pytest.mark.asyncio
    async def test_get_user_rooms(self, websocket_manager_mock, mock_websocket):
        """Test getting rooms a user has joined"""
        user_id = str(uuid4())
        room1_id = f"room1_{uuid4()}"
        room2_id = f"room2_{uuid4()}"
        
        await websocket_manager_mock.connect(mock_websocket, user_id)
        websocket_manager_mock.join_room(user_id, room1_id)
        websocket_manager_mock.join_room(user_id, room2_id)
        
        user_rooms = websocket_manager_mock.get_user_rooms(user_id)
        
        assert len(user_rooms) == 2
        assert room1_id in user_rooms
        assert room2_id in user_rooms
    
    @pytest.mark.asyncio
    async def test_connection_count(self, websocket_manager_mock):
        """Test getting active connection count"""
        assert websocket_manager_mock.get_connection_count() == 0
        
        # Connect users
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        await websocket_manager_mock.connect(websocket1, user1_id)
        assert websocket_manager_mock.get_connection_count() == 1
        
        await websocket_manager_mock.connect(websocket2, user2_id)
        assert websocket_manager_mock.get_connection_count() == 2
        
        # Disconnect one user
        websocket_manager_mock.disconnect(user1_id)
        assert websocket_manager_mock.get_connection_count() == 1
    
    @pytest.mark.asyncio
    async def test_room_count(self, websocket_manager_mock):
        """Test getting active room count"""
        assert websocket_manager_mock.get_room_count() == 0
        
        user_id = str(uuid4())
        websocket = MockWebSocket()
        
        await websocket_manager_mock.connect(websocket, user_id)
        
        room1_id = f"room1_{uuid4()}"
        room2_id = f"room2_{uuid4()}"
        
        websocket_manager_mock.join_room(user_id, room1_id)
        assert websocket_manager_mock.get_room_count() == 1
        
        websocket_manager_mock.join_room(user_id, room2_id)
        assert websocket_manager_mock.get_room_count() == 2
        
        # Disconnect user (should remove empty rooms)
        websocket_manager_mock.disconnect(user_id)
        assert websocket_manager_mock.get_room_count() == 0
