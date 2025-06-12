# WebSocket Events Data Formats

This document contains all the data formats for WebSocket events in the GuzoSync real-time bus tracking system.

## Message Structure

All WebSocket messages follow this structure:

```json
{
  "type": "event_name",
  "data": {
    // Event-specific data
  }
}
```

## Client → Server Events

### 1. Bus Location Update (Driver)

**Event:** `bus_location_update`  
**Role:** BUS_DRIVER  
**Description:** Bus drivers send real-time location updates

```json
{
  "type": "bus_location_update",
  "data": {
    "bus_id": "bus_123",
    "latitude": 9.032,
    "longitude": 38.7469,
    "heading": 45.0, // Optional: direction in degrees (0-360)
    "speed": 25.5 // Optional: speed in km/h
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Location updated successfully",
  "bus_id": "bus_123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. Passenger Location Update

**Event:** `passenger_location_update`  
**Role:** PASSENGER  
**Description:** Passengers send their location for proximity notifications

```json
{
  "type": "passenger_location_update",
  "data": {
    "latitude": 9.032,
    "longitude": 38.7469
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Location updated successfully",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 3. Toggle Location Sharing

**Event:** `toggle_location_sharing`  
**Role:** PASSENGER  
**Description:** Enable/disable location sharing for privacy control

```json
{
  "type": "toggle_location_sharing",
  "data": {
    "enabled": true // true to enable, false to disable
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Location sharing enabled",
  "location_sharing_enabled": true
}
```

### 4. Subscribe to All Bus Locations

**Event:** `subscribe_all_buses`  
**Role:** Any authenticated user  
**Description:** Subscribe to receive all bus location updates

```json
{
  "type": "subscribe_all_buses",
  "data": {}
}
```

**Response:**

```json
{
  "success": true,
  "message": "Subscribed to all bus tracking",
  "room_id": "all_bus_tracking"
}
```

### 5. Subscribe to Proximity Alerts

**Event:** `subscribe_proximity_alerts`  
**Role:** PASSENGER  
**Description:** Subscribe to proximity alerts for specific bus stops

```json
{
  "type": "subscribe_proximity_alerts",
  "data": {
    "bus_stop_ids": ["stop_001", "stop_002"],
    "radius_meters": 500 // Optional, defaults to 500m
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Subscribed to proximity alerts for 2 bus stops",
  "subscribed_stops": ["stop_001", "stop_002"],
  "radius_meters": 500
}
```

### 6. Get Route with Buses

**Event:** `get_route_with_buses`  
**Role:** Any authenticated user  
**Description:** Get route shape with current bus positions

```json
{
  "type": "get_route_with_buses",
  "data": {
    "route_id": "route_001"
  }
}
```

**Response:**

```json
{
  "success": true,
  "route_data": {
    "route_id": "route_001",
    "route_name": "Route 1",
    "geometry": {
      /* GeoJSON LineString */
    },
    "buses": [
      {
        "bus_id": "bus_123",
        "location": { "latitude": 9.032, "longitude": 38.747 },
        "heading": 45.0,
        "speed": 25.5
      }
    ]
  }
}
```

### 7. Calculate ETA

**Event:** `calculate_eta`
**Role:** Any authenticated user
**Description:** Calculate ETA for bus to reach specific stop

```json
{
  "type": "calculate_eta",
  "data": {
    "bus_id": "bus_123",
    "stop_id": "stop_001"
  }
}
```

**Response:**

```json
{
  "success": true,
  "eta_data": {
    "bus_id": "bus_123",
    "target_stop_id": "stop_001",
    "eta_minutes": 5,
    "distance_km": 2.1,
    "current_speed_kmh": 25.0,
    "calculated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 8. Admin Broadcast

**Event:** `admin_broadcast`
**Role:** ADMIN, CONTROL_STAFF
**Description:** Broadcast messages to drivers/regulators

```json
{
  "type": "admin_broadcast",
  "data": {
    "message": "All drivers report to dispatch immediately",
    "target_roles": ["BUS_DRIVER", "QUEUE_REGULATOR"],
    "priority": "HIGH"
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Broadcast sent successfully",
  "notification_id": "1705312200.123456"
}
```

### 9. Emergency Alert

**Event:** `emergency_alert`
**Role:** BUS_DRIVER, QUEUE_REGULATOR, ADMIN, CONTROL_STAFF
**Description:** Send emergency alerts to control staff

```json
{
  "type": "emergency_alert",
  "data": {
    "alert_type": "VEHICLE_BREAKDOWN",
    "message": "Bus engine failure, need immediate assistance",
    "location": {
      "latitude": 9.032,
      "longitude": 38.7469
    }
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Emergency alert sent successfully",
  "alert_id": "1705312200.789012"
}
```

### 10. Join Conversation

**Event:** `join_conversation`
**Role:** Any authenticated user
**Description:** Join a conversation room for real-time messaging

```json
{
  "type": "join_conversation",
  "data": {
    "conversation_id": "conv_123"
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Joined conversation conv_123",
  "conversation_id": "conv_123"
}
```

### 11. Typing Indicator

**Event:** `typing_indicator`
**Role:** Any authenticated user
**Description:** Send typing status in conversations

```json
{
  "type": "typing_indicator",
  "data": {
    "conversation_id": "conv_123",
    "is_typing": true
  }
}
```

**Response:**

```json
{
  "success": true
}
```

### 12. Mark Message Read

**Event:** `mark_message_read`
**Role:** Any authenticated user
**Description:** Mark a message as read in conversations

```json
{
  "type": "mark_message_read",
  "data": {
    "conversation_id": "conv_123",
    "message_id": "msg_456"
  }
}
```

**Response:**

```json
{
  "success": true
}
```

## Server → Client Events

### 1. Bus Location Update (Broadcast)

**Event Type:** `bus_location_update`  
**Sent to:** All subscribers in `all_bus_tracking` room

```json
{
  "type": "bus_location_update",
  "bus_id": "bus_123",
  "location": {
    "latitude": 9.032,
    "longitude": 38.7469
  },
  "heading": 45.0,
  "speed": 25.5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. All Bus Locations (Initial Data)

**Event Type:** `all_bus_locations`  
**Sent to:** Users who subscribe to all buses

```json
{
  "type": "all_bus_locations",
  "buses": [
    {
      "bus_id": "bus_123",
      "license_plate": "AA-12345",
      "location": {
        "latitude": 9.032,
        "longitude": 38.7469
      },
      "heading": 45.0,
      "speed": 25.5,
      "route_id": "route_001",
      "last_update": "2024-01-15T10:29:00Z",
      "status": "ACTIVE"
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 3. Proximity Alert

**Event Type:** `proximity_alert`  
**Sent to:** Passengers within 500m of bus stops when buses approach

```json
{
  "type": "proximity_alert",
  "bus_id": "bus_123",
  "bus_stop_id": "stop_001",
  "bus_stop_name": "Central Station",
  "bus_distance_to_stop_meters": 450.0,
  "passenger_distance_to_stop_meters": 200.0,
  "estimated_arrival_minutes": 2,
  "bus_info": {
    "license_plate": "AA-12345",
    "route_id": "route_001"
  },
  "timestamp": "2024-01-15T10:32:00Z"
}
```

### 4. Notification (General)

**Event Type:** `notification`
**Sent to:** Specific users or broadcast

```json
{
  "type": "notification",
  "notification": {
    "title": "Bus Approaching Central Station",
    "message": "Bus AA-12345 is approaching Central Station (450m away, ~2 min). You are 200m from the stop.",
    "notification_type": "PROXIMITY_ALERT",
    "related_entity": {
      "entity_type": "bus_proximity",
      "entity_id": "bus_123",
      "bus_stop_id": "stop_001",
      "bus_distance_meters": 450.0,
      "passenger_distance_meters": 200.0
    },
    "timestamp": "2024-01-15T10:32:00Z",
    "is_read": false
  }
}
```

### 5. New Message (Chat)

**Event Type:** `new_message`
**Sent to:** Conversation participants

```json
{
  "type": "new_message",
  "conversation_id": "conv_123",
  "message": {
    "id": "msg_456",
    "sender_id": "user_789",
    "content": "Hello, how are you?",
    "type": "TEXT",
    "sent_at": "2024-01-15T10:35:00Z"
  }
}
```

### 6. Typing Status

**Event Type:** `typing_status`
**Sent to:** Conversation participants (excluding typing user)

```json
{
  "type": "typing_status",
  "conversation_id": "conv_123",
  "user_id": "user_789",
  "is_typing": true,
  "timestamp": "2024-01-15T10:36:00Z"
}
```

### 7. Message Read

**Event Type:** `message_read`
**Sent to:** Conversation participants (excluding reader)

```json
{
  "type": "message_read",
  "conversation_id": "conv_123",
  "user_id": "user_789",
  "message_id": "msg_456",
  "timestamp": "2024-01-15T10:37:00Z"
}
```

### 8. Emergency Alert (Broadcast)

**Event Type:** `emergency_alert`
**Sent to:** Emergency response room and control staff

```json
{
  "type": "emergency_alert",
  "id": "1705312200.789012",
  "alert_type": "VEHICLE_BREAKDOWN",
  "title": "Emergency Alert - VEHICLE_BREAKDOWN",
  "message": "Bus engine failure, need immediate assistance",
  "location": {
    "latitude": 9.032,
    "longitude": 38.7469
  },
  "sender_id": "driver_123",
  "priority": "HIGH",
  "timestamp": "2024-01-15T10:38:00Z"
}
```

## Error Responses

All events can return error responses in this format:

```json
{
  "success": false,
  "error": "Error message description"
}
```

### Common Error Messages

**Bus Location Updates:**

- `"Only bus drivers can update bus locations"`
- `"Bus ID, latitude, and longitude are required"`
- `"Driver not assigned to this bus"`
- `"Bus not found"`

**Passenger Location Updates:**

- `"Only passengers can update their location"`
- `"Location sharing is disabled. Enable it in settings to receive proximity alerts."`
- `"Latitude and longitude are required"`

**Proximity Alerts:**

- `"Only passengers can subscribe to proximity alerts"`
- `"At least one bus stop ID is required"`
- `"One or more bus stops not found or inactive"`

**Admin/Emergency Features:**

- `"Insufficient permissions"`
- `"Message content required"`
- `"Alert message required"`

**Chat Features:**

- `"Conversation ID required"`
- `"Conversation ID and Message ID required"`
- `"Route ID required"`
- `"Bus ID and Stop ID required"`

**General:**

- `"Unknown message type: [type]"`

## Usage Examples

### For Bus Drivers

```javascript
// Send location update every 10 seconds
setInterval(() => {
  navigator.geolocation.getCurrentPosition((position) => {
    ws.send(
      JSON.stringify({
        type: "bus_location_update",
        data: {
          bus_id: "bus_123",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          heading: position.coords.heading || 0,
          speed: position.coords.speed || 0,
        },
      })
    );
  });
}, 10000);
```

### For Passengers

```javascript
// Enable location sharing
ws.send(
  JSON.stringify({
    type: "toggle_location_sharing",
    data: { enabled: true },
  })
);

// Send location update every 30 seconds
setInterval(() => {
  navigator.geolocation.getCurrentPosition((position) => {
    ws.send(
      JSON.stringify({
        type: "passenger_location_update",
        data: {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        },
      })
    );
  });
}, 30000);

// Handle proximity alerts
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === "proximity_alert") {
    showNotification(
      `Bus ${message.bus_info.license_plate} approaching!`,
      `Arriving at ${message.bus_stop_name} in ~${message.estimated_arrival_minutes} minutes`
    );
  }
};
```

### For Map Applications

```javascript
// Subscribe to all bus locations
ws.send(
  JSON.stringify({
    type: "subscribe_all_buses",
    data: {},
  })
);

// Handle bus location updates
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === "bus_location_update") {
    updateBusMarkerOnMap(message.bus_id, message.location);
  } else if (message.type === "all_bus_locations") {
    initializeMapWithBuses(message.buses);
  }
};
```

### For Admin/Control Staff

```javascript
// Send admin broadcast
ws.send(
  JSON.stringify({
    type: "admin_broadcast",
    data: {
      message: "All drivers report to dispatch immediately",
      target_roles: ["BUS_DRIVER", "QUEUE_REGULATOR"],
      priority: "HIGH",
    },
  })
);

// Handle emergency alerts
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === "emergency_alert") {
    showEmergencyAlert(
      `Emergency: ${message.alert_type}`,
      `From ${message.sender_id}: ${message.message}`,
      message.location
    );
  }
};
```

### For Drivers/Regulators

```javascript
// Send emergency alert
ws.send(
  JSON.stringify({
    type: "emergency_alert",
    data: {
      alert_type: "VEHICLE_BREAKDOWN",
      message: "Bus engine failure, need immediate assistance",
      location: {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      },
    },
  })
);
```

### For Chat Features

```javascript
// Join conversation
ws.send(
  JSON.stringify({
    type: "join_conversation",
    data: {
      conversation_id: "conv_123",
    },
  })
);

// Send typing indicator
ws.send(
  JSON.stringify({
    type: "typing_indicator",
    data: {
      conversation_id: "conv_123",
      is_typing: true,
    },
  })
);

// Mark message as read
ws.send(
  JSON.stringify({
    type: "mark_message_read",
    data: {
      conversation_id: "conv_123",
      message_id: "msg_456",
    },
  })
);

// Handle chat events
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === "new_message") {
    displayMessage(message.conversation_id, message.message);
  } else if (message.type === "typing_status") {
    showTypingIndicator(
      message.conversation_id,
      message.user_id,
      message.is_typing
    );
  } else if (message.type === "message_read") {
    markMessageAsRead(message.conversation_id, message.message_id);
  }
};
```
