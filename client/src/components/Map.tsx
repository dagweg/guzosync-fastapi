"use client";

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { Bus, BusStop, Route, Location } from "@/types";
import { useWebSocket } from "./WebSocketProvider";
import axios from "axios";

// Set Mapbox access token
const mapboxToken =
  process.env.MAPBOX_ACCESS_TOKEN ||
  process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN;
if (
  mapboxToken &&
  mapboxToken !==
    "pk.eyJ1IjoiZ3V6b3N5bmMiLCJhIjoiY2xvZGVtbzAwMDAwMDNxbzJkZGZkZGZkZiJ9.example_token_replace_with_real_one"
) {
  mapboxgl.accessToken = mapboxToken;
} else {
  console.warn(
    "⚠️ Mapbox access token not configured. Please add MAPBOX_ACCESS_TOKEN to your .env.local file"
  );
}

interface MapProps {
  buses?: Bus[];
  busStops?: BusStop[];
  routes?: Route[];
  selectedBus?: string;
  selectedRoute?: string;
  showRouteShapes?: boolean;
  showETAs?: boolean;
  onBusClick?: (bus: Bus) => void;
  onLocationUpdate?: (busId: string, location: Location) => void;
}

interface ETAInfo {
  stop_id: string;
  stop_name?: string;
  duration_minutes: number;
  estimated_arrival: string;
}

interface BusETAData {
  bus_id: string;
  route_id: string;
  stop_etas: ETAInfo[];
  calculated_at: string;
}

