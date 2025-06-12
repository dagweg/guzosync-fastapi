#!/usr/bin/env python3
"""
Test the broadcast fix to see if it works correctly.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "guzosync")

async def test_broadcast_logic():
    """Test the new broadcast logic."""
    print("🧪 Testing broadcast logic fix...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Simulate the new broadcast logic
        print(f"\n🔍 Simulating broadcast_all_bus_locations logic...")
        
        # Get all buses and filter manually (same as the fixed function)
        all_buses = await db.buses.find({}).to_list(length=None)
        print(f"   📊 Total buses in database: {len(all_buses)}")

        bus_locations = []
        for bus in all_buses:
            # Check if bus is operational or idle
            bus_status = bus.get("bus_status")
            if bus_status not in ["OPERATIONAL", "IDLE"]:
                continue
            
            # Check if bus has valid location
            location = bus.get("current_location")
            if (location is None or 
                not isinstance(location, dict) or 
                not location.get("latitude") or 
                not location.get("longitude")):
                continue
            
            # Bus meets criteria - add to broadcast list
            bus_data = {
                "bus_id": bus["id"],
                "license_plate": bus.get("license_plate"),
                "location": {
                    "latitude": location["latitude"],
                    "longitude": location["longitude"]
                },
                "heading": bus.get("heading"),
                "speed": bus.get("speed"),
                "route_id": bus.get("assigned_route_id"),
                "last_update": bus.get("last_location_update"),
                "status": bus.get("bus_status", "OPERATIONAL")
            }
            bus_locations.append(bus_data)
            
            # Log this bus
            license_plate = bus.get("license_plate", "Unknown")
            lat = location["latitude"]
            lng = location["longitude"]
            print(f"   ✅ {license_plate} ({bus_status}) at ({lat}, {lng})")

        print(f"\n📡 Broadcast Results:")
        print(f"   🚌 Total buses that would be broadcasted: {len(bus_locations)}")
        
        if len(bus_locations) > 0:
            print(f"   ✅ SUCCESS! {len(bus_locations)} buses will be broadcasted")
            
            # Show the message that would be sent
            message = {
                "type": "all_bus_locations",
                "buses": bus_locations,
                "timestamp": "2025-06-12T05:30:00Z"  # Example timestamp
            }
            
            print(f"\n📨 Sample broadcast message structure:")
            print(f"   Type: {message['type']}")
            print(f"   Bus count: {len(message['buses'])}")
            print(f"   First bus: {message['buses'][0]['license_plate']} at {message['buses'][0]['location']}")
            
        else:
            print(f"   ❌ ISSUE: No buses would be broadcasted")
            
            # Debug why no buses match
            print(f"\n🔍 Debugging why no buses match:")
            
            operational_count = 0
            idle_count = 0
            location_count = 0
            
            for bus in all_buses:
                status = bus.get("bus_status")
                location = bus.get("current_location")
                
                if status == "OPERATIONAL":
                    operational_count += 1
                elif status == "IDLE":
                    idle_count += 1
                    
                if (location is not None and 
                    isinstance(location, dict) and 
                    location.get("latitude") and 
                    location.get("longitude")):
                    location_count += 1
            
            print(f"   OPERATIONAL buses: {operational_count}")
            print(f"   IDLE buses: {idle_count}")
            print(f"   Buses with valid locations: {location_count}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_broadcast_logic())
