# GuzoSync Socket.IO Real-Time API Documentation

## Overview

GuzoSync now uses Socket.IO for all real-time communication, providing reliable, maintainable, and feature-rich real-time functionality. This replaces the previous WebSocket implementation with a more robust solution that includes automatic reconnection, fallback to polling, and better error handling.

## Features

### 1. Basic Messaging System
- **Direct messaging** between queue regulators/bus drivers ↔ control staff/admin
- **Conversation management** with real-time updates
- **Typing indicators** and read receipts
- **Message history** and persistence

### 2. Notification System
- **Proximity alerts** when buses approach bus stops
- **Emergency alerts** from drivers/regulators to control center
- **Admin broadcasts** to specific user roles
- **Trip updates** and delays

### 3. Real-Time Bus Tracking
- **Live bus locations** for all active buses
- **Route visualization** with current bus positions
- **ETA calculations** for buses to specific stops
- **Mapbox integration** with route shapes and real-time updates

## Socket.IO Connection

### Connection URL
```
ws://localhost:8000/socket.io/
```

### Authentication
All Socket.IO connections require JWT token authentication:

```javascript
const socket = io('http://localhost:8000', {
    auth: {
        token: 'your-jwt-token'
    }
});

// Or authenticate after connection
socket.emit('authenticate', { token: 'your-jwt-token' });
```

## Event Handlers

### Connection Events

#### `connect`
Fired when client connects to server.

#### `authenticated`
```javascript
socket.on('authenticated', (data) => {
    console.log('Authenticated:', data);
    // { user_id: "123", message: "Successfully authenticated" }
});
```

#### `auth_error`
```javascript
socket.on('auth_error', (data) => {
    console.error('Authentication failed:', data.message);
});
```

### Messaging Events

#### Send Direct Message
```javascript
socket.emit('send_message', {
    recipient_id: 'user-id',
    message: 'Hello!',
    message_type: 'TEXT'
});
```

#### Receive New Message
```javascript
socket.on('new_message', (data) => {
    console.log('New message:', data);
    // {
    //   type: "new_message",
    //   conversation_id: "conv-123",
    //   message: {
    //     id: "msg-456",
    //     sender_id: "user-789",
    //     content: "Hello!",
    //     message_type: "TEXT",
    //     sent_at: "2024-01-01T12:00:00Z"
    //   }
    // }
});
```

#### Join Conversation
```javascript
socket.emit('join_room', { room_id: 'conversation:conv-123' });
```

#### Typing Indicators
```javascript
// Send typing status
socket.emit('typing_status', {
    conversation_id: 'conv-123',
    is_typing: true
});

// Receive typing status
socket.on('typing_status', (data) => {
    console.log('User typing:', data);
});
```

### Bus Tracking Events

#### Subscribe to All Bus Locations
```javascript
socket.emit('join_room', { room_id: 'all_bus_tracking' });

socket.on('all_bus_locations', (data) => {
    console.log('All bus locations:', data.buses);
    // Update map with all bus positions
});
```

#### Subscribe to Specific Bus
```javascript
socket.emit('subscribe_bus_tracking', { bus_id: 'bus-123' });

socket.on('bus_location_update', (data) => {
    console.log('Bus location update:', data);
    // {
    //   type: "bus_location_update",
    //   bus_id: "bus-123",
    //   location: { latitude: 9.0192, longitude: 38.7525 },
    //   heading: 45.5,
    //   speed: 25.0,
    //   timestamp: "2024-01-01T12:00:00Z"
    // }
});
```

#### Subscribe to Route Tracking
```javascript
socket.emit('subscribe_route_tracking', { route_id: 'route-456' });

socket.on('bus_location_update', (data) => {
    // Receive updates for all buses on this route
});
```

#### Update Bus Location (Drivers Only)
```javascript
socket.emit('update_bus_location', {
    bus_id: 'bus-123',
    latitude: 9.0192,
    longitude: 38.7525,
    heading: 45.5,
    speed: 25.0
});
```

#### Get Bus Details
```javascript
socket.emit('get_bus_details', { bus_id: 'bus-123' });

socket.on('bus_details', (data) => {
    console.log('Bus details:', data);
    // {
    //   id: "bus-123",
    //   license_plate: "AA-123-456",
    //   current_location: { latitude: 9.0192, longitude: 38.7525 },
    //   heading: 45.5,
    //   speed: 25.0,
    //   route: {
    //     id: "route-456",
    //     name: "Route A",
    //     route_shape: { /* GeoJSON */ },
    //     bus_stops: [...]
    //   },
    //   eta_info: {
    //     next_stop_eta: 5,
    //     end_destination_eta: 25
    //   }
    // }
});
```

