#!/usr/bin/env python3
"""
Debug script to check why buses aren't being broadcasted.
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

async def debug_buses():
    """Debug bus broadcasting issues."""
    print("🔍 Debugging bus broadcasting...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Check all buses
        buses = await db.buses.find({}).to_list(length=None)
        
        print(f"\n📊 Total buses: {len(buses)}")
        print()
        
        operational_idle = 0
        has_location = 0
        both = 0
        
        for bus in buses:
            license_plate = bus.get('license_plate', 'Unknown')
            bus_status = bus.get('bus_status', 'Unknown')
            location = bus.get('current_location')
            
            is_operational_idle = bus_status in ['OPERATIONAL', 'IDLE']
            has_valid_location = (location is not None and 
                                isinstance(location, dict) and 
                                location.get('latitude') and 
                                location.get('longitude'))
            
            if is_operational_idle:
                operational_idle += 1
            if has_valid_location:
                has_location += 1
            if is_operational_idle and has_valid_location:
                both += 1
                
            location_status = "Valid" if has_valid_location else "Invalid/None"
            print(f"{license_plate}: Status={bus_status}, Location={location_status}")
            
            # Show location details for first few buses
            if location and isinstance(location, dict):
                lat = location.get('latitude')
                lng = location.get('longitude')
                print(f"  Location details: lat={lat}, lng={lng}")
        
        print(f"\n📈 Summary:")
        print(f"   OPERATIONAL/IDLE buses: {operational_idle}")
        print(f"   Buses with valid location: {has_location}")
        print(f"   Buses with both (would be broadcasted): {both}")
        
        # Test the exact query used in broadcast_all_bus_locations
        print(f"\n🔍 Testing broadcast query...")
        broadcast_buses = await db.buses.find({
            "bus_status": {"$in": ["OPERATIONAL", "IDLE"]},
            "current_location": {"$exists": True, "$ne": None}
        }).to_list(length=None)
        
        print(f"   Buses matching broadcast query: {len(broadcast_buses)}")
        
        for bus in broadcast_buses:
            location = bus.get('current_location')
            if location and location.get('latitude') and location.get('longitude'):
                print(f"   ✅ {bus['license_plate']} would be broadcasted")
            else:
                print(f"   ❌ {bus['license_plate']} has invalid location data")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_buses())