export default function Map({
  buses = [],
  busStops = [],
  routes = [],
  selectedBus,
  selectedRoute,
  showRouteShapes = true,
  showETAs = true,
  onBusClick,
  onLocationUpdate,
}: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const busMarkers = useRef<globalThis.Map<string, mapboxgl.Marker>>(
    new globalThis.Map()
  );
  const stopMarkers = useRef<globalThis.Map<string, mapboxgl.Marker>>(
    new globalThis.Map()
  );
  const routeShapes = useRef<globalThis.Map<string, string>>(
    new globalThis.Map()
  ); // route_id -> source_id
  const [busETAs, setBusETAs] = useState<globalThis.Map<string, BusETAData>>(
    new globalThis.Map()
  );
  const { busLocations, wsClient } = useWebSocket();

  // Load route shape from API
  const loadRouteShape = async (routeId: string) => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) return;

      const response = await axios.get(`/api/routes/${routeId}/shape`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const shapeData = response.data;
      if (shapeData.geometry && map.current) {
        const sourceId = `route-${routeId}`;

        // Remove existing source and layer if they exist
        if (map.current.getSource(sourceId)) {
          if (map.current.getLayer(`${sourceId}-line`)) {
            map.current.removeLayer(`${sourceId}-line`);
          }
          map.current.removeSource(sourceId);
        }

        // Add route shape as GeoJSON source
        map.current.addSource(sourceId, {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {
              route_id: routeId,
              distance_km: (shapeData.distance_meters / 1000).toFixed(2),
              duration_minutes: (shapeData.duration_seconds / 60).toFixed(1),
            },
            geometry: shapeData.geometry,
          },
        });

        // Add route line layer
        map.current.addLayer({
          id: `${sourceId}-line`,
          type: "line",
          source: sourceId,
          layout: {
            "line-join": "round",
            "line-cap": "round",
          },
          paint: {
            "line-color": selectedRoute === routeId ? "#3b82f6" : "#6366f1",
            "line-width": selectedRoute === routeId ? 4 : 3,
            "line-opacity": 0.8,
          },
        });

        routeShapes.current.set(routeId, sourceId);
        console.log(`Loaded route shape for ${routeId}`);
      }
    } catch (error) {
      console.error(`Error loading route shape for ${routeId}:`, error);
    }
  };

  // Load ETA data for a bus
  const loadBusETA = async (busId: string) => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) return;

      const response = await axios.get(`/api/buses/${busId}/eta`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const etaData: BusETAData = response.data;
      setBusETAs((prev) => {
        const newMap = new globalThis.Map(prev);
        newMap.set(busId, etaData);
        return newMap;
      });
    } catch (error) {
      console.error(`Error loading ETA for bus ${busId}:`, error);
    }
  };

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    // Check if Mapbox token is available
    if (!mapboxgl.accessToken) {
      console.error("Mapbox access token is required");
      return;
    }

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: [38.7469, 9.032], // Addis Ababa coordinates
      zoom: 12,
    });

    map.current.addControl(new mapboxgl.NavigationControl(), "top-right");
    map.current.addControl(new mapboxgl.FullscreenControl(), "top-right");

    // Add click handler for location updates (admin feature)
    map.current.on("click", (e) => {
      if (selectedBus && onLocationUpdate) {
        const { lng, lat } = e.lngLat;
        onLocationUpdate(selectedBus, { latitude: lat, longitude: lng });
      }
    });

    return () => {
      map.current?.remove();
    };
  }, [selectedBus, onLocationUpdate]);

  // Update bus markers
  useEffect(() => {
    if (!map.current) return;

    // Clear existing bus markers
    busMarkers.current.forEach((marker) => marker.remove());
    busMarkers.current.clear();

    // Add bus markers
    buses.forEach((bus) => {
      if (!bus.current_location) return;

      // Check if we have real-time location update
      const realtimeLocation = busLocations.get(bus.id);
      const location = realtimeLocation
        ? realtimeLocation.location
        : bus.current_location;

      // Create bus marker element
      const el = document.createElement("div");
      el.className = "bus-marker";
      el.style.cssText = `
        width: 30px;
        height: 30px;
        background-color: ${getBusStatusColor(bus.bus_status)};
        border: 2px solid white;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: bold;
        color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        ${
          selectedBus === bus.id
            ? "transform: scale(1.2); border-color: #3b82f6;"
            : ""
        }
      `;
      el.innerHTML = "🚌";

      // Add click handler
      el.addEventListener("click", () => {
        onBusClick?.(bus);
      });

      // Create marker
      const marker = new mapboxgl.Marker(el)
        .setLngLat([location.longitude, location.latitude])
        .addTo(map.current!);

      // Get ETA data for this bus
      const etaData = busETAs.get(bus.id);
      const nextStopETA = etaData?.stop_etas?.[0];

      // Add popup with bus info
      const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(`
          <div class="p-3 max-w-xs">
            <h3 class="font-bold text-lg mb-2">${bus.license_plate}</h3>
            <div class="space-y-1 text-sm">
              <p><span class="font-medium">Status:</span> ${bus.bus_status}</p>
              <p><span class="font-medium">Type:</span> ${bus.bus_type}</p>
              <p><span class="font-medium">Capacity:</span> ${bus.capacity}</p>
              ${
                realtimeLocation
                  ? `
                <div class="border-t pt-2 mt-2">
                  <p class="text-xs text-green-600 font-medium">
                    🟢 Live: ${new Date(
                      realtimeLocation.location.timestamp
                    ).toLocaleTimeString()}
                  </p>
                  ${
                    realtimeLocation.speed
                      ? `<p class="text-xs">Speed: ${realtimeLocation.speed} km/h</p>`
                      : ""
                  }
                </div>
              `
                  : ""
              }
              ${
                nextStopETA
                  ? `
                <div class="border-t pt-2 mt-2">
                  <p class="text-xs font-medium text-blue-600">Next Stop ETA:</p>
                  <p class="text-xs">${
                    nextStopETA.stop_name || "Unknown Stop"
                  }</p>
                  <p class="text-xs">${
                    nextStopETA.duration_minutes
                  } min (${new Date(
                      nextStopETA.estimated_arrival
                    ).toLocaleTimeString()})</p>
                </div>
              `
                  : ""
              }
            </div>
          </div>
        `);

      marker.setPopup(popup);
      busMarkers.current.set(bus.id, marker);
    });
  }, [buses, busLocations, selectedBus, onBusClick]);

  // Update bus stop markers
  useEffect(() => {
    if (!map.current) return;

    // Clear existing stop markers
    stopMarkers.current.forEach((marker) => marker.remove());
    stopMarkers.current.clear();

    // Add bus stop markers
    busStops.forEach((stop) => {
      // Create stop marker element
      const el = document.createElement("div");
      el.className = "stop-marker";
      el.style.cssText = `
        width: 20px;
        height: 20px;
        background-color: #10b981;
        border: 2px solid white;
        border-radius: 50%;
        cursor: pointer;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
      `;

      // Create marker
      const marker = new mapboxgl.Marker(el)
        .setLngLat([stop.location.longitude, stop.location.latitude])
        .addTo(map.current!);

      // Add popup with stop info
      const popup = new mapboxgl.Popup({ offset: 15 }).setHTML(`
          <div class="p-2">
            <h3 class="font-bold">${stop.name}</h3>
            ${
              stop.capacity
                ? `<p class="text-sm">Capacity: ${stop.capacity}</p>`
                : ""
            }
            <p class="text-sm">Status: ${
              stop.is_active ? "Active" : "Inactive"
            }</p>
          </div>
        `);

      marker.setPopup(popup);
      stopMarkers.current.set(stop.id, marker);
    });
  }, [busStops]);

  // Subscribe to bus tracking rooms
  useEffect(() => {
    if (!wsClient) return;

    buses.forEach((bus) => {
      wsClient.joinRoom(`bus_tracking:${bus.id}`);
    });

    return () => {
      buses.forEach((bus) => {
        wsClient.leaveRoom(`bus_tracking:${bus.id}`);
      });
    };
  }, [buses, wsClient]);

  // Load route shapes when routes change
  useEffect(() => {
    if (!map.current || !showRouteShapes) return;

    routes.forEach((route) => {
      if (!routeShapes.current.has(route.id)) {
        loadRouteShape(route.id);
      }
    });
  }, [routes, showRouteShapes, selectedRoute]);

  // Load ETAs for buses when they change
  useEffect(() => {
    if (!showETAs) return;

    buses.forEach((bus) => {
      if (bus.assigned_route_id && bus.current_location) {
        loadBusETA(bus.id);
      }
    });

    // Set up interval to refresh ETAs every 2 minutes
    const etaInterval = setInterval(() => {
      buses.forEach((bus) => {
        if (bus.assigned_route_id && bus.current_location) {
          loadBusETA(bus.id);
        }
      });
    }, 2 * 60 * 1000);

    return () => clearInterval(etaInterval);
  }, [buses, showETAs]);

  // Listen for ETA updates via WebSocket
  useEffect(() => {
    if (!wsClient) return;

    const handleETAUpdate = (message: any) => {
      if (message.type === "bus_eta_update") {
        setBusETAs((prev) => {
          const newMap = new globalThis.Map(prev);
          newMap.set(message.bus_id, {
            bus_id: message.bus_id,
            route_id: message.route_id,
            stop_etas: message.stop_etas,
            calculated_at: message.calculated_at,
          });
          return newMap;
        });
      }
    };

    wsClient.on("bus_eta_update", handleETAUpdate);

    return () => {
      wsClient.off("bus_eta_update", handleETAUpdate);
    };
  }, [wsClient]);

  // Check if Mapbox token is available for rendering
  if (!mapboxgl.accessToken) {
    return (
      <div className="relative w-full h-full flex items-center justify-center bg-gray-100">
        <div className="text-center p-8">
          <div className="text-6xl mb-4">🗺️</div>
          <h3 className="text-lg font-semibold text-gray-700 mb-2">
            Map Not Available
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            Mapbox access token is required to display the map.
          </p>
          <div className="text-xs text-gray-500 bg-gray-50 p-3 rounded border">
            <p className="font-medium mb-1">To fix this:</p>
            <p>
              1. Get a free token from{" "}
              <a
                href="https://mapbox.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline"
              >
                mapbox.com
              </a>
            </p>
            <p>2. Add it to your .env.local file:</p>
            <code className="block mt-1 text-xs bg-white p-1 rounded">
              MAPBOX_ACCESS_TOKEN=your_token_here
            </code>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Map legend */}
      <div className="absolute top-4 left-4 bg-white p-3 rounded-lg shadow-md max-w-xs">
        <h3 className="font-bold text-sm mb-2">Legend</h3>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-500 rounded-full border border-white"></div>
            <span>Operational Bus</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-yellow-500 rounded-full border border-white"></div>
            <span>Idle Bus</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-500 rounded-full border border-white"></div>
            <span>Maintenance/Breakdown</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-emerald-500 rounded-full border border-white"></div>
            <span>Bus Stop</span>
          </div>
          {showRouteShapes && (
            <>
              <div className="flex items-center gap-2">
                <div className="w-6 h-1 bg-indigo-500 rounded"></div>
                <span>Route Shape</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-1 bg-blue-500 rounded"></div>
                <span>Selected Route</span>
              </div>
            </>
          )}
        </div>
        {showETAs && (
          <div className="mt-2 pt-2 border-t">
            <p className="text-xs text-gray-600">
              💡 Click buses to see ETA to next stop
            </p>
          </div>
        )}
      </div>

      {/* Click instruction for admin */}
      {selectedBus && (
        <div className="absolute bottom-4 left-4 bg-blue-100 p-3 rounded-lg shadow-md">
          <p className="text-sm text-blue-800">
            <strong>Admin Mode:</strong> Click on the map to update bus location
          </p>
        </div>
      )}
    </div>
  );
}

function getBusStatusColor(status: string): string {
  switch (status) {
    case "OPERATIONAL":
      return "#10b981"; // green
    case "IDLE":
      return "#f59e0b"; // yellow
    case "MAINTENANCE":
    case "BREAKDOWN":
      return "#ef4444"; // red
    default:
      return "#6b7280"; // gray
  }
}
