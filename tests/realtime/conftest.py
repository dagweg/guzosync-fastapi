"""
Real-time test fixtures and utilities for Socket.IO
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import json

from core.socketio_manager import SocketIOManager, socketio_manager
from tests.conftest import TestFixtures


class MockSocketIOSession:
    """Mock Socket.IO session for testing"""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid4())
        self.is_connected = False
        self.sent_events: List[Dict[str, Any]] = []
        self.received_events: List[Dict[str, Any]] = []
        self.rooms: set = set()
        self.auth_data: Optional[Dict[str, Any]] = None
        
    async def emit(self, event: str, data: Any = None, room: Optional[str] = None):
        """Mock Socket.IO emit"""
        if not self.is_connected:
            raise Exception("Socket.IO session not connected")
        self.sent_events.append({
            'event': event,
            'data': data,
            'room': room,
            'timestamp': datetime.now(timezone.utc)
        })
        
    async def enter_room(self, room: str):
        """Mock entering a room"""
        self.rooms.add(room)
        
    async def leave_room(self, room: str):
        """Mock leaving a room"""
        self.rooms.discard(room)
        
    async def disconnect(self, reason: str = ""):
        """Mock Socket.IO disconnect"""
        self.is_connected = False
        self.rooms.clear()
        
    def connect(self, auth: Optional[Dict[str, Any]] = None):
        """Mock Socket.IO connect"""
        self.is_connected = True
        self.auth_data = auth
        
    def add_received_event(self, event: str, data: Any = None):
        """Add an event to be received"""
        self.received_events.append({
            'event': event,
            'data': data,
            'timestamp': datetime.now(timezone.utc)
        })
        
    def get_sent_events(self) -> List[Dict[str, Any]]:
        """Get all sent events"""
        return self.sent_events.copy()
        
    def get_events_by_name(self, event_name: str) -> List[Dict[str, Any]]:
        """Get events by name"""
        return [event for event in self.sent_events if event['event'] == event_name]
        
    def clear_events(self):
        """Clear all events"""
        self.sent_events.clear()
        self.received_events.clear()


class MockSocketIOServer:
    """Mock Socket.IO server for testing"""

    def __init__(self):
        self.sessions: Dict[str, MockSocketIOSession] = {}
        self.rooms: Dict[str, set] = {}
        self.emitted_events: List[Dict[str, Any]] = []
        
    async def emit(self, event: str, data: Any = None, room: Optional[str] = None):
        """Mock server emit"""
        self.emitted_events.append({
            'event': event,
            'data': data,
            'room': room,
            'timestamp': datetime.now(timezone.utc)
        })
        
        # If room specified, emit to room members
        if room and room in self.rooms:
            for session_id in self.rooms[room]:
                if session_id in self.sessions:
                    await self.sessions[session_id].emit(event, data, room)
        else:
            # Broadcast to all sessions
            for session in self.sessions.values():
                await session.emit(event, data, room)
    
    async def enter_room(self, session_id: str, room: str):
        """Mock entering room"""
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(session_id)
        
        if session_id in self.sessions:
            await self.sessions[session_id].enter_room(room)
    
    async def leave_room(self, session_id: str, room: str):
        """Mock leaving room"""
        if room in self.rooms:
            self.rooms[room].discard(session_id)
            if not self.rooms[room]:
                del self.rooms[room]
        
        if session_id in self.sessions:
            await self.sessions[session_id].leave_room(room)
    
    def add_session(self, session_id: str) -> MockSocketIOSession:
        """Add a mock session"""
        session = MockSocketIOSession(session_id)
        session.connect()
        self.sessions[session_id] = session
        return session
    
    def remove_session(self, session_id: str):
        """Remove a session"""
        if session_id in self.sessions:
            # Remove from all rooms
            for room_id in list(self.rooms.keys()):
                if session_id in self.rooms[room_id]:
                    self.rooms[room_id].discard(session_id)
                    if not self.rooms[room_id]:
                        del self.rooms[room_id]
            del self.sessions[session_id]
    
    def get_room_sessions(self, room: str) -> set:
        """Get sessions in a room"""
        return self.rooms.get(room, set()).copy()


class RealtimeTestFixtures:
    """Test fixtures for real-time functionality"""
    
    @staticmethod
    def create_mock_app_state():
        """Create mock app state with MongoDB"""
        mock_app_state = MagicMock()
        mock_app_state.mongodb = MagicMock()
        
        # Mock collections
        mock_app_state.mongodb.users = AsyncMock()
        mock_app_state.mongodb.buses = AsyncMock()
        mock_app_state.mongodb.bus_stops = AsyncMock()
        mock_app_state.mongodb.routes = AsyncMock()
        mock_app_state.mongodb.conversations = AsyncMock()
        mock_app_state.mongodb.messages = AsyncMock()
        mock_app_state.mongodb.notifications = AsyncMock()
        
        return mock_app_state
    
    @staticmethod
    def create_mock_user(user_id: Optional[str] = None, role: str = "PASSENGER", name: str = "Test User"):
        """Create mock user data"""
        return {
            "id": user_id or str(uuid4()),
            "name": name,
            "role": role,
            "email": f"test_{user_id or 'user'}@example.com",
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }
    
    @staticmethod
    def create_mock_bus(bus_id: Optional[str] = None, route_id: Optional[str] = None):
        """Create mock bus data"""
        return {
            "id": bus_id or str(uuid4()),
            "license_plate": f"AA-{uuid4().hex[:6].upper()}",
            "assigned_route_id": route_id,
            "current_location": {
                "latitude": 9.0192,
                "longitude": 38.7525
            },
            "heading": 45.5,
            "speed": 25.0,
            "status": "ACTIVE",
            "last_location_update": datetime.now(timezone.utc)
        }
    
    @staticmethod
    def create_mock_bus_stop(stop_id: Optional[str] = None, name: str = "Test Stop"):
        """Create mock bus stop data"""
        return {
            "id": stop_id or str(uuid4()),
            "name": name,
            "location": {
                "latitude": 9.0200,
                "longitude": 38.7530
            },
            "address": "Test Address",
            "is_active": True
        }
    
    @staticmethod
    def create_mock_route(route_id: Optional[str] = None, name: str = "Test Route"):
        """Create mock route data"""
        return {
            "id": route_id or str(uuid4()),
            "name": name,
            "start_location": {"latitude": 9.0100, "longitude": 38.7400},
            "end_location": {"latitude": 9.0300, "longitude": 38.7600},
            "route_shape": {
                "type": "LineString",
                "coordinates": [
                    [38.7400, 9.0100],
                    [38.7500, 9.0200],
                    [38.7600, 9.0300]
                ]
            },
            "bus_stops": [],
            "is_active": True
        }


# Fixtures
@pytest_asyncio.fixture
async def mock_socketio_session():
    """Mock Socket.IO session fixture"""
    return MockSocketIOSession()


@pytest_asyncio.fixture
async def mock_socketio_server():
    """Mock Socket.IO server fixture"""
    return MockSocketIOServer()


@pytest_asyncio.fixture
async def socketio_manager_mock():
    """Mock Socket.IO manager with global patching"""
    manager = SocketIOManager()
    # Clear any existing connections
    manager.user_sessions.clear()
    manager.user_connections.clear()
    manager.rooms.clear()
    manager.proximity_preferences.clear()
    
    # Mock the Socket.IO server
    manager.sio = MockSocketIOServer()
    
    # Patch the global socketio_manager in all real-time services
    with patch('core.realtime.bus_tracking.socketio_manager', manager), \
         patch('core.realtime.chat.socketio_manager', manager), \
         patch('core.realtime.notifications.socketio_manager', manager), \
         patch('core.socketio_manager.socketio_manager', manager):
        yield manager


@pytest_asyncio.fixture
async def realtime_fixtures():
    """Real-time test fixtures"""
    return RealtimeTestFixtures()


@pytest_asyncio.fixture
async def mock_app_state():
    """Mock app state fixture"""
    return RealtimeTestFixtures.create_mock_app_state()
