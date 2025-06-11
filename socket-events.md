# WebSocket Events Data Formats

This document contains all the data formats for WebSocket events in the GuzoSync real-time bus tracking system.

## Message Structure

All WebSocket messages follow this structure:
```json
{
  "message_type": "event_name",
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
  "message_type": "bus_location_update",
  "data": {
    "bus_id": "bus_123",
    "latitude": 9.0320,
    "longitude": 38.7469,
    "heading": 45.0,        // Optional: direction in degrees (0-360)
    "speed": 25.5           // Optional: speed in km/h
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
  "message_type": "passenger_location_update",
  "data": {
    "latitude": 9.0320,
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
  "message_type": "toggle_location_sharing",
  "data": {
    "enabled": true  // true to enable, false to disable
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
  "message_type": "subscribe_all_buses",
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
  "message_type": "subscribe_proximity_alerts",
  "data": {
    "bus_stop_ids": ["stop_001", "stop_002"],
    "radius_meters": 500  // Optional, defaults to 500m
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
  "message_type": "get_route_with_buses",
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
    "geometry": { /* GeoJSON LineString */ },
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
  "message_type": "calculate_eta",
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

## Server → Client Events

### 1. Bus Location Update (Broadcast)
**Event Type:** `bus_location_update`  
**Sent to:** All subscribers in `all_bus_tracking` room

```json
{
  "type": "bus_location_update",
  "bus_id": "bus_123",
  "location": {
    "latitude": 9.0320,
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
        "latitude": 9.0320,
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

## Error Responses

All events can return error responses in this format:

```json
{
  "success": false,
  "error": "Error message description"
}
```

### Common Error Messages

- `"Only bus drivers can update bus locations"`
- `"Only passengers can update their location"`
- `"Location sharing is disabled. Enable it in settings to receive proximity alerts."`
- `"Bus ID, latitude, and longitude are required"`
- `"Driver not assigned to this bus"`
- `"Bus not found"`
- `"At least one bus stop ID is required"`
- `"One or more bus stops not found or inactive"`
- `"Insufficient permissions"`

## Usage Examples

### For Bus Drivers
```javascript
// Send location update every 10 seconds
setInterval(() => {
  navigator.geolocation.getCurrentPosition((position) => {
    ws.send(JSON.stringify({
      message_type: "bus_location_update",
      data: {
        bus_id: "bus_123",
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        heading: position.coords.heading || 0,
        speed: position.coords.speed || 0
      }
    }));
  });
}, 10000);
```

### For Passengers
```javascript
// Enable location sharing
ws.send(JSON.stringify({
  message_type: "toggle_location_sharing",
  data: { enabled: true }
}));

// Send location update every 30 seconds
setInterval(() => {
  navigator.geolocation.getCurrentPosition((position) => {
    ws.send(JSON.stringify({
      message_type: "passenger_location_update",
      data: {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude
      }
    }));
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
ws.send(JSON.stringify({
  message_type: "subscribe_all_buses",
  data: {}
}));

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
