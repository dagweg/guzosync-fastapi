"""
One-Time Route Geometry Population Script

This script populates ALL route geometries from Mapbox API once and stores them 
permanently in the database. After running this script, you'll never need to 
call Mapbox API again - all future requests will use cached data.

Usage:
    python scripts/populate_all_routes_once.py --all
    python scripts/populate_all_routes_once.py --batch 50  # Process 50 routes
    python scripts/populate_all_routes_once.py --status    # Check status only
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
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('one_time_route_population.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class AppState:
    """Mock app state for route service"""
    def __init__(self, mongodb):
        self.mongodb = mongodb


async def check_population_status():
    """Check how many routes need geometry population"""
    
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "guzosync")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Count routes with and without geometry
        total_routes = await db.routes.count_documents({"is_active": True})
        routes_with_geometry = await db.routes.count_documents({
            "route_geometry": {"$exists": True, "$ne": None},
            "route_shape_data": {"$exists": True, "$ne": None},
            "is_active": True
        })
        routes_without_geometry = total_routes - routes_with_geometry
        
        logger.info("📊 Route Geometry Population Status:")
        logger.info(f"   📈 Total active routes: {total_routes}")
        logger.info(f"   ✅ Routes with cached geometry: {routes_with_geometry}")
        logger.info(f"   ❌ Routes needing population: {routes_without_geometry}")
        
        if routes_without_geometry > 0:
            # Estimate API calls needed
            mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
            if mapbox_token:
                logger.info(f"🔑 Mapbox token configured - ready to populate {routes_without_geometry} routes")
                logger.info(f"💰 This will use {routes_without_geometry} API calls (one-time cost)")
            else:
                logger.warning("❌ No Mapbox token configured!")
        else:
            logger.info("🎉 All routes already have cached geometry - no API calls needed!")
            
        return {
            "total": total_routes,
            "with_geometry": routes_with_geometry,
            "without_geometry": routes_without_geometry
        }
            
    finally:
        client.close()


async def populate_all_routes(batch_size: int = None):
    """Populate route geometry for all routes (one-time operation)"""
    
    # Check if Mapbox token is configured
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        logger.error("❌ MAPBOX_ACCESS_TOKEN not configured. Please set it in your .env file")
        logger.info("💡 Get a free token from https://mapbox.com")
        return
    
    logger.info("🗺️ Starting ONE-TIME route geometry population with Mapbox")
    logger.info("💾 After this completes, all future requests will use cached data (no more API calls)")
    
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "guzosync")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    app_state = AppState(db)
    
    try:
        # Get all routes that don't have geometry
        routes_cursor = db.routes.find({
            "$or": [
                {"route_geometry": None},
                {"route_geometry": {"$exists": False}},
                {"route_shape_data": None},
                {"route_shape_data": {"$exists": False}}
            ],
            "is_active": True
        })
        
        if batch_size:
            routes = await routes_cursor.to_list(length=batch_size)
            logger.info(f"📊 Processing {len(routes)} routes (batch size: {batch_size})")
        else:
            routes = await routes_cursor.to_list(length=None)
            logger.info(f"📊 Processing ALL {len(routes)} routes needing geometry")
        
        if len(routes) == 0:
            logger.info("✅ All routes already have cached geometry data!")
            return
        
        logger.warning(f"🔑 This will use {len(routes)} Mapbox API calls")
        logger.info("💾 Each route will be permanently cached - no future API calls needed")
        
        success_count = 0
        error_count = 0
        
        for i, route in enumerate(routes, 1):
            route_id = route["id"]
            route_name = route.get("name", "Unknown")
            stop_ids = route.get("stop_ids", [])
            
            logger.info(f"🚌 [{i}/{len(routes)}] Processing: {route_name}")
            
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
                
                # Generate route shape using Mapbox (will be cached permanently)
                shape_data = await route_service.generate_route_shape(route_id, bus_stops, app_state)
                
                if shape_data:
                    logger.info(f"✅ Cached geometry for {route_name}")
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
        logger.info("🎉 ONE-TIME route geometry population completed!")
        logger.info(f"✅ Successfully cached: {success_count} routes")
        logger.info(f"❌ Failed to process: {error_count} routes")
        logger.info(f"📊 Total processed: {len(routes)}")
        
        if success_count > 0:
            logger.info("💾 All cached routes will be used automatically - no more API calls needed!")
            logger.info("🚌 Bus simulation will now use real road paths from cached data!")
        
    except Exception as e:
        logger.error(f"💥 Fatal error during route geometry population: {e}")
        raise
    finally:
        client.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="One-time route geometry population")
    parser.add_argument("--all", action="store_true", help="Populate ALL routes at once")
    parser.add_argument("--batch", type=int, help="Process specific number of routes")
    parser.add_argument("--status", action="store_true", help="Check population status only")
    
    args = parser.parse_args()
    
    if args.status:
        asyncio.run(check_population_status())
    elif args.all:
        asyncio.run(populate_all_routes())
    elif args.batch:
        asyncio.run(populate_all_routes(batch_size=args.batch))
    else:
        # Default: show status and instructions
        asyncio.run(check_population_status())
        print("\nTo populate routes:")
        print("  --all     : Populate ALL routes at once")
        print("  --batch N : Populate N routes")
        print("  --status  : Check status only")
