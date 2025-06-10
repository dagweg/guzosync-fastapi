# GuzoSync Real-Time API Documentation

## Overview

GuzoSync provides comprehensive real-time functionality through Socket.IO connections, enabling live updates for bus tracking, chat messaging, and notifications. Socket.IO provides better reliability, automatic reconnection, and fallback to polling when WebSockets are not available.

## Table of Contents

1. [Socket.IO Connection](#socketio-connection)
2. [Authentication](#authentication)
3. [Event Types](#event-types)
4. [Real-Time Features](#real-time-features)
   - [Bus Tracking](#bus-tracking)
   - [Chat System](#chat-system)
   - [Notifications](#notifications)
5. [Room Management](#room-management)
6. [Error Handling](#error-handling)
7. [Frontend Integration Examples](#frontend-integration-examples)
8. [Testing](#testing)

## Socket.IO Connection

### Endpoint

```
http://localhost:8000/socket.io/
```

### Connection Flow

```javascript
// 1. Install socket.io-client
// npm install socket.io-client

// 2. Establish connection
import { io } from "socket.io-client";

const token = localStorage.getItem("authToken");
const socket = io("http://localhost:8000", {
  transports: ["websocket", "polling"],
  upgrade: true,
});

// 3. Handle connection events
socket.on("connect", () => {
  console.log("Connected to GuzoSync real-time server");

  // Authenticate with JWT token
  socket.emit("authenticate", { token: token });
});

socket.on("authenticated", (data) => {
  console.log("Authentication successful:", data);
  // Now you can join rooms and receive events
});

socket.on("auth_error", (error) => {
  console.error("Authentication failed:", error);
  // Redirect to login
});

socket.on("disconnect", (reason) => {
  console.log("Disconnected:", reason);
  if (reason === "io server disconnect") {
    // Server disconnected, try to reconnect
    socket.connect();
  }
});

socket.on("connect_error", (error) => {
  console.error("Socket.IO connection error:", error);
});
```

## Authentication

Authentication is handled through JWT tokens sent via Socket.IO events after connection.

### Token Requirements

- Valid JWT token issued by the GuzoSync authentication system
- Token must not be expired
- User associated with the token must exist in the database

### Authentication Flow

1. Client connects to Socket.IO endpoint
2. Client emits 'authenticate' event with JWT token
3. Server validates the JWT token
4. If valid, server emits 'authenticated' event
5. If invalid, server emits 'auth_error' event

### Authentication Events

#### Client Authentication Request

```javascript
socket.emit("authenticate", {
  token: "your-jwt-token-here",
});
```

#### Server Authentication Success

```javascript
socket.on("authenticated", (data) => {
  // data = { user_id: "123", message: "Successfully authenticated" }
});
```

#### Server Authentication Error

```javascript
socket.on("auth_error", (error) => {
  // error = { message: "Invalid token" }
});
```

## Event Types

Socket.IO uses event-based communication instead of message types. Here are the main events:

### Client to Server Events

#### Join Room

```javascript
socket.emit("join_room", {
  room_id: "conversation:123", // or "bus_tracking:456" or "route_tracking:789"
});
```

#### Leave Room

```javascript
socket.emit("leave_room", {
  room_id: "conversation:123",
});
```

#### Ping (Keep-Alive)

```javascript
socket.emit("ping", {
  timestamp: new Date().toISOString(),
});
```

### Server to Client Events

#### Room Joined Confirmation

```javascript
socket.on("room_joined", (data) => {
  // data = { room_id: "conversation:123", message: "Joined room..." }
});
```

#### Room Left Confirmation

```javascript
socket.on("room_left", (data) => {
  // data = { room_id: "conversation:123", message: "Left room..." }
});
```

#### Pong Response

```javascript
socket.on("pong", (data) => {
  // data = { timestamp: "2025-06-08T12:00:00.000Z" }
});
```

#### 4. Bus Location Update

```javascript
{
    "type": "bus_location_update",
    "bus_id": "bus_123",
    "location": {
        "latitude": 9.0320,
        "longitude": 38.7469,
        "timestamp": "2025-06-08T12:00:00.000Z"
    },
    "speed": 45.5,
    "heading": 180,
    "status": "en_route"
}
```

#### 5. Chat Message

```javascript
{
    "type": "chat_message",
    "conversation_id": "conv_123",
    "message": {
        "id": "msg_456",
        "sender_id": "user_789",
        "sender_name": "John Doe",
        "content": "Hello everyone!",
        "timestamp": "2025-06-08T12:00:00.000Z",
        "message_type": "text"
    }
}
```

#### 6. Notification

```javascript
{
    "type": "notification",
    "notification": {
        "id": "notif_123",
        "title": "Bus Delayed",
        "message": "Your bus is running 10 minutes late",
        "type": "trip_update",
        "priority": "medium",
        "timestamp": "2025-06-08T12:00:00.000Z",
        "data": {
            "trip_id": "trip_456",
            "delay_minutes": 10
        }
    }
}
```

## Real-Time Features

### Bus Tracking

#### Subscribe to Bus Updates

```javascript
// Join bus tracking room
ws.send(
  JSON.stringify({
    type: "join_room",
    room_id: "bus_tracking:bus_123",
  })
);

// Handle bus location updates
function handleBusUpdate(message) {
  if (message.type === "bus_location_update") {
    const { bus_id, location, speed, heading, status } = message;

    // Update map marker
    updateBusMarker(bus_id, {
      lat: location.latitude,
      lng: location.longitude,
      speed: speed,
      heading: heading,
      status: status,
    });

    // Update UI elements
    updateBusStatus(bus_id, status);
    updateETA(bus_id, calculateETA(location, speed));
  }
}
```

#### Subscribe to Route Tracking

```javascript
// Join route tracking room
ws.send(
  JSON.stringify({
    type: "join_room",
    room_id: "route_tracking:route_456",
  })
);

// Handle multiple buses on a route
function handleRouteUpdate(message) {
  if (message.type === "bus_location_update") {
    // Update all buses on this route
    updateRouteBuses(message.bus_id, message.location);
  }
}
```

### Chat System

#### Join Conversation

```javascript
// Join conversation room
const conversationId = "conv_123";
ws.send(
  JSON.stringify({
    type: "join_room",
    room_id: `conversation:${conversationId}`,
  })
);

// Handle incoming messages
function handleChatMessage(message) {
  if (message.type === "chat_message") {
    const { conversation_id, message: chatMsg } = message;

    // Add message to chat UI
    addMessageToChat(conversation_id, {
      id: chatMsg.id,
      sender: chatMsg.sender_name,
      content: chatMsg.content,
      timestamp: new Date(chatMsg.timestamp),
      isOwn: chatMsg.sender_id === getCurrentUserId(),
    });

    // Show notification if chat is not active
    if (!isChatActive(conversation_id)) {
      showChatNotification(chatMsg.sender_name, chatMsg.content);
    }
  }
}
```

#### Send Message (via REST API)

```javascript
// Send message through REST API (triggers real-time broadcast)
async function sendChatMessage(conversationId, content) {
  try {
    const response = await fetch(
      `/api/conversations/${conversationId}/messages`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: content,
          message_type: "text",
        }),
      }
    );

    if (!response.ok) {
      throw new Error("Failed to send message");
    }

    // Message will be broadcast to all room participants via WebSocket
  } catch (error) {
    console.error("Error sending message:", error);
    showErrorNotification("Failed to send message");
  }
}
```

### Notifications

#### Receive System Notifications

```javascript
function handleNotification(message) {
  if (message.type === "notification") {
    const { notification } = message;

    // Show notification based on type
    switch (notification.type) {
      case "trip_update":
        showTripNotification(notification);
        break;
      case "route_alert":
        showRouteAlert(notification);
        break;
      case "maintenance":
        showMaintenanceNotification(notification);
        break;
      case "emergency":
        showEmergencyAlert(notification);
        break;
      default:
        showGenericNotification(notification);
    }

    // Add to notification history
    addToNotificationHistory(notification);
  }
}

function showTripNotification(notification) {
  const { title, message, data } = notification;

  // Show browser notification
  if (Notification.permission === "granted") {
    new Notification(title, {
      body: message,
      icon: "/icons/bus-icon.png",
    });
  }

  // Update trip status in UI
  if (data.trip_id) {
    updateTripStatus(data.trip_id, {
      delay: data.delay_minutes,
      status: data.status,
    });
  }
}
```

## Room Management

### Room ID Patterns

- **Conversations**: `conversation:{conversation_id}`
- **Bus Tracking**: `bus_tracking:{bus_id}`
- **Route Tracking**: `route_tracking:{route_id}`

### Join Multiple Rooms

```javascript
function subscribeToMultipleRooms(rooms) {
  rooms.forEach((roomId) => {
    ws.send(
      JSON.stringify({
        type: "join_room",
        room_id: roomId,
      })
    );
  });
}

// Example: Subscribe to user's active trip and conversations
const userRooms = [
  "bus_tracking:bus_123",
  "route_tracking:route_456",
  "conversation:conv_789",
];

subscribeToMultipleRooms(userRooms);
```

### Leave Rooms on Navigation

```javascript
function leaveRoom(roomId) {
  ws.send(
    JSON.stringify({
      type: "leave_room",
      room_id: roomId,
    })
  );
}

// Leave all rooms when user navigates away
window.addEventListener("beforeunload", function () {
  activeRooms.forEach((roomId) => {
    leaveRoom(roomId);
  });
});
```

## Error Handling

### Connection Management

```javascript
class GuzoSyncWebSocket {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.activeRooms = new Set();
    this.messageHandlers = new Map();

    this.connect();
  }

  connect() {
    try {
      this.ws = new WebSocket(
        `ws://localhost:8000/ws/connect?token=${this.token}`
      );

      this.ws.onopen = () => {
        console.log("Connected to GuzoSync");
        this.reconnectAttempts = 0;
        this.rejoinRooms();
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(JSON.parse(event.data));
      };

      this.ws.onclose = (event) => {
        this.handleClose(event);
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
      this.scheduleReconnect();
    }
  }

  handleClose(event) {
    this.stopHeartbeat();

    if (event.code === 4001) {
      console.error("Authentication failed");
      this.onAuthError?.();
      return;
    }

    console.log("Connection closed, attempting to reconnect...");
    this.scheduleReconnect();
  }

  scheduleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
    } else {
      console.error("Max reconnection attempts reached");
      this.onMaxReconnectAttemptsReached?.();
    }
  }

  rejoinRooms() {
    this.activeRooms.forEach((roomId) => {
      this.joinRoom(roomId);
    });
  }

  joinRoom(roomId) {
    this.activeRooms.add(roomId);
    this.send({
      type: "join_room",
      room_id: roomId,
    });
  }

  leaveRoom(roomId) {
    this.activeRooms.delete(roomId);
    this.send({
      type: "leave_room",
      room_id: roomId,
    });
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket not ready, message queued");
      // Could implement message queueing here
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.send({
        type: "ping",
        timestamp: new Date().toISOString(),
      });
    }, 30000); // Every 30 seconds
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
  }

  handleMessage(message) {
    const handler = this.messageHandlers.get(message.type);
    if (handler) {
      handler(message);
    } else {
      console.log("Unhandled message type:", message.type);
    }
  }

  on(messageType, handler) {
    this.messageHandlers.set(messageType, handler);
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
    }
  }
}
```

## Frontend Integration Examples

### React Integration

```jsx
import React, { useEffect, useState, useContext } from "react";

const WebSocketContext = React.createContext();

export function WebSocketProvider({ children }) {
  const [wsClient, setWsClient] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const { token } = useAuth();

  useEffect(() => {
    if (token) {
      const client = new GuzoSyncWebSocket(token);

      client.onAuthError = () => {
        // Handle auth error - redirect to login
        logout();
      };

      client.on("bus_location_update", handleBusUpdate);
      client.on("chat_message", handleChatMessage);
      client.on("notification", handleNotification);

      setWsClient(client);
      setIsConnected(true);

      return () => {
        client.disconnect();
        setIsConnected(false);
      };
    }
  }, [token]);

  return (
    <WebSocketContext.Provider value={{ wsClient, isConnected }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export const useWebSocket = () => useContext(WebSocketContext);

// Usage in components
function BusTrackingComponent({ busId }) {
  const { wsClient } = useWebSocket();
  const [busLocation, setBusLocation] = useState(null);

  useEffect(() => {
    if (wsClient && busId) {
      wsClient.joinRoom(`bus_tracking:${busId}`);

      wsClient.on("bus_location_update", (message) => {
        if (message.bus_id === busId) {
          setBusLocation({
            lat: message.location.latitude,
            lng: message.location.longitude,
            speed: message.speed,
            status: message.status,
          });
        }
      });

      return () => {
        wsClient.leaveRoom(`bus_tracking:${busId}`);
      };
    }
  }, [wsClient, busId]);

  return <div>{busLocation && <BusMap location={busLocation} />}</div>;
}
```

### Vue.js Integration

```javascript
// composables/useWebSocket.js
import { ref, onMounted, onUnmounted } from "vue";

export function useWebSocket() {
  const wsClient = ref(null);
  const isConnected = ref(false);

  onMounted(() => {
    const token = localStorage.getItem("authToken");
    if (token) {
      wsClient.value = new GuzoSyncWebSocket(token);
      isConnected.value = true;
    }
  });

  onUnmounted(() => {
    if (wsClient.value) {
      wsClient.value.disconnect();
    }
  });

  return {
    wsClient,
    isConnected,
  };
}

// In component
export default {
  setup() {
    const { wsClient, isConnected } = useWebSocket();
    const notifications = ref([]);

    watchEffect(() => {
      if (wsClient.value) {
        wsClient.value.on("notification", (message) => {
          notifications.value.unshift(message.notification);
        });
      }
    });

    return {
      wsClient,
      isConnected,
      notifications,
    };
  },
};
```

## Testing

### Manual Testing with HTML Client

```html
<!DOCTYPE html>
<html>
  <head>
    <title>GuzoSync WebSocket Test</title>
  </head>
  <body>
    <div id="status">Disconnected</div>
    <div id="messages"></div>

    <input type="text" id="token" placeholder="JWT Token" />
    <button onclick="connect()">Connect</button>
    <button onclick="disconnect()">Disconnect</button>

    <br /><br />

    <input type="text" id="roomId" placeholder="Room ID" />
    <button onclick="joinRoom()">Join Room</button>
    <button onclick="leaveRoom()">Leave Room</button>

    <br /><br />

    <button onclick="sendPing()">Send Ping</button>

    <script>
      let ws = null;

      function connect() {
        const token = document.getElementById("token").value;
        ws = new WebSocket(`ws://localhost:8000/ws/connect?token=${token}`);

        ws.onopen = () => {
          document.getElementById("status").textContent = "Connected";
          addMessage("Connected to server");
        };

        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          addMessage(`Received: ${JSON.stringify(message, null, 2)}`);
        };

        ws.onclose = (event) => {
          document.getElementById("status").textContent = "Disconnected";
          addMessage(`Connection closed: ${event.code} - ${event.reason}`);
        };
      }

      function disconnect() {
        if (ws) {
          ws.close();
        }
      }

      function joinRoom() {
        const roomId = document.getElementById("roomId").value;
        ws.send(
          JSON.stringify({
            type: "join_room",
            room_id: roomId,
          })
        );
      }

      function leaveRoom() {
        const roomId = document.getElementById("roomId").value;
        ws.send(
          JSON.stringify({
            type: "leave_room",
            room_id: roomId,
          })
        );
      }

      function sendPing() {
        ws.send(
          JSON.stringify({
            type: "ping",
            timestamp: new Date().toISOString(),
          })
        );
      }

      function addMessage(message) {
        const div = document.createElement("div");
        div.innerHTML = `<pre>${message}</pre>`;
        document.getElementById("messages").appendChild(div);
      }
    </script>
  </body>
</html>
```

## Best Practices

### 1. Connection Management

- Always implement reconnection logic
- Handle authentication failures gracefully
- Use heartbeat/ping to keep connections alive
- Clean up resources on component unmount

### 2. Message Handling

- Validate message structure before processing
- Handle unknown message types gracefully
- Implement message queueing for offline scenarios
- Use proper error boundaries

### 3. Performance

- Only subscribe to rooms you need
- Unsubscribe when leaving pages/components
- Throttle high-frequency updates (like bus locations)
- Use efficient data structures for message storage

### 4. Security

- Never expose JWT tokens in logs
- Validate all incoming messages
- Implement proper CORS settings
- Use secure WebSocket (WSS) in production

### 5. User Experience

- Show connection status to users
- Provide offline functionality where possible
- Handle slow connections gracefully
- Show appropriate loading states

## Troubleshooting

### Common Issues

1. **Connection Refuses**

   - Check if server is running
   - Verify JWT token is valid
   - Check network connectivity

2. **Authentication Failures**

   - Token expired - refresh token
   - Invalid token format
   - Server configuration issues

3. **Messages Not Received**

   - Check if joined correct room
   - Verify message handler registration
   - Check server logs

4. **Performance Issues**
   - Too many active connections
   - Inefficient message handling
   - Memory leaks from uncleared handlers

### Debug Mode

```javascript
const wsClient = new GuzoSyncWebSocket(token, {
  debug: true,
  logMessages: true,
});
```

This documentation provides everything your frontend team needs to integrate with GuzoSync's real-time features. The WebSocket connection handles bus tracking, chat, and notifications seamlessly across your application.
