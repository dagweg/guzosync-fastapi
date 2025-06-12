#!/usr/bin/env python3
"""
Check which buses are ready for broadcasting.
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

async def check_broadcast_ready():
    """Check which buses are ready for broadcasting."""
    print("🔍 Checking buses ready for broadcasting...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Get all buses and check manually
        buses = await db.buses.find({}).to_list(length=None)
        
        operational_with_location = 0
        idle_with_location = 0
        
        print(f"\n📊 Checking {len(buses)} buses...")
        
        for bus in buses:
            license_plate = bus.get('license_plate', 'Unknown')
            status = bus.get('bus_status')
            location = bus.get('current_location')
            
            has_valid_location = (location is not None and 
                                isinstance(location, dict) and 
                                'latitude' in location and 
                                'longitude' in location and
                                location['latitude'] is not None and
                                location['longitude'] is not None)
            
            if status == 'OPERATIONAL' and has_valid_location:
                operational_with_location += 1
                lat = location['latitude']
                lng = location['longitude']
                print(f"   ✅ OPERATIONAL: {license_plate} at ({lat}, {lng})")
            elif status == 'IDLE' and has_valid_location:
                idle_with_location += 1
                lat = location['latitude']
                lng = location['longitude']
                print(f"   ✅ IDLE: {license_plate} at ({lat}, {lng})")
            elif status in ['OPERATIONAL', 'IDLE']:
                print(f"   ❌ {status}: {license_plate} - invalid/missing location")
        
        total_broadcastable = operational_with_location + idle_with_location
        
        print(f"\n📈 Summary:")
        print(f"   🚌 Total buses that should be broadcasted: {total_broadcastable}")
        print(f"   🟢 OPERATIONAL with location: {operational_with_location}")
        print(f"   🟡 IDLE with location: {idle_with_location}")
        
        if total_broadcastable > 0:
            print(f"\n✅ {total_broadcastable} buses are ready for broadcasting!")
        else:
            print(f"\n⚠️ No buses are ready for broadcasting.")
            print("   This could be because:")
            print("   1. No buses have OPERATIONAL or IDLE status")
            print("   2. Buses don't have valid location data")
            
            # Show status distribution
            status_counts = {}
            for bus in buses:
                status = bus.get('bus_status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"\n📊 Bus status distribution:")
            for status, count in status_counts.items():
                print(f"   {status}: {count} buses")
        
    except Exception as e:
        print(f"❌ Error during check: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_broadcast_ready())
