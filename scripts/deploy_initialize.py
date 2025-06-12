#!/usr/bin/env python3
"""
Complete Deployment Initialization Script

This script handles the complete initialization of a GuzoSync deployment:
1. Database seeding with routes, stops, buses, users
2. Mapbox route geometry population
3. Validation and health checks

Usage:
    python scripts/deploy_initialize.py --full        # Complete initialization
    python scripts/deploy_initialize.py --routes-only # Only populate route geometry
    python scripts/deploy_initialize.py --check       # Check status only
"""

import asyncio
import logging
import os
import sys
import subprocess
import time
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deployment_initialization.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


async def check_database_connection():
    """Check if database is accessible"""
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("DATABASE_NAME", "guzosync")
        
        client = AsyncIOMotorClient(mongodb_url)
        db = client[database_name]
        
        # Test connection
        await db.admin.command('ping')
        logger.info("✅ Database connection successful")
        
        client.close()
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def check_mapbox_token():
    """Check if Mapbox token is configured"""
    token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if token:
        logger.info("✅ Mapbox access token configured")
        return True
    else:
        logger.error("❌ MAPBOX_ACCESS_TOKEN not configured")
        logger.info("💡 Get a free token from https://mapbox.com")
        return False


async def run_database_seeding():
    """Run the database seeding script"""
    logger.info("🌱 Starting database seeding...")
    
    try:
        # Run the seeding script
        result = subprocess.run([
            sys.executable, "scripts/database/init_db_complete.py"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("✅ Database seeding completed successfully")
            logger.info("📊 Seeded: routes, bus stops, buses, users, and test data")
            return True
        else:
            logger.error(f"❌ Database seeding failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Database seeding timed out (5 minutes)")
        return False
    except Exception as e:
        logger.error(f"❌ Database seeding error: {e}")
        return False


async def run_route_geometry_population():
    """Run the route geometry population script"""
    logger.info("🗺️ Starting route geometry population...")
    
    try:
        # Run the population script
        result = subprocess.run([
            sys.executable, "scripts/populate_all_routes_once.py", "--all"
        ], capture_output=True, text=True, timeout=1800)  # 30 minutes timeout
        
        if result.returncode == 0:
            logger.info("✅ Route geometry population completed successfully")
            logger.info("💾 All routes now have cached Mapbox geometry")
            return True
        else:
            logger.error(f"❌ Route geometry population failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Route geometry population timed out (30 minutes)")
        return False
    except Exception as e:
        logger.error(f"❌ Route geometry population error: {e}")
        return False


async def check_deployment_status():
    """Check the status of the deployment"""
    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("DATABASE_NAME", "guzosync")
        
        client = AsyncIOMotorClient(mongodb_url)
        db = client[database_name]
        
        # Count various collections
        routes_count = await db.routes.count_documents({"is_active": True})
        stops_count = await db.bus_stops.count_documents({"is_active": True})
        buses_count = await db.buses.count_documents({})
        users_count = await db.users.count_documents({})
        
        # Count routes with geometry
        routes_with_geometry = await db.routes.count_documents({
            "route_geometry": {"$exists": True, "$ne": None},
            "route_shape_data": {"$exists": True, "$ne": None},
            "is_active": True
        })
        
        logger.info("📊 Deployment Status:")
        logger.info(f"   🚌 Routes: {routes_count}")
        logger.info(f"   🚏 Bus Stops: {stops_count}")
        logger.info(f"   🚐 Buses: {buses_count}")
        logger.info(f"   👥 Users: {users_count}")
        logger.info(f"   🗺️ Routes with Mapbox geometry: {routes_with_geometry}/{routes_count}")
        
        # Calculate completion percentage
        if routes_count > 0:
            completion_pct = (routes_with_geometry / routes_count) * 100
            logger.info(f"   📈 Geometry completion: {completion_pct:.1f}%")
            
            if completion_pct == 100:
                logger.info("🎉 Deployment fully initialized and ready!")
                return True
            else:
                logger.warning(f"⚠️ {routes_count - routes_with_geometry} routes still need geometry")
                return False
        else:
            logger.error("❌ No routes found - database seeding may have failed")
            return False
            
        client.close()
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        return False


async def full_deployment_initialization():
    """Run complete deployment initialization"""
    logger.info("🚀 Starting FULL deployment initialization")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    # Step 1: Check prerequisites
    logger.info("🔍 Step 1: Checking prerequisites...")
    if not await check_database_connection():
        return False
    
    if not await check_mapbox_token():
        return False
    
    # Step 2: Database seeding
    logger.info("🌱 Step 2: Database seeding...")
    if not await run_database_seeding():
        return False
    
    # Wait a moment for database to settle
    await asyncio.sleep(2)
    
    # Step 3: Route geometry population
    logger.info("🗺️ Step 3: Route geometry population...")
    if not await run_route_geometry_population():
        return False
    
    # Step 4: Final validation
    logger.info("✅ Step 4: Final validation...")
    if not await check_deployment_status():
        return False
    
    # Success!
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"🎉 DEPLOYMENT INITIALIZATION COMPLETE!")
    logger.info(f"⏱️ Total time: {elapsed_time/60:.1f} minutes")
    logger.info("🚌 Your GuzoSync deployment is ready for production!")
    
    return True


async def routes_only_initialization():
    """Run only route geometry population"""
    logger.info("🗺️ Starting ROUTES-ONLY initialization")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    # Check prerequisites
    if not await check_database_connection():
        return False
    
    if not await check_mapbox_token():
        return False
    
    # Run route geometry population
    if not await run_route_geometry_population():
        return False
    
    # Validation
    if not await check_deployment_status():
        return False
    
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"🎉 ROUTE GEOMETRY INITIALIZATION COMPLETE!")
    logger.info(f"⏱️ Total time: {elapsed_time/60:.1f} minutes")
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GuzoSync Deployment Initialization")
    parser.add_argument("--full", action="store_true", help="Complete initialization (seeding + routes)")
    parser.add_argument("--routes-only", action="store_true", help="Only populate route geometry")
    parser.add_argument("--check", action="store_true", help="Check deployment status only")
    
    args = parser.parse_args()
    
    if args.full:
        success = asyncio.run(full_deployment_initialization())
    elif args.routes_only:
        success = asyncio.run(routes_only_initialization())
    elif args.check:
        success = asyncio.run(check_deployment_status())
    else:
        # Default: show status and instructions
        asyncio.run(check_deployment_status())
        print("\nDeployment initialization options:")
        print("  --full        : Complete initialization (seeding + routes)")
        print("  --routes-only : Only populate route geometry")
        print("  --check       : Check deployment status only")
        success = True
    
    sys.exit(0 if success else 1)
