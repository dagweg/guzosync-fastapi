#!/usr/bin/env python3
"""
Test 3 specific real-time scenarios:
1. Real-time communication between queue regulator/bus driver and control staff
2. Real-time proximity notifications for passengers near bus stops
3. Real-time bus location streaming from start to destination
"""
import asyncio
import websockets
import json
from datetime import datetime, timezone
from uuid import uuid4
import sys
import os
from typing import Dict, List, Optional, Any, Union, cast
import random

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.jwt import create_access_token
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()


class RealTimeUser:
    """Represents a real-time WebSocket user"""
    
    def __init__(self, user_data: dict, role: str):
        self.user_data = user_data
        self.role = role
        self.user_id = user_data["id"]
        self.email = user_data["email"]
        self.name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}"
        self.websocket: Any = None
        self.token = None
        self.messages_received: list[dict] = []
        self.connected = False
        self.running = False
    
    async def connect(self):
        """Connect to WebSocket"""
        try:
            # Create JWT token
            self.token = create_access_token(data={"sub": self.email})
            
            # Connect to WebSocket
            uri = f"ws://localhost:8000/ws/connect?token={self.token}"
            self.websocket = await websockets.connect(uri)
            self.connected = True
            self.running = True
            
            print(f"✅ {self.role} {self.name} connected")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            await asyncio.sleep(1)  # Wait for connection to stabilize
            
            return True
        except Exception as e:
            print(f"❌ {self.role} {self.name} connection failed: {e}")
            return False
    
    async def _listen_for_messages(self):
        """Listen for incoming messages"""
        try:
            while self.running and self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                self.messages_received.append(data)
                
                # Print important messages
                msg_type = data.get("type", "unknown")
                if msg_type in ["authenticated", "new_message", "notification", "bus_location_update", "proximity_alert"]:
                    print(f"📥 {self.role} {self.name} received: {msg_type}")
                    if msg_type == "new_message":
                        print(f"   💬 Message: {data.get('content', '')}")
                    elif msg_type == "notification":
                        print(f"   🔔 Notification: {data.get('message', '')}")
                    elif msg_type == "proximity_alert":
                        print(f"   📍 Proximity Alert: {data.get('message', '')}")
                        
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            self.running = False
        except Exception as e:
            print(f"⚠️ {self.role} {self.name} message error: {e}")
    
    async def send_message(self, message_type: str, data: Optional[dict] = None):
        """Send message to WebSocket"""
        if not self.websocket or not self.connected:
            return False
        
        try:
            message = {"type": message_type}
            if data:
                message.update(data)
            
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"❌ {self.role} {self.name} send failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        self.connected = False


