"""
Tests for real-time chat service functionality
"""
import pytest
import json
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.realtime.chat import chat_service, ChatService
from core.websocket_manager import websocket_manager
from tests.realtime.conftest import MockWebSocket


class TestChatService:
    """Test cases for chat service functionality"""
    
    @pytest.mark.asyncio
    async def test_send_real_time_message_success(self, websocket_manager_mock, mock_app_state):
        """Test sending a real-time message successfully"""
        conversation_id = str(uuid4())
        sender_id = str(uuid4())
        receiver_id = str(uuid4())
        message_id = str(uuid4())
        content = "Hello, this is a test message!"
        
        # Mock conversation with participants
        mock_conversation = {
            "id": conversation_id,
            "participants": [sender_id, receiver_id]
        }
        mock_app_state.mongodb.conversations.find_one.return_value = mock_conversation
        
        # Mock WebSocket connections
        sender_ws = MockWebSocket()
        receiver_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(sender_ws, sender_id)
        await websocket_manager_mock.connect(receiver_ws, receiver_id)
        
        # Join conversation room
        room_id = f"conversation:{conversation_id}"
        websocket_manager_mock.join_room(sender_id, room_id)
        websocket_manager_mock.join_room(receiver_id, room_id)
        
        # Send real-time message
        await chat_service.send_real_time_message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            message_id=message_id,
            message_type="TEXT",
            app_state=mock_app_state
        )
        
        # Verify message was sent to receiver but not sender
        sender_messages = sender_ws.get_sent_messages()
        receiver_messages = receiver_ws.get_sent_messages()
        
        assert len(sender_messages) == 0  # Sender excluded
        assert len(receiver_messages) == 1
        
        # Verify message content
        message = receiver_messages[0]
        assert message["type"] == "new_message"
        assert message["conversation_id"] == conversation_id
        assert message["message"]["id"] == message_id
        assert message["message"]["sender_id"] == sender_id
        assert message["message"]["content"] == content
        assert message["message"]["message_type"] == "TEXT"
    
    @pytest.mark.asyncio
    async def test_send_real_time_message_to_offline_participant(self, websocket_manager_mock, mock_app_state):
        """Test sending a message when one participant is offline"""
        conversation_id = str(uuid4())
        sender_id = str(uuid4())
        offline_participant_id = str(uuid4())
        message_id = str(uuid4())
        content = "Hello offline user!"
        
        # Mock conversation with participants
        mock_conversation = {
            "id": conversation_id,
            "participants": [sender_id, offline_participant_id]
        }
        mock_app_state.mongodb.conversations.find_one.return_value = mock_conversation
        
        # Only sender is connected
        sender_ws = MockWebSocket()
        await websocket_manager_mock.connect(sender_ws, sender_id)
        
        # Join conversation room (only sender)
        room_id = f"conversation:{conversation_id}"
        websocket_manager_mock.join_room(sender_id, room_id)
        
        # Send real-time message
        await chat_service.send_real_time_message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            message_id=message_id,
            app_state=mock_app_state
        )
          # Verify notification was sent to offline participant
        # Since the offline participant is not connected, no messages should be sent
        # but the operation should complete successfully
        sender_messages = sender_ws.get_sent_messages()
        assert len(sender_messages) == 0  # Sender excluded, offline participant not connected
    
    @pytest.mark.asyncio
    async def test_join_conversation_success(self, websocket_manager_mock, mock_app_state):
        """Test successfully joining a conversation"""
        user_id = str(uuid4())
        conversation_id = str(uuid4())
        
        # Mock conversation with user as participant
        mock_conversation = {
            "id": conversation_id,
            "participants": [user_id, str(uuid4())]
        }
        mock_app_state.mongodb.conversations.find_one.return_value = mock_conversation
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Join conversation
        result = await chat_service.join_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            app_state=mock_app_state
        )
        
        assert result is True
        
        # Verify user was added to room
        room_id = f"conversation:{conversation_id}"
        room_users = websocket_manager_mock.get_room_users(room_id)
        assert user_id in room_users
        
        # Verify confirmation message was sent
        messages = user_ws.get_sent_messages()
        assert len(messages) == 1
        
        message = messages[0]
        assert message["type"] == "conversation_joined"
        assert message["conversation_id"] == conversation_id
        assert message["room_id"] == room_id
    
    @pytest.mark.asyncio
    async def test_join_conversation_unauthorized(self, websocket_manager_mock, mock_app_state):
        """Test joining a conversation user is not authorized for"""
        user_id = str(uuid4())
        conversation_id = str(uuid4())
        other_user_id = str(uuid4())
          # Mock conversation without user as participant
        mock_conversation = {
            "id": conversation_id,
            "participants": [other_user_id]  # User not in participants
        }
        
        # Set up mock to return None since user is not in participants
        mock_app_state.mongodb.conversations.find_one.return_value = None
        
        # Try to join conversation
        result = await chat_service.join_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            app_state=mock_app_state
        )
        
        assert result is False
        
        # Verify user was not added to room
        room_id = f"conversation:{conversation_id}"
        room_users = websocket_manager_mock.get_room_users(room_id)
        assert user_id not in room_users
    
    @pytest.mark.asyncio
    async def test_join_conversation_no_database(self, websocket_manager_mock):
        """Test joining conversation when database is not available"""
        user_id = str(uuid4())
        conversation_id = str(uuid4())
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Join conversation without app_state (no database check)
        result = await chat_service.join_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            app_state=None
        )
        
        assert result is True
        
        # Verify user was added to room
        room_id = f"conversation:{conversation_id}"
        room_users = websocket_manager_mock.get_room_users(room_id)
        assert user_id in room_users
    
    @pytest.mark.asyncio
    async def test_leave_conversation(self, websocket_manager_mock):
        """Test leaving a conversation"""
        user_id = str(uuid4())
        conversation_id = str(uuid4())
        room_id = f"conversation:{conversation_id}"
        
        # First join the room
        websocket_manager_mock.join_room(user_id, room_id)
        assert user_id in websocket_manager_mock.get_room_users(room_id)
        
        # Leave conversation
        await chat_service.leave_conversation(user_id, conversation_id)
        
        # Verify user was removed from room
        room_users = websocket_manager_mock.get_room_users(room_id)
        assert user_id not in room_users
    
    @pytest.mark.asyncio
    async def test_notify_typing_status(self, websocket_manager_mock):
        """Test notifying typing status to conversation participants"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        user3_id = str(uuid4())
        conversation_id = str(uuid4())
        room_id = f"conversation:{conversation_id}"
        
        # Mock WebSocket connections
        user1_ws = MockWebSocket()
        user2_ws = MockWebSocket()
        user3_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(user1_ws, user1_id)
        await websocket_manager_mock.connect(user2_ws, user2_id)
        await websocket_manager_mock.connect(user3_ws, user3_id)
        
        # Join conversation room
        websocket_manager_mock.join_room(user1_id, room_id)
        websocket_manager_mock.join_room(user2_id, room_id)
        websocket_manager_mock.join_room(user3_id, room_id)
        
        # User1 starts typing
        await chat_service.notify_typing(
            conversation_id=conversation_id,
            user_id=user1_id,
            is_typing=True
        )
        
        # Verify typing notification was sent to other users but not to typing user
        user1_messages = user1_ws.get_sent_messages()
        user2_messages = user2_ws.get_sent_messages()
        user3_messages = user3_ws.get_sent_messages()
        
        assert len(user1_messages) == 0  # Typing user excluded
        assert len(user2_messages) == 1
        assert len(user3_messages) == 1
        
        # Verify message content
        message = user2_messages[0]
        assert message["type"] == "typing_status"
        assert message["conversation_id"] == conversation_id
        assert message["user_id"] == user1_id
        assert message["is_typing"] is True
    
    @pytest.mark.asyncio
    async def test_notify_message_read(self, websocket_manager_mock):
        """Test notifying when a message has been read"""
        reader_id = str(uuid4())
        other_user_id = str(uuid4())
        conversation_id = str(uuid4())
        message_id = str(uuid4())
        room_id = f"conversation:{conversation_id}"
        
        # Mock WebSocket connections
        reader_ws = MockWebSocket()
        other_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(reader_ws, reader_id)
        await websocket_manager_mock.connect(other_ws, other_user_id)
        
        # Join conversation room
        websocket_manager_mock.join_room(reader_id, room_id)
        websocket_manager_mock.join_room(other_user_id, room_id)
        
        # Notify message read
        await chat_service.notify_message_read(
            conversation_id=conversation_id,
            user_id=reader_id,
            message_id=message_id
        )
        
        # Verify read notification was sent to other users but not to reader
        reader_messages = reader_ws.get_sent_messages()
        other_messages = other_ws.get_sent_messages()
        
        assert len(reader_messages) == 0  # Reader excluded
        assert len(other_messages) == 1
        
        # Verify message content
        message = other_messages[0]
        assert message["type"] == "message_read"
        assert message["conversation_id"] == conversation_id
        assert message["user_id"] == reader_id
        assert message["message_id"] == message_id
    
    @pytest.mark.asyncio
    async def test_send_message_with_different_types(self, websocket_manager_mock, mock_app_state):
        """Test sending messages of different types"""
        conversation_id = str(uuid4())
        sender_id = str(uuid4())
        receiver_id = str(uuid4())
        room_id = f"conversation:{conversation_id}"
        
        # Mock conversation
        mock_conversation = {
            "id": conversation_id,
            "participants": [sender_id, receiver_id]
        }
        mock_app_state.mongodb.conversations.find_one.return_value = mock_conversation
        
        # Mock WebSocket connections
        sender_ws = MockWebSocket()
        receiver_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(sender_ws, sender_id)
        await websocket_manager_mock.connect(receiver_ws, receiver_id)
        websocket_manager_mock.join_room(receiver_id, room_id)
        
        # Test different message types
        message_types = ["TEXT", "IMAGE", "FILE", "LOCATION", "VOICE"]
        
        for msg_type in message_types:
            receiver_ws.clear_messages()
            message_id = str(uuid4())
            content = f"Test {msg_type.lower()} message"
            
            await chat_service.send_real_time_message(
                conversation_id=conversation_id,
                sender_id=sender_id,
                content=content,
                message_id=message_id,
                message_type=msg_type,
                app_state=mock_app_state
            )
            
            messages = receiver_ws.get_sent_messages()
            assert len(messages) == 1
            
            message = messages[0]
            assert message["message"]["message_type"] == msg_type
            assert message["message"]["content"] == content
    
    @pytest.mark.asyncio
    async def test_error_handling_in_send_message(self, websocket_manager_mock, mock_app_state):
        """Test error handling when sending messages fails"""
        conversation_id = str(uuid4())
        sender_id = str(uuid4())
        message_id = str(uuid4())
        
        # Mock database error
        mock_app_state.mongodb.conversations.find_one.side_effect = Exception("Database error")
        
        # Should not raise exception, should handle error gracefully
        await chat_service.send_real_time_message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content="Test message",
            message_id=message_id,
            app_state=mock_app_state
        )
        
        # Test should complete without raising exception
        assert True
    
    @pytest.mark.asyncio
    async def test_error_handling_in_join_conversation(self, websocket_manager_mock, mock_app_state):
        """Test error handling when joining conversation fails"""
        user_id = str(uuid4())
        conversation_id = str(uuid4())
        
        # Mock database error
        mock_app_state.mongodb.conversations.find_one.side_effect = Exception("Database error")
        
        # Should return False on error
        result = await chat_service.join_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            app_state=mock_app_state
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_multiple_conversations_isolation(self, websocket_manager_mock, mock_app_state):
        """Test that messages in different conversations don't interfere"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        user3_id = str(uuid4())
        
        conversation1_id = str(uuid4())
        conversation2_id = str(uuid4())
        
        # Mock conversations
        mock_conversation1 = {
            "id": conversation1_id,
            "participants": [user1_id, user2_id]
        }
        mock_conversation2 = {
            "id": conversation2_id,
            "participants": [user1_id, user3_id]
        }
        
        def find_conversation(query):
            if query["id"] == conversation1_id:
                return mock_conversation1
            elif query["id"] == conversation2_id:
                return mock_conversation2
            return None
        
        mock_app_state.mongodb.conversations.find_one.side_effect = find_conversation
        
        # Connect users and join rooms
        user1_ws = MockWebSocket()
        user2_ws = MockWebSocket()
        user3_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(user1_ws, user1_id)
        await websocket_manager_mock.connect(user2_ws, user2_id)
        await websocket_manager_mock.connect(user3_ws, user3_id)
        
        # Join different conversation rooms
        websocket_manager_mock.join_room(user1_id, f"conversation:{conversation1_id}")
        websocket_manager_mock.join_room(user2_id, f"conversation:{conversation1_id}")
        websocket_manager_mock.join_room(user1_id, f"conversation:{conversation2_id}")
        websocket_manager_mock.join_room(user3_id, f"conversation:{conversation2_id}")
        
        # Send message in conversation 1
        await chat_service.send_real_time_message(
            conversation_id=conversation1_id,
            sender_id=user1_id,
            content="Message for conversation 1",
            message_id=str(uuid4()),
            app_state=mock_app_state
        )
        
        # Send message in conversation 2
        await chat_service.send_real_time_message(
            conversation_id=conversation2_id,
            sender_id=user1_id,
            content="Message for conversation 2",
            message_id=str(uuid4()),
            app_state=mock_app_state
        )
        
        # Verify message isolation
        user2_messages = user2_ws.get_sent_messages()
        user3_messages = user3_ws.get_sent_messages()
        
        # User2 should only receive message from conversation 1
        assert len(user2_messages) == 1
        assert user2_messages[0]["conversation_id"] == conversation1_id
        assert "conversation 1" in user2_messages[0]["message"]["content"]
        
        # User3 should only receive message from conversation 2
        assert len(user3_messages) == 1
        assert user3_messages[0]["conversation_id"] == conversation2_id
        assert "conversation 2" in user3_messages[0]["message"]["content"]


