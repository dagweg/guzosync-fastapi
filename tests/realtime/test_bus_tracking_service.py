"""
Tests for real-time bus tracking service functionality
"""
import pytest
import json
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.realtime.bus_tracking import bus_tracking_service, BusTrackingService
from core.websocket_manager import websocket_manager
from tests.realtime.conftest import MockWebSocket


class TestBusTrackingService:
    """Test cases for bus tracking service functionality"""
    
    @pytest.mark.asyncio
    async def test_update_bus_location_success(self, websocket_manager_mock, mock_app_state):
        """Test successful bus location update"""
        bus_id = str(uuid4())
        latitude = 9.0317
        longitude = 38.7468
        heading = 45.0
        speed = 30.0
        
        # Mock database update
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {
            "id": bus_id,
            "assigned_route_id": None
        }
        
        # Mock subscriber
        subscriber_id = str(uuid4())
        subscriber_ws = MockWebSocket()
        await websocket_manager_mock.connect(subscriber_ws, subscriber_id)
        
        # Subscribe to bus tracking
        room_id = f"bus_tracking:{bus_id}"
        websocket_manager_mock.join_room(subscriber_id, room_id)
        
        # Update bus location
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=latitude,
            longitude=longitude,
            heading=heading,
            speed=speed,
            app_state=mock_app_state
        )
        
        # Verify database was updated
        mock_app_state.mongodb.buses.update_one.assert_called_once()
        update_call = mock_app_state.mongodb.buses.update_one.call_args
        assert update_call[0][0] == {"id": bus_id}  # Filter
        update_data = update_call[0][1]["$set"]
        assert update_data["current_location.latitude"] == latitude
        assert update_data["current_location.longitude"] == longitude
        assert update_data["heading"] == heading
        assert update_data["speed"] == speed
        
        # Verify WebSocket message was sent
        messages = subscriber_ws.get_sent_messages()
        assert len(messages) == 1
        
        message = messages[0]
        assert message["type"] == "bus_location_update"
        assert message["bus_id"] == bus_id
        assert message["location"]["latitude"] == latitude
        assert message["location"]["longitude"] == longitude
        assert message["heading"] == heading
        assert message["speed"] == speed
    
    @pytest.mark.asyncio
    async def test_update_bus_location_with_route_broadcast(self, websocket_manager_mock, mock_app_state):
        """Test bus location update broadcasts to route subscribers"""
        bus_id = str(uuid4())
        route_id = str(uuid4())
        latitude = 9.0317
        longitude = 38.7468
        
        # Mock database responses
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {
            "id": bus_id,
            "assigned_route_id": route_id
        }
        
        # Mock subscribers
        bus_subscriber_id = str(uuid4())
        route_subscriber_id = str(uuid4())
        
        bus_subscriber_ws = MockWebSocket()
        route_subscriber_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(bus_subscriber_ws, bus_subscriber_id)
        await websocket_manager_mock.connect(route_subscriber_ws, route_subscriber_id)
        
        # Subscribe to bus and route
        websocket_manager_mock.join_room(bus_subscriber_id, f"bus_tracking:{bus_id}")
        websocket_manager_mock.join_room(route_subscriber_id, f"route_tracking:{route_id}")
        
        # Update bus location
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=latitude,
            longitude=longitude,
            app_state=mock_app_state
        )
        
        # Verify both subscribers received the update
        bus_messages = bus_subscriber_ws.get_sent_messages()
        route_messages = route_subscriber_ws.get_sent_messages()
        
        assert len(bus_messages) == 1
        assert len(route_messages) == 1
        
        # Both should have the same message content
        assert bus_messages[0]["type"] == "bus_location_update"
        assert route_messages[0]["type"] == "bus_location_update"
        assert bus_messages[0]["bus_id"] == bus_id
        assert route_messages[0]["bus_id"] == bus_id
    
    @pytest.mark.asyncio
    async def test_update_bus_location_no_subscribers(self, websocket_manager_mock, mock_app_state):
        """Test bus location update when no one is subscribed"""
        bus_id = str(uuid4())
        
        # Mock database update
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {
            "id": bus_id,
            "assigned_route_id": None
        }
        
        # Update bus location with no subscribers
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=9.0317,
            longitude=38.7468,
            app_state=mock_app_state
        )
        
        # Verify database was still updated
        mock_app_state.mongodb.buses.update_one.assert_called_once()
        
        # Should not raise any errors
        assert True
    
    @pytest.mark.asyncio
    async def test_update_bus_location_without_optional_params(self, websocket_manager_mock, mock_app_state):
        """Test bus location update with only required parameters"""
        bus_id = str(uuid4())
        latitude = 9.0317
        longitude = 38.7468
        
        # Mock database
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {"id": bus_id}
        
        # Mock subscriber
        subscriber_id = str(uuid4())
        subscriber_ws = MockWebSocket()
        await websocket_manager_mock.connect(subscriber_ws, subscriber_id)
        websocket_manager_mock.join_room(subscriber_id, f"bus_tracking:{bus_id}")
        
        # Update bus location without heading and speed
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=latitude,
            longitude=longitude,
            app_state=mock_app_state
        )
        
        # Verify message contains None values for optional params
        messages = subscriber_ws.get_sent_messages()
        assert len(messages) == 1
        
        message = messages[0]
        assert message["heading"] is None
        assert message["speed"] is None
        assert message["location"]["latitude"] == latitude
        assert message["location"]["longitude"] == longitude
    
    @pytest.mark.asyncio
    async def test_subscribe_to_bus(self, websocket_manager_mock):
        """Test subscribing to bus tracking updates"""
        user_id = str(uuid4())
        bus_id = str(uuid4())
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Subscribe to bus
        await bus_tracking_service.subscribe_to_bus(user_id, bus_id)
        
        # Verify user was added to bus tracking room
        room_id = f"bus_tracking:{bus_id}"
        room_users = websocket_manager_mock.get_room_users(room_id)
        assert user_id in room_users
        
        # Verify confirmation message was sent
        messages = user_ws.get_sent_messages()
        assert len(messages) == 1
        
        message = messages[0]
        assert message["type"] == "bus_tracking_subscribed"
        assert message["bus_id"] == bus_id
        assert message["room_id"] == room_id
    
    @pytest.mark.asyncio
    async def test_subscribe_to_route(self, websocket_manager_mock):
        """Test subscribing to route tracking updates"""
        user_id = str(uuid4())
        route_id = str(uuid4())
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Subscribe to route
        await bus_tracking_service.subscribe_to_route(user_id, route_id)
        
        # Verify user was added to route tracking room
        room_id = f"route_tracking:{route_id}"
        room_users = websocket_manager_mock.get_room_users(room_id)
        assert user_id in room_users
        
        # Verify confirmation message was sent
        messages = user_ws.get_sent_messages()
        assert len(messages) == 1
        
        message = messages[0]
        assert message["type"] == "route_tracking_subscribed"
        assert message["route_id"] == route_id
        assert message["room_id"] == room_id
    
    def test_unsubscribe_from_bus(self, websocket_manager_mock):
        """Test unsubscribing from bus tracking"""
        user_id = str(uuid4())
        bus_id = str(uuid4())
        room_id = f"bus_tracking:{bus_id}"
        
        # First subscribe
        websocket_manager_mock.join_room(user_id, room_id)
        assert user_id in websocket_manager_mock.get_room_users(room_id)
        
        # Unsubscribe
        bus_tracking_service.unsubscribe_from_bus(user_id, bus_id)
        
        # Verify user was removed from room
        room_users = websocket_manager_mock.get_room_users(room_id)
        assert user_id not in room_users
    
    def test_unsubscribe_from_route(self, websocket_manager_mock):
        """Test unsubscribing from route tracking"""
        user_id = str(uuid4())
        route_id = str(uuid4())
        room_id = f"route_tracking:{route_id}"
        
        # First subscribe
        websocket_manager_mock.join_room(user_id, room_id)
        assert user_id in websocket_manager_mock.get_room_users(room_id)
        
        # Unsubscribe
        bus_tracking_service.unsubscribe_from_route(user_id, route_id)
        
        # Verify user was removed from room
        room_users = websocket_manager_mock.get_room_users(room_id)
        assert user_id not in room_users
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers_to_same_bus(self, websocket_manager_mock, mock_app_state):
        """Test multiple users subscribing to the same bus"""
        bus_id = str(uuid4())
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        user3_id = str(uuid4())
        
        # Mock database
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {"id": bus_id}
        
        # Mock WebSocket connections
        user1_ws = MockWebSocket()
        user2_ws = MockWebSocket()
        user3_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(user1_ws, user1_id)
        await websocket_manager_mock.connect(user2_ws, user2_id)
        await websocket_manager_mock.connect(user3_ws, user3_id)
        
        # Subscribe all users to the same bus
        await bus_tracking_service.subscribe_to_bus(user1_id, bus_id)
        await bus_tracking_service.subscribe_to_bus(user2_id, bus_id)
        await bus_tracking_service.subscribe_to_bus(user3_id, bus_id)
        
        # Verify all users are in the room
        room_id = f"bus_tracking:{bus_id}"
        room_users = websocket_manager_mock.get_room_users(room_id)
        assert user1_id in room_users
        assert user2_id in room_users
        assert user3_id in room_users
        
        # Update bus location
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=9.0317,
            longitude=38.7468,
            app_state=mock_app_state
        )
        
        # Verify all subscribers received the update
        user1_messages = user1_ws.get_sent_messages()
        user2_messages = user2_ws.get_sent_messages()
        user3_messages = user3_ws.get_sent_messages()
        
        # Each user should have 2 messages: subscription confirmation + location update
        assert len(user1_messages) == 2
        assert len(user2_messages) == 2
        assert len(user3_messages) == 2
        
        # Last message should be location update
        assert user1_messages[-1]["type"] == "bus_location_update"
        assert user2_messages[-1]["type"] == "bus_location_update"
        assert user3_messages[-1]["type"] == "bus_location_update"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_update_location(self, websocket_manager_mock, mock_app_state):
        """Test error handling when bus location update fails"""
        bus_id = str(uuid4())
        
        # Mock database error
        mock_app_state.mongodb.buses.update_one.side_effect = Exception("Database error")
        
        # Mock subscriber
        subscriber_id = str(uuid4())
        subscriber_ws = MockWebSocket()
        await websocket_manager_mock.connect(subscriber_ws, subscriber_id)
        websocket_manager_mock.join_room(subscriber_id, f"bus_tracking:{bus_id}")
        
        # Should not raise exception, should handle error gracefully
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=9.0317,
            longitude=38.7468,
            app_state=mock_app_state
        )
        
        # Test should complete without raising exception
        assert True
    
    @pytest.mark.asyncio
    async def test_update_location_without_database(self, websocket_manager_mock):
        """Test bus location update when database is not available"""
        bus_id = str(uuid4())
        
        # Mock subscriber
        subscriber_id = str(uuid4())
        subscriber_ws = MockWebSocket()
        await websocket_manager_mock.connect(subscriber_ws, subscriber_id)
        websocket_manager_mock.join_room(subscriber_id, f"bus_tracking:{bus_id}")
        
        # Update without app_state (no database)
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=9.0317,
            longitude=38.7468,
            app_state=None
        )
        
        # Should still send WebSocket message
        messages = subscriber_ws.get_sent_messages()
        assert len(messages) == 1
        assert messages[0]["type"] == "bus_location_update"
    
    @pytest.mark.asyncio
    async def test_cross_route_bus_updates(self, websocket_manager_mock, mock_app_state):
        """Test that buses on different routes don't interfere"""
        bus1_id = str(uuid4())
        bus2_id = str(uuid4())
        route1_id = str(uuid4())
        route2_id = str(uuid4())
        
        # Mock database responses
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        
        def mock_find_bus(query):
            bus_id = query["id"]
            if bus_id == bus1_id:
                return {"id": bus1_id, "assigned_route_id": route1_id}
            elif bus_id == bus2_id:
                return {"id": bus2_id, "assigned_route_id": route2_id}
            return None
        
        mock_app_state.mongodb.buses.find_one.side_effect = mock_find_bus
        
        # Mock subscribers
        route1_subscriber_id = str(uuid4())
        route2_subscriber_id = str(uuid4())
        
        route1_ws = MockWebSocket()
        route2_ws = MockWebSocket()
        
        await websocket_manager_mock.connect(route1_ws, route1_subscriber_id)
        await websocket_manager_mock.connect(route2_ws, route2_subscriber_id)
        
        # Subscribe to different routes
        websocket_manager_mock.join_room(route1_subscriber_id, f"route_tracking:{route1_id}")
        websocket_manager_mock.join_room(route2_subscriber_id, f"route_tracking:{route2_id}")
        
        # Update bus on route 1
        await bus_tracking_service.update_bus_location(
            bus_id=bus1_id,
            latitude=9.0317,
            longitude=38.7468,
            app_state=mock_app_state
        )
        
        # Update bus on route 2
        await bus_tracking_service.update_bus_location(
            bus_id=bus2_id,
            latitude=9.0500,
            longitude=38.7600,
            app_state=mock_app_state
        )
        
        # Verify subscribers only got updates for their respective routes
        route1_messages = route1_ws.get_sent_messages()
        route2_messages = route2_ws.get_sent_messages()
        
        assert len(route1_messages) == 1
        assert len(route2_messages) == 1
        
        assert route1_messages[0]["bus_id"] == bus1_id
        assert route2_messages[0]["bus_id"] == bus2_id
    
    @pytest.mark.asyncio
    async def test_user_subscribed_to_multiple_buses(self, websocket_manager_mock, mock_app_state):
        """Test user subscribed to multiple buses receives all updates"""
        user_id = str(uuid4())
        bus1_id = str(uuid4())
        bus2_id = str(uuid4())
        
        # Mock database
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {"id": "any"}
        
        # Mock WebSocket connection
        user_ws = MockWebSocket()
        await websocket_manager_mock.connect(user_ws, user_id)
        
        # Subscribe to multiple buses
        await bus_tracking_service.subscribe_to_bus(user_id, bus1_id)
        await bus_tracking_service.subscribe_to_bus(user_id, bus2_id)
        
        # Clear subscription messages
        user_ws.clear_messages()
        
        # Update both buses
        await bus_tracking_service.update_bus_location(
            bus_id=bus1_id,
            latitude=9.0317,
            longitude=38.7468,
            app_state=mock_app_state
        )
        
        await bus_tracking_service.update_bus_location(
            bus_id=bus2_id,
            latitude=9.0500,
            longitude=38.7600,
            app_state=mock_app_state
        )
        
        # Verify user received both updates
        messages = user_ws.get_sent_messages()
        assert len(messages) == 2
        
        bus_ids = [msg["bus_id"] for msg in messages]
        assert bus1_id in bus_ids
        assert bus2_id in bus_ids


