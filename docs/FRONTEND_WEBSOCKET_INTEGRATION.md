# GuzoSync WebSocket Integration Guide for Next.js

## 🚀 Complete Frontend Integration Documentation

This guide provides comprehensive documentation for integrating GuzoSync's real-time WebSocket features into a Next.js frontend application.

## 📋 Table of Contents

1. [Setup & Authentication](#setup--authentication)
2. [WebSocket Connection Management](#websocket-connection-management)
3. [Staff Communication System](#staff-communication-system)
4. [Proximity Notifications](#proximity-notifications)
5. [Real-time Bus Tracking](#real-time-bus-tracking)
6. [Message Types Reference](#message-types-reference)
7. [React Hooks & Components](#react-hooks--components)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)

---

## 🔧 Setup & Authentication

### Installation

```bash
npm install ws @types/ws
# or
yarn add ws @types/ws
```

### Environment Variables

```env
# .env.local
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Authentication Setup

```typescript
// lib/auth.ts
export interface User {
  id: string;
  email: string;
  role:
    | "PASSENGER"
    | "BUS_DRIVER"
    | "QUEUE_REGULATOR"
    | "CONTROL_STAFF"
    | "ADMIN";
  first_name: string;
  last_name: string;
}

export interface AuthToken {
  access_token: string;
  user: User;
}

// Get JWT token from your authentication system
export const getAuthToken = (): string | null => {
  return localStorage.getItem("access_token");
};

export const getCurrentUser = (): User | null => {
  const userStr = localStorage.getItem("user");
  return userStr ? JSON.parse(userStr) : null;
};
```

---

## 🔌 WebSocket Connection Management

### Core WebSocket Hook

```typescript
// hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from "react";

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  isAuthenticated: boolean;
  sendMessage: (type: string, data?: any) => void;
  lastMessage: WebSocketMessage | null;
  connectionError: string | null;
  connect: () => void;
  disconnect: () => void;
}

export const useWebSocket = (): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    const token = getAuthToken();
    if (!token) {
      setConnectionError("No authentication token available");
      return;
    }

    try {
      const wsUrl = `${process.env.NEXT_PUBLIC_WEBSOCKET_URL}/ws/connect?token=${token}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log("✅ WebSocket connected");
        setIsConnected(true);
        setConnectionError(null);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);

          // Handle authentication response
          if (message.type === "authenticated") {
            setIsAuthenticated(true);
            console.log("🔐 WebSocket authenticated");
          } else if (message.type === "auth_error") {
            setIsAuthenticated(false);
            setConnectionError(message.message || "Authentication failed");
          }
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log("🔌 WebSocket disconnected:", event.code, event.reason);
        setIsConnected(false);
        setIsAuthenticated(false);

        // Auto-reconnect after 3 seconds
        if (event.code !== 1000) {
          // Not a normal closure
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log("🔄 Attempting to reconnect...");
            connect();
          }, 3000);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
        setConnectionError("Connection failed");
      };
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
      setConnectionError("Failed to create connection");
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close(1000, "User disconnected");
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsAuthenticated(false);
  }, []);

  const sendMessage = useCallback((type: string, data?: any) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn("WebSocket not connected");
      return;
    }

    const message = { type, ...data };
    wsRef.current.send(JSON.stringify(message));
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected,
    isAuthenticated,
    sendMessage,
    lastMessage,
    connectionError,
    connect,
    disconnect,
  };
};
```

### WebSocket Provider

```typescript
// contexts/WebSocketContext.tsx
import React, { createContext, useContext, ReactNode } from "react";
import { useWebSocket, UseWebSocketReturn } from "../hooks/useWebSocket";

const WebSocketContext = createContext<UseWebSocketReturn | null>(null);

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const webSocket = useWebSocket();

  return (
    <WebSocketContext.Provider value={webSocket}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = (): UseWebSocketReturn => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error(
      "useWebSocketContext must be used within a WebSocketProvider"
    );
  }
  return context;
};
```

---

## 🗣️ Staff Communication System

### Staff Communication Hook

```typescript
// hooks/useStaffCommunication.ts
import { useEffect, useState } from "react";
import { useWebSocketContext } from "../contexts/WebSocketContext";

export interface ChatMessage {
  id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  timestamp: string;
  message_type: "TEXT" | "EMERGENCY" | "BROADCAST";
}

export interface EmergencyAlert {
  id: string;
  alert_type: "VEHICLE_ISSUE" | "SAFETY_CONCERN" | "GENERAL";
  message: string;
  sender_id: string;
  location?: { latitude: number; longitude: number };
  timestamp: string;
}

export const useStaffCommunication = () => {
  const { sendMessage, lastMessage, isAuthenticated } = useWebSocketContext();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [emergencyAlerts, setEmergencyAlerts] = useState<EmergencyAlert[]>([]);

  // Join control center communication room
  useEffect(() => {
    if (isAuthenticated) {
      sendMessage("join_room", { room_id: "control_center:communications" });
    }
  }, [isAuthenticated, sendMessage]);

  // Handle incoming messages
  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case "new_message":
        setMessages((prev) => [
          ...prev,
          {
            id: lastMessage.message_id,
            sender_id: lastMessage.sender_id,
            sender_name: lastMessage.sender_name,
            content: lastMessage.content,
            timestamp: lastMessage.timestamp,
            message_type: lastMessage.message_type || "TEXT",
          },
        ]);
        break;

      case "emergency_alert":
        setEmergencyAlerts((prev) => [
          ...prev,
          {
            id: lastMessage.id,
            alert_type: lastMessage.alert_type,
            message: lastMessage.message,
            sender_id: lastMessage.sender_id,
            location: lastMessage.location,
            timestamp: lastMessage.timestamp,
          },
        ]);
        break;

      case "notification":
        if (lastMessage.type === "ADMIN_BROADCAST") {
          setMessages((prev) => [
            ...prev,
            {
              id: lastMessage.id,
              sender_id: "system",
              sender_name: "Control Center",
              content: lastMessage.message,
              timestamp: lastMessage.timestamp,
              message_type: "BROADCAST",
            },
          ]);
        }
        break;
    }
  }, [lastMessage]);

  // Send direct message to another staff member
  const sendDirectMessage = (recipientId: string, message: string) => {
    sendMessage("send_message", {
      recipient_id: recipientId,
      message,
      message_type: "TEXT",
    });
  };

  // Send emergency alert (for drivers/regulators)
  const sendEmergencyAlert = (
    alertType: string,
    message: string,
    location?: { latitude: number; longitude: number }
  ) => {
    sendMessage("emergency_alert", {
      alert_type: alertType,
      message,
      location,
    });
  };

  // Send admin broadcast (for control staff)
  const sendAdminBroadcast = (
    message: string,
    targetRoles: string[] = ["BUS_DRIVER", "QUEUE_REGULATOR"],
    priority: string = "NORMAL"
  ) => {
    sendMessage("admin_broadcast", {
      message,
      target_roles: targetRoles,
      priority,
    });
  };

  return {
    messages,
    emergencyAlerts,
    sendDirectMessage,
    sendEmergencyAlert,
    sendAdminBroadcast,
  };
};
```

### Staff Communication Component

```typescript
// components/StaffCommunication.tsx
import React, { useState } from "react";
import { useStaffCommunication } from "../hooks/useStaffCommunication";
import { getCurrentUser } from "../lib/auth";

export const StaffCommunication: React.FC = () => {
  const {
    messages,
    emergencyAlerts,
    sendDirectMessage,
    sendEmergencyAlert,
    sendAdminBroadcast,
  } = useStaffCommunication();
  const [newMessage, setNewMessage] = useState("");
  const [emergencyMessage, setEmergencyMessage] = useState("");
  const [broadcastMessage, setBroadcastMessage] = useState("");
  const currentUser = getCurrentUser();

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (newMessage.trim()) {
      // For demo - in real app, you'd select recipient
      sendDirectMessage("recipient_id", newMessage);
      setNewMessage("");
    }
  };

  const handleEmergencyAlert = (e: React.FormEvent) => {
    e.preventDefault();
    if (emergencyMessage.trim()) {
      sendEmergencyAlert("GENERAL", emergencyMessage);
      setEmergencyMessage("");
    }
  };

  const handleBroadcast = (e: React.FormEvent) => {
    e.preventDefault();
    if (broadcastMessage.trim()) {
      sendAdminBroadcast(broadcastMessage);
      setBroadcastMessage("");
    }
  };

  return (
    <div className="staff-communication">
      <h2>Staff Communication</h2>

      {/* Emergency Alerts */}
      {emergencyAlerts.length > 0 && (
        <div className="emergency-alerts">
          <h3>🚨 Emergency Alerts</h3>
          {emergencyAlerts.map((alert) => (
            <div key={alert.id} className="alert emergency">
              <strong>{alert.alert_type}</strong>: {alert.message}
              <small>{new Date(alert.timestamp).toLocaleTimeString()}</small>
            </div>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="messages">
        <h3>💬 Messages</h3>
        <div className="message-list">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.message_type.toLowerCase()}`}
            >
              <strong>{message.sender_name}</strong>: {message.content}
              <small>{new Date(message.timestamp).toLocaleTimeString()}</small>
            </div>
          ))}
        </div>
      </div>

      {/* Send Message */}
      <form onSubmit={handleSendMessage} className="send-message">
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Type a message..."
        />
        <button type="submit">Send</button>
      </form>

      {/* Emergency Alert (for drivers/regulators) */}
      {currentUser?.role === "BUS_DRIVER" ||
      currentUser?.role === "QUEUE_REGULATOR" ? (
        <form onSubmit={handleEmergencyAlert} className="emergency-form">
          <input
            type="text"
            value={emergencyMessage}
            onChange={(e) => setEmergencyMessage(e.target.value)}
            placeholder="Emergency alert message..."
          />
          <button type="submit" className="emergency-btn">
            🚨 Send Emergency Alert
          </button>
        </form>
      ) : null}

      {/* Admin Broadcast (for control staff) */}
      {currentUser?.role === "CONTROL_STAFF" ||
      currentUser?.role === "ADMIN" ? (
        <form onSubmit={handleBroadcast} className="broadcast-form">
          <input
            type="text"
            value={broadcastMessage}
            onChange={(e) => setBroadcastMessage(e.target.value)}
            placeholder="Broadcast message to all staff..."
          />
          <button type="submit" className="broadcast-btn">
            📢 Broadcast
          </button>
        </form>
      ) : null}
    </div>
  );
};
```

---

## 📍 Proximity Notifications

### Geolocation Hook

```typescript
// hooks/useGeolocation.ts
import { useState, useEffect } from "react";

export interface GeolocationPosition {
  latitude: number;
  longitude: number;
  accuracy: number;
}

export const useGeolocation = () => {
  const [position, setPosition] = useState<GeolocationPosition | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported");
      setIsLoading(false);
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setPosition({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
        setError(null);
        setIsLoading(false);
      },
      (err) => {
        setError(err.message);
        setIsLoading(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, []);

  return { position, error, isLoading };
};
```

### Proximity Notifications Hook

```typescript
// hooks/useProximityNotifications.ts
import { useEffect, useState } from "react";
import { useWebSocketContext } from "../contexts/WebSocketContext";
import { useGeolocation } from "./useGeolocation";

export interface ProximityAlert {
  id: string;
  bus_id: string;
  stop_id: string;
  stop_name: string;
  distance: number;
  eta_minutes: number;
  message: string;
  timestamp: string;
}

export interface ProximityPreferences {
  enabled: boolean;
  radius_meters: number;
  interested_stops: string[];
  notification_types: ("APPROACHING" | "ARRIVING" | "DEPARTED")[];
}

export const useProximityNotifications = () => {
  const { sendMessage, lastMessage, isAuthenticated } = useWebSocketContext();
  const { position } = useGeolocation();
  const [alerts, setAlerts] = useState<ProximityAlert[]>([]);
  const [preferences, setPreferences] = useState<ProximityPreferences>({
    enabled: true,
    radius_meters: 500,
    interested_stops: [],
    notification_types: ["APPROACHING", "ARRIVING"],
  });

  // Send location and preferences to server
  useEffect(() => {
    if (isAuthenticated && position && preferences.enabled) {
      sendMessage("set_proximity_preferences", {
        enabled: preferences.enabled,
        radius_meters: preferences.radius_meters,
        current_location: {
          latitude: position.latitude,
          longitude: position.longitude,
        },
        interested_stops: preferences.interested_stops,
        notification_types: preferences.notification_types,
      });
    }
  }, [isAuthenticated, position, preferences, sendMessage]);

  // Handle proximity alerts
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "proximity_alert") {
      const alert: ProximityAlert = {
        id: lastMessage.id || Date.now().toString(),
        bus_id: lastMessage.bus_id,
        stop_id: lastMessage.stop_id,
        stop_name: lastMessage.stop_name,
        distance: lastMessage.distance,
        eta_minutes: lastMessage.eta_minutes,
        message: lastMessage.message,
        timestamp: lastMessage.timestamp || new Date().toISOString(),
      };

      setAlerts((prev) => [alert, ...prev.slice(0, 9)]); // Keep last 10 alerts

      // Show browser notification if permission granted
      if (Notification.permission === "granted") {
        new Notification(`Bus Approaching`, {
          body: alert.message,
          icon: "/bus-icon.png",
        });
      }
    }
  }, [lastMessage]);

  // Request notification permission
  const requestNotificationPermission = async () => {
    if ("Notification" in window) {
      const permission = await Notification.requestPermission();
      return permission === "granted";
    }
    return false;
  };

  // Update preferences
  const updatePreferences = (newPreferences: Partial<ProximityPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...newPreferences }));
  };

  return {
    alerts,
    preferences,
    updatePreferences,
    requestNotificationPermission,
    currentLocation: position,
  };
};
```

---

## 🚌 Real-time Bus Tracking

### Bus Tracking Hook

```typescript
// hooks/useBusTracking.ts
import { useEffect, useState } from "react";
import { useWebSocketContext } from "../contexts/WebSocketContext";

