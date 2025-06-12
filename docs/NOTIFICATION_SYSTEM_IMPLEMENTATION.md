# WebSocket Notification System Implementation

## Overview

This document describes the implementation of a comprehensive WebSocket notification system for GuzoSync that enables real-time notifications for various system events including route reallocations, incident reporting, and reallocation request management.

## Features Implemented

### 1. General Notification WebSocket Event

**Event:** `send_notification`
- **Purpose:** Generic notification handler that can be used by other services to send notifications
- **Permissions:** Role-based access control for system notifications
- **Supports:** Individual user targeting, role-based broadcasting, and custom notification types

### 2. Route Reallocation Notifications

**Triggers:** When buses are reallocated to different routes
**Recipients:**
- **Bus Driver:** Notified about their bus being moved to a new route
- **Old Route Regulators:** Notified about bus being removed from their route
- **New Route Regulators:** Notified about bus being added to their route

**Implementation Locations:**
- `PUT /api/control-center/buses/{bus_id}/reallocate-route/{route_id}`
- `POST /api/control-center/reallocation-requests/{request_id}/process`

### 3. Reallocation Request Discarded Notifications

**Triggers:** When reallocation requests are rejected or discarded
**Recipients:**
- **Requesting Regulator:** Notified with reason for rejection

**Implementation Locations:**
- `POST /api/control-center/reallocation-requests/{request_id}/process` (when AI agent can't find suitable route)
- `POST /api/control-center/reallocation-requests/{request_id}/discard` (manual discard by admin)

### 4. Incident Reporting Notifications

**Triggers:** When incidents are reported by drivers or other users
**Recipients:**
- **Control Center Staff:** All CONTROL_CENTER_ADMIN and CONTROL_STAFF users

**Implementation Locations:**
- `POST /api/issues/report` (general incident reporting)
- `POST /api/drivers/incidents` (driver-specific incident reporting)

## Technical Implementation

### Files Modified

1. **`core/realtime/websocket_events.py`**
   - Added `handle_send_notification` method
   - Added routing for `send_notification` event type
   - Implemented permission checks for system notifications

2. **`core/realtime/notifications.py`**
   - Added `send_route_reallocation_notification` method
   - Added `send_reallocation_request_discarded_notification` method
   - Added `send_incident_reported_notification` method

3. **`models/notifications.py`**
   - Extended `NotificationType` enum with new types:
     - `ROUTE_REALLOCATION`
     - `REALLOCATION_REQUEST_DISCARDED`
     - `INCIDENT_REPORTED`
     - `CHAT_MESSAGE`

4. **`schemas/notification.py`**
   - Updated schema notification types to match model

5. **`routers/control_center.py`**
   - Added notification triggers to reallocation endpoints
   - Added new manual discard endpoint with notifications
   - Imported notification service

6. **`routers/issues.py`**
   - Added notification trigger for incident reporting
   - Imported notification service

7. **`routers/drivers.py`**
   - Added notification trigger for driver incident reporting
   - Imported notification service

8. **`docs/api/socket-events.md`**
   - Documented new `send_notification` event
   - Added examples for all new notification types
   - Updated server-to-client event documentation

### New Notification Types

```typescript
enum NotificationType {
  GENERAL = "GENERAL",
  ROUTE_REALLOCATION = "ROUTE_REALLOCATION",
  REALLOCATION_REQUEST_DISCARDED = "REALLOCATION_REQUEST_DISCARDED", 
  INCIDENT_REPORTED = "INCIDENT_REPORTED",
  CHAT_MESSAGE = "CHAT_MESSAGE",
  TRIP_UPDATE = "TRIP_UPDATE",
  SERVICE_ALERT = "SERVICE_ALERT"
}
```

## Usage Examples

### 1. Route Reallocation Notification

```json
{
  "type": "notification",
  "notification": {
    "title": "Route Reallocation",
    "message": "Your bus has been reallocated from Route A to Route B by Admin John",
    "notification_type": "ROUTE_REALLOCATION",
    "related_entity": {
      "entity_type": "route_reallocation",
      "bus_id": "bus_123",
      "old_route_id": "route_001", 
      "new_route_id": "route_002",
      "reallocated_by": "admin_456"
    },
    "timestamp": "2024-01-15T10:45:00Z",
    "is_read": false
  }
}
```

### 2. Reallocation Request Discarded

```json
{
  "type": "notification",
  "notification": {
    "title": "Reallocation Request Discarded",
    "message": "Your reallocation request for bus AA-12345 has been discarded. Reason: No suitable alternative route found",
    "notification_type": "REALLOCATION_REQUEST_DISCARDED",
    "related_entity": {
      "entity_type": "reallocation_request",
      "request_id": "req_789",
      "bus_id": "bus_123",
      "status": "DISCARDED"
    },
    "timestamp": "2024-01-15T10:50:00Z",
    "is_read": false
  }
}
```

### 3. Incident Reported

```json
{
  "type": "notification", 
  "notification": {
    "title": "Incident Reported",
    "message": "New high severity vehicle issue incident reported by John Driver (BUS_DRIVER) involving bus AA-12345 on route Route A",
    "notification_type": "INCIDENT_REPORTED",
    "related_entity": {
      "entity_type": "incident",
      "incident_id": "inc_101",
      "incident_type": "VEHICLE_ISSUE",
      "severity": "HIGH",
      "reported_by": "driver_123"
    },
    "timestamp": "2024-01-15T10:55:00Z",
    "is_read": false
  }
}
```

## Security & Permissions

- **Role-based access control:** System notifications require appropriate roles
- **Permission validation:** Sender permissions are checked before sending notifications
- **Data validation:** All notification data is validated before processing

## Integration Points

The notification system integrates with:
- **Route Management:** Automatic notifications on route changes
- **Incident Management:** Real-time alerts to control center
- **Request Management:** Status updates for reallocation requests
- **WebSocket Manager:** Real-time delivery to connected clients
- **Database:** Persistent storage of notifications

## Future Enhancements

- **Push Notifications:** Mobile push notification support
- **Email Notifications:** Email fallback for offline users
- **Notification Preferences:** User-configurable notification settings
- **Notification History:** Enhanced notification management interface
- **Batch Notifications:** Efficient handling of bulk notifications

## Testing

The system can be tested using:
1. **WebSocket clients:** Connect and send `send_notification` events
2. **API endpoints:** Trigger notifications through existing endpoints
3. **Integration tests:** Verify end-to-end notification flow
4. **Role-based testing:** Verify permission controls work correctly

## Deployment Notes

- **Database Migration:** New notification types are backward compatible
- **WebSocket Compatibility:** Existing WebSocket connections continue to work
- **Performance:** Notification system is designed for high throughput
- **Monitoring:** All notification events are logged for debugging
