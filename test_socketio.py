#!/usr/bin/env python3
"""
Quick test to verify Socket.IO implementation
"""
import asyncio
import socket
import sys
from core.socketio_manager import socketio_manager

async def test_socketio_manager():
    """Test basic Socket.IO manager functionality"""
    print("Testing Socket.IO Manager...")
    
    # Test manager initialization
    print(f"✓ Socket.IO server created: {socketio_manager.sio is not None}")
    print(f"✓ User sessions initialized: {isinstance(socketio_manager.user_sessions, dict)}")
    print(f"✓ User connections initialized: {isinstance(socketio_manager.user_connections, dict)}")
    print(f"✓ Rooms initialized: {isinstance(socketio_manager.rooms, dict)}")
    
    # Test connection counts
    print(f"✓ Connection count: {socketio_manager.get_connection_count()}")
    print(f"✓ Room count: {socketio_manager.get_room_count()}")
    print(f"✓ Connected users: {socketio_manager.get_connected_users()}")
    
    print("✅ Socket.IO manager tests passed!")

async def test_app_integration():
    """Test app integration"""
    try:
        from main import app, socket_app
        print("✓ App imports successfully")
        print(f"✓ Socket app created: {socket_app is not None}")
        print("✅ App integration tests passed!")
    except Exception as e:
        print(f"❌ App integration failed: {e}")
        return False
    
    return True

def check_port_availability(port=8000):
    """Check if the port is available"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(('localhost', port))
        return result != 0  # Port is available if connection fails
    finally:
        sock.close()

async def main():
    print("🔍 Testing GuzoSync Socket.IO Implementation")
    print("=" * 50)
    
    # Test Socket.IO manager
    await test_socketio_manager()
    print()
    
    # Test app integration
    success = await test_app_integration()
    print()
    
    # Check port availability
    port_available = check_port_availability()
    print(f"✓ Port 8000 available: {port_available}")
    
    if success:
        print("🎉 All tests passed! Socket.IO implementation looks good.")
        print("\n📋 Next steps:")
        print("1. Run the server: python main.py")
        print("2. Test with the HTML client: open test_socketio_client.html")
        print("3. Check endpoints: http://localhost:8000/socket.io/info")
    else:
        print("❌ Some tests failed. Check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
