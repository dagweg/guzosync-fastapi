"use client";

import { useState } from "react";
import { Bus } from "@/types";
import { useWebSocket } from "./WebSocketProvider";
import { BusIcon, MapPinIcon, ClockIcon } from "lucide-react";

interface BusTrackerProps {
  buses?: Bus[];
  selectedBus?: string;
  onBusSelect?: (busId: string) => void;
  userRole?: string;
}

export default function BusTracker({
  buses = [],
  selectedBus = "",
  onBusSelect = () => {},
  userRole,
}: BusTrackerProps) {
  const { busLocations, wsClient } = useWebSocket();
  const [searchTerm, setSearchTerm] = useState("");

  // Filter buses based on search term
  const filteredBuses = buses.filter(
    (bus) =>
      bus.license_plate.toLowerCase().includes(searchTerm.toLowerCase()) ||
      bus.bus_model?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getBusStatusColor = (status: string) => {
    switch (status) {
      case "OPERATIONAL":
        return "text-green-600 bg-green-100";
      case "IDLE":
        return "text-yellow-600 bg-yellow-100";
      case "MAINTENANCE":
      case "BREAKDOWN":
        return "text-red-600 bg-red-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  const formatLastUpdate = (timestamp?: string) => {
    if (!timestamp) return "No data";
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Bus Tracker</h2>
        <span className="text-sm text-gray-500">{buses.length} buses</span>
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search buses..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
        />
      </div>

      {/* Bus List */}
      <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
        {filteredBuses.map((bus) => {
          const realtimeLocation = busLocations.get(bus.id);
          const isSelected = selectedBus === bus.id;

          return (
            <div
              key={bus.id}
              onClick={() => onBusSelect(bus.id)}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                isSelected
                  ? "border-primary-500 bg-primary-50"
                  : "border-gray-200 hover:border-gray-300 bg-white"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <BusIcon className="w-4 h-4 text-gray-600" />
                  <div>
                    <h3 className="font-medium text-sm">{bus.license_plate}</h3>
                    <p className="text-xs text-gray-500">{bus.bus_type}</p>
                  </div>
                </div>

                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${getBusStatusColor(
                    bus.bus_status
                  )}`}
                >
                  {bus.bus_status}
                </span>
              </div>

              {/* Real-time info */}
              {realtimeLocation && (
                <div className="mt-2 pt-2 border-t border-gray-100">
                  <div className="flex items-center gap-4 text-xs text-gray-600">
                    {realtimeLocation.speed && (
                      <div className="flex items-center gap-1">
                        <span>{Math.round(realtimeLocation.speed)} km/h</span>
                      </div>
                    )}
                    <div className="flex items-center gap-1">
                      <ClockIcon className="w-3 h-3" />
                      <span>
                        {formatLastUpdate(realtimeLocation.location.timestamp)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 mt-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-xs text-green-600 font-medium">
                      Live
                    </span>
                  </div>
                </div>
              )}

              {/* Static location info */}
              {!realtimeLocation && bus.current_location && (
                <div className="mt-2 pt-2 border-t border-gray-100">
                  <div className="flex items-center gap-1 text-xs text-gray-600">
                    <MapPinIcon className="w-3 h-3" />
                    <span>
                      Last: {formatLastUpdate(bus.last_location_update)}
                    </span>
                  </div>
                </div>
              )}

              {/* Bus details */}
              <div className="mt-2 text-xs text-gray-500">
                <div className="flex justify-between">
                  <span>Capacity: {bus.capacity}</span>
                  {bus.bus_model && <span>{bus.bus_model}</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {filteredBuses.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <BusIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No buses found</p>
        </div>
      )}

      {/* Admin controls */}
      {userRole === "CONTROL_ADMIN" && selectedBus && (
        <div className="mt-4 p-3 bg-blue-50 rounded-lg">
          <h3 className="text-sm font-medium text-blue-900 mb-2">
            Admin Controls
          </h3>
          <p className="text-xs text-blue-700">
            Selected bus:{" "}
            {buses.find((b) => b.id === selectedBus)?.license_plate}
          </p>
          <p className="text-xs text-blue-600 mt-1">
            Click on the map to update this bus's location
          </p>
        </div>
      )}
    </div>
  );
}
