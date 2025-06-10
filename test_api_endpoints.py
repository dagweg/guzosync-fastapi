#!/usr/bin/env python3
"""
Quick test script to check API endpoints and database content
"""
import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.config import settings
    MONGODB_URL = settings.MONGODB_URL
    DATABASE_NAME = settings.DATABASE_NAME
except ImportError:
    # Fallback to environment variables
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "guzosync")

async def test_database_content():
    """Test if database has the required data"""
    print("🔍 Testing database content...")
    
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DATABASE_NAME]
        
        # Check collections
        collections = {
            "buses": db.buses,
            "bus_stops": db.bus_stops,
            "routes": db.routes,
            "users": db.users
        }
        
        for name, collection in collections.items():
            count = await collection.count_documents({})
            print(f"  📊 {name}: {count} documents")
            
            if count > 0:
                # Get a sample document
                sample = await collection.find_one({})
                if sample:
                    print(f"    📄 Sample {name[:-1]} ID: {sample.get('id', sample.get('_id', 'NO_ID'))}")
        
        # Test specific queries that the API uses
        print("\n🔍 Testing API-style queries...")
        
        # Test bus query
        buses = await db.buses.find({}).to_list(length=5)
        print(f"  🚌 Found {len(buses)} buses (showing first 5)")
        
        # Test bus stops query  
        stops = await db.bus_stops.find({}).to_list(length=5)
        print(f"  🚏 Found {len(stops)} bus stops (showing first 5)")
        
        # Test routes query
        routes = await db.routes.find({}).to_list(length=5)
        print(f"  🛣️  Found {len(routes)} routes (showing first 5)")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

async def main():
    print("🧪 API Endpoint Test Script")
    print("=" * 50)
    
    # Test database
    db_ok = await test_database_content()
    
    if not db_ok:
        print("\n❌ Database test failed. Try running:")
        print("   python seed_db_startup.py --minimal")
        sys.exit(1)
    
    print("\n✅ Database test completed!")
    print("\n📋 Next steps:")
    print("1. Make sure your FastAPI server is running: uvicorn main:app --reload")
    print("2. Test the debug endpoints:")
    print("   - GET http://localhost:8000/api/buses/debug/count")
    print("   - GET http://localhost:8000/api/routes/debug/count")
    print("3. Check the frontend map at: http://localhost:3003/mapbox-demo")

if __name__ == "__main__":
    asyncio.run(main())