export interface BusLocation {
  bus_id: string;
  route_id: string;
  latitude: number;
  longitude: number;
  heading: number;
  speed: number;
  next_stop_id?: string;
  distance_to_next_stop?: number;
  timestamp: string;
  status: "IN_TRANSIT" | "AT_STOP" | "OFFLINE";
}

export interface BusArrival {
  bus_id: string;
  stop_id: string;
  stop_name: string;
  latitude: number;
  longitude: number;
  timestamp: string;
}

export const useBusTracking = () => {
  const { sendMessage, lastMessage, isAuthenticated } = useWebSocketContext();
  const [busLocations, setBusLocations] = useState<Map<string, BusLocation>>(
    new Map()
  );
  const [busArrivals, setBusArrivals] = useState<BusArrival[]>([]);
  const [subscribedRoutes, setSubscribedRoutes] = useState<Set<string>>(
    new Set()
  );
  const [subscribedBuses, setSubscribedBuses] = useState<Set<string>>(
    new Set()
  );

  // Subscribe to all bus tracking on authentication
  useEffect(() => {
    if (isAuthenticated) {
      sendMessage("subscribe_all_buses");
      sendMessage("join_room", { room_id: "all_bus_tracking" });
    }
  }, [isAuthenticated, sendMessage]);

  // Handle incoming bus updates
  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case "bus_location_update":
        const location: BusLocation = {
          bus_id: lastMessage.bus_id,
          route_id: lastMessage.route_id,
          latitude: lastMessage.latitude,
          longitude: lastMessage.longitude,
          heading: lastMessage.heading || 0,
          speed: lastMessage.speed || 0,
          next_stop_id: lastMessage.next_stop_id,
          distance_to_next_stop: lastMessage.distance_to_next_stop,
          timestamp: lastMessage.timestamp,
          status: lastMessage.status || "IN_TRANSIT",
        };

        setBusLocations((prev) => new Map(prev.set(location.bus_id, location)));
        break;

      case "bus_arrival":
        const arrival: BusArrival = {
          bus_id: lastMessage.bus_id,
          stop_id: lastMessage.stop_id,
          stop_name: lastMessage.stop_name,
          latitude: lastMessage.latitude,
          longitude: lastMessage.longitude,
          timestamp: lastMessage.timestamp,
        };

        setBusArrivals((prev) => [arrival, ...prev.slice(0, 19)]); // Keep last 20 arrivals
        break;

      case "all_bus_locations":
        // Handle bulk bus location updates
        if (lastMessage.buses && Array.isArray(lastMessage.buses)) {
          const newLocations = new Map(busLocations);
          lastMessage.buses.forEach((bus: BusLocation) => {
            newLocations.set(bus.bus_id, bus);
          });
          setBusLocations(newLocations);
        }
        break;
    }
  }, [lastMessage, busLocations]);

  // Subscribe to specific route tracking
  const subscribeToRoute = (routeId: string) => {
    if (!subscribedRoutes.has(routeId)) {
      sendMessage("subscribe_route_tracking", { route_id: routeId });
      sendMessage("join_room", { room_id: `route_tracking:${routeId}` });
      setSubscribedRoutes((prev) => new Set(prev.add(routeId)));
    }
  };

  // Subscribe to specific bus tracking
  const subscribeToBus = (busId: string) => {
    if (!subscribedBuses.has(busId)) {
      sendMessage("subscribe_bus_tracking", { bus_id: busId });
      sendMessage("join_room", { room_id: `bus_tracking:${busId}` });
      setSubscribedBuses((prev) => new Set(prev.add(busId)));
    }
  };

  // Get route with buses
  const getRouteWithBuses = (routeId: string) => {
    sendMessage("get_route_with_buses", { route_id: routeId });
  };

  // Calculate ETA for bus to stop
  const calculateETA = (busId: string, stopId: string) => {
    sendMessage("calculate_eta", { bus_id: busId, stop_id: stopId });
  };

  // Get buses for a specific route
  const getBusesForRoute = (routeId: string): BusLocation[] => {
    return Array.from(busLocations.values()).filter(
      (bus) => bus.route_id === routeId
    );
  };

  // Get active buses (updated in last 5 minutes)
  const getActiveBuses = (): BusLocation[] => {
    const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
    return Array.from(busLocations.values()).filter(
      (bus) => new Date(bus.timestamp).getTime() > fiveMinutesAgo
    );
  };

  return {
    busLocations: Array.from(busLocations.values()),
    busArrivals,
    subscribedRoutes: Array.from(subscribedRoutes),
    subscribedBuses: Array.from(subscribedBuses),
    subscribeToRoute,
    subscribeToBus,
    getRouteWithBuses,
    calculateETA,
    getBusesForRoute,
    getActiveBuses,
  };
};
```

---

## 📋 Message Types Reference

### Outgoing Messages (Client → Server)

```typescript
// Authentication & Connection
{ type: 'ping', timestamp: string }

