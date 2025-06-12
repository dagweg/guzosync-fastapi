#!/usr/bin/env python3
"""
Simple script to assign a route to a bus for testing purposes
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def assign_route_to_bus():
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "guzosync")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Get first bus and first route
        bus = await db.buses.find_one({})
        route = await db.routes.find_one({})
        
        if not bus or not route:
            print("❌ No bus or route found")
            return
        
        print(f"📍 Assigning route '{route['name']}' to bus '{bus.get('license_plate', bus['id'])}'")
        
        # Update bus with route assignment
        result = await db.buses.update_one(
            {"_id": bus["_id"]},
            {"$set": {"assigned_route_id": route["id"]}}
        )
        
        if result.modified_count > 0:
            print("✅ Bus route assignment successful!")
            print(f"   Bus: {bus.get('license_plate', bus['id'])}")
            print(f"   Route: {route['name']} ({route['id']})")
        else:
            print("❌ Failed to assign route to bus")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(assign_route_to_bus())
