"""
Comprehensive WebSocket Test Client for Chat, Notifications, and Bus Tracking
"""
import asyncio
import websockets
import json
import requests
from datetime import datetime
import time
import uuid

class GuzosyncWebSocketTester:
    def __init__(self, base_url="http://localhost:8000", ws_url="ws://localhost:8000"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.websocket = None
        self.token = None
        self.user_id = None
        self.running = False
        
    async def authenticate(self, email="test@example.com", password="testpassword"):
        """Get JWT token for authentication"""
        try:
            response = requests.post(f"{self.base_url}/api/auth/login", 
                data={"username": email, "password": password})
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print(f"✅ Authenticated successfully")
                return True
            else:
                print(f"❌ Authentication failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    async def connect_websocket(self):
        """Connect to WebSocket"""
        if not self.token:
            print("❌ No token available. Please authenticate first.")
            return False
            
        try:
            uri = f"{self.ws_url}/ws/connect?token={self.token}"
            self.websocket = await websockets.connect(uri)
            print("✅ WebSocket connected successfully")
            self.running = True
            return True
            
        except Exception as e:
            print(f"❌ WebSocket connection error: {e}")
            return False
    
    async def listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        try:
            while self.running and self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                await self.handle_incoming_message(data)
                
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket connection closed")
        except Exception as e:
            print(f"❌ Error listening for messages: {e}")
    
    async def handle_incoming_message(self, data):
        """Handle different types of incoming messages"""
        msg_type = data.get("type")
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if msg_type == "notification":
            notification = data.get("notification", {})
            print(f"🔔 [{timestamp}] NOTIFICATION: {notification.get('title')} - {notification.get('message')}")
            
        elif msg_type == "new_message":
            message = data.get("message", {})
            print(f"💬 [{timestamp}] NEW MESSAGE in {data.get('conversation_id')}: {message.get('content')}")
            
        elif msg_type == "bus_location_update":
            location = data.get("location", {})
            print(f"🚌 [{timestamp}] BUS UPDATE {data.get('bus_id')}: Lat {location.get('latitude')}, Lon {location.get('longitude')}")
            
        elif msg_type == "trip_update":
            delay = data.get("delay_minutes", 0)
            print(f"🚌 [{timestamp}] TRIP UPDATE {data.get('trip_id')}: {data.get('message')} (Delay: {delay}min)")
            
        elif msg_type == "typing_status":
            status = "typing..." if data.get("is_typing") else "stopped typing"
            print(f"✏️ [{timestamp}] TYPING: User {data.get('user_id')} {status}")
            
        elif msg_type == "message_read":
            print(f"👀 [{timestamp}] MESSAGE READ: {data.get('message_id')} by {data.get('user_id')}")
            
        elif msg_type == "room_joined":
            print(f"🏠 [{timestamp}] JOINED ROOM: {data.get('room_id')}")
            
        elif msg_type == "pong":
            print(f"🏓 [{timestamp}] PONG received")
            
        else:
            print(f"📝 [{timestamp}] OTHER: {data}")
    
    async def send_message(self, message):
        """Send message to WebSocket"""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
    
    # === CHAT TESTING METHODS ===
    
    async def test_chat_features(self):
        """Test chat/conversation features"""
        print("\n🔥 === TESTING CHAT FEATURES ===")
        
        # Join a conversation room
        conversation_id = "test_conversation_123"
        await self.send_message({
            "type": "join_room",
            "room_id": f"conversation:{conversation_id}"
        })
        
        await asyncio.sleep(1)
        
        # Send a chat message via API
        try:
            response = requests.post(
                f"{self.base_url}/api/realtime/demo/chat-message",
                json={
                    "conversation_id": conversation_id,
                    "content": "Hello from WebSocket test!",
                    "message_type": "TEXT"
                },
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if response.status_code == 200:
                print("✅ Chat message sent via API")
            else:
                print(f"❌ Chat message failed: {response.text}")
        except Exception as e:
            print(f"❌ Chat API error: {e}")
        
        await asyncio.sleep(2)
        
        # Test typing indicator
        await self.test_typing_status(conversation_id)
    
    async def test_typing_status(self, conversation_id):
        """Test typing status functionality"""
        try:
            # Start typing
            response = requests.post(
                f"{self.base_url}/api/conversations/{conversation_id}/typing",
                json={"is_typing": True},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            await asyncio.sleep(2)
            
            # Stop typing
            response = requests.post(
                f"{self.base_url}/api/conversations/{conversation_id}/typing",
                json={"is_typing": False},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            print("✅ Typing status test completed")
            
        except Exception as e:
            print(f"❌ Typing status error: {e}")
    
    # === NOTIFICATION TESTING METHODS ===
    
    async def test_notification_features(self):
        """Test notification features"""
        print("\n🔔 === TESTING NOTIFICATION FEATURES ===")
        
        # Test personal notification
        try:
            response = requests.post(
                f"{self.base_url}/api/realtime/demo/notification",
                json={
                    "title": "Test Personal Notification",
                    "message": "This is a test notification from WebSocket client",
                    "target_user_id": self.user_id
                },
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if response.status_code == 200:
                print("✅ Personal notification sent")
            else:
                print(f"❌ Personal notification failed: {response.text}")
        except Exception as e:
            print(f"❌ Notification API error: {e}")
        
        await asyncio.sleep(2)
        
        # Test broadcast notification
        try:
            response = requests.post(
                f"{self.base_url}/api/notifications/broadcast",
                json={
                    "title": "Broadcast Test",
                    "message": "This is a broadcast notification test",
                    "type": "GENERAL",
                    "target_roles": ["PASSENGER"]
                },
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if response.status_code == 200:
                print("✅ Broadcast notification sent")
            else:
                print(f"❌ Broadcast notification failed: {response.text}")
        except Exception as e:
            print(f"❌ Broadcast notification error: {e}")
    
    # === BUS TRACKING TESTING METHODS ===
    
    async def test_bus_tracking_features(self):
        """Test bus tracking features"""
        print("\n🚌 === TESTING BUS TRACKING FEATURES ===")
        
        bus_id = "test_bus_001"
        
        # Subscribe to bus tracking
        await self.send_message({
            "type": "join_room",
            "room_id": f"bus_tracking:{bus_id}"
        })
        
        await asyncio.sleep(1)
        
        # Send bus location update
        locations = [
            {"latitude": 9.0317, "longitude": 38.7468, "heading": 45.0, "speed": 30.0},  # Addis Ababa
            {"latitude": 9.0327, "longitude": 38.7478, "heading": 50.0, "speed": 35.0},  # Moving north
            {"latitude": 9.0337, "longitude": 38.7488, "heading": 55.0, "speed": 40.0},  # Moving further
        ]
        
        for i, location in enumerate(locations):
            try:
                response = requests.post(
                    f"{self.base_url}/api/realtime/demo/bus-location-update",
                    json={
                        "bus_id": bus_id,
                        **location
                    },
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if response.status_code == 200:
                    print(f"✅ Bus location update {i+1} sent")
                else:
                    print(f"❌ Bus location update {i+1} failed: {response.text}")
                
                await asyncio.sleep(3)  # Wait 3 seconds between updates
                
            except Exception as e:
                print(f"❌ Bus tracking API error: {e}")
        
        # Test route subscription
        await self.test_route_subscription()
    
    async def test_route_subscription(self):
        """Test route subscription functionality"""
        route_id = "route_001"
        
        # Subscribe to route tracking
        await self.send_message({
            "type": "join_room",
            "room_id": f"route_tracking:{route_id}"
        })
        
        print("✅ Subscribed to route tracking")
        await asyncio.sleep(2)
    
    # === UTILITY METHODS ===
    
    async def test_ping_pong(self):
        """Test ping-pong for connection health"""
        print("\n🏓 === TESTING PING-PONG ===")
        
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_message(ping_message)
        print("✅ Ping sent")
    
    async def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive WebSocket Test")
        print("=" * 50)
        
        # Authenticate
        if not await self.authenticate():
            return
        
        # Connect to WebSocket
        if not await self.connect_websocket():
            return
        
        # Start listening for messages in background
        listen_task = asyncio.create_task(self.listen_for_messages())
        
        try:
            # Run tests
            await self.test_ping_pong()
            await asyncio.sleep(2)
            
            await self.test_notification_features()
            await asyncio.sleep(3)
            
            await self.test_chat_features()
            await asyncio.sleep(3)
            
            await self.test_bus_tracking_features()
            await asyncio.sleep(5)
            
            print("\n✅ All tests completed! Listening for more messages...")
            print("Press Ctrl+C to exit")
            
            # Keep listening
            await listen_task
            
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
        finally:
            self.running = False
            if self.websocket:
                await self.websocket.close()
    
    async def interactive_mode(self):
        """Interactive mode for manual testing"""
        print("🎮 Interactive WebSocket Test Mode")
        print("Commands: chat, notify, bus, ping, quit")
        
        if not await self.authenticate():
            return
        
        if not await self.connect_websocket():
            return
        
        # Start listening
        listen_task = asyncio.create_task(self.listen_for_messages())
        
        try:
            while self.running:
                command = input("\nEnter command: ").strip().lower()
                
                if command == "quit":
                    break
                elif command == "chat":
                    await self.test_chat_features()
                elif command == "notify":
                    await self.test_notification_features()
                elif command == "bus":
                    await self.test_bus_tracking_features()
                elif command == "ping":
                    await self.test_ping_pong()
                else:
                    print("Available commands: chat, notify, bus, ping, quit")
                    
        except KeyboardInterrupt:
            print("\n🛑 Interactive mode interrupted")
        finally:
            self.running = False
            if self.websocket:
                await self.websocket.close()

# === MAIN EXECUTION ===

async def main():
    tester = GuzosyncWebSocketTester()
    
    print("Select test mode:")
    print("1. Comprehensive automated test")
    print("2. Interactive mode")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            await tester.run_comprehensive_test()
        elif choice == "2":
            await tester.interactive_mode()
        else:
            print("Invalid choice")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())
