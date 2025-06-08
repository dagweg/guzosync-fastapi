"""
Real-time test fixtures and utilities
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from typing import Dict, List, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta
import json

from core.websocket_manager import WebSocketManager, websocket_manager
from tests.conftest import TestFixtures


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.sent_messages: List[str] = []
        self.received_messages: List[str] = []
        self.is_connected = False
        self.close_code: Optional[int] = None
        self.close_reason: Optional[str] = None
    
    async def accept(self):
        """Mock WebSocket accept"""
        self.is_connected = True
    
    async def send_text(self, data: str):
        """Mock sending text data"""
        self.sent_messages.append(data)
    
    async def receive_text(self) -> str:
        """Mock receiving text data"""
        if self.received_messages:
            return self.received_messages.pop(0)
        raise Exception("No more messages to receive")
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Mock WebSocket close"""
        self.is_connected = False
        self.close_code = code
        self.close_reason = reason
    
    def add_received_message(self, message: Dict[str, Any]):
        """Add a message to be received"""
        self.received_messages.append(json.dumps(message))
    
    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages as parsed JSON"""
        return [json.loads(msg) for msg in self.sent_messages]
    
    def clear_messages(self):
        """Clear all messages"""
        self.sent_messages.clear()
        self.received_messages.clear()


class RealtimeTestFixtures(TestFixtures):
    """Extended test fixtures for real-time functionality"""
    
    @staticmethod
    def create_websocket_message(message_type: str, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket message"""
        base_message = {
            "type": message_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        base_message.update(kwargs)
        return base_message
    
    @staticmethod
    def create_chat_message(**kwargs) -> Dict[str, Any]:
        """Create a chat message payload"""
        return {
            "conversation_id": kwargs.get("conversation_id", f"conv_{uuid4()}"),
            "content": kwargs.get("content", "Test message"),
            "message_type": kwargs.get("message_type", "TEXT"),
            "sender_id": kwargs.get("sender_id", str(uuid4())),
            "message_id": kwargs.get("message_id", str(uuid4())),
            "timestamp": kwargs.get("timestamp", datetime.utcnow().isoformat())
        }
    
    @staticmethod
    def create_bus_location_update(**kwargs) -> Dict[str, Any]:
        """Create a bus location update payload"""
        return {
            "bus_id": kwargs.get("bus_id", f"bus_{uuid4()}"),
            "latitude": kwargs.get("latitude", 9.0192),
            "longitude": kwargs.get("longitude", 38.7525),
            "heading": kwargs.get("heading", 45.0),
            "speed": kwargs.get("speed", 30.0),
            "timestamp": kwargs.get("timestamp", datetime.utcnow().isoformat())
        }
    
    @staticmethod
    def create_notification_payload(**kwargs) -> Dict[str, Any]:
        """Create a notification payload"""
        return {
            "title": kwargs.get("title", "Test Notification"),
            "message": kwargs.get("message", "Test notification message"),
            "notification_type": kwargs.get("notification_type", "DEMO"),
            "target_user_id": kwargs.get("target_user_id", str(uuid4())),
            "created_at": kwargs.get("created_at", datetime.utcnow().isoformat())
        }


@pytest_asyncio.fixture
async def mock_websocket():
    """Mock WebSocket fixture"""
    return MockWebSocket()


@pytest_asyncio.fixture
async def websocket_manager_mock():
    """Mock WebSocket manager with global patching"""
    manager = WebSocketManager()
    # Clear any existing connections
    manager.active_connections.clear()
    manager.rooms.clear()
    
    # Patch the global websocket_manager in all real-time services
    with patch('core.realtime.bus_tracking.websocket_manager', manager), \
         patch('core.realtime.chat.websocket_manager', manager), \
         patch('core.realtime.notifications.websocket_manager', manager), \
         patch('core.websocket_manager.websocket_manager', manager):
        yield manager


@pytest_asyncio.fixture
async def realtime_fixtures():
    """Real-time test fixtures"""
    return RealtimeTestFixtures()


@pytest_asyncio.fixture
async def mock_app_state():
    """Mock FastAPI app state"""
    mock_state = MagicMock()
    mock_state.mongodb = MagicMock()
    
    # Mock collections - these should be regular mocks for non-async collection methods
    # but the actual query/update methods need to be AsyncMock
    mock_state.mongodb.users = MagicMock()
    mock_state.mongodb.conversations = MagicMock()
    mock_state.mongodb.messages = MagicMock()
    mock_state.mongodb.notifications = MagicMock()
    mock_state.mongodb.buses = MagicMock()
    mock_state.mongodb.routes = MagicMock()
    mock_state.mongodb.trips = MagicMock()
    
    # Set up async methods for database operations
    mock_state.mongodb.notifications.insert_one = AsyncMock()
    mock_state.mongodb.notifications.insert_many = AsyncMock()
    mock_state.mongodb.trips.find_one = AsyncMock()
    mock_state.mongodb.conversations.find_one = AsyncMock()
    mock_state.mongodb.buses.find_one = AsyncMock() 
    mock_state.mongodb.buses.update_one = AsyncMock()
    mock_state.mongodb.messages.insert_one = AsyncMock()
    
    # Set up cursor mocking for find operations that use to_list()
    # Users find for notification service
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_state.mongodb.users.find.return_value = mock_cursor
    
    return mock_state


@pytest_asyncio.fixture
async def connected_websocket(mock_websocket, websocket_manager_mock):
    """WebSocket connected to manager"""
    user_id = str(uuid4())
    await websocket_manager_mock.connect(mock_websocket, user_id)
    
    return {
        "websocket": mock_websocket,
        "user_id": user_id,
        "manager": websocket_manager_mock
    }
