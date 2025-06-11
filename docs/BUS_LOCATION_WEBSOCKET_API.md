# Bus Location WebSocket API Documentation

This document describes the WebSocket API for real-time bus location tracking and proximity notifications.

## Overview

The bus location WebSocket system provides five main features:

1. **Bus Location Updates**: Bus drivers can send real-time location updates
2. **Location Broadcasting**: All location updates are broadcasted to subscribers
3. **Passenger Location Tracking**: Passengers can share their location for proximity notifications
4. **Location Sharing Control**: Passengers can enable/disable location sharing for privacy
5. **Smart Proximity Notifications**: Passengers within 500m of bus stops receive alerts when buses approach

## WebSocket Connection

Connect to the WebSocket endpoint with proper authentication:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws");
```

## Message Format

All WebSocket messages follow this format:

```json
{
  "message_type": "event_name",
  "data": {
    // Event-specific data
  }
}
```

## 1. Bus Location Updates (Driver → Server)

### Event: `bus_location_update`

Bus drivers send location updates to the server.

**Requirements:**

- User must have `BUS_DRIVER` role
- Driver must be assigned to the bus being updated

**Message Format:**

```json
{
  "message_type": "bus_location_update",
  "data": {
    "bus_id": "bus_123",
    "latitude": 9.032,
    "longitude": 38.7469,
    "heading": 45.0, // Optional: direction in degrees
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

**What Happens:**

1. Bus location is updated in database
2. Location is broadcasted to all subscribers
3. Proximity checks are performed for nearby bus stops
4. Notifications sent to passengers within 500m of approaching bus

## 2. Subscribe to All Bus Locations (Client → Server)

### Event: `subscribe_all_buses`

Subscribe to receive real-time location updates for all buses.

**Message Format:**

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

**Received Messages:**
After subscribing, you'll receive:

1. **Initial bus locations:**

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
      "status": "ACTIVE"
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

2. **Real-time location updates:**

```json
{
  "type": "bus_location_update",
  "bus_id": "bus_123",
  "location": {
    "latitude": 9.0325,
    "longitude": 38.747
  },
  "heading": 50.0,
  "speed": 30.0,
  "timestamp": "2024-01-15T10:31:00Z"
}
```

## 3. Passenger Location Updates (Passenger → Server)

### Event: `passenger_location_update`

Passengers send their location to receive proximity notifications when buses approach nearby stops.

**Requirements:**

- User must have `PASSENGER` role
- Location sharing must be enabled

**Message Format:**

```json
{
  "message_type": "passenger_location_update",
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

## 4. Toggle Location Sharing (Passenger → Server)

### Event: `toggle_location_sharing`

Passengers can enable or disable location sharing for privacy control.

**Requirements:**

- User must have `PASSENGER` role

**Message Format:**

```json
{
  "message_type": "toggle_location_sharing",
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

## 5. Subscribe to Proximity Alerts (Passenger → Server)

### Event: `subscribe_proximity_alerts`

Passengers can subscribe to receive notifications when buses approach specific bus stops.

**Requirements:**

- User must have `PASSENGER` role

**Message Format:**

```json
{
  "message_type": "subscribe_proximity_alerts",
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

**Received Proximity Alerts:**
When a bus approaches a bus stop and you are within 500m of that stop:

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

**Database Notifications:**
Proximity alerts are also saved as notifications in the database and can be retrieved via the notifications API.

## Client Implementation Examples

### JavaScript/TypeScript Example

```javascript
class BusLocationWebSocket {
  constructor(wsUrl, authToken) {
    this.ws = new WebSocket(wsUrl);
    this.authToken = authToken;
    this.setupEventHandlers();
  }

  setupEventHandlers() {
    this.ws.onopen = () => {
      console.log("Connected to bus location WebSocket");
      this.subscribeToAllBuses();
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
  }

  // Subscribe to all bus locations
  subscribeToAllBuses() {
    this.send("subscribe_all_buses", {});
  }

  // Subscribe to proximity alerts
  subscribeToProximityAlerts(busStopIds, radiusMeters = 500) {
    this.send("subscribe_proximity_alerts", {
      bus_stop_ids: busStopIds,
      radius_meters: radiusMeters,
    });
  }

  // Send bus location update (for drivers)
  updateBusLocation(busId, latitude, longitude, heading, speed) {
    this.send("bus_location_update", {
      bus_id: busId,
      latitude: latitude,
      longitude: longitude,
      heading: heading,
      speed: speed,
    });
  }

  send(messageType, data) {
    const message = {
      message_type: messageType,
      data: data,
    };
    this.ws.send(JSON.stringify(message));
  }

  handleMessage(message) {
    switch (message.type) {
      case "bus_location_update":
        this.onBusLocationUpdate(message);
        break;
      case "proximity_alert":
        this.onProximityAlert(message);
        break;
      case "all_bus_locations":
        this.onAllBusLocations(message);
        break;
    }
  }

  onBusLocationUpdate(message) {
    console.log(`Bus ${message.bus_id} updated location:`, message.location);
    // Update map markers, etc.
  }

  onProximityAlert(message) {
    console.log(`Bus approaching ${message.bus_stop_name}!`);
    // Show notification to user
    this.showNotification(
      `Bus ${message.bus_info?.license_plate} approaching`,
      `Arriving at ${message.bus_stop_name} in ~${message.estimated_arrival_minutes} minutes`
    );
  }

  onAllBusLocations(message) {
    console.log(`Received ${message.buses.length} bus locations`);
    // Initialize map with all bus positions
  }

  showNotification(title, message) {
    if (Notification.permission === "granted") {
      new Notification(title, { body: message });
    }
  }
}

// Usage
const busWS = new BusLocationWebSocket(
  "ws://localhost:8000/ws",
  "your-auth-token"
);

// For passengers - subscribe to proximity alerts
busWS.subscribeToProximityAlerts(["stop_001", "stop_002"]);

// For drivers - send location updates
busWS.updateBusLocation("bus_123", 9.032, 38.7469, 45.0, 25.5);
```

## Error Handling

All WebSocket events return success/error responses:

```json
{
  "success": false,
  "error": "Only bus drivers can update bus locations"
}
```

Common error scenarios:

- **Permission denied**: User role doesn't match required role
- **Bus not found**: Invalid bus ID
- **Driver not assigned**: Driver trying to update unassigned bus
- **Invalid data**: Missing required fields
- **Bus stop not found**: Invalid bus stop ID in proximity subscription

## Security & Validation

- All location updates are validated for proper user roles
- Bus drivers can only update buses assigned to them
- Passengers can only subscribe to proximity alerts
- All coordinates are validated for reasonable ranges
- Database operations are atomic and error-handled

## Performance Considerations

- Proximity checks are performed efficiently using the Haversine formula
- WebSocket rooms are used to minimize unnecessary message broadcasting
- Database queries are optimized with proper indexing
- Location updates are throttled to prevent spam

## Integration with Frontend

This WebSocket API integrates seamlessly with the existing Next.js frontend. See `docs/FRONTEND_WEBSOCKET_INTEGRATION.md` for detailed frontend implementation examples.
