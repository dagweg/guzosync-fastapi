#!/usr/bin/env python3
"""
Test the 3 main WebSocket features: Bus Tracking, Chat, and Notifications
"""
import asyncio
import websockets
import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.jwt import create_access_token


class WebSocketFeatureTester:
    """Test WebSocket real-time features"""
    
    def __init__(self):
        self.websocket = None
        self.token = None
        self.user_id = None
        self.messages_received = []
        self.running = False
        
    async def authenticate_and_connect(self):
        """Use an existing user from the seeded database"""
        try:
            # Import here to avoid circular imports
            from motor.motor_asyncio import AsyncIOMotorClient
            import os
            from dotenv import load_dotenv

            load_dotenv()
            mongodb_url = os.getenv("MONGODB_URL")
            database_name = os.getenv("DATABASE_NAME")

            if not mongodb_url or not database_name:
                print("❌ Database configuration not found")
                return False

            client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_url, uuidRepresentation="unspecified")
            db = client[database_name]

            # Find any existing user from the seeded database
            existing_user = await db.users.find_one({"is_active": True})
            if not existing_user:
                print("❌ No active users found in database")
                return False

            self.user_id = existing_user["id"]
            test_email = existing_user["email"]

            print(f"✅ Using existing user: {test_email} (ID: {self.user_id})")

            # Create a JWT token for this user
            self.token = create_access_token(data={"sub": test_email})
            print(f"✅ Created JWT token for user")

            # Connect to WebSocket
            uri = f"ws://localhost:8000/ws/connect?token={self.token}"
            self.websocket = await websockets.connect(uri)
            self.running = True
            print("✅ Connected to WebSocket")

            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            await asyncio.sleep(2)  # Wait for connection to stabilize and auth

            return True

        except Exception as e:
            print(f"❌ Authentication/connection failed: {e}")
            return False
    
    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        try:
            while self.running and self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                self.messages_received.append(data)
                print(f"📥 Received: {data.get('type', 'unknown')} - {data}")
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket connection closed")
            self.running = False
        except Exception as e:
            print(f"⚠️ Error listening for messages: {e}")
    
    async def send_message(self, message_type: str, data: Optional[dict] = None):
        """Send message to WebSocket server"""
        if not self.websocket or not self.running:
            print("❌ Not connected to WebSocket")
            return False
        
        try:
            message = {"type": message_type}
            if data:
                message.update(data)
            
            await self.websocket.send(json.dumps(message))
            print(f"📤 Sent: {message_type}")
            return True
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False
    
    async def test_bus_tracking(self):
        """Test bus tracking features"""
        print("\n🚌 Testing Bus Tracking Features...")
        print("-" * 40)
        
        # Test 1: Subscribe to all bus tracking
        await self.send_message("subscribe_all_buses", {})
        await asyncio.sleep(2)
        
        # Test 2: Subscribe to specific bus
        test_bus_id = "test_bus_123"
        await self.send_message("subscribe_bus_tracking", {"bus_id": test_bus_id})
        await asyncio.sleep(2)
        
        # Test 3: Simulate bus location update (this would normally come from a bus driver app)
        await self.send_message("update_bus_location", {
            "bus_id": test_bus_id,
            "latitude": 9.0579,
            "longitude": 7.4951,
            "heading": 45,
            "speed": 25
        })
        await asyncio.sleep(2)
        
        print("✅ Bus tracking tests completed")
    
    async def test_chat_messaging(self):
        """Test chat/messaging features"""
        print("\n💬 Testing Chat/Messaging Features...")
        print("-" * 40)
        
        # Test 1: Join a conversation room
        conversation_id = "test_conversation_123"
        await self.send_message("join_conversation", {"conversation_id": conversation_id})
        await asyncio.sleep(1)
        
        # Test 2: Send a direct message
        await self.send_message("send_message", {
            "recipient_id": "test_recipient_456",
            "message": "Hello from WebSocket test!",
            "message_type": "TEXT"
        })
        await asyncio.sleep(1)
        
        # Test 3: Send typing indicator
        await self.send_message("typing_indicator", {
            "conversation_id": conversation_id,
            "is_typing": True
        })
        await asyncio.sleep(1)
        
        await self.send_message("typing_indicator", {
            "conversation_id": conversation_id,
            "is_typing": False
        })
        await asyncio.sleep(1)
        
        print("✅ Chat messaging tests completed")
    
    async def test_notifications(self):
        """Test notification features"""
        print("\n🔔 Testing Notification Features...")
        print("-" * 40)
        
        # Test 1: Admin broadcast (if user has permissions)
        await self.send_message("admin_broadcast", {
            "message": "Test admin broadcast message",
            "target_roles": ["PASSENGER"],
            "priority": "NORMAL"
        })
        await asyncio.sleep(2)
        
        # Test 2: Emergency alert
        await self.send_message("emergency_alert", {
            "alert_type": "GENERAL",
            "message": "Test emergency alert",
            "location": {"latitude": 9.0579, "longitude": 7.4951}
        })
        await asyncio.sleep(2)
        
        print("✅ Notification tests completed")
    
    async def test_room_management(self):
        """Test room join/leave functionality"""
        print("\n🏠 Testing Room Management...")
        print("-" * 40)
        
        # Test joining rooms
        test_rooms = ["test_room_1", "test_room_2", "bus_tracking:123"]
        
        for room in test_rooms:
            await self.send_message("join_room", {"room_id": room})
            await asyncio.sleep(0.5)
        
        # Test leaving a room
        await self.send_message("leave_room", {"room_id": "test_room_1"})
        await asyncio.sleep(0.5)
        
        print("✅ Room management tests completed")
    
    async def test_ping_pong(self):
        """Test basic ping/pong functionality"""
        print("\n🏓 Testing Ping/Pong...")
        print("-" * 40)
        
        await self.send_message("ping", {"timestamp": datetime.now(timezone.utc).isoformat()})
        await asyncio.sleep(1)
        
        print("✅ Ping/pong test completed")
    
    async def run_all_tests(self):
        """Run all WebSocket feature tests"""
        print("🚀 Starting WebSocket Feature Tests")
        print("=" * 50)
        
        # Connect
        if not await self.authenticate_and_connect():
            print("❌ Failed to connect, aborting tests")
            return
        
        try:
            # Run all tests
            await self.test_ping_pong()
            await self.test_room_management()
            await self.test_bus_tracking()
            await self.test_chat_messaging()
            await self.test_notifications()
            
            # Wait a bit to see any final messages
            print("\n⏳ Waiting for final messages...")
            await asyncio.sleep(3)
            
            # Summary
            print("\n📊 Test Summary:")
            print(f"Total messages received: {len(self.messages_received)}")
            
            message_types: dict[str, int] = {}
            for msg in self.messages_received:
                msg_type = msg.get('type', 'unknown')
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            
            for msg_type, count in message_types.items():
                print(f"  - {msg_type}: {count}")
            
            print("\n🎉 All WebSocket feature tests completed!")
            
        except Exception as e:
            print(f"❌ Test error: {e}")
        finally:
            self.running = False
            if self.websocket:
                await self.websocket.close()


async def main():
    """Run the WebSocket feature tests"""
    tester = WebSocketFeatureTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
