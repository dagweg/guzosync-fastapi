import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import uuid4
import jwt
import os
from bson import ObjectId

from main import app
from models.user import User, UserRole
from models.payment import Payment, Ticket, PaymentStatus, TicketStatus, PaymentMethod, TicketType
from models.transport import Bus, BusStop
from models.feedback import Feedback, Incident, IncidentSeverity
from models.notifications import Notification, NotificationType


class TestFixtures:
    """Test data fixtures"""
    def __init__(self):
        self.object_ids = [ObjectId() for _ in range(10)]
        self.uuids = [str(uuid4()) for _ in range(10)]
        self.passenger_user = self.create_test_user(role=UserRole.PASSENGER)
        self.admin_user = self.create_test_user(role=UserRole.CONTROL_ADMIN)
        self.driver_user = self.create_test_user(role=UserRole.BUS_DRIVER)
        self.regulator_user = self.create_test_user(role=UserRole.QUEUE_REGULATOR)
    
    @staticmethod
    def create_test_user(
        role: UserRole = UserRole.PASSENGER,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        user_id = user_id or str(uuid4())
        user = {
            "id": str(user_id),  # Ensure id is always a string
            "first_name": kwargs.get("first_name", "Test"),
            "last_name": kwargs.get("last_name", "User"),
            "email": kwargs.get("email", f"test{str(user_id)[:8]}@example.com"),
            "password": kwargs.get("password", "hashed_password"),
            "role": role.value,
            "phone_number": kwargs.get("phone_number", "+1234567890"),
            "is_active": kwargs.get("is_active", True),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        return user
    
    @staticmethod
    def create_test_bus(**kwargs) -> Dict[str, Any]:
        return {
            "_id": ObjectId(),
            "id": str(uuid4()),
            "license_plate": kwargs.get("license_plate", "ABC-123"),
            "capacity": kwargs.get("capacity", 50),
            "current_route_id": kwargs.get("current_route_id"),
            "driver_id": kwargs.get("driver_id"),
            "is_active": kwargs.get("is_active", True),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    
    @staticmethod
    def create_test_bus_stop(**kwargs) -> Dict[str, Any]:
        return {
            "_id": ObjectId(),
            "id": str(uuid4()),
            "name": kwargs.get("name", "Test Bus Stop"),
            "location": {
                "type": "Point",
                "coordinates": [38.7267, 9.0084]  # Addis Ababa coordinates
            },
            "is_active": kwargs.get("is_active", True),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    
    @staticmethod
    def create_test_route(**kwargs) -> Dict[str, Any]:
        return {
            "_id": ObjectId(),
            "id": str(uuid4()),
            "name": kwargs.get("name", "Test Route"),
            "origin_stop_id": kwargs.get("origin_stop_id", str(uuid4())),
            "destination_stop_id": kwargs.get("destination_stop_id", str(uuid4())),
            "stops": kwargs.get("stops", []),
            "is_active": kwargs.get("is_active", True),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    
    @staticmethod
    def create_test_notification(**kwargs) -> Dict[str, Any]:
        return {
            "_id": ObjectId(),
            "id": str(uuid4()),
            "user_id": kwargs.get("user_id", str(uuid4())),
            "title": kwargs.get("title", "Test Notification"),
            "message": kwargs.get("message", "Test message"),
            "type": kwargs.get("type", NotificationType.GENERAL.value),
            "is_read": kwargs.get("is_read", False),
            "created_at": datetime.utcnow(),
        }


@pytest_asyncio.fixture
async def mock_mongodb():
    """Mock MongoDB database"""
    mock_db = MagicMock()
    
    # Mock collections
    mock_db.users = AsyncMock()
    mock_db.buses = AsyncMock()
    mock_db.bus_stops = AsyncMock()
    mock_db.routes = AsyncMock()
    mock_db.notifications = AsyncMock()
    mock_db.feedback = AsyncMock()
    mock_db.incidents = AsyncMock()
    mock_db.alerts = AsyncMock()
    mock_db.attendance = AsyncMock()
    mock_db.conversations = AsyncMock()
    mock_db.messages = AsyncMock()
    mock_db.payments = AsyncMock()
    mock_db.tickets = AsyncMock()
    mock_db.regulator_assignments = AsyncMock()
    
    return mock_db


@pytest_asyncio.fixture
async def test_client(mock_mongodb):
    """Test client with mocked dependencies"""
    app.state.mongodb = mock_mongodb
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client(test_client, mock_mongodb):
    """Test client with authenticated user"""
    # Create test user
    test_user_data = TestFixtures.create_test_user()
    test_user = User(**{k: v for k, v in test_user_data.items() if k != "_id"})
    
    # Mock user lookup
    mock_mongodb.users.find_one.return_value = test_user_data
    
    # Create JWT token
    jwt_secret = os.getenv("JWT_SECRET", "test-secret")
    token_payload = {
        "sub": str(test_user_data["id"]),  # Use UUID string, not ObjectId
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(token_payload, jwt_secret, algorithm="HS256")
    
    # Set authorization header
    test_client.headers = {"Authorization": f"Bearer {token}"}
    test_client.test_user = test_user
    test_client.test_user_data = test_user_data
    
    return test_client


@pytest_asyncio.fixture
async def admin_client(test_client, mock_mongodb):
    """Test client with admin user"""
    # Create admin user
    admin_user_data = TestFixtures.create_test_user(role=UserRole.CONTROL_ADMIN)
    admin_user = User(**{k: v for k, v in admin_user_data.items() if k != "_id"})
    
    # Mock user lookup
    mock_mongodb.users.find_one.return_value = admin_user_data
    
    # Create JWT token
    jwt_secret = os.getenv("JWT_SECRET", "test-secret")
    token_payload = {
        "sub": str(admin_user_data["_id"]),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(token_payload, jwt_secret, algorithm="HS256")
    
    # Set authorization header
    test_client.headers = {"Authorization": f"Bearer {token}"}
    test_client.test_user = admin_user
    test_client.test_user_data = admin_user_data
    
    return test_client


@pytest_asyncio.fixture
async def driver_client(test_client, mock_mongodb):
    """Test client with driver user"""
    # Create driver user
    driver_user_data = TestFixtures.create_test_user(role=UserRole.BUS_DRIVER)
    driver_user = User(**{k: v for k, v in driver_user_data.items() if k != "_id"})
    
    # Mock user lookup
    mock_mongodb.users.find_one.return_value = driver_user_data
    
    # Create JWT token
    jwt_secret = os.getenv("JWT_SECRET", "test-secret")
    token_payload = {
        "sub": str(driver_user_data["_id"]),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(token_payload, jwt_secret, algorithm="HS256")
    
    # Set authorization header
    test_client.headers = {"Authorization": f"Bearer {token}"}
    test_client.test_user = driver_user
    test_client.test_user_data = driver_user_data
    
    return test_client


@pytest_asyncio.fixture
async def regulator_client(test_client, mock_mongodb):
    """Test client with regulator user"""
    # Create regulator user
    regulator_user_data = TestFixtures.create_test_user(role=UserRole.QUEUE_REGULATOR)
    regulator_user = User(**{k: v for k, v in regulator_user_data.items() if k != "_id"})
    
    # Mock user lookup
    mock_mongodb.users.find_one.return_value = regulator_user_data
    
    # Create JWT token
    jwt_secret = os.getenv("JWT_SECRET", "test-secret")
    token_payload = {
        "sub": str(regulator_user_data["_id"]),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(token_payload, jwt_secret, algorithm="HS256")
    
    # Set authorization header
    test_client.headers = {"Authorization": f"Bearer {token}"}
    test_client.test_user = regulator_user
    test_client.test_user_data = regulator_user_data
    
    return test_client
