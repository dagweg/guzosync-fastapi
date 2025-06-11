"""
Integration tests for Socket.IO real-time functionality
Tests all three main features working together:
1. Basic messaging between roles
2. Notification system with proximity alerts
3. Real-time bus tracking with Mapbox integration
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from core.realtime.bus_tracking import bus_tracking_service
from core.realtime.chat import chat_service
from core.realtime.notifications import notification_service
from core.realtime.socketio_events import websocket_event_handlers
from tests.realtime.conftest import RealtimeTestFixtures


class TestSocketIOIntegration:
    """Integration tests for complete Socket.IO real-time workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_bus_tracking_workflow(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test complete bus tracking workflow with messaging and notifications"""
        # Create test scenario: Driver, Control Staff, and Passengers
        driver_id = str(uuid4())
        control_id = str(uuid4())
        passenger1_id = str(uuid4())
        passenger2_id = str(uuid4())
        
        bus_id = str(uuid4())
        route_id = str(uuid4())
        bus_stop_id = str(uuid4())
        
        # Create test data
        driver = realtime_fixtures.create_mock_user(driver_id, "BUS_DRIVER", "John Driver")
        control = realtime_fixtures.create_mock_user(control_id, "CONTROL_STAFF", "Jane Controller")
        passenger1 = realtime_fixtures.create_mock_user(passenger1_id, "PASSENGER", "Alice Passenger")
        passenger2 = realtime_fixtures.create_mock_user(passenger2_id, "PASSENGER", "Bob Passenger")
        
        bus = realtime_fixtures.create_mock_bus(bus_id, route_id)
        route = realtime_fixtures.create_mock_route(route_id, "Main Route")
        bus_stop = realtime_fixtures.create_mock_bus_stop(bus_stop_id, "Central Station")
        
        # Mock database responses
        mock_app_state.mongodb.users.find_one.side_effect = lambda query: {
            driver_id: driver,
            control_id: control,
            passenger1_id: passenger1,
            passenger2_id: passenger2
        }.get(query.get("id"))
        
        mock_app_state.mongodb.buses.find_one.return_value = bus
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        mock_app_state.mongodb.routes.find_one.return_value = route
        mock_app_state.mongodb.bus_stops.find.return_value.to_list.return_value = [bus_stop]
        mock_app_state.mongodb.bus_stops.find_one.return_value = bus_stop
        
        # Connect all users to Socket.IO
        driver_session = socketio_manager_mock.sio.add_session(f"session_{driver_id}")
        control_session = socketio_manager_mock.sio.add_session(f"session_{control_id}")
        passenger1_session = socketio_manager_mock.sio.add_session(f"session_{passenger1_id}")
        passenger2_session = socketio_manager_mock.sio.add_session(f"session_{passenger2_id}")
        
        await socketio_manager_mock.connect_user(f"session_{driver_id}", driver_id)
        await socketio_manager_mock.connect_user(f"session_{control_id}", control_id)
        await socketio_manager_mock.connect_user(f"session_{passenger1_id}", passenger1_id)
        await socketio_manager_mock.connect_user(f"session_{passenger2_id}", passenger2_id)
        
        # Step 1: Passengers subscribe to bus tracking and proximity alerts
        await bus_tracking_service.subscribe_to_bus(passenger1_id, bus_id)
        await bus_tracking_service.subscribe_to_route(passenger2_id, route_id)
        
        # Subscribe to proximity alerts
        proximity_room_id = f"proximity_alerts:{bus_stop_id}"
        await socketio_manager_mock.join_room_user(passenger1_id, proximity_room_id)
        await socketio_manager_mock.join_room_user(passenger2_id, proximity_room_id)
        
        socketio_manager_mock.proximity_preferences[passenger1_id] = {
            'bus_stop_id': bus_stop_id,
            'radius_meters': 100,
            'subscribed_at': datetime.now(timezone.utc)
        }
        socketio_manager_mock.proximity_preferences[passenger2_id] = {
            'bus_stop_id': bus_stop_id,
            'radius_meters': 150,
            'subscribed_at': datetime.now(timezone.utc)
        }
        
        # Step 2: Driver updates bus location (approaching bus stop)
        approaching_lat, approaching_lng = 9.0195, 38.7528  # Close to bus stop
        
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=approaching_lat,
            longitude=approaching_lng,
            heading=90.0,
            speed=25.0,
            app_state=mock_app_state
        )
        
        # Verify bus location updates were sent
        server_events = socketio_manager_mock.sio.emitted_events
        location_events = [e for e in server_events if e['event'] == 'bus_location_update']
        assert len(location_events) >= 2  # Bus room and route room
        
        # Verify proximity alerts were triggered
        passenger1_session = socketio_manager_mock.sio.sessions[f"session_{passenger1_id}"]
        passenger2_session = socketio_manager_mock.sio.sessions[f"session_{passenger2_id}"]
        
        proximity_events_p1 = passenger1_session.get_events_by_name('proximity_alert')
        proximity_events_p2 = passenger2_session.get_events_by_name('proximity_alert')
        
        assert len(proximity_events_p1) > 0
        assert len(proximity_events_p2) > 0
        
        # Step 3: Driver sends message to control staff about delay
        conversation_id = str(uuid4())
        message_id = str(uuid4())
        
        mock_app_state.mongodb.conversations.find_one.return_value = None
        mock_app_state.mongodb.conversations.insert_one.return_value = MagicMock(inserted_id=conversation_id)
        mock_app_state.mongodb.messages.insert_one.return_value = MagicMock(inserted_id=message_id)
        
        delay_message = "Traffic jam ahead, will be 10 minutes late"
        
        await chat_service.send_real_time_message(
            conversation_id=conversation_id,
            sender_id=driver_id,
            content=delay_message,
            message_id=message_id,
            message_type="TEXT",
            app_state=mock_app_state
        )
        
        # Verify message was sent
        message_events = [e for e in server_events if e['event'] == 'new_message']
        assert len(message_events) > 0
        
        # Step 4: Control staff broadcasts delay notification to passengers
        mock_app_state.mongodb.users.find.return_value.to_list.return_value = [passenger1, passenger2]
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        await notification_service.broadcast_notification(
            title="Bus Delay Alert",
            message=f"Bus {bus['license_plate']} on {route['name']} is delayed by 10 minutes due to traffic",
            notification_type="DELAY_ALERT",
            target_roles=["PASSENGER"],
            related_entity={
                "entity_type": "bus_delay",
                "bus_id": bus_id,
                "route_id": route_id,
                "delay_minutes": 10
            },
            app_state=mock_app_state
        )
        
        # Verify delay notifications were sent
        notification_events = [e for e in server_events if e['event'] == 'notification']
        assert len(notification_events) >= 2  # Should send to both passengers
        
        # Step 5: Calculate and verify ETA
        eta_result = await websocket_event_handlers.handle_calculate_eta(
            passenger1_id, bus_id, bus_stop_id, mock_app_state
        )
        
        assert eta_result["success"] is True
        assert "eta_minutes" in eta_result["eta_data"]
        assert eta_result["eta_data"]["eta_minutes"] > 0
        
        # Verify all components worked together
        assert len(socketio_manager_mock.user_connections) == 4  # All users connected
        assert len(socketio_manager_mock.rooms) >= 4  # Multiple rooms active
    
    @pytest.mark.asyncio
    async def test_emergency_scenario_workflow(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test emergency scenario with messaging, notifications, and tracking"""
        # Create emergency scenario: Driver breakdown, control response, passenger notifications
        driver_id = str(uuid4())
        control1_id = str(uuid4())
        control2_id = str(uuid4())
        passenger_id = str(uuid4())
        
        bus_id = str(uuid4())
        route_id = str(uuid4())
        
        # Create test data
        driver = realtime_fixtures.create_mock_user(driver_id, "BUS_DRIVER", "Emergency Driver")
        control1 = realtime_fixtures.create_mock_user(control1_id, "CONTROL_STAFF", "Control 1")
        control2 = realtime_fixtures.create_mock_user(control2_id, "ADMIN", "Admin 1")
        passenger = realtime_fixtures.create_mock_user(passenger_id, "PASSENGER", "Affected Passenger")
        
        bus = realtime_fixtures.create_mock_bus(bus_id, route_id)
        route = realtime_fixtures.create_mock_route(route_id, "Emergency Route")
        
        # Mock database responses
        mock_app_state.mongodb.users.find_one.side_effect = lambda query: {
            driver_id: driver,
            control1_id: control1,
            control2_id: control2,
            passenger_id: passenger
        }.get(query.get("id"))
        
        mock_app_state.mongodb.users.find.return_value.to_list.side_effect = [
            [control1, control2],  # For emergency alert
            [passenger]  # For passenger notification
        ]
        
        mock_app_state.mongodb.buses.find_one.return_value = bus
        mock_app_state.mongodb.notifications.insert_many.return_value = MagicMock()
        
        # Connect all users
        driver_session = socketio_manager_mock.sio.add_session(f"session_{driver_id}")
        control1_session = socketio_manager_mock.sio.add_session(f"session_{control1_id}")
        control2_session = socketio_manager_mock.sio.add_session(f"session_{control2_id}")
        passenger_session = socketio_manager_mock.sio.add_session(f"session_{passenger_id}")
        
        await socketio_manager_mock.connect_user(f"session_{driver_id}", driver_id)
        await socketio_manager_mock.connect_user(f"session_{control1_id}", control1_id)
        await socketio_manager_mock.connect_user(f"session_{control2_id}", control2_id)
        await socketio_manager_mock.connect_user(f"session_{passenger_id}", passenger_id)
        
        # Subscribe control staff to emergency alerts
        await socketio_manager_mock.join_room_user(control1_id, "emergency_alerts")
        await socketio_manager_mock.join_room_user(control2_id, "emergency_alerts")
        
        # Step 1: Driver sends emergency alert
        emergency_result = await websocket_event_handlers.handle_emergency_alert(
            driver_id,
            {
                "alert_type": "VEHICLE_BREAKDOWN",
                "message": "Engine failure, bus stopped on Main Street",
                "location": {"latitude": 9.0192, "longitude": 38.7525}
            },
            mock_app_state
        )
        
        assert emergency_result["success"] is True
        
        # Verify emergency alerts were sent
        server_events = socketio_manager_mock.sio.emitted_events
        emergency_events = [e for e in server_events if e['event'] == 'emergency_alert']
        assert len(emergency_events) > 0
        
        # Step 2: Control staff broadcasts service disruption to passengers
        await notification_service.broadcast_notification(
            title="🚨 Service Disruption",
            message=f"Bus service on {route['name']} is temporarily suspended due to vehicle breakdown. Alternative arrangements are being made.",
            notification_type="SERVICE_DISRUPTION",
            target_roles=["PASSENGER"],
            related_entity={
                "entity_type": "service_disruption",
                "route_id": route_id,
                "bus_id": bus_id,
                "reason": "vehicle_breakdown"
            },
            app_state=mock_app_state
        )
        
        # Verify service disruption notifications
        notification_events = [e for e in server_events if e['event'] == 'notification']
        assert len(notification_events) > 0
        
        # Step 3: Update bus status to inactive
        bus["status"] = "INACTIVE"
        mock_app_state.mongodb.buses.update_one.return_value = MagicMock()
        
        await bus_tracking_service.update_bus_location(
            bus_id=bus_id,
            latitude=9.0192,
            longitude=38.7525,
            heading=0.0,
            speed=0.0,
            app_state=mock_app_state
        )
        
        # Verify the emergency workflow completed successfully
        assert len(socketio_manager_mock.user_connections) == 4
        assert "emergency_alerts" in socketio_manager_mock.rooms
        assert len(socketio_manager_mock.rooms["emergency_alerts"]) == 2  # Both control staff
    
    @pytest.mark.asyncio
    async def test_multi_user_conversation_with_notifications(self, socketio_manager_mock, mock_app_state, realtime_fixtures):
        """Test multi-user conversation with real-time notifications"""
        # Create group conversation scenario
        admin_id = str(uuid4())
        driver1_id = str(uuid4())
        driver2_id = str(uuid4())
        regulator_id = str(uuid4())
        
        conversation_id = str(uuid4())
        
        # Create test users
        admin = realtime_fixtures.create_mock_user(admin_id, "ADMIN", "System Admin")
        driver1 = realtime_fixtures.create_mock_user(driver1_id, "BUS_DRIVER", "Driver Alpha")
        driver2 = realtime_fixtures.create_mock_user(driver2_id, "BUS_DRIVER", "Driver Beta")
        regulator = realtime_fixtures.create_mock_user(regulator_id, "QUEUE_REGULATOR", "Regulator One")
        
        # Mock conversation
        mock_conversation = {
            "id": conversation_id,
            "type": "GROUP",
            "participants": [admin_id, driver1_id, driver2_id, regulator_id],
            "name": "Daily Operations Chat"
        }
        
        mock_app_state.mongodb.conversations.find_one.return_value = mock_conversation
        mock_app_state.mongodb.messages.insert_one.return_value = MagicMock(inserted_id=str(uuid4()))
        
        # Connect all users
        admin_session = socketio_manager_mock.sio.add_session(f"session_{admin_id}")
        driver1_session = socketio_manager_mock.sio.add_session(f"session_{driver1_id}")
        driver2_session = socketio_manager_mock.sio.add_session(f"session_{driver2_id}")
        regulator_session = socketio_manager_mock.sio.add_session(f"session_{regulator_id}")
        
        await socketio_manager_mock.connect_user(f"session_{admin_id}", admin_id)
        await socketio_manager_mock.connect_user(f"session_{driver1_id}", driver1_id)
        await socketio_manager_mock.connect_user(f"session_{driver2_id}", driver2_id)
        await socketio_manager_mock.connect_user(f"session_{regulator_id}", regulator_id)
        
        # All users join the conversation room
        conversation_room = f"conversation:{conversation_id}"
        await socketio_manager_mock.join_room_user(admin_id, conversation_room)
        await socketio_manager_mock.join_room_user(driver1_id, conversation_room)
        await socketio_manager_mock.join_room_user(driver2_id, conversation_room)
        await socketio_manager_mock.join_room_user(regulator_id, conversation_room)
        
        # Admin sends message to group
        message_content = "Good morning team! Please report your status for today's operations."
        
        await chat_service.send_real_time_message(
            conversation_id=conversation_id,
            sender_id=admin_id,
            content=message_content,
            message_id=str(uuid4()),
            message_type="TEXT",
            app_state=mock_app_state
        )
        
        # Verify message was broadcast to all participants
        server_events = socketio_manager_mock.sio.emitted_events
        message_events = [e for e in server_events if e['event'] == 'new_message']
        assert len(message_events) > 0
        
        # Test typing indicators
        await chat_service.notify_typing(conversation_id, driver1_id, True)
        
        typing_events = [e for e in server_events if e['event'] == 'typing_status']
        assert len(typing_events) > 0
        
        typing_event = typing_events[0]
        assert typing_event['data']['user_id'] == driver1_id
        assert typing_event['data']['is_typing'] is True
        
        # Verify all users are in the conversation room
        assert len(socketio_manager_mock.rooms[conversation_room]) == 4