// Room Management
{ type: 'join_room', room_id: string }
{ type: 'leave_room', room_id: string }

// Bus Tracking
{ type: 'subscribe_all_buses' }
{ type: 'subscribe_bus_tracking', bus_id: string }
{ type: 'subscribe_route_tracking', route_id: string }
{ type: 'get_route_with_buses', route_id: string }
{ type: 'calculate_eta', bus_id: string, stop_id: string }

// Staff Communication
{ type: 'send_message', recipient_id: string, message: string, message_type: 'TEXT' | 'EMERGENCY' }
{ type: 'emergency_alert', alert_type: string, message: string, location?: { latitude: number, longitude: number } }
{ type: 'admin_broadcast', message: string, target_roles: string[], priority: string }

// Chat Features
{ type: 'join_conversation', conversation_id: string }
{ type: 'typing_indicator', conversation_id: string, is_typing: boolean }
{ type: 'mark_message_read', conversation_id: string, message_id: string }

// Proximity Notifications
{ type: 'set_proximity_preferences', enabled: boolean, radius_meters: number, current_location: { latitude: number, longitude: number }, interested_stops: string[] }
```

### Incoming Messages (Server → Client)

```typescript
// Authentication
{ type: 'authenticated', user_id: string, connection_id: string, message: string }
{ type: 'auth_error', message: string }

