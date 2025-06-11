"""
Tests for Socket.IO bus tracking features with Mapbox integration
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from core.realtime.bus_tracking import bus_tracking_service
from core.realtime.socketio_events import websocket_event_handlers
from tests.realtime.conftest import RealtimeTestFixtures


class TestSocketIOBusTracking:
    """Test cases for Socket.IO bus tracking functionality"""
    
    @pytest.mark.asyncio
    async def test_bus_location_update_and_broadcast(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test bus location updates and real-time broadcasting"""
        # Create test data
        bus_id = str(uuid4())
        route_id = str(uuid4())
        driver_id = str(uuid4())
        passenger_id = str(uuid4())
        
        bus = realtime_fixtures.create_mock_bus(bus_id, route_id)
        driver = realtime_fixtures.create_mock_user(driver_id, "BUS_DRIVER", "Test Driver")
        passenger = realtime_fixtures.create_mock_user(passenger_id, "PASSENGER", "Test Passenger")
        
        # Mock database responses
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = bus
        
        # Connect users
        driver_session = socketio_manager_mock.sio.add_session(f"session_{driver_id}")
        passenger_session = socketio_manager_mock.sio.add_session(f"session_{passenger_id}")
        
        await socketio_manager_mock.connect_user(f"session_{driver_id}", driver_id)
        await socketio_manager_mock.connect_user(f"session_{passenger_id}", passenger_id)
        
        # Subscribe passenger to bus tracking
        bus_room_id = f"bus_tracking:{bus_id}"
        route_room_id = f"route_tracking:{route_id}"
        
        await socketio_manager_mock.join_room_user(passenger_id, bus_room_id)
        await socketio_manager_mock.join_room_user(passenger_id, route_room_id)
        
        # Driver updates bus location
        new_lat, new_lng = 9.0250, 38.7550
        heading = 90.0
        speed = 35.0
        
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=new_lat,
            longitude=new_lng,
            heading=heading,
            speed=speed,
            app_state=mock_app_state
        )
        
        # Verify database was updated
        mock_app_state.mongodb.buses.update_one.assert_called_once()
        
        # Verify real-time updates were sent
        server_events = socketio_manager_mock.sio.emitted_events
        location_events = [e for e in server_events if e['event'] == 'bus_location_update']
        
        assert len(location_events) >= 2  # Should send to both bus room and route room
        
        # Verify location update content
        location_event = location_events[0]
        assert location_event['data']['bus_id'] == bus_id
        assert location_event['data']['location']['latitude'] == new_lat
        assert location_event['data']['location']['longitude'] == new_lng
        assert location_event['data']['heading'] == heading
        assert location_event['data']['speed'] == speed
    
    @pytest.mark.asyncio
    async def test_subscribe_to_all_bus_tracking(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test subscribing to all bus location updates"""
        # Create test data
        user_id = str(uuid4())
        bus1_id = str(uuid4())
        bus2_id = str(uuid4())
        
        bus1 = realtime_fixtures.create_mock_bus(bus1_id)
        bus2 = realtime_fixtures.create_mock_bus(bus2_id)
        
        # Mock database responses
        mock_app_state.mongodb.buses.find.return_value.to_list.return_value = [bus1, bus2]
        
        # Connect user
        user_session = socketio_manager_mock.sio.add_session(f"session_{user_id}")
        await socketio_manager_mock.connect_user(f"session_{user_id}", user_id)
        
        # Subscribe to all bus tracking
        result = await websocket_event_handlers.handle_subscribe_all_buses(
            user_id, {}, mock_app_state
        )
        
        assert result["success"] is True
        
        # Verify user is in all bus tracking room
        all_bus_room = "all_bus_tracking"
        assert user_id in socketio_manager_mock.rooms.get(all_bus_room, set())
        
        # Verify all bus locations were broadcast
        server_events = socketio_manager_mock.sio.emitted_events
        all_locations_events = [e for e in server_events if e['event'] == 'all_bus_locations']
        
        assert len(all_locations_events) > 0
        
        locations_event = all_locations_events[0]
        assert len(locations_event['data']['buses']) == 2
        assert any(bus['bus_id'] == bus1_id for bus in locations_event['data']['buses'])
        assert any(bus['bus_id'] == bus2_id for bus in locations_event['data']['buses'])
    
    @pytest.mark.asyncio
    async def test_get_route_with_live_buses(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test getting route shape with current bus positions for Mapbox"""
        # Create test data
        route_id = str(uuid4())
        bus1_id = str(uuid4())
        bus2_id = str(uuid4())
        user_id = str(uuid4())
        
        route = realtime_fixtures.create_mock_route(route_id, "Test Route")
        bus1 = realtime_fixtures.create_mock_bus(bus1_id, route_id)
        bus2 = realtime_fixtures.create_mock_bus(bus2_id, route_id)
        
        # Mock database responses
        mock_app_state.mongodb.routes.find_one.return_value = route
        mock_app_state.mongodb.buses.find.return_value.to_list.return_value = [bus1, bus2]
        
        # Get route with live buses
        result = await websocket_event_handlers.handle_get_route_with_buses(
            user_id, route_id, mock_app_state
        )
        
        assert result["success"] is True
        
        route_data = result["route_data"]
        assert route_data["route_id"] == route_id
        assert route_data["route_name"] == "Test Route"
        assert "route_shape" in route_data  # GeoJSON for Mapbox
        assert len(route_data["active_buses"]) == 2
        
        # Verify bus position data
        bus_positions = route_data["active_buses"]
        bus_ids = [bus["bus_id"] for bus in bus_positions]
        assert bus1_id in bus_ids
        assert bus2_id in bus_ids
        
        # Verify each bus has required location data
        for bus_pos in bus_positions:
            assert "location" in bus_pos
            assert "latitude" in bus_pos["location"]
            assert "longitude" in bus_pos["location"]
            assert "heading" in bus_pos
            assert "speed" in bus_pos
    
    @pytest.mark.asyncio
    async def test_eta_calculation(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test ETA calculation for bus to reach specific stop"""
        # Create test data
        bus_id = str(uuid4())
        stop_id = str(uuid4())
        route_id = str(uuid4())
        user_id = str(uuid4())
        
        bus = realtime_fixtures.create_mock_bus(bus_id, route_id)
        bus_stop = realtime_fixtures.create_mock_bus_stop(stop_id, "Target Stop")
        route = realtime_fixtures.create_mock_route(route_id, "Test Route")
        
        # Set bus stop location slightly different from bus location for distance calculation
        bus_stop["location"] = {"latitude": 9.0220, "longitude": 38.7540}
        
        # Mock database responses
        mock_app_state.mongodb.buses.find_one.return_value = bus
        mock_app_state.mongodb.bus_stops.find_one.return_value = bus_stop
        mock_app_state.mongodb.routes.find_one.return_value = route
        
        # Calculate ETA
        result = await websocket_event_handlers.handle_calculate_eta(
            user_id, bus_id, stop_id, mock_app_state
        )
        
        assert result["success"] is True
        
        eta_data = result["eta_data"]
        assert eta_data["bus_id"] == bus_id
        assert eta_data["target_stop_id"] == stop_id
        assert "eta_minutes" in eta_data
        assert "distance_km" in eta_data
        assert "current_speed_kmh" in eta_data
        assert eta_data["eta_minutes"] > 0
        assert eta_data["distance_km"] > 0
    
    @pytest.mark.asyncio
    async def test_bus_subscription_management(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test subscribing and unsubscribing from specific bus tracking"""
        # Create test data
        user_id = str(uuid4())
        bus_id = str(uuid4())
        
        # Connect user
        user_session = socketio_manager_mock.sio.add_session(f"session_{user_id}")
        await socketio_manager_mock.connect_user(f"session_{user_id}", user_id)
        
        # Subscribe to bus tracking
        await bus_tracking_service.subscribe_to_bus(user_id, bus_id)
        
        # Verify user is in bus tracking room
        bus_room_id = f"bus_tracking:{bus_id}"
        assert user_id in socketio_manager_mock.rooms.get(bus_room_id, set())
        
        # Verify subscription confirmation was sent
        user_session = socketio_manager_mock.sio.sessions[f"session_{user_id}"]
        subscription_events = user_session.get_events_by_name('bus_tracking_subscribed')
        assert len(subscription_events) > 0
        
        subscription_event = subscription_events[0]
        assert subscription_event['data']['bus_id'] == bus_id
        
        # Unsubscribe from bus tracking
        await bus_tracking_service.unsubscribe_from_bus(user_id, bus_id)
        
        # Verify user is no longer in bus tracking room
        assert user_id not in socketio_manager_mock.rooms.get(bus_room_id, set())
    
    @pytest.mark.asyncio
    async def test_route_subscription_management(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test subscribing and unsubscribing from route tracking"""
        # Create test data
        user_id = str(uuid4())
        route_id = str(uuid4())
        
        # Connect user
        user_session = socketio_manager_mock.sio.add_session(f"session_{user_id}")
        await socketio_manager_mock.connect_user(f"session_{user_id}", user_id)
        
        # Subscribe to route tracking
        await bus_tracking_service.subscribe_to_route(user_id, route_id)
        
        # Verify user is in route tracking room
        route_room_id = f"route_tracking:{route_id}"
        assert user_id in socketio_manager_mock.rooms.get(route_room_id, set())
        
        # Verify subscription confirmation was sent
        user_session = socketio_manager_mock.sio.sessions[f"session_{user_id}"]
        subscription_events = user_session.get_events_by_name('route_tracking_subscribed')
        assert len(subscription_events) > 0
        
        subscription_event = subscription_events[0]
        assert subscription_event['data']['route_id'] == route_id
        
        # Unsubscribe from route tracking
        await bus_tracking_service.unsubscribe_from_route(user_id, route_id)
        
        # Verify user is no longer in route tracking room
        assert user_id not in socketio_manager_mock.rooms.get(route_room_id, set())
    
    @pytest.mark.asyncio
    async def test_broadcast_all_bus_locations(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test broadcasting all active bus locations for map display"""
        # Create test data
        bus1_id = str(uuid4())
        bus2_id = str(uuid4())
        bus3_id = str(uuid4())  # Inactive bus
        
        bus1 = realtime_fixtures.create_mock_bus(bus1_id)
        bus2 = realtime_fixtures.create_mock_bus(bus2_id)
        bus3 = realtime_fixtures.create_mock_bus(bus3_id)
        bus3["status"] = "INACTIVE"  # This bus should not be included
        
        # Mock database responses - only return active buses
        mock_app_state.mongodb.buses.find.return_value.to_list.return_value = [bus1, bus2]
        
        # Broadcast all bus locations
        await bus_tracking_service.broadcast_all_bus_locations(mock_app_state)
        
        # Verify broadcast was sent
        server_events = socketio_manager_mock.sio.emitted_events
        broadcast_events = [e for e in server_events if e['event'] == 'all_bus_locations']
        
        assert len(broadcast_events) > 0
        
        broadcast_event = broadcast_events[0]
        buses = broadcast_event['data']['buses']
        
        # Should only include active buses
        assert len(buses) == 2
        bus_ids = [bus['bus_id'] for bus in buses]
        assert bus1_id in bus_ids
        assert bus2_id in bus_ids
        assert bus3_id not in bus_ids  # Inactive bus should not be included
        
        # Verify each bus has required data for map display
        for bus in buses:
            assert 'bus_id' in bus
            assert 'license_plate' in bus
            assert 'location' in bus
            assert 'latitude' in bus['location']
            assert 'longitude' in bus['location']
            assert 'heading' in bus
            assert 'speed' in bus
            assert 'status' in bus
    
    @pytest.mark.asyncio
    async def test_bus_location_update_triggers_proximity_check(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test that bus location updates trigger proximity alert checks"""
        # Create test data
        bus_id = str(uuid4())
        bus_stop_id = str(uuid4())
        user_id = str(uuid4())
        
        bus = realtime_fixtures.create_mock_bus(bus_id)
        bus_stop = realtime_fixtures.create_mock_bus_stop(bus_stop_id, "Test Stop")
        
        # Mock database responses
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.buses.find_one.return_value = bus
        mock_app_state.mongodb.bus_stops.find.return_value.to_list.return_value = [bus_stop]
        
        # Connect user and subscribe to proximity alerts
        user_session = socketio_manager_mock.sio.add_session(f"session_{user_id}")
        await socketio_manager_mock.connect_user(f"session_{user_id}", user_id)
        
        proximity_room_id = f"proximity_alerts:{bus_stop_id}"
        await socketio_manager_mock.join_room_user(user_id, proximity_room_id)
        
        # Set proximity preferences
        socketio_manager_mock.proximity_preferences[user_id] = {
            'bus_stop_id': bus_stop_id,
            'radius_meters': 200,
            'subscribed_at': datetime.now(timezone.utc)
        }
        
        # Update bus location near the stop
        near_lat, near_lng = 9.0205, 38.7535  # Close to bus stop
        
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=near_lat,
            longitude=near_lng,
            heading=45.0,
            speed=20.0,
            app_state=mock_app_state
        )
        
        # Verify proximity alert was triggered
        user_session = socketio_manager_mock.sio.sessions[f"session_{user_id}"]
        proximity_events = user_session.get_events_by_name('proximity_alert')
        
        assert len(proximity_events) > 0
        
        proximity_event = proximity_events[0]
        assert proximity_event['data']['bus_id'] == bus_id
        assert proximity_event['data']['bus_stop_id'] == bus_stop_id
