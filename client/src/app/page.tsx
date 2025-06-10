"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Bus, BusStop, Route, User, Location } from "@/types";
import { apiClient } from "@/lib/api";
import { useWebSocket } from "@/components/WebSocketProvider";
import Map from "@/components/Map";
import BusTracker from "@/components/BusTracker";
import ChatPanel from "@/components/ChatPanel";
import NotificationPanel from "@/components/NotificationPanel";
import ConnectionTest from "@/components/ConnectionTest";
import toast from "react-hot-toast";
import {
  MapIcon,
  MessageSquareIcon,
  BellIcon,
  LogOutIcon,
  UserIcon,
} from "lucide-react";

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [buses, setBuses] = useState<Bus[]>([]);
  const [busStops, setBusStops] = useState<BusStop[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [selectedBus, setSelectedBus] = useState<string>("");
  const [selectedRoute, setSelectedRoute] = useState<string>("");
  const [busDetails, setBusDetails] = useState<any>(null);
  const [activePanel, setActivePanel] = useState<
    "map" | "chat" | "notifications"
  >("map");
  const [isLoading, setIsLoading] = useState(true);

  const router = useRouter();
  const { isConnected } = useWebSocket();

  // Check authentication and load initial data
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    loadInitialData();
  }, [router]);

  const loadInitialData = async () => {
    try {
      setIsLoading(true);

      // Load user data
      const userData = await apiClient.getCurrentUser();
      setUser(userData);

      // Load buses, stops, and routes in parallel
      const [busesData, stopsData, routesData] = await Promise.all([
        apiClient.getBuses(),
        apiClient.getBusStops(),
        apiClient.getRoutes(),
      ]);

      setBuses(busesData);
      setBusStops(stopsData);
      setRoutes(routesData);

      toast.success("Data loaded successfully");
    } catch (error: any) {
      console.error("Error loading data:", error);
      toast.error("Failed to load data");

      if (error.response?.status === 401) {
        router.push("/login");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleBusClick = async (bus: Bus) => {
    setSelectedBus(bus.id);
    toast.success(`Selected bus: ${bus.license_plate}`);

    // Fetch detailed bus information
    try {
      const details = await apiClient.getBusDetails(bus.id);
      setBusDetails(details);

      // If bus has a route, set it as selected to show the route shape
      if (details.current_route?.id) {
        setSelectedRoute(details.current_route.id);
        toast.info(`Showing route: ${details.current_route.name}`);
      } else if (bus.assigned_route_id) {
        setSelectedRoute(bus.assigned_route_id);
        // Load route details
        const route = await apiClient.getRoute(bus.assigned_route_id);
        toast.info(`Showing route: ${route.name}`);
      }
    } catch (error) {
      console.error("Error fetching bus details:", error);
      toast.error("Failed to load bus details");
    }
  };

  const handleLocationUpdate = async (busId: string, location: Location) => {
    if (!user || user.role !== "CONTROL_ADMIN") {
      toast.error("Only admins can update bus locations");
      return;
    }

    try {
      await apiClient.updateBusLocation(busId, location);
      toast.success("Bus location updated");
    } catch (error) {
      console.error("Error updating bus location:", error);
      toast.error("Failed to update bus location");
    }
  };

  const handleLogout = async () => {
    try {
      await apiClient.logout();
      router.push("/login");
    } catch (error) {
      console.error("Logout error:", error);
      // Still redirect even if logout fails
      localStorage.removeItem("access_token");
      router.push("/login");
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading GuzoSync...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-900">GuzoSync</h1>
            <div
              className={`flex items-center gap-2 px-2 py-1 rounded-full text-xs ${
                isConnected
                  ? "bg-green-100 text-green-800"
                  : "bg-red-100 text-red-800"
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  isConnected ? "bg-green-500" : "bg-red-500"
                }`}
              ></div>
              {isConnected ? "Connected" : "Disconnected"}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <UserIcon className="w-4 h-4" />
              <span>
                {user?.first_name} {user?.last_name}
              </span>
              <span className="px-2 py-1 bg-primary-100 text-primary-800 rounded-full text-xs">
                {user?.role}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md"
            >
              <LogOutIcon className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 flex">
        {/* Sidebar */}
        <aside className="w-64 bg-white shadow-sm border-r">
          {/* Navigation */}
          <nav className="p-4">
            <div className="space-y-2">
              <button
                onClick={() => setActivePanel("map")}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-left ${
                  activePanel === "map"
                    ? "bg-primary-100 text-primary-900"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <MapIcon className="w-5 h-5" />
                Map View
              </button>
              <button
                onClick={() => setActivePanel("chat")}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-left ${
                  activePanel === "chat"
                    ? "bg-primary-100 text-primary-900"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <MessageSquareIcon className="w-5 h-5" />
                Chat
              </button>
              <button
                onClick={() => setActivePanel("notifications")}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-left ${
                  activePanel === "notifications"
                    ? "bg-primary-100 text-primary-900"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <BellIcon className="w-5 h-5" />
                Notifications
              </button>
            </div>
          </nav>

          {/* Bus Tracker Component */}
          <div className="border-t">
            <BusTracker
              buses={buses || []}
              selectedBus={selectedBus || ""}
              onBusSelect={setSelectedBus}
              userRole={user?.role}
            />
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col">
          {activePanel === "map" && (
            <div className="flex-1 flex">
              <div className="flex-1">
                <Map
                  buses={buses || []}
                  busStops={busStops || []}
                  routes={routes || []}
                  selectedBus={selectedBus || ""}
                  selectedRoute={selectedRoute || ""}
                  onBusClick={handleBusClick}
                  onLocationUpdate={handleLocationUpdate}
                />
              </div>

              {/* Bus Details Panel */}
              {busDetails && (
                <div className="w-80 bg-white border-l shadow-lg overflow-y-auto">
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-bold text-gray-900">
                        Bus Details
                      </h3>
                      <button
                        onClick={() => {
                          setBusDetails(null);
                          setSelectedBus("");
                          setSelectedRoute("");
                        }}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        ✕
                      </button>
                    </div>

                    {/* Basic Bus Info */}
                    <div className="space-y-3 mb-6">
                      <div>
                        <h4 className="font-semibold text-gray-700">
                          License Plate
                        </h4>
                        <p className="text-lg font-mono">
                          {busDetails.license_plate}
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-semibold text-gray-700">Type</h4>
                          <p>{busDetails.bus_type}</p>
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-700">
                            Capacity
                          </h4>
                          <p>{busDetails.capacity} passengers</p>
                        </div>
                      </div>

                      <div>
                        <h4 className="font-semibold text-gray-700">Status</h4>
                        <span
                          className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${
                            busDetails.bus_status === "OPERATIONAL"
                              ? "bg-green-100 text-green-800"
                              : busDetails.bus_status === "IDLE"
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {busDetails.bus_status}
                        </span>
                      </div>
                    </div>

                    {/* Driver Info */}
                    {busDetails.assigned_driver && (
                      <div className="mb-6">
                        <h4 className="font-semibold text-gray-700 mb-2">
                          Driver
                        </h4>
                        <div className="bg-gray-50 p-3 rounded">
                          <p className="font-medium">
                            {busDetails.assigned_driver.first_name}{" "}
                            {busDetails.assigned_driver.last_name}
                          </p>
                          <p className="text-sm text-gray-600">
                            {busDetails.assigned_driver.email}
                          </p>
                          <p className="text-sm text-gray-600">
                            {busDetails.assigned_driver.phone_number}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Current Route Info */}
                    {busDetails.current_route && (
                      <div className="mb-6">
                        <h4 className="font-semibold text-gray-700 mb-2">
                          Current Route
                        </h4>
                        <div className="bg-blue-50 p-3 rounded">
                          <p className="font-medium text-blue-900">
                            {busDetails.current_route.name}
                          </p>
                          {busDetails.current_route.description && (
                            <p className="text-sm text-blue-700">
                              {busDetails.current_route.description}
                            </p>
                          )}

                          {/* Start and End Destinations */}
                          {busDetails.current_route.start_destination && (
                            <div className="mt-2 space-y-1">
                              <div className="flex items-center gap-2 text-sm">
                                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                                <span className="text-gray-600">From:</span>
                                <span className="font-medium">
                                  {
                                    busDetails.current_route.start_destination
                                      .name
                                  }
                                </span>
                              </div>
                              {busDetails.current_route.end_destination && (
                                <div className="flex items-center gap-2 text-sm">
                                  <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                                  <span className="text-gray-600">To:</span>
                                  <span className="font-medium">
                                    {
                                      busDetails.current_route.end_destination
                                        .name
                                    }
                                  </span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Current Trip Info */}
                    {busDetails.current_trip && (
                      <div className="mb-6">
                        <h4 className="font-semibold text-gray-700 mb-2">
                          Current Trip
                        </h4>
                        <div className="bg-green-50 p-3 rounded">
                          <div className="flex justify-between items-center mb-2">
                            <span className="font-medium text-green-900">
                              Trip Status
                            </span>
                            <span
                              className={`px-2 py-1 rounded-full text-xs font-medium ${
                                busDetails.current_trip.status === "IN_PROGRESS"
                                  ? "bg-green-100 text-green-800"
                                  : busDetails.current_trip.status ===
                                    "SCHEDULED"
                                  ? "bg-blue-100 text-blue-800"
                                  : "bg-gray-100 text-gray-800"
                              }`}
                            >
                              {busDetails.current_trip.status}
                            </span>
                          </div>

                          {busDetails.current_trip.scheduled_departure && (
                            <p className="text-sm text-green-700">
                              Departure:{" "}
                              {new Date(
                                busDetails.current_trip.scheduled_departure
                              ).toLocaleTimeString()}
                            </p>
                          )}

                          {busDetails.current_trip.estimated_arrival && (
                            <p className="text-sm text-green-700">
                              Est. Arrival:{" "}
                              {new Date(
                                busDetails.current_trip.estimated_arrival
                              ).toLocaleTimeString()}
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Location Info */}
                    {busDetails.current_location && (
                      <div className="mb-6">
                        <h4 className="font-semibold text-gray-700 mb-2">
                          Location
                        </h4>
                        <div className="bg-gray-50 p-3 rounded text-sm">
                          <p>
                            Lat:{" "}
                            {busDetails.current_location.latitude.toFixed(6)}
                          </p>
                          <p>
                            Lng:{" "}
                            {busDetails.current_location.longitude.toFixed(6)}
                          </p>
                          {busDetails.speed && (
                            <p>Speed: {busDetails.speed} km/h</p>
                          )}
                          {busDetails.heading && (
                            <p>Heading: {busDetails.heading}°</p>
                          )}
                          {busDetails.last_location_update && (
                            <p className="text-gray-600 mt-1">
                              Updated:{" "}
                              {new Date(
                                busDetails.last_location_update
                              ).toLocaleString()}
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {activePanel === "chat" && (
            <div className="flex-1 p-4">
              <ChatPanel />
            </div>
          )}

          {activePanel === "notifications" && (
            <div className="flex-1 p-4">
              <NotificationPanel />
            </div>
          )}
        </main>
      </div>

      {/* Connection Test Component */}
      <ConnectionTest />
    </div>
  );
}
