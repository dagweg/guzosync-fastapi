"""
Tests for Socket.IO notification features including proximity alerts
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from core.realtime.notifications import notification_service
from core.socketio_manager import socketio_manager
from tests.realtime.conftest import RealtimeTestFixtures


class TestSocketIONotifications:
    """Test cases for Socket.IO notification functionality"""
    
    @pytest.mark.asyncio
    async def test_proximity_alert_subscription(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test subscribing to proximity alerts for bus stops"""
        # Create test user and bus stop
        user_id = str(uuid4())
        bus_stop_id = str(uuid4())
        
        user = realtime_fixtures.create_mock_user(user_id, "PASSENGER", "Test Passenger")
        bus_stop = realtime_fixtures.create_mock_bus_stop(bus_stop_id, "Main Station")
        
        # Connect user to Socket.IO
        user_session = socketio_manager_mock.sio.add_session(f"session_{user_id}")
        await socketio_manager_mock.connect_user(f"session_{user_id}", user_id)
        
        # Subscribe to proximity alerts
        data = {
            'bus_stop_id': bus_stop_id,
            'radius_meters': 150
        }
        
        # Simulate the subscribe_proximity_alerts event
        room_id = f"proximity_alerts:{bus_stop_id}"
        await socketio_manager_mock.join_room_user(user_id, room_id)
        
        # Store proximity preferences
        socketio_manager_mock.proximity_preferences[user_id] = {
            'bus_stop_id': bus_stop_id,
            'radius_meters': 150,
            'subscribed_at': datetime.now(timezone.utc)
        }
        
        # Verify user is in proximity alerts room
        assert user_id in socketio_manager_mock.rooms.get(room_id, set())
        
        # Verify proximity preferences are stored
        assert user_id in socketio_manager_mock.proximity_preferences
        assert socketio_manager_mock.proximity_preferences[user_id]['bus_stop_id'] == bus_stop_id
        assert socketio_manager_mock.proximity_preferences[user_id]['radius_meters'] == 150
    
    @pytest.mark.asyncio
    async def test_proximity_alert_triggered(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test proximity alert triggered when bus approaches stop"""
        # Create test data
        user_id = str(uuid4())
        bus_id = str(uuid4())
        bus_stop_id = str(uuid4())
        
        user = realtime_fixtures.create_mock_user(user_id, "PASSENGER", "Test Passenger")
        bus = realtime_fixtures.create_mock_bus(bus_id)
        bus_stop = realtime_fixtures.create_mock_bus_stop(bus_stop_id, "Main Station")
        
        # Mock database responses
        mock_app_state.mongodb.bus_stops.find.return_value.to_list.return_value = [bus_stop]
        
        # Connect user and subscribe to proximity alerts
        user_session = socketio_manager_mock.sio.add_session(f"session_{user_id}")
        await socketio_manager_mock.connect_user(f"session_{user_id}", user_id)
        
        room_id = f"proximity_alerts:{bus_stop_id}"
        await socketio_manager_mock.join_room_user(user_id, room_id)
        
        # Set proximity preferences
        socketio_manager_mock.proximity_preferences[user_id] = {
            'bus_stop_id': bus_stop_id,
            'radius_meters': 100,
            'subscribed_at': datetime.now(timezone.utc)
        }
        
        # Simulate bus approaching the stop (within 100m)
        bus_lat, bus_lng = 9.0195, 38.7528  # Close to bus stop location
        
        # Trigger proximity check
        await socketio_manager_mock._check_proximity_alerts(bus_id, bus_lat, bus_lng)
        
        # Verify proximity alert was sent
        user_session = socketio_manager_mock.sio.sessions[f"session_{user_id}"]
        proximity_events = user_session.get_events_by_name('proximity_alert')
        
        assert len(proximity_events) > 0
        
        alert_event = proximity_events[0]
        assert alert_event['data']['bus_id'] == bus_id
        assert alert_event['data']['bus_stop_id'] == bus_stop_id
        assert alert_event['data']['distance_meters'] <= 100
        assert 'estimated_arrival_minutes' in alert_event['data']
    
    @pytest.mark.asyncio
    async def test_proximity_alert_not_triggered_when_far(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test proximity alert not triggered when bus is far from stop"""
        # Create test data
        user_id = str(uuid4())
        bus_id = str(uuid4())
        bus_stop_id = str(uuid4())
        
        bus_stop = realtime_fixtures.create_mock_bus_stop(bus_stop_id, "Main Station")
        
        # Mock database responses
        mock_app_state.mongodb.bus_stops.find.return_value.to_list.return_value = [bus_stop]
        
        # Connect user and subscribe to proximity alerts
        user_session = socketio_manager_mock.sio.add_session(f"session_{user_id}")
        await socketio_manager_mock.connect_user(f"session_{user_id}", user_id)
        
        room_id = f"proximity_alerts:{bus_stop_id}"
        await socketio_manager_mock.join_room_user(user_id, room_id)
        
        # Set proximity preferences with small radius
        socketio_manager_mock.proximity_preferences[user_id] = {
            'bus_stop_id': bus_stop_id,
            'radius_meters': 50,  # Small radius
            'subscribed_at': datetime.now(timezone.utc)
        }
        
        # Simulate bus far from the stop (more than 50m away)
        bus_lat, bus_lng = 9.0300, 38.7600  # Far from bus stop location
        
        # Trigger proximity check
        await socketio_manager_mock._check_proximity_alerts(bus_id, bus_lat, bus_lng)
        
        # Verify no proximity alert was sent
        user_session = socketio_manager_mock.sio.sessions[f"session_{user_id}"]
        proximity_events = user_session.get_events_by_name('proximity_alert')
        
        assert len(proximity_events) == 0
    
    @pytest.mark.asyncio
    async def test_general_notification_broadcast(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test broadcasting general notifications to users"""
        # Create test users
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        user3_id = str(uuid4())
        
        user1 = realtime_fixtures.create_mock_user(user1_id, "BUS_DRIVER", "Driver 1")
        user2 = realtime_fixtures.create_mock_user(user2_id, "BUS_DRIVER", "Driver 2")
        user3 = realtime_fixtures.create_mock_user(user3_id, "PASSENGER", "Passenger 1")
        
        # Mock database responses
        mock_app_state.mongodb.users.find.return_value.to_list.return_value = [user1, user2]
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        # Connect users
        user1_session = socketio_manager_mock.sio.add_session(f"session_{user1_id}")
        user2_session = socketio_manager_mock.sio.add_session(f"session_{user2_id}")
        user3_session = socketio_manager_mock.sio.add_session(f"session_{user3_id}")
        
        await socketio_manager_mock.connect_user(f"session_{user1_id}", user1_id)
        await socketio_manager_mock.connect_user(f"session_{user2_id}", user2_id)
        await socketio_manager_mock.connect_user(f"session_{user3_id}", user3_id)
        
        # Broadcast notification to drivers only
        await notification_service.broadcast_notification(
            title="Route Update",
            message="Route A has been modified due to road construction",
            notification_type="ROUTE_UPDATE",
            target_roles=["BUS_DRIVER"],
            app_state=mock_app_state
        )
        
        # Verify notifications were saved to database
        mock_app_state.mongodb.notifications.insert_many.assert_called_once()
        
        # Verify real-time notifications were sent to drivers
        server_events = socketio_manager_mock.sio.emitted_events
        notification_events = [e for e in server_events if e['event'] == 'notification']
        
        # Should send to both drivers but not passenger
        assert len(notification_events) >= 2
        
        # Verify notification content
        notification_event = notification_events[0]
        assert notification_event['data']['notification']['title'] == "Route Update"
        assert notification_event['data']['notification']['notification_type'] == "ROUTE_UPDATE"
    
    @pytest.mark.asyncio
    async def test_trip_update_notification(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test trip update notifications with delay information"""
        # Create test data
        trip_id = str(uuid4())
        route_id = str(uuid4())
        bus_id = str(uuid4())
        passenger1_id = str(uuid4())
        passenger2_id = str(uuid4())
        
        # Mock trip data
        mock_trip = {
            "id": trip_id,
            "route_id": route_id,
            "bus_id": bus_id,
            "participants": [passenger1_id, passenger2_id]
        }
        
        mock_app_state.mongodb.trips.find_one.return_value = mock_trip
        
        # Connect passengers
        passenger1_session = socketio_manager_mock.sio.add_session(f"session_{passenger1_id}")
        passenger2_session = socketio_manager_mock.sio.add_session(f"session_{passenger2_id}")
        
        await socketio_manager_mock.connect_user(f"session_{passenger1_id}", passenger1_id)
        await socketio_manager_mock.connect_user(f"session_{passenger2_id}", passenger2_id)
        
        # Subscribe passengers to trip tracking
        trip_room_id = f"trip_tracking:{trip_id}"
        route_room_id = f"route_tracking:{route_id}"
        
        await socketio_manager_mock.join_room_user(passenger1_id, trip_room_id)
        await socketio_manager_mock.join_room_user(passenger2_id, route_room_id)
        
        # Send trip update notification
        delay_minutes = 15
        message = f"Trip delayed by {delay_minutes} minutes due to traffic"
        
        await notification_service.send_trip_update_notification(
            trip_id=trip_id,
            message=message,
            delay_minutes=delay_minutes,
            app_state=mock_app_state
        )
        
        # Verify trip notifications were sent
        server_events = socketio_manager_mock.sio.emitted_events
        trip_events = [e for e in server_events if e['event'] == 'trip_notification']
        
        assert len(trip_events) >= 2  # Should send to trip room and route room
        
        # Verify notification content
        trip_event = trip_events[0]
        assert trip_event['data']['notification']['notification_type'] == "TRIP_UPDATE"
        assert trip_event['data']['notification']['related_entity']['delay_minutes'] == delay_minutes
        assert message in trip_event['data']['notification']['message']
    
    @pytest.mark.asyncio
    async def test_personal_notification(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test sending personal notifications to specific users"""
        # Create test user
        user_id = str(uuid4())
        user = realtime_fixtures.create_mock_user(user_id, "PASSENGER", "Test User")
        
        # Mock database
        mock_app_state.mongodb.notifications.insert_one.return_value = MagicMock(inserted_id=str(uuid4()))
        
        # Connect user
        user_session = socketio_manager_mock.sio.add_session(f"session_{user_id}")
        await socketio_manager_mock.connect_user(f"session_{user_id}", user_id)
        
        # Send personal notification
        await notification_service.send_real_time_notification(
            user_id=user_id,
            title="Payment Reminder",
            message="Your monthly pass expires in 3 days",
            notification_type="PAYMENT_REMINDER",
            related_entity={"entity_type": "payment", "days_remaining": 3},
            app_state=mock_app_state
        )
        
        # Verify notification was saved to database
        mock_app_state.mongodb.notifications.insert_one.assert_called_once()
        
        # Verify real-time notification was sent
        server_events = socketio_manager_mock.sio.emitted_events
        notification_events = [e for e in server_events if e['event'] == 'notification']
        
        assert len(notification_events) == 1
        
        notification_event = notification_events[0]
        assert notification_event['data']['notification']['title'] == "Payment Reminder"
        assert notification_event['data']['notification']['notification_type'] == "PAYMENT_REMINDER"
        assert notification_event['data']['notification']['related_entity']['days_remaining'] == 3
    
    @pytest.mark.asyncio
    async def test_multiple_proximity_subscriptions(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test user subscribing to multiple bus stop proximity alerts"""
        # Create test user and multiple bus stops
        user_id = str(uuid4())
        bus_stop1_id = str(uuid4())
        bus_stop2_id = str(uuid4())
        
        bus_stop1 = realtime_fixtures.create_mock_bus_stop(bus_stop1_id, "Stop 1")
        bus_stop2 = realtime_fixtures.create_mock_bus_stop(bus_stop2_id, "Stop 2")
        
        # Connect user
        user_session = socketio_manager_mock.sio.add_session(f"session_{user_id}")
        await socketio_manager_mock.connect_user(f"session_{user_id}", user_id)
        
        # Subscribe to multiple proximity alerts
        room1_id = f"proximity_alerts:{bus_stop1_id}"
        room2_id = f"proximity_alerts:{bus_stop2_id}"
        
        await socketio_manager_mock.join_room_user(user_id, room1_id)
        await socketio_manager_mock.join_room_user(user_id, room2_id)
        
        # Verify user is in both rooms
        assert user_id in socketio_manager_mock.rooms.get(room1_id, set())
        assert user_id in socketio_manager_mock.rooms.get(room2_id, set())
        
        # Verify user can leave specific proximity alerts
        await socketio_manager_mock.leave_room_user(user_id, room1_id)
        
        assert user_id not in socketio_manager_mock.rooms.get(room1_id, set())
        assert user_id in socketio_manager_mock.rooms.get(room2_id, set())  # Still in room 2