// Connection
{ type: 'pong', timestamp: string, server_time: string }
{ type: 'error', message: string }

// Room Management
{ type: 'room_joined', room_id: string, message: string }
{ type: 'room_left', room_id: string, message: string }

// Bus Tracking
{ type: 'bus_location_update', bus_id: string, route_id: string, latitude: number, longitude: number, heading: number, speed: number, timestamp: string, status: string }
{ type: 'bus_arrival', bus_id: string, stop_id: string, stop_name: string, latitude: number, longitude: number, timestamp: string }
{ type: 'all_bus_locations', buses: BusLocation[] }

// Staff Communication
{ type: 'new_message', message_id: string, sender_id: string, sender_name: string, content: string, timestamp: string, message_type: string }
{ type: 'emergency_alert', id: string, alert_type: string, message: string, sender_id: string, location?: object, timestamp: string }

// Notifications
{ type: 'notification', id: string, title: string, message: string, priority: string, timestamp: string }
{ type: 'proximity_alert', id: string, bus_id: string, stop_id: string, stop_name: string, distance: number, eta_minutes: number, message: string, timestamp: string }

// Chat Features
{ type: 'conversation_joined', conversation_id: string, room_id: string, message: string }
{ type: 'typing_status', conversation_id: string, user_id: string, is_typing: boolean, timestamp: string }
{ type: 'message_read', conversation_id: string, user_id: string, message_id: string, timestamp: string }
```

---

## 🎯 Complete Integration Example

### Main App Setup

```typescript
// pages/_app.tsx
import { WebSocketProvider } from "../contexts/WebSocketContext";
import type { AppProps } from "next/app";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <WebSocketProvider>
      <Component {...pageProps} />
    </WebSocketProvider>
  );
}
```

### Dashboard Component

```typescript
// components/Dashboard.tsx
import React from "react";
import { StaffCommunication } from "./StaffCommunication";
import { ProximityNotifications } from "./ProximityNotifications";
import { BusTrackingMap } from "./BusTrackingMap";
import { useWebSocketContext } from "../contexts/WebSocketContext";
import { getCurrentUser } from "../lib/auth";

