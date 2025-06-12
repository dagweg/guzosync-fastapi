#!/usr/bin/env python
"""
Bus Simulation Demo

This script demonstrates the bus simulation system by:
1. Starting a minimal simulation with a few buses
2. Showing real-time location updates
3. Demonstrating WebSocket integration
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from simulation.bus_simulator import BusSimulator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# MongoDB configuration
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "guzosync")


async def create_demo_data(db):
    """Create minimal demo data for simulation."""
    logger.info("🌱 Creating demo data...")
    
    try:
        # Create demo bus stops
        demo_stops = [
            {
                "id": "demo_stop_1",
                "name": "Demo Stop 1 - Megenagna",
                "location": {"latitude": 9.0123, "longitude": 38.7456},
                "capacity": 50,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "_id": "demo_stop_1"
            },
            {
                "id": "demo_stop_2", 
                "name": "Demo Stop 2 - Bole",
                "location": {"latitude": 9.0234, "longitude": 38.7567},
                "capacity": 40,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "_id": "demo_stop_2"
            },
            {
                "id": "demo_stop_3",
                "name": "Demo Stop 3 - Piazza", 
                "location": {"latitude": 9.0345, "longitude": 38.7678},
                "capacity": 60,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "_id": "demo_stop_3"
            }
        ]
        
        # Insert stops (replace if exist)
        for stop in demo_stops:
            await db.bus_stops.replace_one(
                {"id": stop["id"]}, 
                stop, 
                upsert=True
            )
        
        # Create demo route
        demo_route = {
            "id": "demo_route_1",
            "name": "Demo Route - City Center",
            "description": "Demonstration route for simulation",
            "stop_ids": ["demo_stop_1", "demo_stop_2", "demo_stop_3"],
            "total_distance": 5.2,
            "estimated_duration": 25.0,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "_id": "demo_route_1"
        }
        
        await db.routes.replace_one(
            {"id": demo_route["id"]},
            demo_route,
            upsert=True
        )
        
        # Create demo buses
        demo_buses = [
            {
                "id": "demo_bus_1",
                "license_plate": "DEMO-001",
                "bus_type": "STANDARD",
                "capacity": 45,
                "current_location": {"latitude": 9.0123, "longitude": 38.7456},
                "last_location_update": datetime.now(timezone.utc),
                "heading": 0.0,
                "speed": 0.0,
                "assigned_route_id": "demo_route_1",
                "bus_status": "OPERATIONAL",
                "manufacture_year": 2020,
                "bus_model": "Demo Bus Model",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "_id": "demo_bus_1"
            },
            {
                "id": "demo_bus_2",
                "license_plate": "DEMO-002", 
                "bus_type": "STANDARD",
                "capacity": 45,
                "current_location": {"latitude": 9.0234, "longitude": 38.7567},
                "last_location_update": datetime.now(timezone.utc),
                "heading": 180.0,
                "speed": 0.0,
                "assigned_route_id": "demo_route_1",
                "bus_status": "OPERATIONAL",
                "manufacture_year": 2021,
                "bus_model": "Demo Bus Model",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "_id": "demo_bus_2"
            }
        ]
        
        # Insert buses (replace if exist)
        for bus in demo_buses:
            await db.buses.replace_one(
                {"id": bus["id"]},
                bus,
                upsert=True
            )
        
        logger.info("✅ Demo data created successfully")
        logger.info(f"   📍 Created {len(demo_stops)} bus stops")
        logger.info(f"   🛣️ Created 1 route")
        logger.info(f"   🚌 Created {len(demo_buses)} buses")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create demo data: {e}")
        return False


async def run_demo_simulation():
    """Run a demonstration of the bus simulation."""
    logger.info("🚀 Starting Bus Simulation Demo")
    logger.info(f"📡 MongoDB URL: {mongodb_url}")
    logger.info(f"🗄️ Database: {database_name}")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        logger.info("✅ Connected to MongoDB successfully")
        
        # Create demo data
        if not await create_demo_data(db):
            logger.error("❌ Failed to create demo data")
            return
        
        # Initialize simulator
        logger.info("🔧 Initializing bus simulator...")
        simulator = BusSimulator(db, update_interval=2.0)  # Fast updates for demo
        simulator.max_buses_to_simulate = 5  # Limit for demo
        
        # Initialize and start simulation
        await simulator.initialize()
        
        # Check if buses were loaded
        status = simulator.get_simulation_status()
        if status['total_buses'] == 0:
            logger.error("❌ No buses loaded for simulation")
            return
        
        logger.info("🎯 Demo Simulation Status:")
        logger.info(f"   📊 Total buses: {status['total_buses']}")
        logger.info(f"   🚌 Active buses: {status['active_buses']}")
        logger.info(f"   🛣️ Routes loaded: {status['routes_loaded']}")
        logger.info(f"   ⏱️ Update interval: {status['update_interval']}s")
        
        # Start simulation
        await simulator.start_simulation()
        
        logger.info("✅ Demo simulation started!")
        logger.info("🔄 Buses are now moving along their routes...")
        logger.info("📡 Location updates are being broadcast")
        logger.info("🕐 Demo will run for 60 seconds...")
        
        # Run demo for 60 seconds
        demo_duration = 60
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < demo_duration:
            await asyncio.sleep(5)
            
            # Print status update
            elapsed = int((datetime.now() - start_time).total_seconds())
            remaining = demo_duration - elapsed
            
            logger.info(f"🕐 Demo running... {elapsed}s elapsed, {remaining}s remaining")
            
            # Show bus positions
            buses_cursor = db.buses.find({"id": {"$in": ["demo_bus_1", "demo_bus_2"]}})
            buses = await buses_cursor.to_list(length=None)
            
            for bus in buses:
                location = bus.get("current_location", {})
                lat = location.get("latitude", 0)
                lon = location.get("longitude", 0)
                speed = bus.get("speed", 0)
                heading = bus.get("heading", 0)
                
                logger.info(f"   🚌 {bus['license_plate']}: ({lat:.4f}, {lon:.4f}) | {speed:.1f} km/h | {heading:.0f}°")
        
        # Stop simulation
        logger.info("🛑 Stopping demo simulation...")
        await simulator.stop_simulation()
        
        logger.info("✅ Demo completed successfully!")
        logger.info("💡 To run full simulation: python start_simulation.py --seed-first --assign-routes")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        raise
    
    finally:
        client.close()


async def cleanup_demo_data(db):
    """Clean up demo data."""
    logger.info("🧹 Cleaning up demo data...")
    
    try:
        # Remove demo data
        await db.buses.delete_many({"id": {"$in": ["demo_bus_1", "demo_bus_2"]}})
        await db.routes.delete_many({"id": "demo_route_1"})
        await db.bus_stops.delete_many({"id": {"$in": ["demo_stop_1", "demo_stop_2", "demo_stop_3"]}})
        
        logger.info("✅ Demo data cleaned up")
        
    except Exception as e:
        logger.error(f"⚠️ Error cleaning up demo data: {e}")


async def main():
    """Main demo function."""
    try:
        await run_demo_simulation()
        
        # Ask user if they want to clean up
        print("\n" + "="*50)
        response = input("🧹 Clean up demo data? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            client = AsyncIOMotorClient(mongodb_url)
            db = client[database_name]
            try:
                await cleanup_demo_data(db)
            finally:
                client.close()
        else:
            logger.info("💡 Demo data left in database for further testing")
        
    except KeyboardInterrupt:
        logger.info("🛑 Demo interrupted by user")
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
