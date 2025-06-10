// User types
export interface User {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: UserRole;
  phone_number: string;
  profile_image?: string;
  is_active: boolean;
  preferred_language?: string;
  created_at: string;
  updated_at: string;
}

export enum UserRole {
  PASSENGER = "PASSENGER",
  BUS_DRIVER = "BUS_DRIVER",
  QUEUE_REGULATOR = "QUEUE_REGULATOR",
  CONTROL_STAFF = "CONTROL_STAFF",
  CONTROL_ADMIN = "CONTROL_ADMIN",
}

// Location types
export interface Location {
  latitude: number;
  longitude: number;
}

// Bus types
export interface Bus {
  id: string;
  license_plate: string;
  bus_type: BusType;
  capacity: number;
  current_location?: Location;
  last_location_update?: string;
  heading?: number;
  speed?: number;
  location_accuracy?: number;
  current_address?: string;
  assigned_route_id?: string;
  assigned_driver_id?: string;
  bus_status: BusStatus;
  manufacture_year?: number;
  bus_model?: string;
  created_at: string;
  updated_at: string;
}

export enum BusType {
  STANDARD = "STANDARD",
  ARTICULATED = "ARTICULATED",
  MINIBUS = "MINIBUS",
}

export enum BusStatus {
  OPERATIONAL = "OPERATIONAL",
  MAINTENANCE = "MAINTENANCE",
  BREAKDOWN = "BREAKDOWN",
  IDLE = "IDLE",
}

// Route types
export interface Route {
  id: string;
  name: string;
  description?: string;
  stop_ids: string[];
  total_distance?: number;
  estimated_duration?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  // Mapbox integration fields
  route_geometry?: any; // GeoJSON LineString
  route_shape_data?: any; // Full Mapbox route response
  last_shape_update?: string;
}

// ETA types
export interface ETAInfo {
  stop_id: string;
  stop_name?: string;
  duration_seconds: number;
  duration_minutes: number;
  distance_meters: number;
  distance_km: number;
  estimated_arrival: string;
  traffic_aware: boolean;
  current_speed_kmh?: number;
  calculated_at: string;
  fallback_calculation?: boolean;
}

export interface BusETAResponse {
  bus_id: string;
  route_id: string;
  current_location: {
    latitude: number;
    longitude: number;
  };
  current_speed_kmh?: number;
  stop_etas: ETAInfo[];
  calculated_at: string;
}

export interface RouteShapeResponse {
  route_id: string;
  geometry: any; // GeoJSON LineString
  distance_meters: number;
  duration_seconds: number;
  profile: string;
  created_at: string;
}

// Bus Stop types
export interface BusStop {
  id: string;
  name: string;
  location: Location;
  capacity?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// WebSocket message types
export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface BusLocationUpdate {
  type: "bus_location_update";
  bus_id: string;
  location: {
    latitude: number;
    longitude: number;
    timestamp: string;
  };
  speed?: number;
  heading?: number;
  status?: string;
}

export interface BusETAUpdate {
  type: "bus_eta_update";
  bus_id: string;
  route_id: string;
  stop_etas: ETAInfo[];
  calculated_at: string;
}

export interface ChatMessage {
  type: "chat_message";
  conversation_id: string;
  message: {
    id: string;
    sender_id: string;
    sender_name: string;
    content: string;
    timestamp: string;
    message_type: string;
  };
}

export interface NotificationMessage {
  type: "notification";
  notification: {
    id: string;
    title: string;
    message: string;
    type: string;
    priority: string;
    timestamp: string;
    data?: any;
  };
}

// API Response types
export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
}

export interface ApiResponse<T> {
  data?: T;
  message?: string;
  error?: string;
}

// Auth types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  phone_number: string;
  role?: UserRole;
}
