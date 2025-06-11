"""
Real-world Socket.IO integration tests without mocks
Tests actual Socket.IO functionality with real server and database
"""
import pytest
import pytest_asyncio
import asyncio
import socketio
import httpx
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict, List, Any
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from main import app
from core.database import get_mongodb_client
from core.auth import create_access_token
from tests.conftest import TestFixtures


class RealWorldSocketIOClient:
    """Real Socket.IO client for testing"""
    
    def __init__(self, user_token: str):
        self.sio = socketio.AsyncClient()
        self.user_token = user_token
        self.received_events: List[Dict[str, Any]] = []
        self.connected = False
        
        # Register event handlers
        @self.sio.event
        async def connect():
            self.connected = True
            print(f"Client connected")
        
        @self.sio.event
        async def disconnect():
            self.connected = False
            print(f"Client disconnected")
        
        @self.sio.event
        async def authenticated(data):
            print(f"Client authenticated: {data}")
            self.received_events.append({"event": "authenticated", "data": data})
        
        @self.sio.event
        async def auth_error(data):
            print(f"Auth error: {data}")
            self.received_events.append({"event": "auth_error", "data": data})
        
        @self.sio.event
        async def new_message(data):
            print(f"New message: {data}")
            self.received_events.append({"event": "new_message", "data": data})
        
        @self.sio.event
        async def notification(data):
            print(f"Notification: {data}")
            self.received_events.append({"event": "notification", "data": data})
        
        @self.sio.event
        async def proximity_alert(data):
            print(f"Proximity alert: {data}")
            self.received_events.append({"event": "proximity_alert", "data": data})
        
        @self.sio.event
        async def bus_location_update(data):
            print(f"Bus location update: {data}")
            self.received_events.append({"event": "bus_location_update", "data": data})
        
        @self.sio.event
        async def all_bus_locations(data):
            print(f"All bus locations: {data}")
            self.received_events.append({"event": "all_bus_locations", "data": data})
        
        @self.sio.event
        async def emergency_alert(data):
            print(f"Emergency alert: {data}")
            self.received_events.append({"event": "emergency_alert", "data": data})
        
        @self.sio.event
        async def error(data):
            print(f"Error: {data}")
            self.received_events.append({"event": "error", "data": data})
    
    async def connect_to_server(self, server_url: str = "http://localhost:8000"):
        """Connect to Socket.IO server"""
        await self.sio.connect(server_url, auth={"token": self.user_token})
        await asyncio.sleep(0.1)  # Give time for connection
    
    async def disconnect_from_server(self):
        """Disconnect from server"""
        await self.sio.disconnect()
    
    async def emit_and_wait(self, event: str, data: Any = None, timeout: float = 2.0):
        """Emit event and wait for response"""
        await self.sio.emit(event, data)
        await asyncio.sleep(timeout)  # Wait for response
    
    def get_events_by_name(self, event_name: str) -> List[Dict[str, Any]]:
        """Get received events by name"""
        return [event for event in self.received_events if event["event"] == event_name]
    
    def clear_events(self):
        """Clear received events"""
        self.received_events.clear()


@pytest_asyncio.fixture
async def test_database():
    """Set up test database"""
    mongodb = await get_mongodb_client()
    
    # Clean up test data before tests
    test_collections = ["users", "buses", "bus_stops", "routes", "conversations", "messages", "notifications"]
    for collection_name in test_collections:
        collection = getattr(mongodb, collection_name)
        await collection.delete_many({"test_data": True})
    
    yield mongodb
    
    # Clean up test data after tests
    for collection_name in test_collections:
        collection = getattr(mongodb, collection_name)
        await collection.delete_many({"test_data": True})


@pytest_asyncio.fixture
async def test_users(test_database):
    """Create test users in database"""
    users_data = [
        {
            "id": str(uuid4()),
            "name": "Test Driver",
            "email": "driver@test.com",
            "role": "BUS_DRIVER",
            "is_active": True,
            "test_data": True
        },
        {
            "id": str(uuid4()),
            "name": "Test Control Staff",
            "email": "control@test.com", 
            "role": "CONTROL_STAFF",
            "is_active": True,
            "test_data": True
        },
        {
            "id": str(uuid4()),
            "name": "Test Admin",
            "email": "admin@test.com",
            "role": "ADMIN", 
            "is_active": True,
            "test_data": True
        },
        {
            "id": str(uuid4()),
            "name": "Test Passenger",
            "email": "passenger@test.com",
            "role": "PASSENGER",
            "is_active": True,
            "test_data": True
        }
    ]
    
    await test_database.users.insert_many(users_data)
    return users_data