export const Dashboard: React.FC = () => {
  const { isConnected, isAuthenticated, connectionError } =
    useWebSocketContext();
  const currentUser = getCurrentUser();

  if (!currentUser) {
    return <div>Please log in to access the dashboard</div>;
  }

  return (
    <div className="dashboard">
      <header>
        <h1>GuzoSync Dashboard</h1>
        <div className="connection-status">
          {isConnected ? (
            isAuthenticated ? (
              <span className="status connected">
                🟢 Connected & Authenticated
              </span>
            ) : (
              <span className="status connecting">
                🟡 Connected, Authenticating...
              </span>
            )
          ) : (
            <span className="status disconnected">🔴 Disconnected</span>
          )}
          {connectionError && (
            <span className="error">❌ {connectionError}</span>
          )}
        </div>
      </header>

      <div className="dashboard-grid">
        {/* Bus Tracking Map */}
        <div className="map-section">
          <BusTrackingMap />
        </div>

        {/* Staff Communication */}
        {(currentUser.role === "CONTROL_STAFF" ||
          currentUser.role === "BUS_DRIVER" ||
          currentUser.role === "QUEUE_REGULATOR") && (
          <div className="communication-section">
            <StaffCommunication />
          </div>
        )}

        {/* Proximity Notifications for Passengers */}
        {currentUser.role === "PASSENGER" && (
          <div className="notifications-section">
            <ProximityNotifications />
          </div>
        )}
      </div>
    </div>
  );
};
```

---

## ⚠️ Error Handling & Best Practices

### Error Handling

```typescript
// hooks/useWebSocketErrorHandler.ts
import { useEffect } from "react";
import { useWebSocketContext } from "../contexts/WebSocketContext";

