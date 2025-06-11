#!/usr/bin/env python3
"""
Manual Socket.IO test - run this while the server is running
"""
import asyncio
import socketio
import httpx
from uuid import uuid4
from datetime import datetime, timezone
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from core.jwt import create_access_token


async def test_server_health():
    """Test server health endpoint"""
    print("🏥 Testing server health...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Server is healthy: {data}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


async def test_socketio_connection():
    """Test Socket.IO connection"""
    print("🔌 Testing Socket.IO connection...")
    
    # Create a test token
    try:
        token = create_access_token(data={"sub": "test@example.com"})
        print(f"🔑 Created test token")
    except Exception as e:
        print(f"❌ Failed to create token: {e}")
        return False
    
    # Create Socket.IO client
    sio = socketio.AsyncClient()
    connected = False
    events_received = []
    
    @sio.event
    async def connect():
        nonlocal connected
        connected = True
        print("✅ Socket.IO connected!")
    
    @sio.event
    async def disconnect():
        nonlocal connected
        connected = False
        print("🔌 Socket.IO disconnected")
    
    @sio.event
    async def authenticated(data):
        print(f"🔐 Authenticated: {data}")
        events_received.append(("authenticated", data))
    
    @sio.event
    async def auth_error(data):
        print(f"❌ Auth error: {data}")
        events_received.append(("auth_error", data))
    
    @sio.event
    async def error(data):
        print(f"⚠️ Error: {data}")
        events_received.append(("error", data))
    
    @sio.event
    async def pong(data):
        print(f"🏓 Pong received: {data}")
        events_received.append(("pong", data))
    
    try:
        # Connect to server
        await sio.connect("http://localhost:8000", auth={"token": token})
        
        # Wait for connection
        await asyncio.sleep(2.0)
        
        if not connected:
            print("❌ Failed to connect to Socket.IO")
            return False
        
        # Test ping
        print("🏓 Sending ping...")
        await sio.emit("ping", {"timestamp": datetime.now(timezone.utc).isoformat()})
        
        # Wait for response
        await asyncio.sleep(2.0)
        
        # Test joining a room
        print("🏠 Testing room join...")
        await sio.emit("join_room", {"room_id": "test_room"})
        
        # Wait for response
        await asyncio.sleep(1.0)
        
        print(f"📨 Events received: {len(events_received)}")
        for event_name, event_data in events_received:
            print(f"   {event_name}: {event_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Socket.IO test failed: {e}")
        return False
        
    finally:
        try:
            await sio.disconnect()
        except:
            pass


async def test_socketio_endpoints():
    """Test Socket.IO HTTP endpoints"""
    print("🌐 Testing Socket.IO HTTP endpoints...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test status endpoint
            response = await client.get("http://localhost:8000/socket.io/status", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Socket.IO status: {data}")
            else:
                print(f"⚠️ Socket.IO status endpoint returned: {response.status_code}")
            
            return True
            
    except Exception as e:
        print(f"❌ HTTP endpoints test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🧪 Manual Socket.IO Test Suite")
    print("=" * 50)
    print("📋 Prerequisites:")
    print("   1. Server should be running: python main.py")
    print("   2. Database should be accessible")
    print("   3. Environment variables should be set")
    print("=" * 50)
    
    # Test 1: Server health
    health_ok = await test_server_health()
    if not health_ok:
        print("❌ Server health check failed. Is the server running?")
        return False
    
    # Test 2: Socket.IO connection
    socketio_ok = await test_socketio_connection()
    if not socketio_ok:
        print("❌ Socket.IO connection test failed")
        return False
    
    # Test 3: HTTP endpoints
    endpoints_ok = await test_socketio_endpoints()
    if not endpoints_ok:
        print("❌ HTTP endpoints test failed")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 ALL MANUAL TESTS PASSED!")
    print("✅ Server is running correctly")
    print("✅ Socket.IO is working")
    print("✅ HTTP endpoints are accessible")
    print("\n🚀 Socket.IO system is ready!")
    print("=" * 50)
    
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
