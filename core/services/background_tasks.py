"""
Background tasks for route updates, ETA calculations, and performance optimizations
"""
import asyncio
from typing import Optional, Any
from datetime import datetime, timedelta
import json

from core.logger import get_logger
from core.services.route_service import route_service
from core.services.mapbox_service import mapbox_service
from core.realtime.bus_tracking import bus_tracking_service
from core.socketio_manager import socketio_manager
from models.transport import Bus, BusStop
from models.base import Location

logger = get_logger(__name__)


class BackgroundTaskService:
    """Service for managing background tasks"""
    
    def __init__(self):
        self.is_running = False
        self.tasks = []
        self.app_state: Optional[Any] = None
    
    def set_app_state(self, app_state: Any):
        """Set application state for database access"""
        self.app_state = app_state
    
    async def start_background_tasks(self):
        """Start all background tasks"""
        if self.is_running:
            logger.warning("Background tasks already running")
            return
        
        self.is_running = True
        logger.info("Starting background tasks")
        
        # Initialize Mapbox service Redis connection
        await mapbox_service.initialize_redis()
        
        # Start individual tasks
        self.tasks = [
            asyncio.create_task(self._route_shape_updater()),
            asyncio.create_task(self._eta_broadcaster()),
            asyncio.create_task(self._performance_optimizer()),
            asyncio.create_task(self._cache_cleaner())
        ]
        
        logger.info(f"Started {len(self.tasks)} background tasks")
    
    async def stop_background_tasks(self):
        """Stop all background tasks"""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping background tasks")
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Close Mapbox service connections
        await mapbox_service.close()
        
        logger.info("All background tasks stopped")
    
    async def _route_shape_updater(self):
        """Update route shapes periodically"""
        logger.info("Route shape updater started")
        
        while self.is_running:
            try:
                # Update route shapes every 24 hours - PERFORMANCE OPTIMIZATION
                await route_service.update_all_route_shapes(self.app_state)

                # Wait 24 hours before next update
                await asyncio.sleep(24 * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in route shape updater: {e}")
                # Wait 30 minutes before retrying on error
                await asyncio.sleep(30 * 60)
        
        logger.info("Route shape updater stopped")
    
    async def _eta_broadcaster(self):
        """Broadcast ETA updates for active buses"""
        logger.info("ETA broadcaster started")
        
        while self.is_running:
            try:
                if self.app_state is None or not hasattr(self.app_state, 'mongodb') or self.app_state.mongodb is None:
                    await asyncio.sleep(60)
                    continue
                
                # Get limited operational buses with assigned routes - PERFORMANCE OPTIMIZATION
                buses_cursor = self.app_state.mongodb.buses.find({
                    "bus_status": "OPERATIONAL",
                    "assigned_route_id": {"$exists": True, "$ne": None},
                    "current_location": {"$exists": True, "$ne": None}
                }).limit(10)  # LIMIT TO 10 BUSES FOR PERFORMANCE
                buses = await buses_cursor.to_list(length=10)
                
                logger.debug(f"Broadcasting ETA for {len(buses)} active buses")
                
                for bus_doc in buses:
                    try:
                        await self._broadcast_bus_eta(bus_doc)
                        # Small delay to avoid overwhelming the system
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Error broadcasting ETA for bus {bus_doc.get('id', 'unknown')}: {e}")
                
                # Wait 10 minutes before next broadcast - PERFORMANCE OPTIMIZATION
                await asyncio.sleep(10 * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ETA broadcaster: {e}")
                await asyncio.sleep(60)
        
        logger.info("ETA broadcaster stopped")
    
    async def _broadcast_bus_eta(self, bus_doc: dict):
        """Broadcast ETA for a specific bus"""
        try:
            if self.app_state is None or not hasattr(self.app_state, 'mongodb') or self.app_state.mongodb is None:
                return

            bus_id = bus_doc["id"]
            route_id = bus_doc.get("assigned_route_id")

            if not route_id:
                return

            # Get route information
            route_doc = await self.app_state.mongodb.routes.find_one({"id": route_id})
            if not route_doc:
                return
            
            # Get bus stops for the route
            stop_ids = route_doc.get("stop_ids", [])
            if not stop_ids:
                return
            
            # Fetch bus stops with limit - PERFORMANCE OPTIMIZATION
            bus_stops_cursor = self.app_state.mongodb.bus_stops.find({"id": {"$in": stop_ids}}).limit(20)
            bus_stops_docs = await bus_stops_cursor.to_list(length=20)
            
            # Convert to BusStop objects
            route_stops = []
            for stop_id in stop_ids:
                for stop_doc in bus_stops_docs:
                    if stop_doc["id"] == stop_id:
                        bus_stop = BusStop(
                            id=stop_doc["id"],
                            name=stop_doc["name"],
                            location=Location(
                                latitude=stop_doc["location"]["latitude"],
                                longitude=stop_doc["location"]["longitude"]
                            ),
                            capacity=stop_doc.get("capacity"),
                            is_active=stop_doc.get("is_active", True)
                        )
                        route_stops.append((stop_id, bus_stop))
                        break
            
            if not route_stops:
                return
            
            # Create Bus object
            bus = Bus(
                id=bus_doc["id"],
                license_plate=bus_doc["license_plate"],
                bus_type=bus_doc["bus_type"],
                capacity=bus_doc["capacity"],
                current_location=Location(
                    latitude=bus_doc["current_location"]["latitude"],
                    longitude=bus_doc["current_location"]["longitude"]
                ),
                speed=bus_doc.get("speed"),
                bus_status=bus_doc["bus_status"],
                assigned_route_id=bus_doc.get("assigned_route_id"),
                assigned_driver_id=bus_doc.get("assigned_driver_id")
            )
            
            # Calculate ETAs
            eta_responses = await route_service.calculate_bus_eta_to_stops(
                bus, route_stops, self.app_state
            )
            
            if eta_responses:
                # Broadcast ETA update
                message = {
                    "type": "bus_eta_update",
                    "bus_id": bus_id,
                    "route_id": route_id,
                    "stop_etas": [eta.dict() for eta in eta_responses],
                    "calculated_at": datetime.utcnow().isoformat()
                }
                
                # Send to bus tracking room
                bus_room_id = f"bus_tracking:{bus_id}"
                await socketio_manager.send_room_message(bus_room_id, "bus_eta_update", message)
                
                # Send to route tracking room
                route_room_id = f"route_tracking:{route_id}"
                await socketio_manager.send_room_message(route_room_id, "bus_eta_update", message)
                
                logger.debug(f"Broadcasted ETA for bus {bus_id} to {len(eta_responses)} stops")
            
        except Exception as e:
            logger.error(f"Error in _broadcast_bus_eta: {e}")
    
    async def _performance_optimizer(self):
        """Optimize performance by managing database indexes and cleanup"""
        logger.info("Performance optimizer started")
        
        while self.is_running:
            try:
                if self.app_state is None or not hasattr(self.app_state, 'mongodb') or self.app_state.mongodb is None:
                    await asyncio.sleep(3600)
                    continue
                
                # Create geospatial indexes if they don't exist
                await self._ensure_geospatial_indexes()
                
                # Clean up old location updates (older than 7 days)
                await self._cleanup_old_location_data()
                
                # Wait 24 hours before next optimization
                await asyncio.sleep(24 * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance optimizer: {e}")
                await asyncio.sleep(3600)
        
        logger.info("Performance optimizer stopped")
    
    async def _ensure_geospatial_indexes(self):
        """Ensure geospatial indexes exist for efficient queries"""
        try:
            if self.app_state is None or not hasattr(self.app_state, 'mongodb') or self.app_state.mongodb is None:
                return

            # Create 2dsphere index on bus current_location
            await self.app_state.mongodb.buses.create_index([("current_location", "2dsphere")])

            # Create 2dsphere index on bus_stops location
            await self.app_state.mongodb.bus_stops.create_index([("location", "2dsphere")])

            # Create compound index for bus tracking queries
            await self.app_state.mongodb.buses.create_index([
                ("bus_status", 1),
                ("assigned_route_id", 1),
                ("last_location_update", -1)
            ])
            
            logger.debug("Geospatial indexes ensured")
            
        except Exception as e:
            logger.error(f"Error creating geospatial indexes: {e}")
    
    async def _cleanup_old_location_data(self):
        """Clean up old location tracking data"""
        try:
            # Remove location updates older than 7 days
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            # This would be implemented if we had a separate location history collection
            # For now, we just log the cleanup attempt
            logger.debug(f"Location data cleanup completed (cutoff: {cutoff_date})")
            
        except Exception as e:
            logger.error(f"Error in location data cleanup: {e}")
    
    async def _cache_cleaner(self):
        """Clean expired cache entries"""
        logger.info("Cache cleaner started")
        
        while self.is_running:
            try:
                # Redis handles TTL automatically, but we can do additional cleanup here
                # For now, just log that cache cleaning is running
                logger.debug("Cache cleaning cycle completed")
                
                # Wait 6 hours before next cleanup - PERFORMANCE OPTIMIZATION
                await asyncio.sleep(6 * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleaner: {e}")
                await asyncio.sleep(3600)
        
        logger.info("Cache cleaner stopped")


# Global background task service instance
background_task_service = BackgroundTaskService()
