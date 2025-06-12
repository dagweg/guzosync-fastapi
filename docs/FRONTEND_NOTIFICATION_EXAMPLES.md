# Frontend WebSocket Notification Examples

This document provides practical examples for implementing the new notification system in frontend applications.

## WebSocket Connection Setup

```javascript
// Connect to WebSocket
const ws = new WebSocket("ws://localhost:8000/ws");

// Handle connection
ws.onopen = () => {
  console.log("Connected to WebSocket");
};

// Handle incoming messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleWebSocketMessage(message);
};

// Handle errors
ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};
```

## Sending Notifications (Admin/Control Staff)

### Send Route Reallocation Notification

```javascript
function sendRouteReallocationNotification(
  busId,
  oldRouteId,
  newRouteId,
  targetUserIds
) {
  const notification = {
    type: "send_notification",
    data: {
      title: "Route Reallocation",
      message: `Bus ${busId} has been reallocated from ${oldRouteId} to ${newRouteId}`,
      notification_type: "ROUTE_REALLOCATION",
      target_user_ids: targetUserIds,
      related_entity: {
        entity_type: "route_reallocation",
        bus_id: busId,
        old_route_id: oldRouteId,
        new_route_id: newRouteId,
        reallocated_by: getCurrentUserId(),
      },
    },
  };

  ws.send(JSON.stringify(notification));
}

// Usage
sendRouteReallocationNotification("bus_123", "route_001", "route_002", [
  "driver_456",
  "regulator_789",
]);
```

### Send General Notification to Role

```javascript
function sendNotificationToRole(
  title,
  message,
  targetRoles,
  notificationType = "GENERAL"
) {
  const notification = {
    type: "send_notification",
    data: {
      title: title,
      message: message,
      notification_type: notificationType,
      target_roles: targetRoles,
    },
  };

  ws.send(JSON.stringify(notification));
}

// Usage - Send to all drivers
sendNotificationToRole(
  "System Maintenance",
  "System will be down for maintenance from 2-4 AM",
  ["BUS_DRIVER", "QUEUE_REGULATOR"],
  "SERVICE_ALERT"
);
```

## Receiving and Handling Notifications

### Notification Handler

```javascript
function handleWebSocketMessage(message) {
  switch (message.type) {
    case "notification":
      handleNotification(message.notification);
      break;
    case "bus_location_update":
      handleBusLocationUpdate(message);
      break;
    case "proximity_alert":
      handleProximityAlert(message);
      break;
    default:
      console.log("Unknown message type:", message.type);
  }
}

function handleNotification(notification) {
  console.log("Received notification:", notification);

  // Show notification in UI
  showNotificationToast(notification);

  // Handle specific notification types
  switch (notification.notification_type) {
    case "ROUTE_REALLOCATION":
      handleRouteReallocationNotification(notification);
      break;
    case "INCIDENT_REPORTED":
      handleIncidentReportedNotification(notification);
      break;
    case "REALLOCATION_REQUEST_DISCARDED":
      handleReallocationRequestDiscardedNotification(notification);
      break;
    default:
      handleGeneralNotification(notification);
  }
}
```

### Specific Notification Handlers

```javascript
function handleRouteReallocationNotification(notification) {
  const { related_entity } = notification;

  // Update UI to reflect route change
  if (related_entity && related_entity.entity_type === "route_reallocation") {
    updateBusRouteInUI(
      related_entity.bus_id,
      related_entity.old_route_id,
      related_entity.new_route_id
    );
  }

  // Show specific UI for route reallocation
  showRouteReallocationModal(notification);
}

function handleIncidentReportedNotification(notification) {
  const { related_entity } = notification;

  // Add incident to incident list
  if (related_entity && related_entity.entity_type === "incident") {
    addIncidentToList(related_entity);
  }

  // Show urgent notification for high severity incidents
  if (
    related_entity.severity === "HIGH" ||
    related_entity.severity === "CRITICAL"
  ) {
    showUrgentIncidentAlert(notification);
  }
}

function handleReallocationRequestDiscardedNotification(notification) {
  const { related_entity } = notification;

  // Update request status in UI
  if (related_entity && related_entity.entity_type === "reallocation_request") {
    updateReallocationRequestStatus(related_entity.request_id, "DISCARDED");
  }

  // Show feedback to user
  showReallocationRequestFeedback(notification);
}
```

## UI Components

### Notification Toast Component (React Example)

