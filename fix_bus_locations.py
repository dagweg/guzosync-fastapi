#!/usr/bin/env python3
"""
Fix script to add locations to buses that don't have them.
"""

import asyncio
import random
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "guzosync")

def random_location():
    """Generate a random location within Addis Ababa bounds."""
    # Addis Ababa approximate bounds
    lat_min, lat_max = 8.8, 9.2
    lng_min, lng_max = 38.6, 39.0
    
    return {
        "latitude": round(random.uniform(lat_min, lat_max), 6),
        "longitude": round(random.uniform(lng_min, lng_max), 6)
    }

async def fix_bus_locations():
    """Add locations to buses that don't have them."""
    print("🔧 Fixing bus locations for broadcasting...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Find buses without locations
        buses_without_location = await db.buses.find({
            "current_location": None
        }).to_list(length=None)
        
        print(f"📊 Found {len(buses_without_location)} buses without locations")
        
        if not buses_without_location:
            print("✅ All buses already have locations!")
            return
        
        # Update buses with random locations
        updated_count = 0
        
        for bus in buses_without_location:
            # Generate random location and other movement data
            location = random_location()
            
            update_data = {
                "current_location": location,
                "last_location_update": datetime.now(timezone.utc),
                "heading": round(random.uniform(0, 359), 1),
                "speed": round(random.uniform(0, 60), 1),
                "location_accuracy": round(random.uniform(3, 15), 1),
                "updated_at": datetime.now(timezone.utc)
            }
            
            result = await db.buses.update_one(
                {"id": bus["id"]},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"   ✅ Added location to bus {bus['license_plate']}: {location['latitude']}, {location['longitude']}")
        
        print(f"✅ Updated {updated_count} buses with locations")
        
        # Verify the fix
        print(f"\n🔍 Verifying fix...")
        
        # Check how many buses would now be broadcasted
        operational_idle_with_location = await db.buses.count_documents({
            "bus_status": {"$in": ["OPERATIONAL", "IDLE"]},
            "current_location": {"$exists": True, "$ne": None}
        })
        
        total_with_location = await db.buses.count_documents({
            "current_location": {"$exists": True, "$ne": None}
        })
        
        print(f"   📊 Total buses with locations: {total_with_location}")
        print(f"   📊 OPERATIONAL/IDLE buses with locations: {operational_idle_with_location}")
        print(f"   📡 Buses that would be broadcasted: {operational_idle_with_location}")
        
        if operational_idle_with_location > 0:
            print(f"✅ Fix successful! {operational_idle_with_location} buses will now be broadcasted")
        else:
            print(f"⚠️ No OPERATIONAL/IDLE buses found. You may need to update bus statuses.")
            
            # Show current status distribution
            pipeline = [
                {"$group": {"_id": "$bus_status", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            status_counts = await db.buses.aggregate(pipeline).to_list(length=None)
            
            print(f"\n📊 Current bus status distribution:")
            for status in status_counts:
                print(f"   {status['_id']}: {status['count']} buses")
        
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_bus_locations())
