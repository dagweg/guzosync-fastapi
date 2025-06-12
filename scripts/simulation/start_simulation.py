#!/usr/bin/env python
"""
Bus Simulation Startup Script

This script starts the bus simulation system that simulates all buses
in the database moving along their assigned routes.

Usage:
    python start_simulation.py                    # Start with default settings
    python start_simulation.py --interval 3      # Update every 3 seconds
    python start_simulation.py --max-buses 20    # Limit to 20 buses
    python start_simulation.py --seed-first      # Seed database first
"""

import asyncio
import argparse
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from simulation.bus_simulator import BusSimulator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/simulation.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)

# MongoDB configuration
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "guzosync")

# Global simulation instance
simulator: Optional[BusSimulator] = None


async def seed_database_if_needed():
    """Seed the database if it's empty."""
    logger.info("🌱 Checking if database seeding is needed...")
    
    try:
        # Import and run seeding
        from seed_db_startup import main as seed_main
        await seed_main()
        logger.info("✅ Database seeding completed")
    except Exception as e:
        logger.error(f"❌ Database seeding failed: {e}")
        raise


async def check_database_ready(db) -> bool:
    """Check if database has the necessary data for simulation."""
    try:
        # Check for buses with assigned routes
        bus_count = await db.buses.count_documents({
            "assigned_route_id": {"$ne": None, "$exists": True},
            "bus_status": "OPERATIONAL"
        })
        
        # Check for routes
        route_count = await db.routes.count_documents({"is_active": True})
        
        # Check for bus stops
        stop_count = await db.bus_stops.count_documents({"is_active": True})
        
        logger.info(f"📊 Database status: {bus_count} buses, {route_count} routes, {stop_count} stops")
        
        if bus_count == 0:
            logger.warning("⚠️ No operational buses with assigned routes found")
            return False
        
        if route_count == 0:
            logger.warning("⚠️ No active routes found")
            return False
        
        if stop_count < 2:
            logger.warning("⚠️ Insufficient bus stops found")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking database: {e}")
        return False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    if simulator:
        asyncio.create_task(simulator.stop_simulation())
    sys.exit(0)


async def assign_routes_to_buses(db):
    """Assign routes to buses that don't have them."""
    logger.info("🔄 Assigning routes to buses without assignments...")
    
    try:
        # Get buses without assigned routes
        unassigned_buses = await db.buses.find({
            "$or": [
                {"assigned_route_id": None},
                {"assigned_route_id": {"$exists": False}}
            ],
            "bus_status": "OPERATIONAL"
        }).to_list(length=None)
        
        if not unassigned_buses:
            logger.info("✅ All operational buses already have route assignments")
            return
        
        # Get available routes
        routes = await db.routes.find({"is_active": True}).to_list(length=None)
        
        if not routes:
            logger.warning("⚠️ No active routes available for assignment")
            return
        
        # Assign routes randomly to buses
        import random
        assignments_made = 0
        
        for bus in unassigned_buses:
            route = random.choice(routes)
            
            await db.buses.update_one(
                {"id": bus["id"]},
                {"$set": {"assigned_route_id": route["id"]}}
            )
            
            assignments_made += 1
            logger.debug(f"🚌 Assigned bus {bus.get('license_plate')} to route {route.get('name')}")
        
        logger.info(f"✅ Assigned routes to {assignments_made} buses")
        
    except Exception as e:
        logger.error(f"Error assigning routes to buses: {e}")


async def main():
    """Main simulation function."""
    global simulator
    
    parser = argparse.ArgumentParser(description='Start bus route simulation')
    parser.add_argument('--interval', type=float, default=5.0, 
                       help='Update interval in seconds (default: 5.0)')
    parser.add_argument('--max-buses', type=int, default=50,
                       help='Maximum number of buses to simulate (default: 50)')
    parser.add_argument('--seed-first', action='store_true',
                       help='Seed database before starting simulation')
    parser.add_argument('--assign-routes', action='store_true',
                       help='Assign routes to buses without assignments')
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 Starting GuzoSync Bus Simulation")
    logger.info(f"📡 MongoDB URL: {mongodb_url}")
    logger.info(f"🗄️ Database: {database_name}")
    logger.info(f"⏱️ Update interval: {args.interval} seconds")
    logger.info(f"🚌 Max buses: {args.max_buses}")
    
    # Connect to MongoDB
    client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        logger.info("✅ Connected to MongoDB successfully")
        
        # Seed database if requested
        if args.seed_first:
            await seed_database_if_needed()
        
        # Assign routes if requested
        if args.assign_routes:
            await assign_routes_to_buses(db)
        
        # Check if database is ready
        if not await check_database_ready(db):
            logger.error("❌ Database is not ready for simulation")
            logger.info("💡 Try running with --seed-first or --assign-routes flags")
            return
        
        # Initialize simulator
        simulator = BusSimulator(db, update_interval=args.interval)
        simulator.max_buses_to_simulate = args.max_buses
        
        # Initialize and start simulation
        await simulator.initialize()
        await simulator.start_simulation()
        
        # Print status
        status = simulator.get_simulation_status()
        logger.info("🎯 Simulation Status:")
        logger.info(f"   📊 Total buses: {status['total_buses']}")
        logger.info(f"   🚌 Active buses: {status['active_buses']}")
        logger.info(f"   🛣️ Routes loaded: {status['routes_loaded']}")
        logger.info(f"   ⏱️ Update interval: {status['update_interval']}s")
        
        if status['active_buses'] == 0:
            logger.warning("⚠️ No active buses to simulate!")
            return
        
        logger.info("✅ Bus simulation is running!")
        logger.info("🔄 Buses are now moving along their routes...")
        logger.info("📡 Location updates are being broadcast via WebSocket")
        logger.info("🛑 Press Ctrl+C to stop the simulation")
        
        # Keep the simulation running
        try:
            while simulator.is_running:
                await asyncio.sleep(10)
                
                # Print periodic status updates
                current_time = datetime.now().strftime("%H:%M:%S")
                logger.info(f"🕐 {current_time} - Simulation running with {status['active_buses']} active buses")
                
        except KeyboardInterrupt:
            logger.info("🛑 Received keyboard interrupt")
        
    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")
        raise
    
    finally:
        # Clean shutdown
        if simulator:
            await simulator.stop_simulation()
        
        client.close()
        logger.info("👋 Simulation shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Simulation interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