@pytest_asyncio.fixture
async def test_bus_data(test_database):
    """Create test bus and route data"""
    route_id = str(uuid4())
    bus_id = str(uuid4())
    bus_stop_id = str(uuid4())
    
    # Create route
    route_data = {
        "id": route_id,
        "name": "Test Route",
        "start_location": {"latitude": 9.0100, "longitude": 38.7400},
        "end_location": {"latitude": 9.0300, "longitude": 38.7600},
        "route_shape": {
            "type": "LineString",
            "coordinates": [[38.7400, 9.0100], [38.7500, 9.0200], [38.7600, 9.0300]]
        },
        "bus_stops": [bus_stop_id],
        "is_active": True,
        "test_data": True
    }
    
    # Create bus
    bus_data = {
        "id": bus_id,
        "license_plate": "TEST-123",
        "assigned_route_id": route_id,
        "current_location": {"latitude": 9.0192, "longitude": 38.7525},
        "heading": 45.0,
        "speed": 25.0,
        "status": "ACTIVE",
        "last_location_update": datetime.now(timezone.utc),
        "test_data": True
    }
    
    # Create bus stop
    bus_stop_data = {
        "id": bus_stop_id,
        "name": "Test Bus Stop",
        "location": {"latitude": 9.0200, "longitude": 38.7530},
        "address": "Test Address",
        "is_active": True,
        "test_data": True
    }
    
    await test_database.routes.insert_one(route_data)
    await test_database.buses.insert_one(bus_data)
    await test_database.bus_stops.insert_one(bus_stop_data)
    
    return {
        "route": route_data,
        "bus": bus_data,
        "bus_stop": bus_stop_data
    }