class RealTimeScenarioTester:
    """Test real-time scenarios"""
    
    def __init__(self):
        self.users: Dict[str, RealTimeUser] = {}
        self.mongodb = None
        
    async def setup_database_connection(self):
        """Connect to database to get real users"""
        try:
            mongodb_url = os.getenv("MONGODB_URL")
            database_name = os.getenv("DATABASE_NAME")
            
            if not mongodb_url or not database_name:
                print("❌ Database configuration not found")
                return False
                
            client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_url, uuidRepresentation="unspecified")
            self.mongodb = client[database_name]
            
            print("✅ Connected to database")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    async def get_users_by_roles(self) -> Dict[str, List[dict]]:
        """Get users from database by roles"""
        try:
            users_by_role: dict[str, list[dict]] = {
                "CONTROL_STAFF": [],
                "BUS_DRIVER": [],
                "QUEUE_REGULATOR": [],
                "PASSENGER": []
            }
            
            # Get users from database
            if self.mongodb is not None:
                async for user in self.mongodb.users.find({"is_active": True}):
                    role = user.get("role", "PASSENGER")
                    if role in users_by_role:
                        users_by_role[role].append(user)
            
            print(f"📊 Found users: Control Staff: {len(users_by_role['CONTROL_STAFF'])}, "
                  f"Bus Drivers: {len(users_by_role['BUS_DRIVER'])}, "
                  f"Queue Regulators: {len(users_by_role['QUEUE_REGULATOR'])}, "
                  f"Passengers: {len(users_by_role['PASSENGER'])}")
            
            return users_by_role
        except Exception as e:
            print(f"❌ Error getting users: {e}")
            return {}
    
    async def setup_test_users(self):
        """Setup test users for scenarios"""
        users_by_role = await self.get_users_by_roles()
        
        # Select one user from each role
        if users_by_role["CONTROL_STAFF"]:
            control_staff = users_by_role["CONTROL_STAFF"][0]
            self.users["control_staff"] = RealTimeUser(control_staff, "CONTROL_STAFF")
        
        if users_by_role["BUS_DRIVER"]:
            bus_driver = users_by_role["BUS_DRIVER"][0]
            self.users["bus_driver"] = RealTimeUser(bus_driver, "BUS_DRIVER")
        
        if users_by_role["QUEUE_REGULATOR"]:
            queue_regulator = users_by_role["QUEUE_REGULATOR"][0]
            self.users["queue_regulator"] = RealTimeUser(queue_regulator, "QUEUE_REGULATOR")
        
        if users_by_role["PASSENGER"]:
            # Get 2 passengers for proximity testing
            passengers = users_by_role["PASSENGER"][:2]
            for i, passenger in enumerate(passengers):
                self.users[f"passenger_{i+1}"] = RealTimeUser(passenger, "PASSENGER")
        
        print(f"✅ Setup {len(self.users)} test users")
        return len(self.users) > 0
    
    async def connect_all_users(self):
        """Connect all test users to WebSocket"""
        print("\n🔗 Connecting all users to WebSocket...")
        
        connected_count = 0
        for user in self.users.values():
            if await user.connect():
                connected_count += 1
            await asyncio.sleep(0.5)  # Stagger connections
        
        print(f"✅ Connected {connected_count}/{len(self.users)} users")
        return connected_count > 0
    
    async def test_staff_communication(self):
        """Test 1: Real-time communication between staff roles"""
        print("\n" + "="*60)
        print("🧪 TEST 1: Staff Communication")
        print("Testing real-time communication between queue regulator/bus driver and control staff")
        print("="*60)
        
        control_staff = self.users.get("control_staff")
        bus_driver = self.users.get("bus_driver")
        queue_regulator = self.users.get("queue_regulator")
        
        if not all([control_staff, bus_driver, queue_regulator]):
            print("❌ Missing required staff users")
            return False
        
        # Test 1a: Queue Regulator reports to Control Staff
        print("\n📡 Scenario 1a: Queue Regulator → Control Staff")
        
        # Queue regulator joins control room
        if queue_regulator:
            await queue_regulator.send_message("join_room", {"room_id": "control_center:communications"})
        if control_staff:
            await control_staff.send_message("join_room", {"room_id": "control_center:communications"})
        await asyncio.sleep(1)

        # Queue regulator sends message to control staff
        if queue_regulator and control_staff:
            await queue_regulator.send_message("send_message", {
                "recipient_id": control_staff.user_id,
                "message": "Heavy congestion at Terminal A. Need immediate assistance.",
                "message_type": "TEXT"
            })
        
        await asyncio.sleep(2)
        
        # Test 1b: Bus Driver emergency alert to Control Staff
        print("\n📡 Scenario 1b: Bus Driver → Control Staff (Emergency)")

        if bus_driver:
            await bus_driver.send_message("emergency_alert", {
                "alert_type": "VEHICLE_ISSUE",
                "message": "Bus breakdown on Route 12. Passengers need evacuation.",
                "location": {"latitude": 9.0579, "longitude": 7.4951}
            })

        await asyncio.sleep(2)

        # Test 1c: Control Staff broadcasts to all field staff
        print("\n📡 Scenario 1c: Control Staff → All Field Staff")

        if control_staff:
            await control_staff.send_message("admin_broadcast", {
                "message": "Weather alert: Heavy rain expected. All drivers exercise caution.",
                "target_roles": ["BUS_DRIVER", "QUEUE_REGULATOR"],
                "priority": "HIGH"
            })
        
        await asyncio.sleep(3)
        
        print("✅ Staff communication test completed")
        return True
    
    async def test_proximity_notifications(self):
        """Test 2: Proximity notifications for passengers"""
        print("\n" + "="*60)
        print("🧪 TEST 2: Proximity Notifications")
        print("Testing real-time notifications when passengers are near bus stops and buses arrive")
        print("="*60)
        
        passenger1 = self.users.get("passenger_1")
        passenger2 = self.users.get("passenger_2")
        
        if not all([passenger1, passenger2]):
            print("❌ Missing passenger users")
            return False
        
        # Simulate passengers near bus stops
        bus_stop_locations = [
            {"id": "stop_001", "name": "Central Terminal", "lat": 9.0579, "lng": 7.4951},
            {"id": "stop_002", "name": "University Gate", "lat": 9.0589, "lng": 7.4961}
        ]
        
        # Test 2a: Passengers subscribe to proximity alerts
        print("\n📍 Scenario 2a: Passengers enable proximity alerts")
        
        for i, passenger in enumerate([passenger1, passenger2]):
            if passenger:
                location = bus_stop_locations[i]
                await passenger.send_message("set_proximity_preferences", {
                    "enabled": True,
                    "radius_meters": 500,
                    "current_location": {"latitude": location["lat"], "longitude": location["lng"]},
                    "interested_stops": [location["id"]]
                })
        
        await asyncio.sleep(1)
        
        # Test 2b: Simulate bus approaching bus stop
        print("\n🚌 Scenario 2b: Bus approaching bus stop")
        
        # Simulate bus location updates approaching the stop
        bus_id = "bus_001"
        route_id = "route_001"
        
        # Bus starts far from stop
        bus_locations: list[dict[str, Any]] = [
            {"lat": 9.0500, "lng": 7.4900, "distance_to_stop": 1000},  # 1km away
            {"lat": 9.0540, "lng": 7.4920, "distance_to_stop": 600},   # 600m away
            {"lat": 9.0570, "lng": 7.4940, "distance_to_stop": 200},   # 200m away - trigger alert
            {"lat": 9.0579, "lng": 7.4951, "distance_to_stop": 0}      # At stop
        ]

        for i, location in enumerate(bus_locations):
            distance_to_stop = cast(float, location['distance_to_stop'])
            print(f"   🚌 Bus update {i+1}: {distance_to_stop}m from stop")

            # Send bus location update
            await self.simulate_bus_location_update(bus_id, route_id, location)

            if distance_to_stop <= 300:  # Within 300m - should trigger proximity alert
                print(f"   📱 Proximity alert should be triggered!")
            
            await asyncio.sleep(2)
        
        await asyncio.sleep(3)
        
        print("✅ Proximity notifications test completed")
        return True
    
    async def simulate_bus_location_update(self, bus_id: str, route_id: str, location: dict):
        """Simulate a bus location update"""
        # This would normally come from a bus driver's app or GPS system
        # For testing, we'll send it directly to the bus tracking service
        
        # Send to bus tracking room
        bus_location_message = {
            "type": "bus_location_update",
            "bus_id": bus_id,
            "route_id": route_id,
            "latitude": location["lat"],
            "longitude": location["lng"],
            "heading": 45,
            "speed": 25,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "next_stop_distance": location.get("distance_to_stop", 0)
        }
        
        # Broadcast to all users subscribed to bus tracking
        for user in self.users.values():
            if user.connected:
                await user.send_message("bus_location_update", bus_location_message)

    async def test_bus_location_streaming(self):
        """Test 3: Real-time bus location streaming from start to destination"""
        print("\n" + "="*60)
        print("🧪 TEST 3: Bus Location Streaming")
        print("Testing real-time streaming of bus locations from start to destination")
        print("="*60)

        # Get all users to subscribe to bus tracking
        print("\n📡 Scenario 3a: Users subscribe to bus tracking")

        for user in self.users.values():
            if user.connected:
                await user.send_message("subscribe_all_buses", {})
                await user.send_message("join_room", {"room_id": "all_bus_tracking"})

        await asyncio.sleep(1)

        # Test 3b: Simulate complete bus journey
        print("\n🚌 Scenario 3b: Complete bus journey simulation")

        bus_id = "bus_route_12"
        route_id = "route_12"

        # Define bus stops along the route
        bus_stops = [
            {"name": "Central Terminal", "lat": 9.0579, "lng": 7.4951, "stop_id": "stop_001"},
            {"name": "Market Square", "lat": 9.0620, "lng": 7.5000, "stop_id": "stop_002"},
            {"name": "University Gate", "lat": 9.0680, "lng": 7.5080, "stop_id": "stop_003"},
            {"name": "Hospital Junction", "lat": 9.0750, "lng": 7.5150, "stop_id": "stop_004"},
            {"name": "Airport Terminal", "lat": 9.0820, "lng": 7.5220, "stop_id": "stop_005"}
        ]

        print(f"   🛣️ Route: {bus_stops[0]['name']} → {bus_stops[-1]['name']}")
        print(f"   📍 Total stops: {len(bus_stops)}")

        # Simulate bus journey with multiple location updates between stops
        for i in range(len(bus_stops) - 1):
            current_stop = bus_stops[i]
            next_stop = bus_stops[i + 1]

            print(f"\n   🚌 Traveling: {current_stop['name']} → {next_stop['name']}")

            # Generate intermediate locations between stops
            intermediate_locations = self.generate_route_points(
                current_stop, next_stop, num_points=5
            )

            for j, location in enumerate(intermediate_locations):
                # Calculate distance to next stop
                lat1 = cast(float, location["lat"])
                lng1 = cast(float, location["lng"])
                lat2 = cast(float, next_stop["lat"])
                lng2 = cast(float, next_stop["lng"])

                distance_to_next = self.calculate_distance(lat1, lng1, lat2, lng2) * 1000  # Convert to meters

                # Send bus location update
                await self.send_bus_location_update(
                    bus_id, route_id, location,
                    str(next_stop["stop_id"]), distance_to_next
                )

                print(f"     📍 Update {j+1}/5: {distance_to_next:.0f}m to {next_stop['name']}")

                # Simulate real-time delay
                await asyncio.sleep(1.5)

            # Bus arrives at stop
            print(f"     🏁 Arrived at {next_stop['name']}")
            await self.send_bus_arrival_notification(bus_id, next_stop)
            await asyncio.sleep(2)  # Stop duration

        print("\n✅ Bus location streaming test completed")
        return True

    def generate_route_points(self, start_stop: dict[str, Any], end_stop: dict[str, Any], num_points: int = 5) -> List[dict[str, Any]]:
        """Generate intermediate GPS points between two stops"""
        points = []

        lat_diff = end_stop["lat"] - start_stop["lat"]
        lng_diff = end_stop["lng"] - start_stop["lng"]

        for i in range(1, num_points + 1):
            progress = i / (num_points + 1)

            lat = start_stop["lat"] + (lat_diff * progress)
            lng = start_stop["lng"] + (lng_diff * progress)

            # Add some realistic variation
            lat += random.uniform(-0.0005, 0.0005)
            lng += random.uniform(-0.0005, 0.0005)

            points.append({
                "lat": lat,
                "lng": lng,
                "heading": self.calculate_heading(start_stop, end_stop),
                "speed": random.uniform(20, 40)  # km/h
            })

        return points

    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two GPS points (simplified)"""
        # Simplified distance calculation (not accurate for long distances)
        lat_diff = lat2 - lat1
        lng_diff = lng2 - lng1
        return (lat_diff**2 + lng_diff**2)**0.5 * 111  # Rough km conversion

    def calculate_heading(self, start: dict, end: dict) -> float:
        """Calculate heading between two points"""
        import math
        lat_diff = end["lat"] - start["lat"]
        lng_diff = end["lng"] - start["lng"]
        return math.degrees(math.atan2(lng_diff, lat_diff))

    async def send_bus_location_update(self, bus_id: str, route_id: str, location: dict,
                                     next_stop_id: str, distance_to_next: float):
        """Send bus location update to all connected users"""
        message = {
            "type": "bus_location_update",
            "bus_id": bus_id,
            "route_id": route_id,
            "latitude": location["lat"],
            "longitude": location["lng"],
            "heading": location.get("heading", 0),
            "speed": location.get("speed", 0),
            "next_stop_id": next_stop_id,
            "distance_to_next_stop": distance_to_next,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "IN_TRANSIT"
        }

        # Send to all connected users
        for user in self.users.values():
            if user.connected:
                await user.send_message("bus_location_update", message)

    async def send_bus_arrival_notification(self, bus_id: str, stop: dict):
        """Send bus arrival notification"""
        message = {
            "type": "bus_arrival",
            "bus_id": bus_id,
            "stop_id": stop["stop_id"],
            "stop_name": stop["name"],
            "latitude": stop["lat"],
            "longitude": stop["lng"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "ARRIVED"
        }

        # Send to all connected users
        for user in self.users.values():
            if user.connected:
                await user.send_message("bus_arrival", message)


async def main():
    """Run all real-time scenario tests"""
    print("🚀 Real-Time Scenario Testing Suite")
    print("="*60)
    
    tester = RealTimeScenarioTester()
    
    # Setup
    if not await tester.setup_database_connection():
        print("❌ Database setup failed")
        return
    
    if not await tester.setup_test_users():
        print("❌ User setup failed")
        return
    
    if not await tester.connect_all_users():
        print("❌ WebSocket connections failed")
        return
    
    try:
        # Run tests
        print("\n🎬 Starting real-time scenario tests...")
        
        # Test 1: Staff Communication
        await tester.test_staff_communication()
        
        # Test 2: Proximity Notifications  
        await tester.test_proximity_notifications()
        
        # Test 3: Bus Location Streaming
        await tester.test_bus_location_streaming()
        
        print("\n" + "="*60)
        print("🎉 ALL REAL-TIME SCENARIO TESTS COMPLETED!")
        print("="*60)
        
        # Summary
        total_messages = sum(len(user.messages_received) for user in tester.users.values())
        print(f"📊 Total messages exchanged: {total_messages}")
        
        for user in tester.users.values():
            print(f"   {user.role} {user.name}: {len(user.messages_received)} messages")
        
    finally:
        # Cleanup
        print("\n🧹 Cleaning up connections...")
        for user in tester.users.values():
            await user.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
