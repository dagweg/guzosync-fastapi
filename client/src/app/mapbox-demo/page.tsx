"use client";

import { useState, useEffect } from "react";
import Map from "@/components/Map";
import BusTracker from "@/components/BusTracker";
import WebSocketProvider from "@/components/WebSocketProvider";
import { Bus, BusStop, Route } from "@/types";
import axios from "axios";
import toast from "react-hot-toast";
import { apiClient } from "@/lib/api";

export default function MapboxDemo() {
  const [buses, setBuses] = useState<Bus[]>([]);
  const [busStops, setBusStops] = useState<BusStop[]>([]);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [selectedBus, setSelectedBus] = useState<string>("");
  const [selectedRoute, setSelectedRoute] = useState<string>("");
  const [showRouteShapes, setShowRouteShapes] = useState(true);
  const [showETAs, setShowETAs] = useState(true);
  const [loading, setLoading] = useState(true);

  // Load data from API
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("access_token");

      if (!token) {
        toast.error("Please login to access the demo");
        return;
      }

      const headers = { Authorization: `Bearer ${token}` };

      // Load buses, bus stops, and routes in parallel using apiClient
      const [busesData, stopsData, routesData] = await Promise.all([
        apiClient.getBuses(),
        apiClient.getBusStops(),
        apiClient.getRoutes(),
      ]);

      setBuses(busesData);
      setBusStops(stopsData);
      setRoutes(routesData);

      // Select first route by default
      if (routesData.length > 0) {
        setSelectedRoute(routesData[0].id);
      }

      toast.success("Data loaded successfully");
    } catch (error) {
      console.error("Error loading data:", error);
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const handleBusClick = (bus: Bus) => {
    setSelectedBus(bus.id);
    toast.success(`Selected bus: ${bus.license_plate}`);
  };

  const handleLocationUpdate = async (
    busId: string,
    location: { latitude: number; longitude: number }
  ) => {
    try {
      await apiClient.updateBusLocation(busId, {
        latitude: location.latitude,
        longitude: location.longitude,
        timestamp: new Date().toISOString(),
      });

      toast.success("Bus location updated");
    } catch (error) {
      console.error("Error updating location:", error);
      toast.error("Failed to update location");
    }
  };

  const generateRouteShape = async (routeId: string) => {
    try {
      await apiClient.generateRouteShape(routeId);
      toast.success("Route shape generated successfully");
    } catch (error) {
      console.error("Error generating route shape:", error);
      toast.error("Failed to generate route shape");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading Mapbox demo...</p>
        </div>
      </div>
    );
  }

  return (
    <WebSocketProvider>
      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <div className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Mapbox Integration Demo
                </h1>
                <p className="text-sm text-gray-600">
                  Real-time bus tracking with route shapes and ETA calculations
                </p>
              </div>
              <div className="flex items-center space-x-4">
                <button
                  onClick={loadData}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Refresh Data
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Controls Panel */}
            <div className="lg:col-span-1 space-y-6">
              {/* Route Selection */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold text-gray-900 mb-3">
                  Route Selection
                </h3>
                <select
                  value={selectedRoute}
                  onChange={(e) => setSelectedRoute(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select a route</option>
                  {routes.map((route) => (
                    <option key={route.id} value={route.id}>
                      {route.name}
                    </option>
                  ))}
                </select>
                {selectedRoute && (
                  <button
                    onClick={() => generateRouteShape(selectedRoute)}
                    className="mt-2 w-full px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors text-sm"
                  >
                    Generate Route Shape
                  </button>
                )}
              </div>

              {/* Display Options */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold text-gray-900 mb-3">
                  Display Options
                </h3>
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={showRouteShapes}
                      onChange={(e) => setShowRouteShapes(e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Show Route Shapes
                    </span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={showETAs}
                      onChange={(e) => setShowETAs(e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      Show ETAs
                    </span>
                  </label>
                </div>
              </div>

              {/* Stats */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Statistics</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Buses:</span>
                    <span className="font-medium">{buses.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Bus Stops:</span>
                    <span className="font-medium">{busStops.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Routes:</span>
                    <span className="font-medium">{routes.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Operational:</span>
                    <span className="font-medium text-green-600">
                      {
                        buses.filter((b) => b.bus_status === "OPERATIONAL")
                          .length
                      }
                    </span>
                  </div>
                </div>
              </div>

              {/* Bus Tracker */}
              <div className="bg-white rounded-lg shadow">
                <BusTracker
                  buses={buses}
                  selectedBus={selectedBus}
                  onBusSelect={setSelectedBus}
                />
              </div>
            </div>

            {/* Map */}
            <div className="lg:col-span-3">
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="h-[600px]">
                  <Map
                    buses={buses}
                    busStops={busStops}
                    routes={routes}
                    selectedBus={selectedBus}
                    selectedRoute={selectedRoute}
                    showRouteShapes={showRouteShapes}
                    showETAs={showETAs}
                    onBusClick={handleBusClick}
                    onLocationUpdate={handleLocationUpdate}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </WebSocketProvider>
  );
}
