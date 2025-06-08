#!/usr/bin/env python3
"""
Simple WebSocket client to test the /ws/connect endpoint
"""
import asyncio
import websockets
import json
import sys

async def test_websocket_connection():
    """Test WebSocket connection with a dummy token"""
    # You'll need to replace this with a real JWT token from your auth system
    token = "test_token_here"  # Replace with actual JWT token
    uri = f"ws://localhost:8000/ws/connect?token={token}"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket successfully!")
            
            # Test joining a room
            join_message = {
                "type": "join_room",
                "room_id": "test_room_123"
            }
            await websocket.send(json.dumps(join_message))
            print(f"📤 Sent: {join_message}")
            
            # Listen for response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📥 Received: {data}")
            
            # Test ping message
            ping_message = {
                "type": "ping",
                "timestamp": "2025-06-08T18:52:00Z"
            }
            await websocket.send(json.dumps(ping_message))
            print(f"📤 Sent: {ping_message}")
            
            # Listen for pong response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📥 Received: {data}")
            
            print("✅ WebSocket test completed successfully!")
            
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 4001:
            print("❌ Authentication failed - Invalid token")
            print("💡 You need to provide a valid JWT token")
        elif e.code == 4002:
            print("❌ Connection error")
        else:
            print(f"❌ Connection closed: {e}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("💡 Make sure your FastAPI server is running on localhost:8000")

if __name__ == "__main__":
    print("🚀 Testing WebSocket connection...")
    print("📋 Instructions:")
    print("1. Make sure your FastAPI server is running")
    print("2. Replace 'test_token_here' with a valid JWT token")
    print("3. Run this script")
    print()
    
    if len(sys.argv) > 1:
        token = sys.argv[1]
        print(f"Using provided token: {token[:20]}...")
    
    asyncio.run(test_websocket_connection())
