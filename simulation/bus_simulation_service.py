"""
Bus Simulation Background Service

This service integrates the bus simulation with the FastAPI application lifecycle.
It starts automatically when the server starts and runs as a background service.
"""

import asyncio
import logging
import os
from typing import Optional, Any
from datetime import datetime, timezone

from .bus_simulator import BusSimulator
from core.logger import get_logger

logger = get_logger(__name__)


class BusSimulationService:
    """Background service for bus simulation."""
    
    def __init__(self):
        self.simulator: Optional[BusSimulator] = None
        self.app_state: Optional[Any] = None
        self.is_running = False
        self.simulation_task: Optional[asyncio.Task] = None
        
        # Configuration from environment variables
        self.enabled = os.getenv("BUS_SIMULATION_ENABLED", "true").lower() == "true"
        self.update_interval = float(os.getenv("BUS_SIMULATION_INTERVAL", "5.0"))
        self.max_buses = int(os.getenv("BUS_SIMULATION_MAX_BUSES", "50"))
        self.auto_assign_routes = os.getenv("BUS_SIMULATION_AUTO_ASSIGN", "true").lower() == "true"
        
    def set_app_state(self, app_state: Any):
        """Set the FastAPI app state."""
        self.app_state = app_state
        
    async def start(self):
        """Start the bus simulation service."""
        if not self.enabled:
            logger.info("🚌 Bus simulation service disabled via environment variable")
            return
            
        if self.is_running:
            logger.warning("Bus simulation service already running")
            return
            
        if not self.app_state or not hasattr(self.app_state, 'mongodb'):
            logger.error("App state or MongoDB not available for bus simulation")
            return
            
        logger.info("🚀 Starting bus simulation service...")
        logger.info(f"   ⏱️ Update interval: {self.update_interval}s")
        logger.info(f"   🚌 Max buses: {self.max_buses}")
        logger.info(f"   🔄 Auto assign routes: {self.auto_assign_routes}")
        
        try:
            # Check if simulation should start
            if not await self._should_start_simulation():
                logger.info("🚌 Bus simulation conditions not met, service will retry later")
                # Start monitoring task that will start simulation when ready
                self.simulation_task = asyncio.create_task(self._monitoring_loop())
                return
            
            # Initialize simulator
            self.simulator = BusSimulator(
                db=self.app_state.mongodb,
                update_interval=self.update_interval
            )
            self.simulator.max_buses_to_simulate = self.max_buses
            
            # Auto-assign routes if enabled
            if self.auto_assign_routes:
                await self._assign_routes_to_buses()
            
            # Initialize and start simulation
            await self.simulator.initialize()
            
            # Check if we have buses to simulate
            status = self.simulator.get_simulation_status()
            if status['total_buses'] == 0:
                logger.warning("🚌 No buses available for simulation, starting monitoring mode")
                self.simulation_task = asyncio.create_task(self._monitoring_loop())
                return
            
            # Start simulation
            await self.simulator.start_simulation()
            self.is_running = True
            
            # Start monitoring task
            self.simulation_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info("✅ Bus simulation service started successfully")
            logger.info(f"   📊 Total buses: {status['total_buses']}")
            logger.info(f"   🚌 Active buses: {status['active_buses']}")
            logger.info(f"   🛣️ Routes loaded: {status['routes_loaded']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start bus simulation service: {e}")
            # Start monitoring loop to retry later
            self.simulation_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Stop the bus simulation service."""
        logger.info("🛑 Stopping bus simulation service...")
        
        self.is_running = False
        
        # Cancel monitoring task
        if self.simulation_task:
            self.simulation_task.cancel()
            try:
                await self.simulation_task
            except asyncio.CancelledError:
                pass
        
        # Stop simulator
        if self.simulator:
            await self.simulator.stop_simulation()
            self.simulator = None
        
        logger.info("✅ Bus simulation service stopped")
    
    async def _should_start_simulation(self) -> bool:
        """Check if conditions are met to start simulation."""
        try:
            if not self.app_state or not hasattr(self.app_state, 'mongodb'):
                return False
            
            # Check for operational buses
            bus_count = await self.app_state.mongodb.buses.count_documents({
                "bus_status": "OPERATIONAL"
            })
            
            # Check for active routes
            route_count = await self.app_state.mongodb.routes.count_documents({
                "is_active": True
            })
            
            # Check for bus stops
            stop_count = await self.app_state.mongodb.bus_stops.count_documents({
                "is_active": True
            })
            
            logger.debug(f"🚌 Simulation readiness check: {bus_count} buses, {route_count} routes, {stop_count} stops")
            
            return bus_count > 0 and route_count > 0 and stop_count >= 2

        except Exception as e:
            logger.error(f"Error checking simulation conditions: {e}")
            return False

    async def _assign_routes_to_buses(self):
        """Assign routes to buses that don't have them."""
        try:
            # Get buses without assigned routes
            unassigned_buses = await self.app_state.mongodb.buses.find({
                "$or": [
                    {"assigned_route_id": None},
                    {"assigned_route_id": {"$exists": False}}
                ],
                "bus_status": "OPERATIONAL"
            }).to_list(length=None)

            if not unassigned_buses:
                logger.debug("All operational buses already have route assignments")
                return

            # Get available routes
            routes = await self.app_state.mongodb.routes.find({
                "is_active": True
            }).to_list(length=None)

            if not routes:
                logger.warning("No active routes available for assignment")
                return

            # Assign routes randomly to buses
            import random
            assignments_made = 0

            for bus in unassigned_buses:
                route = random.choice(routes)

                await self.app_state.mongodb.buses.update_one(
                    {"id": bus["id"]},
                    {"$set": {"assigned_route_id": route["id"]}}
                )

                assignments_made += 1
                logger.debug(f"🚌 Assigned bus {bus.get('license_plate')} to route {route.get('name')}")

            logger.info(f"✅ Auto-assigned routes to {assignments_made} buses")

        except Exception as e:
            logger.error(f"Error auto-assigning routes: {e}")

    async def _monitoring_loop(self):
        """Monitor simulation health and restart if needed."""
        logger.info("🔍 Starting bus simulation monitoring loop")

        retry_count = 0
        max_retries = 5

        try:
            while True:
                await asyncio.sleep(60)  # Check every minute

                # If simulation is not running, try to start it
                if not self.is_running and self.enabled:
                    if await self._should_start_simulation():
                        logger.info("🚌 Conditions met, attempting to start simulation...")

                        try:
                            # Initialize simulator if not exists
                            if not self.simulator:
                                self.simulator = BusSimulator(
                                    db=self.app_state.mongodb,
                                    update_interval=self.update_interval
                                )
                                self.simulator.max_buses_to_simulate = self.max_buses

                            # Auto-assign routes if enabled
                            if self.auto_assign_routes:
                                await self._assign_routes_to_buses()

                            # Initialize and start
                            await self.simulator.initialize()
                            status = self.simulator.get_simulation_status()

                            if status['total_buses'] > 0:
                                await self.simulator.start_simulation()
                                self.is_running = True
                                retry_count = 0  # Reset retry count on success

                                logger.info("✅ Bus simulation started from monitoring loop")
                                logger.info(f"   📊 Total buses: {status['total_buses']}")
                                logger.info(f"   🚌 Active buses: {status['active_buses']}")
                            else:
                                logger.debug("🚌 No buses available for simulation yet")

                        except Exception as e:
                            retry_count += 1
                            logger.error(f"❌ Failed to start simulation (attempt {retry_count}/{max_retries}): {e}")

                            if retry_count >= max_retries:
                                logger.error("🚌 Max retries reached, disabling simulation service")
                                break

                # If simulation is running, check health
                elif self.is_running and self.simulator:
                    status = self.simulator.get_simulation_status()
                    if not status['is_running']:
                        logger.warning("🚌 Simulation stopped unexpectedly, attempting restart...")
                        self.is_running = False
                        # Will be restarted in next loop iteration

        except asyncio.CancelledError:
            logger.info("🔍 Bus simulation monitoring loop cancelled")
        except Exception as e:
            logger.error(f"❌ Error in simulation monitoring loop: {e}")

    def get_status(self) -> dict:
        """Get current simulation service status."""
        status = {
            "enabled": self.enabled,
            "is_running": self.is_running,
            "update_interval": self.update_interval,
            "max_buses": self.max_buses,
            "auto_assign_routes": self.auto_assign_routes
        }

        if self.simulator:
            sim_status = self.simulator.get_simulation_status()
            status.update(sim_status)

        return status


# Global service instance
bus_simulation_service = BusSimulationService()
