#!/usr/bin/env python3
"""
Debug script to test ETA calculation functionality
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from core.realtime.bus_tracking import bus_tracking_service
from core.logger import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

# MongoDB configuration
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "guzosync")

class MockAppState:
    def __init__(self, mongodb):
        self.mongodb = mongodb

async def test_eta_calculation():
    """Test ETA calculation with real database data"""
    print("🧪 Testing ETA Calculation")
    print(f"📡 MongoDB URL: {mongodb_url}")
    print(f"🗄️ Database: {database_name}")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    app_state = MockAppState(db)
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Get a bus with current location
        bus = await db.buses.find_one({"current_location": {"$exists": True}})
        if not bus:
            print("❌ No buses with current location found")
            return
        
        print(f"🚌 Found bus: {bus['id']} ({bus.get('license_plate')})")
        print(f"📍 Bus location: {bus.get('current_location')}")
        print(f"🛣️ Assigned route: {bus.get('assigned_route_id')}")
        
        # Get an active bus stop
        bus_stop = await db.bus_stops.find_one({"is_active": True})
        if not bus_stop:
            print("❌ No active bus stops found")
            return
        
        print(f"🚏 Found bus stop: {bus_stop['id']} ({bus_stop.get('name')})")
        print(f"📍 Stop location: {bus_stop.get('location')}")
        
        # Test ETA calculation
        print("\n🧮 Testing ETA calculation...")
        eta_result = await bus_tracking_service.calculate_eta_for_bus(
            bus['id'], 
            bus_stop['id'], 
            app_state
        )
        
        if eta_result:
            print("✅ ETA calculation successful!")
            print(f"📊 Result: {eta_result}")
        else:
            print("❌ ETA calculation failed")
            
        # Test with non-existent bus
        print("\n🧪 Testing with non-existent bus...")
        eta_result = await bus_tracking_service.calculate_eta_for_bus(
            "non-existent-bus", 
            bus_stop['id'], 
            app_state
        )
        
        if eta_result:
            print("❌ Unexpected success with non-existent bus")
        else:
            print("✅ Correctly failed with non-existent bus")
            
        # Test with non-existent stop
        print("\n🧪 Testing with non-existent stop...")
        eta_result = await bus_tracking_service.calculate_eta_for_bus(
            bus['id'], 
            "non-existent-stop", 
            app_state
        )
        
        if eta_result:
            print("❌ Unexpected success with non-existent stop")
        else:
            print("✅ Correctly failed with non-existent stop")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        raise
    finally:
        client.close()

async def list_available_data():
    """List available buses and bus stops for testing"""
    print("📋 Listing Available Test Data")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # List buses with locations
        buses = await db.buses.find({
            "current_location": {"$exists": True}
        }).limit(5).to_list(length=5)
        
        print(f"\n🚌 Buses with locations ({len(buses)} found):")
        for bus in buses:
            print(f"  - ID: {bus['id']}")
            print(f"    License: {bus.get('license_plate')}")
            print(f"    Location: {bus.get('current_location')}")
            print(f"    Route: {bus.get('assigned_route_id')}")
            print()
        
        # List active bus stops
        bus_stops = await db.bus_stops.find({
            "is_active": True
        }).limit(5).to_list(length=5)
        
        print(f"🚏 Active bus stops ({len(bus_stops)} found):")
        for stop in bus_stops:
            print(f"  - ID: {stop['id']}")
            print(f"    Name: {stop.get('name')}")
            print(f"    Location: {stop.get('location')}")
            print()
            
    except Exception as e:
        print(f"❌ Failed to list data: {str(e)}")
        raise
    finally:
        client.close()

async def main():
    """Main test function"""
    print("🚀 ETA Calculation Debug Tool")
    print("=" * 50)
    
    await list_available_data()
    print("=" * 50)
    await test_eta_calculation()
    
    print("\n✨ Debug test completed!")

if __name__ == "__main__":
    asyncio.run(main())
