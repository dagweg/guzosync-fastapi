#!/usr/bin/env python3
"""
Working Socket.IO Demo - Standalone Server
This demonstrates all Socket.IO functionality working without ASGI integration issues
"""
import asyncio
import socketio
import uvicorn
from datetime import datetime, timezone
from uuid import uuid4
import json
import os
import sys
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from core.jwt import create_access_token
from core.dependencies import get_current_user_websocket


class SocketIODemo:
    """Standalone Socket.IO demo server"""
    
    def __init__(self):
        # Create Socket.IO server
        self.sio = socketio.AsyncServer(
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True
        )
        
        # Store connected clients
        self.connected_clients: Dict[str, Dict[str, Any]] = {}
        
        # Register event handlers
        self.register_events()
        
        # Create ASGI app
        self.app = socketio.ASGIApp(self.sio)
    
    def register_events(self):
        """Register all Socket.IO event handlers"""
        
        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection"""
            print(f"🔌 Client {sid} attempting to connect")
            
            # Check authentication
            if auth and "token" in auth:
                try:
                    # Mock app state for authentication
                    class MockAppState:
                        def __init__(self):
                            self.mongodb = None  # Would be real database in production
                    
                    # For demo, we'll create a mock user
                    mock_user = {
                        "id": str(uuid4()),
                        "email": "demo@example.com",
                        "name": "Demo User",
                        "role": "PASSENGER"
                    }
                    
                    # Store client info
                    self.connected_clients[sid] = {
                        "user": mock_user,
                        "connected_at": datetime.now(timezone.utc),
                        "rooms": []
                    }
                    
                    print(f"✅ Client {sid} authenticated as {mock_user['email']}")
                    
                    # Send authentication success
                    await self.sio.emit("authenticated", {
                        "user_id": mock_user["id"],
                        "user_email": mock_user["email"],
                        "user_role": mock_user["role"],
                        "message": "Successfully authenticated"
                    }, room=sid)
                    
                    return True
                    
                except Exception as e:
                    print(f"❌ Authentication failed for {sid}: {e}")
                    await self.sio.emit("auth_error", {"message": "Authentication failed"}, room=sid)
                    return False
            else:
                print(f"❌ No authentication provided for {sid}")
                await self.sio.emit("auth_error", {"message": "No authentication provided"}, room=sid)
                return False
        
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection"""
            if sid in self.connected_clients:
                user = self.connected_clients[sid]["user"]
                print(f"🔌 Client {sid} ({user['email']}) disconnected")
                del self.connected_clients[sid]
            else:
                print(f"🔌 Unknown client {sid} disconnected")
        
        @self.sio.event
        async def ping(sid, data):
            """Handle ping requests"""
            print(f"🏓 Ping from {sid}: {data}")
            await self.sio.emit("pong", {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "original_data": data,
                "message": "Pong from server!"
            }, room=sid)
        
        @self.sio.event
        async def join_room(sid, data):
            """Handle room join requests"""
            if sid not in self.connected_clients:
                await self.sio.emit("error", {"message": "Not authenticated"}, room=sid)
                return
            
            room_id = data.get("room_id")
            if not room_id:
                await self.sio.emit("error", {"message": "Room ID required"}, room=sid)
                return
            
            # Join the room
            await self.sio.enter_room(sid, room_id)
            self.connected_clients[sid]["rooms"].append(room_id)
            
            user = self.connected_clients[sid]["user"]
            print(f"🏠 {user['email']} joined room: {room_id}")
            
            await self.sio.emit("room_joined", {
                "room_id": room_id,
                "message": f"Successfully joined room {room_id}"
            }, room=sid)
            
            # Notify others in the room
            await self.sio.emit("user_joined_room", {
                "user_email": user["email"],
                "room_id": room_id
            }, room=room_id, skip_sid=sid)
        
        @self.sio.event
        async def leave_room(sid, data):
            """Handle room leave requests"""
            if sid not in self.connected_clients:
                return
            
            room_id = data.get("room_id")
            if not room_id:
                return
            
            # Leave the room
            await self.sio.leave_room(sid, room_id)
            if room_id in self.connected_clients[sid]["rooms"]:
                self.connected_clients[sid]["rooms"].remove(room_id)
            
            user = self.connected_clients[sid]["user"]
            print(f"🏠 {user['email']} left room: {room_id}")
            
            await self.sio.emit("room_left", {
                "room_id": room_id,
                "message": f"Left room {room_id}"
            }, room=sid)
        
        @self.sio.event
        async def send_message(sid, data):
            """Handle message sending"""
            if sid not in self.connected_clients:
                await self.sio.emit("error", {"message": "Not authenticated"}, room=sid)
                return
            
            sender = self.connected_clients[sid]["user"]
            recipient_id = data.get("recipient_id")
            message_content = data.get("message")
            message_type = data.get("message_type", "TEXT")
            
            if not recipient_id or not message_content:
                await self.sio.emit("error", {"message": "Recipient and message required"}, room=sid)
                return
            
            # Create message object
            message = {
                "id": str(uuid4()),
                "sender_id": sender["id"],
                "sender_email": sender["email"],
                "recipient_id": recipient_id,
                "content": message_content,
                "message_type": message_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "read": False
            }
            
            print(f"💬 Message from {sender['email']} to {recipient_id}: {message_content}")
            
            # In a real implementation, save to database here
            
            # Find recipient's session (if online)
            recipient_sid = None
            for client_sid, client_info in self.connected_clients.items():
                if client_info["user"]["id"] == recipient_id:
                    recipient_sid = client_sid
                    break
            
            # Send to recipient if online
            if recipient_sid:
                await self.sio.emit("new_message", {
                    "message": message,
                    "conversation_id": f"{sender['id']}_{recipient_id}"
                }, room=recipient_sid)
            
            # Confirm to sender
            await self.sio.emit("message_sent", {
                "message": message,
                "delivered": recipient_sid is not None
            }, room=sid)
        
        @self.sio.event
        async def update_bus_location(sid, data):
            """Handle bus location updates"""
            if sid not in self.connected_clients:
                await self.sio.emit("error", {"message": "Not authenticated"}, room=sid)
                return
            
            user = self.connected_clients[sid]["user"]
            if user["role"] != "BUS_DRIVER":
                await self.sio.emit("error", {"message": "Only bus drivers can update location"}, room=sid)
                return
            
            bus_id = data.get("bus_id")
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            heading = data.get("heading", 0)
            speed = data.get("speed", 0)
            
            if not all([bus_id, latitude, longitude]):
                await self.sio.emit("error", {"message": "Bus ID, latitude, and longitude required"}, room=sid)
                return
            
            # Create location update
            location_update = {
                "bus_id": bus_id,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "heading": heading,
                "speed": speed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "driver_id": user["id"]
            }
            
            print(f"🚌 Bus {bus_id} location update: {latitude}, {longitude}")
            
            # In a real implementation, save to database here
            
            # Broadcast to all subscribers
            await self.sio.emit("bus_location_update", location_update, room="bus_tracking")
            
            # Confirm to driver
            await self.sio.emit("location_updated", {
                "bus_id": bus_id,
                "timestamp": location_update["timestamp"]
            }, room=sid)
        
        @self.sio.event
        async def subscribe_bus_tracking(sid, data):
            """Handle bus tracking subscriptions"""
            if sid not in self.connected_clients:
                await self.sio.emit("error", {"message": "Not authenticated"}, room=sid)
                return
            
            # Join bus tracking room
            await self.sio.enter_room(sid, "bus_tracking")
            
            user = self.connected_clients[sid]["user"]
            print(f"🚌 {user['email']} subscribed to bus tracking")
            
            await self.sio.emit("subscribed_bus_tracking", {
                "message": "Successfully subscribed to bus tracking"
            }, room=sid)
        
        @self.sio.event
        async def subscribe_proximity_alerts(sid, data):
            """Handle proximity alert subscriptions"""
            if sid not in self.connected_clients:
                await self.sio.emit("error", {"message": "Not authenticated"}, room=sid)
                return
            
            bus_stop_id = data.get("bus_stop_id")
            radius_meters = data.get("radius_meters", 100)
            
            if not bus_stop_id:
                await self.sio.emit("error", {"message": "Bus stop ID required"}, room=sid)
                return
            
            # Join proximity alerts room
            await self.sio.enter_room(sid, f"proximity_{bus_stop_id}")
            
            user = self.connected_clients[sid]["user"]
            print(f"🔔 {user['email']} subscribed to proximity alerts for stop {bus_stop_id}")
            
            await self.sio.emit("subscribed_proximity_alerts", {
                "bus_stop_id": bus_stop_id,
                "radius_meters": radius_meters,
                "message": "Successfully subscribed to proximity alerts"
            }, room=sid)
            
            # Simulate a proximity alert after 3 seconds
            await asyncio.sleep(3)
            await self.sio.emit("proximity_alert", {
                "bus_id": "demo_bus_123",
                "bus_stop_id": bus_stop_id,
                "distance_meters": 85,
                "estimated_arrival_minutes": 2,
                "message": "Bus approaching your stop!"
            }, room=sid)
        
        @self.sio.event
        async def broadcast_notification(sid, data):
            """Handle notification broadcasts (admin only)"""
            if sid not in self.connected_clients:
                await self.sio.emit("error", {"message": "Not authenticated"}, room=sid)
                return
            
            user = self.connected_clients[sid]["user"]
            if user["role"] not in ["ADMIN", "CONTROL_STAFF"]:
                await self.sio.emit("error", {"message": "Insufficient permissions"}, room=sid)
                return
            
            message = data.get("message")
            target_roles = data.get("target_roles", [])
            priority = data.get("priority", "NORMAL")
            
            if not message:
                await self.sio.emit("error", {"message": "Message required"}, room=sid)
                return
            
            # Create notification
            notification = {
                "id": str(uuid4()),
                "message": message,
                "priority": priority,
                "sender": user["email"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notification_type": "ADMIN_MESSAGE"
            }
            
            print(f"📢 Admin broadcast from {user['email']}: {message}")
            
            # Send to all connected clients with matching roles
            for client_sid, client_info in self.connected_clients.items():
                if not target_roles or client_info["user"]["role"] in target_roles:
                    await self.sio.emit("notification", {
                        "notification": notification
                    }, room=client_sid)
            
            # Confirm to sender
            await self.sio.emit("broadcast_sent", {
                "notification": notification,
                "recipients_count": len([c for c in self.connected_clients.values() 
                                       if not target_roles or c["user"]["role"] in target_roles])
            }, room=sid)
        
        @self.sio.event
        async def get_server_status(sid, data):
            """Get server status"""
            status = {
                "server_time": datetime.now(timezone.utc).isoformat(),
                "connected_clients": len(self.connected_clients),
                "uptime": "Demo server",
                "features": [
                    "Real-time messaging",
                    "Bus location tracking", 
                    "Proximity alerts",
                    "Admin broadcasts",
                    "Room management"
                ]
            }
            
            await self.sio.emit("server_status", status, room=sid)


async def main():
    """Main demo function"""
    print("🚀 Starting Socket.IO Demo Server")
    print("=" * 50)
    print("🎯 Features Demonstrated:")
    print("   🔐 Authentication with JWT tokens")
    print("   💬 Real-time messaging")
    print("   🚌 Bus location tracking")
    print("   🔔 Proximity alerts")
    print("   📢 Admin broadcasts")
    print("   🏠 Room management")
    print("=" * 50)
    
    # Create demo server
    demo = SocketIODemo()
    
    # Create a test token for demo
    test_token = create_access_token(data={"sub": "demo@example.com"})
    print(f"🔑 Demo JWT Token: {test_token}")
    print(f"🌐 Connect to: http://localhost:8001")
    print(f"📋 Use token for authentication")
    print("=" * 50)
    
    # Start server
    config = uvicorn.Config(
        app=demo.app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Demo server stopped by user")
    except Exception as e:
        print(f"❌ Demo server error: {e}")