export const useWebSocketErrorHandler = () => {
  const { lastMessage, connectionError } = useWebSocketContext();

  useEffect(() => {
    if (lastMessage?.type === "error") {
      console.error("WebSocket error:", lastMessage.message);

      // Handle specific error types
      switch (lastMessage.code) {
        case "AUTH_EXPIRED":
          // Redirect to login
          window.location.href = "/login";
          break;
        case "RATE_LIMITED":
          // Show rate limit warning
          alert("Too many requests. Please slow down.");
          break;
        default:
          // Show generic error
          console.warn("WebSocket error:", lastMessage.message);
      }
    }

    if (connectionError) {
      console.error("Connection error:", connectionError);
    }
  }, [lastMessage, connectionError]);
};
```

### Best Practices

1. **Connection Management**

   ```typescript
   // Always check connection status before sending messages
   const sendMessage = useCallback(
     (type: string, data?: any) => {
       if (!isConnected || !isAuthenticated) {
         console.warn("Cannot send message: not connected or authenticated");
         return false;
       }
       // Send message...
     },
     [isConnected, isAuthenticated]
   );
   ```

2. **Memory Management**

   ```typescript
   // Limit stored messages to prevent memory leaks
   const [messages, setMessages] = useState<Message[]>([]);

   const addMessage = (message: Message) => {
     setMessages((prev) => [message, ...prev.slice(0, 99)]); // Keep last 100 messages
   };
   ```

3. **Performance Optimization**

   ```typescript
   // Debounce location updates
   import { useDebouncedCallback } from "use-debounce";

   const debouncedLocationUpdate = useDebouncedCallback(
     (location: GeolocationPosition) => {
       sendMessage("update_location", {
         latitude: location.latitude,
         longitude: location.longitude,
       });
     },
     1000 // Update at most once per second
   );
   ```

4. **Offline Handling**

   ```typescript
   // Handle offline/online events
   useEffect(() => {
     const handleOnline = () => {
       console.log("Back online, reconnecting...");
       connect();
     };

     const handleOffline = () => {
       console.log("Gone offline");
     };

     window.addEventListener("online", handleOnline);
     window.addEventListener("offline", handleOffline);

     return () => {
       window.removeEventListener("online", handleOnline);
       window.removeEventListener("offline", handleOffline);
     };
   }, [connect]);
   ```

---

## 🚀 Quick Start Checklist

1. **✅ Install Dependencies**

   ```bash
   npm install ws @types/ws
   ```

2. **✅ Setup Environment Variables**

   ```env
   NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000
   ```

3. **✅ Add WebSocket Provider to App**

   ```typescript
   // pages/_app.tsx
   <WebSocketProvider>
     <Component {...pageProps} />
   </WebSocketProvider>
   ```

4. **✅ Implement Authentication**

   - Store JWT token in localStorage
   - Pass token in WebSocket connection URL

5. **✅ Use Hooks in Components**

   ```typescript
   const { isConnected, sendMessage } = useWebSocketContext();
   const { busLocations } = useBusTracking();
   const { alerts } = useProximityNotifications();
   ```

6. **✅ Handle Real-time Updates**
   - Subscribe to relevant rooms/events
   - Update UI based on incoming messages
   - Implement error handling

---

## 📚 Additional Resources

- **WebSocket API Documentation**: `/ws/connect` endpoint
- **Message Types**: See reference section above
- **Authentication**: JWT token required in query parameter
- **Rate Limiting**: Max 100 messages per minute per connection
- **Browser Support**: Modern browsers with WebSocket support

This documentation provides everything needed to integrate GuzoSync's real-time features into a Next.js frontend application. All features have been tested and verified to work with the WebSocket backend implementation.
