#!/usr/bin/env python3
"""
Test MongoDB queries to find the issue with bus broadcasting.
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

async def test_mongo_queries():
    """Test different MongoDB queries to find the issue."""
    print("🔍 Testing MongoDB queries...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Get one bus to examine its structure
        bus = await db.buses.find_one()
        
        print(f"\n📋 Sample bus structure:")
        for key, value in bus.items():
            if key in ['bus_status', 'current_location', '_id', 'id', 'license_plate']:
                print(f"   {key}: {value} (type: {type(value)})")
        
        print(f"\n🔍 Testing different query approaches:")
        
        # Test 1: Simple status query
        try:
            count1 = await db.buses.count_documents({"bus_status": "OPERATIONAL"})
            print(f"   ✅ bus_status='OPERATIONAL': {count1} buses")
        except Exception as e:
            print(f"   ❌ bus_status query failed: {e}")
        
        # Test 2: Status with $in operator
        try:
            count2 = await db.buses.count_documents({"bus_status": {"$in": ["OPERATIONAL", "IDLE"]}})
            print(f"   ✅ bus_status in ['OPERATIONAL', 'IDLE']: {count2} buses")
        except Exception as e:
            print(f"   ❌ bus_status $in query failed: {e}")
        
        # Test 3: Location exists
        try:
            count3 = await db.buses.count_documents({"current_location": {"$exists": True}})
            print(f"   ✅ current_location exists: {count3} buses")
        except Exception as e:
            print(f"   ❌ current_location exists query failed: {e}")
        
        # Test 4: Location not null
        try:
            count4 = await db.buses.count_documents({"current_location": {"$ne": None}})
            print(f"   ✅ current_location not null: {count4} buses")
        except Exception as e:
            print(f"   ❌ current_location not null query failed: {e}")
        
        # Test 5: Combined query
        try:
            count5 = await db.buses.count_documents({
                "bus_status": {"$in": ["OPERATIONAL", "IDLE"]},
                "current_location": {"$exists": True, "$ne": None}
            })
            print(f"   ✅ Combined query: {count5} buses")
        except Exception as e:
            print(f"   ❌ Combined query failed: {e}")
        
        # Test 6: Alternative location check
        try:
            count6 = await db.buses.count_documents({"current_location.latitude": {"$exists": True}})
            print(f"   ✅ current_location.latitude exists: {count6} buses")
        except Exception as e:
            print(f"   ❌ current_location.latitude query failed: {e}")
        
        # Test 7: Get actual buses that match our criteria manually
        print(f"\n🔍 Manual verification:")
        all_buses = await db.buses.find({}).to_list(length=None)
        
        matching_buses = []
        for bus in all_buses:
            status = bus.get('bus_status')
            location = bus.get('current_location')
            
            if (status in ['OPERATIONAL', 'IDLE'] and 
                location is not None and 
                isinstance(location, dict) and
                'latitude' in location and 'longitude' in location):
                matching_buses.append(bus)
        
        print(f"   📊 Manual count of matching buses: {len(matching_buses)}")
        
        for bus in matching_buses:
            license_plate = bus.get('license_plate', 'Unknown')
            status = bus.get('bus_status')
            location = bus.get('current_location')
            print(f"      {license_plate}: {status} at ({location['latitude']}, {location['longitude']})")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_mongo_queries())
