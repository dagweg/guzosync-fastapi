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

  const handleBusClick = (bus: Bus) => {
    setSelectedBus(bus.id);
    toast.success(`Selected bus: ${bus.license_plate}`);
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
            <div className="flex-1">
              <Map
                buses={buses || []}
                busStops={busStops || []}
                routes={routes || []}
                selectedBus={selectedBus || ""}
                onBusClick={handleBusClick}
                onLocationUpdate={handleLocationUpdate}
              />
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