```jsx
import React, { useState, useEffect } from "react";

const NotificationToast = ({ notification, onClose }) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      onClose();
    }, 5000);

    return () => clearTimeout(timer);
  }, [onClose]);

  if (!visible) return null;

  const getNotificationIcon = (type) => {
    switch (type) {
      case "ROUTE_REALLOCATION":
        return "🔄";
      case "INCIDENT_REPORTED":
        return "🚨";
      case "REALLOCATION_REQUEST_DISCARDED":
        return "❌";
      default:
        return "📢";
    }
  };

  const getNotificationColor = (type) => {
    switch (type) {
      case "INCIDENT_REPORTED":
        return "bg-red-500";
      case "ROUTE_REALLOCATION":
        return "bg-blue-500";
      case "REALLOCATION_REQUEST_DISCARDED":
        return "bg-yellow-500";
      default:
        return "bg-gray-500";
    }
  };

  return (
    <div
      className={`fixed top-4 right-4 p-4 rounded-lg text-white ${getNotificationColor(
        notification.notification_type
      )} shadow-lg z-50`}
    >
      <div className="flex items-start">
        <span className="text-2xl mr-3">
          {getNotificationIcon(notification.notification_type)}
        </span>
        <div className="flex-1">
          <h4 className="font-bold">{notification.title}</h4>
          <p className="text-sm mt-1">{notification.message}</p>
          <p className="text-xs mt-2 opacity-75">
            {new Date(notification.timestamp).toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={() => {
            setVisible(false);
            onClose();
          }}
          className="ml-2 text-white hover:text-gray-200"
        >
          ×
        </button>
      </div>
    </div>
  );
};

export default NotificationToast;
```

### Notification Manager Hook (React)

```jsx
import { useState, useEffect, useCallback } from "react";

export const useNotifications = (websocket) => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const addNotification = useCallback((notification) => {
    const newNotification = {
      ...notification,
      id: Date.now() + Math.random(),
      timestamp: notification.timestamp || new Date().toISOString(),
    };

    setNotifications((prev) => [newNotification, ...prev]);
    setUnreadCount((prev) => prev + 1);
  }, []);

  const markAsRead = useCallback((notificationId) => {
    setNotifications((prev) =>
      prev.map((notif) =>
        notif.id === notificationId ? { ...notif, is_read: true } : notif
      )
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
    setUnreadCount(0);
  }, []);

  useEffect(() => {
    if (!websocket) return;

    const handleMessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "notification") {
        addNotification(message.notification);
      }
    };

    websocket.addEventListener("message", handleMessage);

    return () => {
      websocket.removeEventListener("message", handleMessage);
    };
  }, [websocket, addNotification]);

  return {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    clearAll,
  };
};
```

## Role-Based Notification Handling

### Driver Interface

```javascript
// Driver-specific notification handling
function setupDriverNotifications(ws) {
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "notification") {
      const notification = message.notification;

      switch (notification.notification_type) {
        case "ROUTE_REALLOCATION":
          // Show route change notification prominently
          showDriverRouteChangeAlert(notification);
          break;
        case "SERVICE_ALERT":
          // Show service alerts
          showServiceAlert(notification);
          break;
        default:
          showGeneralNotification(notification);
      }
    }
  };
}
```

### Control Center Interface

```javascript
// Control center notification handling
function setupControlCenterNotifications(ws) {
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "notification") {
      const notification = message.notification;

      switch (notification.notification_type) {
        case "INCIDENT_REPORTED":
          // High priority - show immediately
          showIncidentAlert(notification);
          playAlertSound();
          break;
        case "REALLOCATION_REQUEST_DISCARDED":
          // Update dashboard
          updateReallocationDashboard(notification);
          break;
        default:
          addToNotificationCenter(notification);
      }
    }
  };
}
```

## Testing the Notification System

### Test Notification Sending

```javascript
// Test function to send various notification types
function testNotifications() {
  // Test route reallocation
  ws.send(
    JSON.stringify({
      type: "send_notification",
      data: {
        title: "Test Route Reallocation",
        message: "This is a test route reallocation notification",
        notification_type: "ROUTE_REALLOCATION",
        target_user_ids: ["test_user_123"],
      },
    })
  );

  // Test incident report
  setTimeout(() => {
    ws.send(
      JSON.stringify({
        type: "send_notification",
        data: {
          title: "Test Incident Report",
          message: "This is a test incident notification",
          notification_type: "INCIDENT_REPORTED",
          target_roles: [UserRole.CONTROL_ADMIN],
        },
      })
    );
  }, 2000);
}
```

This notification system provides a robust foundation for real-time communication in the GuzoSync application, enabling efficient coordination between drivers, regulators, and control center staff.