class TestRealWorldSocketIO:
    """Real-world Socket.IO integration tests"""
    
    @pytest.mark.asyncio
    async def test_socket_connection_and_authentication(self, test_users):
        """Test real Socket.IO connection and authentication"""
        driver = test_users[0]  # BUS_DRIVER
        
        # Create real JWT token
        token = create_access_token(data={"sub": driver["email"]})
        
        # Create real Socket.IO client
        client = RealWorldSocketIOClient(token)
        
        try:
            # Connect to real server
            await client.connect_to_server()
            
            # Verify connection
            assert client.connected
            
            # Wait for authentication
            await asyncio.sleep(1.0)
            
            # Check authentication events
            auth_events = client.get_events_by_name("authenticated")
            assert len(auth_events) > 0
            assert auth_events[0]["data"]["user_id"] == driver["id"]
            
        finally:
            await client.disconnect_from_server()
    
    @pytest.mark.asyncio
    async def test_real_messaging_between_users(self, test_users, test_database):
        """Test real messaging between driver and control staff"""
        driver = test_users[0]  # BUS_DRIVER
        control_staff = test_users[1]  # CONTROL_STAFF
        
        # Create tokens
        driver_token = create_access_token(data={"sub": driver["email"]})
        control_token = create_access_token(data={"sub": control_staff["email"]})
        
        # Create clients
        driver_client = RealWorldSocketIOClient(driver_token)
        control_client = RealWorldSocketIOClient(control_token)
        
        try:
            # Connect both clients
            await driver_client.connect_to_server()
            await control_client.connect_to_server()
            
            # Wait for authentication
            await asyncio.sleep(1.0)
            
            # Driver sends message to control staff
            message_data = {
                "recipient_id": control_staff["id"],
                "message": "Need assistance with route guidance",
                "message_type": "TEXT"
            }
            
            await driver_client.emit_and_wait("send_message", message_data, timeout=3.0)
            
            # Check if control staff received the message
            control_messages = control_client.get_events_by_name("new_message")
            assert len(control_messages) > 0
            
            received_message = control_messages[0]["data"]
            assert received_message["message"]["content"] == "Need assistance with route guidance"
            assert received_message["message"]["sender_id"] == driver["id"]
            
            # Verify message was saved to database
            messages = await test_database.messages.find({"test_data": True}).to_list(length=None)
            assert len(messages) > 0
            
        finally:
            await driver_client.disconnect_from_server()
            await control_client.disconnect_from_server()
    
    @pytest.mark.asyncio
    async def test_real_bus_location_updates(self, test_users, test_bus_data, test_database):
        """Test real bus location updates and tracking"""
        driver = test_users[0]  # BUS_DRIVER
        passenger = test_users[3]  # PASSENGER
        bus_data = test_bus_data["bus"]
        
        # Create tokens
        driver_token = create_access_token(data={"sub": driver["email"]})
        passenger_token = create_access_token(data={"sub": passenger["email"]})
        
        # Create clients
        driver_client = RealWorldSocketIOClient(driver_token)
        passenger_client = RealWorldSocketIOClient(passenger_token)
        
        try:
            # Connect both clients
            await driver_client.connect_to_server()
            await passenger_client.connect_to_server()
            
            # Wait for authentication
            await asyncio.sleep(1.0)
            
            # Passenger subscribes to bus tracking
            await passenger_client.emit_and_wait("subscribe_bus_tracking", {"bus_id": bus_data["id"]})
            
            # Driver updates bus location
            location_update = {
                "bus_id": bus_data["id"],
                "latitude": 9.0250,
                "longitude": 38.7550,
                "heading": 90.0,
                "speed": 30.0
            }
            
            await driver_client.emit_and_wait("update_bus_location", location_update, timeout=3.0)
            
            # Check if passenger received location update
            location_events = passenger_client.get_events_by_name("bus_location_update")
            assert len(location_events) > 0
            
            received_update = location_events[0]["data"]
            assert received_update["bus_id"] == bus_data["id"]
            assert received_update["location"]["latitude"] == 9.0250
            assert received_update["location"]["longitude"] == 38.7550
            
            # Verify database was updated
            updated_bus = await test_database.buses.find_one({"id": bus_data["id"]})
            assert updated_bus["current_location"]["latitude"] == 9.0250
            assert updated_bus["current_location"]["longitude"] == 38.7550
            
        finally:
            await driver_client.disconnect_from_server()
            await passenger_client.disconnect_from_server()
    
    @pytest.mark.asyncio
    async def test_real_proximity_alerts(self, test_users, test_bus_data, test_database):
        """Test real proximity alerts when bus approaches stop"""
        driver = test_users[0]  # BUS_DRIVER
        passenger = test_users[3]  # PASSENGER
        bus_data = test_bus_data["bus"]
        bus_stop_data = test_bus_data["bus_stop"]
        
        # Create tokens
        driver_token = create_access_token(data={"sub": driver["email"]})
        passenger_token = create_access_token(data={"sub": passenger["email"]})
        
        # Create clients
        driver_client = RealWorldSocketIOClient(driver_token)
        passenger_client = RealWorldSocketIOClient(passenger_token)
        
        try:
            # Connect both clients
            await driver_client.connect_to_server()
            await passenger_client.connect_to_server()
            
            # Wait for authentication
            await asyncio.sleep(1.0)
            
            # Passenger subscribes to proximity alerts
            proximity_data = {
                "bus_stop_id": bus_stop_data["id"],
                "radius_meters": 200
            }
            await passenger_client.emit_and_wait("subscribe_proximity_alerts", proximity_data)
            
            # Driver updates bus location near the stop
            near_stop_location = {
                "bus_id": bus_data["id"],
                "latitude": 9.0195,  # Very close to bus stop
                "longitude": 38.7528,
                "heading": 45.0,
                "speed": 20.0
            }
            
            await driver_client.emit_and_wait("update_bus_location", near_stop_location, timeout=3.0)
            
            # Check if passenger received proximity alert
            proximity_events = passenger_client.get_events_by_name("proximity_alert")
            assert len(proximity_events) > 0
            
            alert = proximity_events[0]["data"]
            assert alert["bus_id"] == bus_data["id"]
            assert alert["bus_stop_id"] == bus_stop_data["id"]
            assert alert["distance_meters"] < 200
            assert "estimated_arrival_minutes" in alert
            
        finally:
            await driver_client.disconnect_from_server()
            await passenger_client.disconnect_from_server()
    
    @pytest.mark.asyncio
    async def test_real_emergency_alerts(self, test_users, test_database):
        """Test real emergency alert system"""
        driver = test_users[0]  # BUS_DRIVER
        admin = test_users[2]  # ADMIN
        control_staff = test_users[1]  # CONTROL_STAFF
        
        # Create tokens
        driver_token = create_access_token(data={"sub": driver["email"]})
        admin_token = create_access_token(data={"sub": admin["email"]})
        control_token = create_access_token(data={"sub": control_staff["email"]})
        
        # Create clients
        driver_client = RealWorldSocketIOClient(driver_token)
        admin_client = RealWorldSocketIOClient(admin_token)
        control_client = RealWorldSocketIOClient(control_token)
        
        try:
            # Connect all clients
            await driver_client.connect_to_server()
            await admin_client.connect_to_server()
            await control_client.connect_to_server()
            
            # Wait for authentication
            await asyncio.sleep(1.0)
            
            # Admin and control staff join emergency alerts room
            await admin_client.emit_and_wait("join_room", {"room_id": "emergency_alerts"})
            await control_client.emit_and_wait("join_room", {"room_id": "emergency_alerts"})
            
            # Driver sends emergency alert
            emergency_data = {
                "alert_type": "VEHICLE_BREAKDOWN",
                "message": "Engine failure, need immediate assistance",
                "location": {"latitude": 9.0192, "longitude": 38.7525}
            }
            
            # Use HTTP endpoint for emergency alert (as per our design)
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    "http://localhost:8000/socket.io/emergency-alert",
                    json=emergency_data,
                    headers={"Authorization": f"Bearer {driver_token}"}
                )
                assert response.status_code == 200
            
            # Wait for emergency alerts to be processed
            await asyncio.sleep(2.0)
            
            # Check if admin and control staff received emergency alerts
            admin_alerts = admin_client.get_events_by_name("emergency_alert")
            control_alerts = control_client.get_events_by_name("emergency_alert")
            
            assert len(admin_alerts) > 0 or len(control_alerts) > 0  # At least one should receive
            
            # Verify emergency notification was saved to database
            notifications = await test_database.notifications.find({
                "notification_type": "EMERGENCY",
                "test_data": True
            }).to_list(length=None)
            assert len(notifications) > 0
            
        finally:
            await driver_client.disconnect_from_server()
            await admin_client.disconnect_from_server()
            await control_client.disconnect_from_server()
    
    @pytest.mark.asyncio
    async def test_real_admin_broadcast(self, test_users, test_database):
        """Test real admin broadcast to drivers"""
        admin = test_users[2]  # ADMIN
        driver = test_users[0]  # BUS_DRIVER
        
        # Create tokens
        admin_token = create_access_token(data={"sub": admin["email"]})
        driver_token = create_access_token(data={"sub": driver["email"]})
        
        # Create clients
        admin_client = RealWorldSocketIOClient(admin_token)
        driver_client = RealWorldSocketIOClient(driver_token)
        
        try:
            # Connect both clients
            await admin_client.connect_to_server()
            await driver_client.connect_to_server()
            
            # Wait for authentication
            await asyncio.sleep(1.0)
            
            # Admin broadcasts message to drivers
            broadcast_data = {
                "message": "All drivers report to dispatch immediately",
                "target_roles": ["BUS_DRIVER"],
                "priority": "HIGH"
            }
            
            # Use HTTP endpoint for broadcast
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    "http://localhost:8000/socket.io/broadcast",
                    json=broadcast_data,
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                assert response.status_code == 200
            
            # Wait for broadcast to be processed
            await asyncio.sleep(2.0)
            
            # Check if driver received notification
            driver_notifications = driver_client.get_events_by_name("notification")
            assert len(driver_notifications) > 0
            
            notification = driver_notifications[0]["data"]
            assert "All drivers report to dispatch" in notification["notification"]["message"]
            assert notification["notification"]["notification_type"] == "ADMIN_MESSAGE"
            
        finally:
            await admin_client.disconnect_from_server()
            await driver_client.disconnect_from_server()