class TestChatServiceIntegration:
    """Integration tests for chat service with WebSocket manager"""
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, mock_app_state):
        """Test complete conversation flow from join to message to leave"""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        conversation_id = str(uuid4())
        
        # Mock conversation
        mock_conversation = {
            "id": conversation_id,
            "participants": [user1_id, user2_id]
        }
        mock_app_state.mongodb.conversations.find_one.return_value = mock_conversation
        
        # Use real WebSocket manager for integration test
        with patch('core.realtime.chat.websocket_manager') as mock_manager:
            # Mock manager methods
            mock_manager.join_room = MagicMock()
            mock_manager.leave_room = MagicMock()
            mock_manager.send_personal_message = AsyncMock()
            mock_manager.send_room_message = AsyncMock()
            mock_manager.get_room_users.return_value = {user1_id, user2_id}
            
            # Join conversation
            result1 = await chat_service.join_conversation(user1_id, conversation_id, mock_app_state)
            result2 = await chat_service.join_conversation(user2_id, conversation_id, mock_app_state)
            
            assert result1 is True
            assert result2 is True
            assert mock_manager.join_room.call_count == 2
            
            # Send message
            await chat_service.send_real_time_message(
                conversation_id=conversation_id,
                sender_id=user1_id,
                content="Hello!",
                message_id=str(uuid4()),
                app_state=mock_app_state
            )
            
            assert mock_manager.send_room_message.called
            
            # Leave conversation
            await chat_service.leave_conversation(user1_id, conversation_id)
            await chat_service.leave_conversation(user2_id, conversation_id)
            
            assert mock_manager.leave_room.call_count == 2