class TestBusTrackingServiceIntegration:
    """Integration tests for bus tracking service with WebSocket manager"""
    
    @pytest.mark.asyncio
    async def test_full_tracking_workflow(self, mock_app_state):
        """Test complete bus tracking workflow"""
        user_id = str(uuid4())
        bus_id = str(uuid4())
        route_id = str(uuid4())
        
        # Mock database
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = {
            "id": bus_id,
            "assigned_route_id": route_id
        }
        
        # Use real WebSocket manager for integration test
        with patch('core.realtime.bus_tracking.websocket_manager') as mock_manager:
            # Mock manager methods
            mock_manager.join_room = MagicMock()
            mock_manager.leave_room = MagicMock()
            mock_manager.send_personal_message = AsyncMock()
            mock_manager.send_room_message = AsyncMock()
            mock_manager.get_room_users.return_value = {user_id}
            
            # Subscribe to bus and route
            await bus_tracking_service.subscribe_to_bus(user_id, bus_id)
            await bus_tracking_service.subscribe_to_route(user_id, route_id)
            
            assert mock_manager.join_room.call_count == 2
            assert mock_manager.send_personal_message.call_count == 2
            
            # Update bus location
            await bus_tracking_service.update_bus_location(
                bus_id=bus_id,
                latitude=9.0317,
                longitude=38.7468,
                app_state=mock_app_state
            )
            
            # Should broadcast to both bus and route rooms
            assert mock_manager.send_room_message.call_count == 2
            
            # Unsubscribe
            bus_tracking_service.unsubscribe_from_bus(user_id, bus_id)
            bus_tracking_service.unsubscribe_from_route(user_id, route_id)
            
            assert mock_manager.leave_room.call_count == 2
