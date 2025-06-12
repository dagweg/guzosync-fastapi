#!/usr/bin/env python
"""
Bus Simulation Monitor

This script provides a simple monitoring interface for the bus simulation.
It shows real-time statistics about the running simulation.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "guzosync")


async def get_simulation_stats(db) -> Dict[str, Any]:
    """Get current simulation statistics."""
    try:
        # Count buses by status
        total_buses = await db.buses.count_documents({})
        operational_buses = await db.buses.count_documents({"bus_status": "OPERATIONAL"})
        buses_with_routes = await db.buses.count_documents({
            "assigned_route_id": {"$ne": None, "$exists": True}
        })
        
        # Count buses with recent location updates (last 2 minutes)
        two_minutes_ago = datetime.now(timezone.utc).timestamp() - 120
        active_buses = await db.buses.count_documents({
            "last_location_update": {"$gte": datetime.fromtimestamp(two_minutes_ago, timezone.utc)}
        })
        
        # Count routes and stops
        total_routes = await db.routes.count_documents({})
        active_routes = await db.routes.count_documents({"is_active": True})
        total_stops = await db.bus_stops.count_documents({})
        active_stops = await db.bus_stops.count_documents({"is_active": True})
        
        # Get recent location updates
        recent_updates = await db.buses.find(
            {"last_location_update": {"$exists": True}},
            {"license_plate": 1, "last_location_update": 1, "current_location": 1, "speed": 1}
        ).sort("last_location_update", -1).limit(5).to_list(length=None)
        
        return {
            "buses": {
                "total": total_buses,
                "operational": operational_buses,
                "with_routes": buses_with_routes,
                "recently_active": active_buses
            },
            "routes": {
                "total": total_routes,
                "active": active_routes
            },
            "stops": {
                "total": total_stops,
                "active": active_stops
            },
            "recent_updates": recent_updates
        }
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {}


def print_stats(stats: Dict[str, Any]):
    """Print formatted statistics."""
    print("\n" + "="*60)
    print("🚌 GUZOSYNC BUS SIMULATION MONITOR")
    print("="*60)
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not stats:
        print("❌ Unable to retrieve statistics")
        return
    
    # Bus statistics
    buses = stats.get("buses", {})
    print("🚌 BUS STATISTICS:")
    print(f"   Total Buses: {buses.get('total', 0)}")
    print(f"   Operational: {buses.get('operational', 0)}")
    print(f"   With Routes: {buses.get('with_routes', 0)}")
    print(f"   Recently Active: {buses.get('recently_active', 0)}")
    print()
    
    # Route statistics
    routes = stats.get("routes", {})
    print("🛣️ ROUTE STATISTICS:")
    print(f"   Total Routes: {routes.get('total', 0)}")
    print(f"   Active Routes: {routes.get('active', 0)}")
    print()
    
    # Stop statistics
    stops = stats.get("stops", {})
    print("🚏 STOP STATISTICS:")
    print(f"   Total Stops: {stops.get('total', 0)}")
    print(f"   Active Stops: {stops.get('active', 0)}")
    print()
    
    # Recent activity
    recent_updates = stats.get("recent_updates", [])
    if recent_updates:
        print("📡 RECENT BUS ACTIVITY:")
        for bus in recent_updates:
            license_plate = bus.get("license_plate", "Unknown")
            last_update = bus.get("last_location_update")
            speed = bus.get("speed", 0)
            location = bus.get("current_location", {})
            
            if last_update:
                time_str = last_update.strftime("%H:%M:%S")
                lat = location.get("latitude", 0)
                lon = location.get("longitude", 0)
                print(f"   {license_plate}: {time_str} | Speed: {speed:.1f} km/h | Pos: ({lat:.4f}, {lon:.4f})")
    else:
        print("📡 RECENT BUS ACTIVITY: No recent activity")
    
    print()
    
    # Simulation health check
    recently_active = buses.get('recently_active', 0)
    with_routes = buses.get('with_routes', 0)
    
    if recently_active == 0:
        print("⚠️ WARNING: No buses have updated their location recently!")
        print("   The simulation may not be running.")
    elif recently_active < with_routes * 0.5:
        print("⚠️ WARNING: Less than 50% of buses with routes are active!")
        print("   Some buses may not be moving properly.")
    else:
        print("✅ SIMULATION STATUS: Healthy")
        print(f"   {recently_active}/{with_routes} buses are actively moving")


async def monitor_loop():
    """Main monitoring loop."""
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        while True:
            try:
                # Clear screen (works on most terminals)
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # Get and display stats
                stats = await get_simulation_stats(db)
                print_stats(stats)
                
                print("🔄 Refreshing in 10 seconds... (Press Ctrl+C to exit)")
                await asyncio.sleep(10)
                
            except KeyboardInterrupt:
                print("\n👋 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(5)
                
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
    finally:
        client.close()


async def main():
    """Main function."""
    print("🚀 Starting GuzoSync Bus Simulation Monitor")
    print(f"📡 MongoDB URL: {mongodb_url}")
    print(f"🗄️ Database: {database_name}")
    print()
    
    try:
        await monitor_loop()
    except KeyboardInterrupt:
        print("\n🛑 Monitor interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
