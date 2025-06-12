"""
Populate Route Geometry Script

This script fetches real road paths from Mapbox for all routes in the database
and stores them as GeoJSON LineString geometry for realistic bus simulation.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from core.services.route_service import route_service
from models.base import Location
from models.transport import BusStop

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Reduce logging for batch processing
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('route_geometry_population.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class AppState:
    """Mock app state for route service"""
    def __init__(self, mongodb):
        self.mongodb = mongodb


async def populate_route_geometry():
    """Populate route geometry for all routes using Mapbox API"""
    
    # Check if Mapbox token is configured
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        logger.error("❌ MAPBOX_ACCESS_TOKEN not configured. Please set it in your .env file")
        logger.info("💡 Get a free token from https://mapbox.com")
        return
    
    logger.info("🗺️ Starting route geometry population with Mapbox integration")
    
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "guzosync")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    app_state = AppState(db)
    
    try:
        # Get all routes that don't have geometry or have old geometry
        routes_cursor = db.routes.find({
            "$or": [
                {"route_geometry": None},
                {"route_geometry": {"$exists": False}},
                {"last_shape_update": None},
                {"last_shape_update": {"$exists": False}}
            ],
            "is_active": True
        })
        
        routes = await routes_cursor.to_list(length=3)  # Test with 3 routes to verify fix
        logger.info(f"📊 Found {len(routes)} routes needing geometry population (testing fix with 3 routes)")
        
        if len(routes) == 0:
            logger.info("✅ All routes already have geometry data")
            return
        
        success_count = 0
        error_count = 0
        
        for i, route in enumerate(routes, 1):
            route_id = route["id"]
            route_name = route.get("name", "Unknown")
            stop_ids = route.get("stop_ids", [])
            
            logger.info(f"🚌 [{i}/{len(routes)}] Processing route: {route_name} ({route_id})")
            
            if len(stop_ids) < 2:
                logger.warning(f"⚠️ Route {route_name} has insufficient stops ({len(stop_ids)}), skipping")
                error_count += 1
                continue
            
            try:
                # Fetch bus stops for this route
                bus_stops_cursor = db.bus_stops.find({"id": {"$in": stop_ids}})
                bus_stops_docs = await bus_stops_cursor.to_list(length=None)
                
                # Convert to BusStop objects in correct order
                bus_stops = []
                for stop_id in stop_ids:
                    for stop_doc in bus_stops_docs:
                        if stop_doc["id"] == stop_id:
                            location = stop_doc.get("location", {})
                            if location.get("latitude") and location.get("longitude"):
                                bus_stop = BusStop(
                                    id=stop_doc["id"],
                                    name=stop_doc["name"],
                                    location=Location(
                                        latitude=location["latitude"],
                                        longitude=location["longitude"]
                                    ),
                                    capacity=stop_doc.get("capacity"),
                                    is_active=stop_doc.get("is_active", True)
                                )
                                bus_stops.append(bus_stop)
                            break
                
                if len(bus_stops) < 2:
                    logger.warning(f"⚠️ Route {route_name} has insufficient valid stops ({len(bus_stops)}), skipping")
                    error_count += 1
                    continue
                
                # Generate route shape using Mapbox
                logger.info(f"🗺️ Fetching route geometry from Mapbox for {route_name}")
                shape_data = await route_service.generate_route_shape(route_id, bus_stops, app_state)
                
                if shape_data:
                    logger.info(f"✅ Successfully generated geometry for {route_name}")
                    logger.info(f"   📏 Distance: {shape_data.get('distance', 0)/1000:.2f} km")
                    logger.info(f"   ⏱️ Duration: {shape_data.get('duration', 0)/60:.1f} minutes")
                    success_count += 1
                else:
                    logger.error(f"❌ Failed to generate geometry for {route_name}")
                    error_count += 1
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Error processing route {route_name}: {e}")
                error_count += 1
                continue
        
        # Summary
        logger.info("🎉 Route geometry population completed!")
        logger.info(f"✅ Successfully processed: {success_count} routes")
        logger.info(f"❌ Failed to process: {error_count} routes")
        logger.info(f"📊 Total routes: {len(routes)}")
        
        if success_count > 0:
            logger.info("🚌 Bus simulation will now use real road paths!")
        
    except Exception as e:
        logger.error(f"💥 Fatal error during route geometry population: {e}")
        raise
    finally:
        client.close()


async def check_geometry_status():
    """Check the current status of route geometry in the database"""
    
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "guzosync")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Count routes with and without geometry
        total_routes = await db.routes.count_documents({"is_active": True})
        routes_with_geometry = await db.routes.count_documents({
            "route_geometry": {"$exists": True, "$ne": None},
            "is_active": True
        })
        routes_without_geometry = total_routes - routes_with_geometry
        
        logger.info("📊 Route Geometry Status:")
        logger.info(f"   📈 Total active routes: {total_routes}")
        logger.info(f"   ✅ Routes with geometry: {routes_with_geometry}")
        logger.info(f"   ❌ Routes without geometry: {routes_without_geometry}")
        
        if routes_without_geometry > 0:
            logger.info(f"💡 Run populate_route_geometry() to fetch geometry for {routes_without_geometry} routes")
        else:
            logger.info("🎉 All routes have geometry data!")
            
    finally:
        client.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate route geometry using Mapbox")
    parser.add_argument("--check", action="store_true", help="Check current geometry status")
    parser.add_argument("--populate", action="store_true", help="Populate missing geometry")
    
    args = parser.parse_args()
    
    if args.check:
        asyncio.run(check_geometry_status())
    elif args.populate:
        asyncio.run(populate_route_geometry())
    else:
        # Default: check status first, then populate if needed
        asyncio.run(check_geometry_status())
        print("\nTo populate geometry, run: python scripts/populate_route_geometry.py --populate")
