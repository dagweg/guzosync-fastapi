#!/usr/bin/env python
"""
Fix Bus Simulation Issues

This script fixes the current bus simulation issues by:
1. Assigning routes to buses that don't have them
2. Setting proper current_location for buses that have None
3. Ensuring all operational buses have the required data for simulation
"""

import asyncio
import os
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "guzosync")


def random_location():
    """Generate a random location in Addis Ababa area."""
    # Addis Ababa approximate bounds
    lat_min, lat_max = 8.9, 9.1
    lon_min, lon_max = 38.6, 38.9
    
    return {
        "latitude": round(random.uniform(lat_min, lat_max), 6),
        "longitude": round(random.uniform(lon_min, lon_max), 6)
    }


async def fix_bus_simulation_data():
    """Fix bus simulation data issues."""
    print("🔧 Fixing bus simulation data...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # 1. Fix buses with None current_location
        print("\n1️⃣ Fixing buses with None current_location...")
        buses_with_none_location = await db.buses.find({
            "current_location": None
        }).to_list(length=None)
        
        print(f"Found {len(buses_with_none_location)} buses with None location")
        
        for bus in buses_with_none_location:
            new_location = random_location()
            await db.buses.update_one(
                {"id": bus["id"]},
                {
                    "$set": {
                        "current_location": new_location,
                        "last_location_update": datetime.now(timezone.utc),
                        "heading": random.uniform(0, 359),
                        "speed": 0.0,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            print(f"   ✅ Fixed location for bus {bus.get('license_plate', bus['id'])}")
        
        # 2. Assign routes to operational buses without routes
        print("\n2️⃣ Assigning routes to buses without assignments...")
        
        # Get operational buses without routes
        unassigned_buses = await db.buses.find({
            "$or": [
                {"assigned_route_id": None},
                {"assigned_route_id": {"$exists": False}}
            ],
            "bus_status": "OPERATIONAL"
        }).to_list(length=None)
        
        print(f"Found {len(unassigned_buses)} operational buses without routes")
        
        # Get active routes
        active_routes = await db.routes.find({
            "is_active": True
        }).to_list(length=None)
        
        print(f"Found {len(active_routes)} active routes")
        
        if active_routes and unassigned_buses:
            assignments_made = 0
            for bus in unassigned_buses:
                route = random.choice(active_routes)
                
                await db.buses.update_one(
                    {"id": bus["id"]},
                    {
                        "$set": {
                            "assigned_route_id": route["id"],
                            "updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                assignments_made += 1
                print(f"   ✅ Assigned bus {bus.get('license_plate', bus['id'])} to route {route.get('name', route['id'])}")
            
            print(f"✅ Assigned routes to {assignments_made} buses")
        else:
            print("⚠️ No active routes or unassigned buses found")
        
        # 3. Ensure all operational buses have proper status
        print("\n3️⃣ Ensuring operational buses have proper data...")
        
        operational_buses = await db.buses.find({
            "bus_status": "OPERATIONAL"
        }).to_list(length=None)
        
        print(f"Found {len(operational_buses)} operational buses")
        
        fixed_count = 0
        for bus in operational_buses:
            updates = {}
            
            # Ensure current_location is not None
            if bus.get("current_location") is None:
                updates["current_location"] = random_location()
                updates["last_location_update"] = datetime.now(timezone.utc)
            
            # Ensure heading is set
            if bus.get("heading") is None:
                updates["heading"] = random.uniform(0, 359)
            
            # Ensure speed is set
            if bus.get("speed") is None:
                updates["speed"] = 0.0
            
            # Ensure assigned_route_id exists
            if not bus.get("assigned_route_id") and active_routes:
                updates["assigned_route_id"] = random.choice(active_routes)["id"]
            
            if updates:
                updates["updated_at"] = datetime.now(timezone.utc)
                await db.buses.update_one(
                    {"id": bus["id"]},
                    {"$set": updates}
                )
                fixed_count += 1
                print(f"   ✅ Fixed data for bus {bus.get('license_plate', bus['id'])}")
        
        print(f"✅ Fixed data for {fixed_count} buses")
        
        # 4. Verify simulation readiness
        print("\n4️⃣ Verifying simulation readiness...")
        
        # Check buses ready for simulation
        simulation_ready_buses = await db.buses.find({
            "assigned_route_id": {"$ne": None, "$exists": True},
            "bus_status": "OPERATIONAL",
            "current_location": {"$ne": None, "$exists": True}
        }).to_list(length=None)
        
        print(f"✅ {len(simulation_ready_buses)} buses are ready for simulation")
        
        # Check routes with stops
        routes_with_stops = await db.routes.find({
            "is_active": True,
            "stop_ids": {"$exists": True, "$not": {"$size": 0}}
        }).to_list(length=None)
        
        print(f"✅ {len(routes_with_stops)} routes have bus stops")
        
        # Check bus stops
        active_stops = await db.bus_stops.count_documents({
            "is_active": True
        })
        
        print(f"✅ {active_stops} active bus stops available")
        
        print("\n🎉 Bus simulation data fix completed!")
        print(f"📊 Summary:")
        print(f"   🚌 Buses ready for simulation: {len(simulation_ready_buses)}")
        print(f"   🛣️ Routes with stops: {len(routes_with_stops)}")
        print(f"   🚏 Active bus stops: {active_stops}")
        
        if len(simulation_ready_buses) > 0 and len(routes_with_stops) > 0 and active_stops >= 2:
            print("✅ Simulation should now work properly!")
        else:
            print("⚠️ Simulation may still have issues - check the data above")
        
    except Exception as e:
        print(f"❌ Error fixing bus simulation data: {e}")
        raise
    
    finally:
        client.close()


async def main():
    """Main function."""
    print("🚀 Starting Bus Simulation Data Fix")
    print(f"📡 MongoDB URL: {mongodb_url}")
    print(f"🗄️ Database: {database_name}")
    print()
    
    try:
        await fix_bus_simulation_data()
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
