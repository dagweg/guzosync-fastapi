"""
Bus Simulator for GuzoSync

This module provides the main bus simulation engine that:
1. Fetches buses and routes from the database
2. Simulates realistic movement along routes
3. Updates bus locations in real-time via WebSocket
4. Handles bus stops, traffic, and realistic timing
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import random

from motor.motor_asyncio import AsyncIOMotorDatabase

from .movement_calculator import MovementCalculator
from .route_path_generator import RoutePathGenerator
from core.realtime.bus_tracking import bus_tracking_service

logger = logging.getLogger(__name__)


class BusState:
    """Represents the current state of a simulated bus."""
    
    def __init__(self, bus_data: Dict[str, Any]):
        self.bus_id = bus_data['id']
        self.license_plate = bus_data.get('license_plate', 'Unknown')
        self.route_id = bus_data.get('assigned_route_id')
        
        # Current position
        current_location = bus_data.get('current_location') or {}
        self.latitude = current_location.get('latitude', 0.0) if current_location else 0.0
        self.longitude = current_location.get('longitude', 0.0) if current_location else 0.0
        
        # Movement state
        self.speed = bus_data.get('speed', 0.0)
        self.heading = bus_data.get('heading', 0.0)
        
        # Route following
        self.route_waypoints: List[Dict[str, Any]] = []
        self.current_waypoint_index = 0
        self.target_waypoint: Optional[Dict[str, Any]] = None
        
        # Stop state
        self.is_at_stop = False
        self.stop_start_time: Optional[datetime] = None
        self.stop_duration = 0
        
        # Traffic simulation
        self.traffic_delay_factor = 1.0
        self.last_traffic_update = datetime.now(timezone.utc)
        
        # Status
        self.is_active = bus_data.get('bus_status') == 'OPERATIONAL'
        self.last_update = datetime.now(timezone.utc)


class BusSimulator:
    """Main bus simulation engine."""
    
    def __init__(self, db: AsyncIOMotorDatabase, update_interval: float = 5.0):
        self.db = db
        self.update_interval = update_interval  # seconds between updates
        self.movement_calc = MovementCalculator()
        self.path_generator = RoutePathGenerator()
        
        # Simulation state
        self.buses: Dict[str, BusState] = {}
        self.routes_cache: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        self.simulation_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.max_buses_to_simulate = 50  # Limit for performance
        self.route_completion_behavior = 'loop'  # 'loop' or 'reverse'
        
    async def initialize(self):
        """Initialize the simulation by loading buses and routes."""
        #logger.info("🚌 Initializing bus simulation...")
        
        try:
            # Load active buses with assigned routes
            buses_cursor = self.db.buses.find({
                "assigned_route_id": {"$ne": None, "$exists": True},
                "bus_status": "OPERATIONAL"
            }).limit(self.max_buses_to_simulate)
            
            buses = await buses_cursor.to_list(length=None)
            #logger.info(f"📊 Found {len(buses)} operational buses with assigned routes")
            
            # Initialize bus states
            for bus_data in buses:
                bus_state = BusState(bus_data)
                
                if bus_state.route_id:
                    # Load route data
                    route_data = await self._load_route_data(bus_state.route_id)
                    if route_data:
                        # Generate route path
                        waypoints = await self._generate_route_waypoints(route_data)
                        if waypoints:
                            bus_state.route_waypoints = waypoints
                            bus_state.target_waypoint = waypoints[0] if waypoints else None
                            
                            # Set initial position if bus doesn't have one
                            if bus_state.latitude == 0.0 and bus_state.longitude == 0.0:
                                first_waypoint = waypoints[0]
                                bus_state.latitude = first_waypoint['latitude']
                                bus_state.longitude = first_waypoint['longitude']
                            
                            self.buses[bus_state.bus_id] = bus_state
                            #logger.debug(f"✅ Initialized bus {bus_state.license_plate} on route {route_data.get('name')}")
                        # else:
                            #logger.warning(f"⚠️ No waypoints generated for bus {bus_state.license_plate}")
                    # else:
                        #logger.warning(f"⚠️ Route data not found for bus {bus_state.license_plate}")
            
            #logger.info(f"✅ Initialized {len(self.buses)} buses for simulation")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize simulation: {e}")
            raise
    
    async def _load_route_data(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Load route data from database with caching."""
        if route_id in self.routes_cache:
            return self.routes_cache[route_id]
        
        try:
            route_data = await self.db.routes.find_one({"id": route_id})
            if route_data:
                self.routes_cache[route_id] = route_data
                return route_data
        except Exception as e:
            logger.error(f"Error loading route {route_id}: {e}")
        
        return None
    
    async def _generate_route_waypoints(self, route_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate waypoints for a route using Mapbox geometry if available."""
        try:
            stop_ids = route_data.get('stop_ids', [])
            if not stop_ids:
                return []

            # Load bus stops
            bus_stops_cursor = self.db.bus_stops.find({"id": {"$in": stop_ids}})
            bus_stops_docs = await bus_stops_cursor.to_list(length=None)

            # Sort bus stops according to route order
            bus_stops = []
            for stop_id in stop_ids:
                for stop_doc in bus_stops_docs:
                    if stop_doc['id'] == stop_id:
                        bus_stops.append(stop_doc)
                        break

            if len(bus_stops) < 2:
                #logger.warning(f"Route {route_data.get('name')} has insufficient stops")
                return []

            # Check if we have Mapbox route geometry
            route_geometry = route_data.get('route_geometry')
            route_name = route_data.get('name', 'Unknown')

            if route_geometry and route_geometry.get('type') == 'LineString':
                #logger.info(f"🗺️ Using Mapbox geometry for route {route_name} (real roads)")
                waypoints = self.path_generator.generate_route_path(bus_stops, route_geometry)
            else:
                #logger.info(f"📍 Using simple path for route {route_name} (no Mapbox geometry)")
                waypoints = self.path_generator.generate_route_path(bus_stops, None)

            # Make route circular for continuous simulation
            waypoints = self.path_generator.create_circular_route(waypoints)

            # Log waypoint statistics
            road_points = sum(1 for wp in waypoints if wp.get('source') == 'mapbox')
            total_points = len(waypoints)

            # if road_points > 0:
                #logger.info(f"✅ Route {route_name}: {total_points} waypoints ({road_points} from real roads)")
            # else:
                #logger.info(f"📍 Route {route_name}: {total_points} waypoints (simple path)")

            return waypoints

        except Exception as e:
            #logger.error(f"Error generating waypoints for route {route_data.get('id')}: {e}")
            return []
    
    async def start_simulation(self):
        """Start the bus simulation."""
        if self.is_running:
            #logger.warning("Simulation is already running")
            return
        
        #logger.info("🚀 Starting bus simulation...")
        self.is_running = True
        
        # Start simulation loop
        self.simulation_task = asyncio.create_task(self._simulation_loop())
        
        #logger.info("✅ Bus simulation started successfully")
    
    async def stop_simulation(self):
        """Stop the bus simulation."""
        if not self.is_running:
            return
        
        #logger.info("🛑 Stopping bus simulation...")
        self.is_running = False
        
        if self.simulation_task:
            self.simulation_task.cancel()
            try:
                await self.simulation_task
            except asyncio.CancelledError:
                pass
        
        #logger.info("✅ Bus simulation stopped")
    
    async def _simulation_loop(self):
        """Main simulation loop."""
        #logger.info(f"🔄 Starting simulation loop with {len(self.buses)} buses")
        
        try:
            while self.is_running:
                start_time = datetime.now(timezone.utc)
                
                # Update all buses
                update_tasks = []
                for bus_state in self.buses.values():
                    if bus_state.is_active:
                        task = asyncio.create_task(self._update_bus(bus_state))
                        update_tasks.append(task)
                
                # Wait for all updates to complete
                if update_tasks:
                    await asyncio.gather(*update_tasks, return_exceptions=True)
                
                # Calculate sleep time to maintain consistent update interval
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                sleep_time = max(0, self.update_interval - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled")
        except Exception as e:
            logger.error(f"Error in simulation loop: {e}")
            self.is_running = False
    
    async def _update_bus(self, bus_state: BusState):
        """Update a single bus's position and state."""
        try:
            current_time = datetime.now(timezone.utc)
            time_delta = (current_time - bus_state.last_update).total_seconds()
            
            # Handle bus at stop
            if bus_state.is_at_stop:
                if bus_state.stop_start_time:
                    stop_elapsed = (current_time - bus_state.stop_start_time).total_seconds()
                    if stop_elapsed >= bus_state.stop_duration:
                        # Finished stopping, move to next waypoint
                        bus_state.is_at_stop = False
                        bus_state.stop_start_time = None
                        bus_state.current_waypoint_index = (bus_state.current_waypoint_index + 1) % len(bus_state.route_waypoints)
                        bus_state.target_waypoint = bus_state.route_waypoints[bus_state.current_waypoint_index]
                        #logger.debug(f"🚌 Bus {bus_state.license_plate} finished stop, moving to next waypoint")
                return
            
            # Check if we have a target waypoint
            if not bus_state.target_waypoint or not bus_state.route_waypoints:
                return
            
            # Update traffic conditions periodically
            if (current_time - bus_state.last_traffic_update).total_seconds() > 30:
                bus_state.traffic_delay_factor = self.movement_calc.simulate_traffic_delay()
                bus_state.last_traffic_update = current_time
            
            # Calculate movement
            target_lat = bus_state.target_waypoint['latitude']
            target_lon = bus_state.target_waypoint['longitude']
            
            # Get speed for this segment
            base_speed = bus_state.target_waypoint.get('estimated_speed', 25.0)
            if base_speed == 0:  # This is a bus stop
                base_speed = 25.0  # Use default speed when approaching stop
            
            current_speed = self.movement_calc.get_realistic_speed(base_speed)
            current_speed *= bus_state.traffic_delay_factor  # Apply traffic delay
            
            # Calculate new position
            new_lat, new_lon, remaining_distance = self.movement_calc.calculate_next_position(
                bus_state.latitude, bus_state.longitude,
                target_lat, target_lon,
                current_speed, time_delta
            )
            
            # Update bus state
            bus_state.latitude = new_lat
            bus_state.longitude = new_lon
            bus_state.speed = current_speed
            bus_state.heading = self.movement_calc.calculate_bearing(
                bus_state.latitude, bus_state.longitude, target_lat, target_lon
            )
            bus_state.last_update = current_time
            
            # Check if we reached the waypoint
            if remaining_distance <= 0.01:  # Within 10 meters
                if bus_state.target_waypoint.get('is_bus_stop', False):
                    # Start stop at bus stop
                    bus_state.is_at_stop = True
                    bus_state.stop_start_time = current_time
                    bus_state.stop_duration = self.movement_calc.calculate_stop_duration()
                    bus_state.speed = 0.0
                    #logger.debug(f"🚏 Bus {bus_state.license_plate} arrived at stop {bus_state.target_waypoint.get('stop_name', 'Unknown')}")
                else:
                    # Move to next waypoint
                    bus_state.current_waypoint_index = (bus_state.current_waypoint_index + 1) % len(bus_state.route_waypoints)
                    bus_state.target_waypoint = bus_state.route_waypoints[bus_state.current_waypoint_index]
            
            # Broadcast location update
            await self._broadcast_bus_location(bus_state)
            
        except Exception as e:
            logger.error(f"Error updating bus {bus_state.bus_id}: {e}")
    
    async def _broadcast_bus_location(self, bus_state: BusState):
        """Broadcast bus location update via WebSocket."""
        try:
            # Create app_state-like object for the bus tracking service
            class AppState:
                def __init__(self, db):
                    self.mongodb = db
            
            app_state = AppState(self.db)
            
            await bus_tracking_service.update_bus_location(
                bus_id=bus_state.bus_id,
                latitude=bus_state.latitude,
                longitude=bus_state.longitude,
                heading=bus_state.heading,
                speed=bus_state.speed,
                app_state=app_state
            )
            
        except Exception as e:
            logger.error(f"Error broadcasting location for bus {bus_state.bus_id}: {e}")
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get current simulation status."""
        active_buses = sum(1 for bus in self.buses.values() if bus.is_active)
        
        return {
            'is_running': self.is_running,
            'total_buses': len(self.buses),
            'active_buses': active_buses,
            'update_interval': self.update_interval,
            'routes_loaded': len(self.routes_cache)
        }