### Notification Events

#### Subscribe to Proximity Alerts
```javascript
socket.emit('subscribe_proximity_alerts', {
    bus_stop_id: 'stop-789',
    radius_meters: 100
});

socket.on('proximity_alert', (data) => {
    console.log('Bus approaching:', data);
    // {
    //   type: "proximity_alert",
    //   bus_id: "bus-123",
    //   bus_stop_id: "stop-789",
    //   bus_stop_name: "Main Station",
    //   distance_meters: 85.5,
    //   estimated_arrival_minutes: 2
    // }
});
```

#### Emergency Alerts (Drivers/Regulators)
```javascript
socket.emit('emergency_alert', {
    alert_type: 'VEHICLE_BREAKDOWN',
    message: 'Bus engine failure, need assistance',
    location: { latitude: 9.0192, longitude: 38.7525 }
});
```

#### Admin Broadcasts (Admin/Control Staff)
```javascript
socket.emit('admin_broadcast', {
    message: 'All drivers report to dispatch',
    target_roles: ['BUS_DRIVER'],
    priority: 'HIGH'
});
```

#### Receive Notifications
```javascript
socket.on('notification', (data) => {
    console.log('New notification:', data);
    // Display notification to user
});

socket.on('emergency_alert', (data) => {
    console.log('Emergency alert:', data);
    // Handle emergency with high priority
});
```

## HTTP Endpoints

### Socket.IO Status
```
GET /socket.io/status
```
Returns Socket.IO server status and connection count.

### Broadcast Message (Admin/Control Staff)
```
POST /socket.io/broadcast
{
    "message": "Important announcement",
    "target_roles": ["BUS_DRIVER", "QUEUE_REGULATOR"],
    "priority": "HIGH"
}
```

### Emergency Alert (Drivers/Regulators)
```
POST /socket.io/emergency-alert
{
    "alert_type": "VEHICLE_BREAKDOWN",
    "message": "Need immediate assistance",
    "location": { "latitude": 9.0192, "longitude": 38.7525 }
}
```

### Calculate ETA
```
POST /socket.io/calculate-eta
{
    "bus_id": "bus-123",
    "stop_id": "stop-456"
}
```

### Get Live Route Data
```
GET /socket.io/route/{route_id}/live
```
Returns route shape with current bus positions for Mapbox integration.

## Error Handling

All Socket.IO events can return errors:

```javascript
socket.on('error', (data) => {
    console.error('Socket.IO error:', data.message);
});
```

## Room Management

The system uses rooms for efficient message broadcasting:

- `all_bus_tracking` - All bus location updates
- `bus_tracking:{bus_id}` - Specific bus updates
- `route_tracking:{route_id}` - All buses on a route
- `conversation:{conversation_id}` - Chat conversations
- `proximity_alerts:{bus_stop_id}` - Bus stop proximity alerts
- `emergency_alerts` - Emergency notifications

## Integration with Mapbox

The Socket.IO system is designed for seamless Mapbox integration:

1. **Real-time bus positions** - Update map markers in real-time
2. **Route shapes** - Display route paths with live bus positions
3. **ETA calculations** - Show estimated arrival times
4. **Proximity alerts** - Notify users when buses approach their stops

## Frontend Integration Example

```javascript
// Initialize Socket.IO connection
const socket = io('http://localhost:8000');

// Authenticate
socket.emit('authenticate', { token: localStorage.getItem('access_token') });

// Subscribe to all bus tracking for map display
socket.on('authenticated', () => {
    socket.emit('join_room', { room_id: 'all_bus_tracking' });
});

// Update Mapbox map with bus locations
socket.on('all_bus_locations', (data) => {
    data.buses.forEach(bus => {
        updateBusMarkerOnMap(bus.bus_id, bus.location);
    });
});

// Handle individual bus updates
socket.on('bus_location_update', (data) => {
    updateBusMarkerOnMap(data.bus_id, data.location);
});

// Handle proximity alerts
socket.on('proximity_alert', (data) => {
    showNotification(`Bus ${data.bus_id} arriving at ${data.bus_stop_name} in ${data.estimated_arrival_minutes} minutes`);
});
```

This Socket.IO implementation provides a robust, scalable foundation for all real-time features in GuzoSync.
