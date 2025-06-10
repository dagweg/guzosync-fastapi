#!/usr/bin/env python3
"""
Import bus stops and routes from CSV files
"""
import asyncio
import csv
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from models.transport import BusStop, Route, Location
from core.mongo_utils import model_to_mongo_doc

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

async def import_bus_stops():
    """Import bus stops from CSV file"""
    print("🚏 Importing bus stops from data/stops.txt...")
    
    client: AsyncIOMotorClient = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    try:
        bus_stops = []
        with open('data/stops.txt', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Create BusStop model
                    bus_stop = BusStop(
                        name=row['stop_name'],
                        location=Location(
                            latitude=float(row['stop_lat']),
                            longitude=float(row['stop_lon'])
                        ),
                        is_active=True
                    )
                    
                    # Convert to MongoDB document
                    bus_stop_doc = model_to_mongo_doc(bus_stop)
                    bus_stops.append(bus_stop_doc)
                    
                except (ValueError, KeyError) as e:
                    print(f"⚠️ Skipping invalid bus stop row: {e}")
                    continue
        
        if bus_stops:
            # Insert all bus stops
            result = await db.bus_stops.insert_many(bus_stops)
            print(f"✅ Imported {len(result.inserted_ids)} bus stops")
        else:
            print("❌ No valid bus stops found")
            
    except FileNotFoundError:
        print("❌ data/stops.txt not found")
    except Exception as e:
        print(f"❌ Error importing bus stops: {e}")
    finally:
        client.close()

async def import_routes():
    """Import routes from CSV file"""
    print("🛣️ Importing routes from data/routes.txt...")
    
    client: AsyncIOMotorClient = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    try:
        routes = []
        with open('data/routes.txt', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Create Route model
                    route = Route(
                        name=row['route_long_name'],
                        description=row.get('route_desc', ''),
                        stop_ids=[],  # Will be populated later when stops are linked
                        is_active=True
                    )
                    
                    # Convert to MongoDB document
                    route_doc = model_to_mongo_doc(route)
                    routes.append(route_doc)
                    
                except (ValueError, KeyError) as e:
                    print(f"⚠️ Skipping invalid route row: {e}")
                    continue
        
        if routes:
            # Insert all routes
            result = await db.routes.insert_many(routes)
            print(f"✅ Imported {len(result.inserted_ids)} routes")
        else:
            print("❌ No valid routes found")
            
    except FileNotFoundError:
        print("❌ data/routes.txt not found")
    except Exception as e:
        print(f"❌ Error importing routes: {e}")
    finally:
        client.close()

async def main():
    print("📊 CSV Data Import Script")
    print("=" * 50)
    
    # Import bus stops
    await import_bus_stops()
    
    # Import routes
    await import_routes()
    
    print("\n✅ CSV import completed!")
    print("🧪 Run test_api_endpoints.py to verify the data")

if __name__ == "__main__":
    asyncio.run(main())
