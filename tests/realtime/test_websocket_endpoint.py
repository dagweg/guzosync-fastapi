"""
WebSocket Endpoint Tests
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any
from uuid import uuid4
import json
import asyncio

from routers.websocket import websocket_endpoint
from tests.realtime.conftest import RealtimeTestFixtures


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection"""
    websocket = MagicMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.close = AsyncMock()
    websocket.app = MagicMock()
    websocket.app.state = MagicMock()
    return websocket


class TestWebSocketEndpoint:
    """Test cases for WebSocket endpoint functionality"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_with_valid_token(self, mock_websocket, mock_mongodb):
        """Test WebSocket connection with valid authentication token"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                # Simulate connection then immediate disconnection
                mock_websocket.receive_text.side_effect = WebSocketDisconnect()
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Verify connection was established and cleaned up
                mock_manager.connect.assert_called_once_with(mock_websocket, user_data["id"])
                mock_manager.disconnect.assert_called_once_with(user_data["id"])
    
    @pytest.mark.asyncio
    async def test_websocket_connection_invalid_token(self, mock_websocket):
        """Test WebSocket connection with invalid token"""
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = None
            
            await websocket_endpoint(mock_websocket, token="invalid_token")
            
            # Should close connection
            mock_websocket.close.assert_called_once_with(code=4001, reason="Authentication failed")
    
    @pytest.mark.asyncio
    async def test_websocket_join_room_message(self, mock_websocket, mock_mongodb):
        """Test sending join_room message via WebSocket"""
        user_data = RealtimeTestFixtures.create_test_user()
        room_id = f"test_room_{uuid4()}"
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.join_room = MagicMock()
                mock_manager.disconnect = AsyncMock()
                
                # Simulate receiving join_room message then disconnection
                join_message = json.dumps({
                    "type": "join_room",
                    "room_id": room_id
                })
                mock_websocket.receive_text.side_effect = [join_message, WebSocketDisconnect()]
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Verify join_room was called
                mock_manager.join_room.assert_called_once_with(user_data["id"], room_id)
                
                # Verify response was sent
                expected_response = json.dumps({
                    "type": "room_joined",
                    "room_id": room_id,
                    "message": f"Joined room {room_id}"
                })
                mock_websocket.send_text.assert_called_with(expected_response)
    
    @pytest.mark.asyncio
    async def test_websocket_leave_room_message(self, mock_websocket, mock_mongodb):
        """Test sending leave_room message via WebSocket"""
        user_data = RealtimeTestFixtures.create_test_user()
        room_id = f"test_room_{uuid4()}"
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.leave_room = MagicMock()
                mock_manager.disconnect = AsyncMock()
                
                # Simulate receiving leave_room message then disconnection
                leave_message = json.dumps({
                    "type": "leave_room",
                    "room_id": room_id
                })
                mock_websocket.receive_text.side_effect = [leave_message, WebSocketDisconnect()]
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Verify leave_room was called
                mock_manager.leave_room.assert_called_once_with(user_data["id"], room_id)
                
                # Verify response was sent
                expected_response = json.dumps({
                    "type": "room_left",
                    "room_id": room_id,
                    "message": f"Left room {room_id}"
                })
                mock_websocket.send_text.assert_called_with(expected_response)
    
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, mock_websocket, mock_mongodb):
        """Test ping-pong functionality"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                # Simulate receiving ping message then disconnection
                timestamp = "2025-06-08T12:00:00.000Z"
                ping_message = json.dumps({
                    "type": "ping",
                    "timestamp": timestamp
                })
                mock_websocket.receive_text.side_effect = [ping_message, WebSocketDisconnect()]
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Verify pong response was sent
                expected_response = json.dumps({
                    "type": "pong",
                    "timestamp": timestamp
                })
                mock_websocket.send_text.assert_called_with(expected_response)
    
    @pytest.mark.asyncio
    async def test_websocket_unknown_message_type(self, mock_websocket, mock_mongodb):
        """Test handling unknown message types"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                # Simulate receiving unknown message then disconnection
                unknown_message = json.dumps({
                    "type": "unknown_type",
                    "data": "test"
                })
                mock_websocket.receive_text.side_effect = [unknown_message, WebSocketDisconnect()]
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Should not cause any errors, just ignore unknown message
                mock_manager.connect.assert_called_once()
                mock_manager.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_cleanup_on_disconnect(self, mock_websocket, mock_mongodb):
        """Test that connections are properly cleaned up on disconnect"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                # Simulate WebSocket disconnect
                mock_websocket.receive_text.side_effect = WebSocketDisconnect()
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Verify cleanup was called
                mock_manager.disconnect.assert_called_once_with(user_data["id"])
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, mock_websocket, mock_mongodb):
        """Test WebSocket error handling"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                # Simulate error during message processing
                mock_websocket.receive_text.side_effect = Exception("Test error")
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Should still clean up connection
                mock_manager.disconnect.assert_called_once_with(user_data["id"])
    
    @pytest.mark.asyncio
    async def test_websocket_malformed_json(self, mock_websocket, mock_mongodb):
        """Test handling of malformed JSON messages"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.disconnect = AsyncMock()
                
                # Simulate receiving malformed JSON
                mock_websocket.receive_text.side_effect = ["invalid json {", WebSocketDisconnect()]
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Should handle error gracefully
                mock_manager.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_multiple_room_operations(self, mock_websocket, mock_mongodb):
        """Test multiple room operations in sequence"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.join_room = MagicMock()
                mock_manager.leave_room = MagicMock()
                mock_manager.disconnect = AsyncMock()
                
                # Simulate sequence of messages
                messages = [
                    json.dumps({"type": "join_room", "room_id": "room1"}),
                    json.dumps({"type": "join_room", "room_id": "room2"}),
                    json.dumps({"type": "ping", "timestamp": "2025-06-08T12:00:00.000Z"}),
                    json.dumps({"type": "leave_room", "room_id": "room1"}),
                ]
                mock_websocket.receive_text.side_effect = messages + [WebSocketDisconnect()]
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Verify all operations were called
                assert mock_manager.join_room.call_count == 2
                assert mock_manager.leave_room.call_count == 1
                mock_manager.join_room.assert_any_call(user_data["id"], "room1")
                mock_manager.join_room.assert_any_call(user_data["id"], "room2")
                mock_manager.leave_room.assert_called_with(user_data["id"], "room1")
    
    @pytest.mark.asyncio
    async def test_websocket_room_subscription_scenarios(self, mock_websocket, mock_mongodb):
        """Test various room subscription scenarios"""
        user_data = RealtimeTestFixtures.create_test_user()
        
        with patch('routers.websocket.get_current_user_websocket') as mock_auth:
            mock_auth.return_value = MagicMock(id=user_data["id"])
            
            with patch('routers.websocket.websocket_manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                mock_manager.join_room = MagicMock()
                mock_manager.disconnect = AsyncMock()
                
                # Test different room types
                messages = [
                    json.dumps({"type": "join_room", "room_id": "conversation:test_chat_123"}),
                    json.dumps({"type": "join_room", "room_id": "bus_tracking:bus_456"}),
                    json.dumps({"type": "join_room", "room_id": "route_tracking:route_789"}),
                ]
                mock_websocket.receive_text.side_effect = messages + [WebSocketDisconnect()]
                
                await websocket_endpoint(mock_websocket, token="valid_token")
                
                # Verify all joins were called
                assert mock_manager.join_room.call_count == 3
                mock_manager.join_room.assert_any_call(user_data["id"], "conversation:test_chat_123")
                mock_manager.join_room.assert_any_call(user_data["id"], "bus_tracking:bus_456")
                mock_manager.join_room.assert_any_call(user_data["id"], "route_tracking:route_789")
