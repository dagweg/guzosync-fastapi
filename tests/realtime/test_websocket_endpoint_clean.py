"""
WebSocket Endpoint Tests
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
from fastapi import WebSocketDisconnect
from typing import Dict, Any
from uuid import uuid4
import json

from main import app
from tests.realtime.conftest import RealtimeTestFixtures


@pytest.fixture
def websocket_test_client():
    """Test client specifically for WebSocket testing"""
    return TestClient(app)


class TestWebSocketEndpoint:
    """Test cases for WebSocket endpoint functionality"""
    
    def test_websocket_connection_with_valid_token(self, websocket_test_client, mock_mongodb):
        """Test WebSocket connection with valid authentication token"""
        # Mock user authentication
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                # Test WebSocket connection
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Should successfully connect
                    assert websocket is not None
    
    def test_websocket_connection_invalid_token(self, websocket_test_client):
        """Test WebSocket connection with invalid token"""
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = None
            
            # Should fail to connect
            with pytest.raises(WebSocketDisconnect):
                with websocket_test_client.websocket_connect("/ws/connect?token=invalid_token"):
                    pass
    
    def test_websocket_join_room_message(self, websocket_test_client, mock_mongodb):
        """Test sending join_room message via WebSocket"""
        user_data = RealtimeTestFixtures.create_test_user()
        room_id = f"test_room_{uuid4()}"
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.join_room = MagicMock()
                mock_manager.disconnect = AsyncMock()
                
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Send join room message
                    join_message = {
                        "type": "join_room",
                        "room_id": room_id
                    }
                    websocket.send_json(join_message)
                    
                    # Should receive confirmation
                    response = websocket.receive_json()
                    assert response["type"] == "room_joined"
                    assert response["room_id"] == room_id
                    
                    # Verify manager was called
                    mock_manager.join_room.assert_called_once_with(user_data["id"], room_id)
    
    def test_websocket_leave_room_message(self, websocket_test_client, mock_mongodb):
        """Test sending leave_room message via WebSocket"""
        user_data = RealtimeTestFixtures.create_test_user()
        room_id = f"test_room_{uuid4()}"
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.leave_room = MagicMock()
                mock_manager.disconnect = AsyncMock()
                
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Send leave room message
                    leave_message = {
                        "type": "leave_room",
                        "room_id": room_id
                    }
                    websocket.send_json(leave_message)
                    
                    # Should receive confirmation
                    response = websocket.receive_json()
                    assert response["type"] == "room_left"
                    assert response["room_id"] == room_id
                    
                    # Verify manager was called
                    mock_manager.leave_room.assert_called_once_with(user_data["id"], room_id)
    
    def test_websocket_ping_pong(self, websocket_test_client, mock_mongodb):
        """Test ping-pong functionality"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Send ping message
                    ping_message = {
                        "type": "ping",
                        "timestamp": "2025-06-08T12:00:00.000Z"
                    }
                    websocket.send_json(ping_message)
                    
                    # Should receive pong
                    response = websocket.receive_json()
                    assert response["type"] == "pong"
                    assert response["timestamp"] == ping_message["timestamp"]
    
    def test_websocket_unknown_message_type(self, websocket_test_client, mock_mongodb):
        """Test handling unknown message types"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Send unknown message type
                    unknown_message = {
                        "type": "unknown_type",
                        "data": "test"
                    }
                    websocket.send_json(unknown_message)
                    
                    # Should not crash, but may not respond
                    # The WebSocket should remain open
    
    def test_websocket_connection_cleanup_on_disconnect(self, websocket_test_client, mock_mongodb):
        """Test that connections are properly cleaned up on disconnect"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Connection established
                    pass
                
                # Verify cleanup was called on connection close
                mock_manager.disconnect.assert_called_once()
    
    def test_websocket_multiple_connections_same_user(self, websocket_test_client, mock_mongodb):
        """Test multiple WebSocket connections for the same user"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                # First connection
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token1") as ws1:
                    # Second connection (should replace first)
                    with websocket_test_client.websocket_connect("/ws/connect?token=valid_token2") as ws2:
                        # Both connections should work
                        assert mock_manager.connect.call_count == 2
    
    def test_websocket_room_subscription_scenarios(self, websocket_test_client, mock_mongodb):
        """Test various room subscription scenarios"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.join_room = MagicMock()
                mock_manager.leave_room = MagicMock()
                mock_manager.disconnect = AsyncMock()
                
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Test conversation room
                    conversation_room = "conversation:test_chat_123"
                    websocket.send_json({"type": "join_room", "room_id": conversation_room})
                    response = websocket.receive_json()
                    assert response["type"] == "room_joined"
                    assert response["room_id"] == conversation_room
                    
                    # Test bus tracking room
                    bus_room = "bus_tracking:bus_456"
                    websocket.send_json({"type": "join_room", "room_id": bus_room})
                    response = websocket.receive_json()
                    assert response["type"] == "room_joined"
                    assert response["room_id"] == bus_room
                    
                    # Test route tracking room
                    route_room = "route_tracking:route_789"
                    websocket.send_json({"type": "join_room", "room_id": route_room})
                    response = websocket.receive_json()
                    assert response["type"] == "room_joined"
                    assert response["room_id"] == route_room
                    
                    # Verify all joins were called
                    assert mock_manager.join_room.call_count == 3
    
    def test_websocket_error_handling(self, websocket_test_client, mock_mongodb):
        """Test WebSocket error handling"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.join_room = MagicMock(side_effect=Exception("Test error"))
                mock_manager.disconnect = AsyncMock()
                
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Send message that causes error
                    websocket.send_json({"type": "join_room", "room_id": "test_room"})
                    
                    # Connection should still be maintained despite error
                    # (Depending on error handling implementation)
    
    def test_websocket_malformed_json(self, websocket_test_client, mock_mongodb):
        """Test handling of malformed JSON messages"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Send malformed JSON
                    websocket.send_text("invalid json {")
                    
                    # Connection should handle the error gracefully
                    # (Implementation dependent)
    
    def test_websocket_missing_token(self, websocket_test_client):
        """Test WebSocket connection without token"""
        with pytest.raises(Exception):  # Should fail without token
            with websocket_test_client.websocket_connect("/ws/connect"):
                pass
    
    def test_websocket_concurrent_operations(self, websocket_test_client, mock_mongodb):
        """Test concurrent WebSocket operations"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('core.websocket_manager.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.join_room = MagicMock()
                mock_manager.leave_room = MagicMock()
                mock_manager.disconnect = AsyncMock()
                
                with websocket_test_client.websocket_connect("/ws/connect?token=valid_token") as websocket:
                    # Send multiple messages rapidly
                    messages = [
                        {"type": "join_room", "room_id": "room1"},
                        {"type": "join_room", "room_id": "room2"},
                        {"type": "ping", "timestamp": "2025-06-08T12:00:00.000Z"},
                        {"type": "leave_room", "room_id": "room1"},
                    ]
                    
                    for message in messages:
                        websocket.send_json(message)
                    
                    # Receive all responses
                    responses = []
                    for _ in messages:
                        try:
                            responses.append(websocket.receive_json())
                        except:
                            break
                    
                    # Should handle all messages
