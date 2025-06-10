#!/usr/bin/env python
"""
Database Seeding Startup Script

This script is designed to be run before starting the FastAPI server
to ensure the database is properly seeded with test data.

It checks if the database is empty and seeds it if necessary.
Can also force re-seeding with --force flag.

Usage:
    python seed_db_startup.py              # Seed only if database is empty
    python seed_db_startup.py --force      # Force re-seed even if data exists
    python seed_db_startup.py --minimal    # Create minimal seed data only
"""

import asyncio
import argparse
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Import the complete seeding functions
from init_db_complete import (
    clear_database, import_bus_stops_from_geojson, create_users, 
    create_buses, create_routes, create_schedules, create_trips,
    create_payments, create_tickets, create_feedback, create_incidents,
    create_notifications, create_notification_settings
)

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "guzosync")

async def check_database_empty(db) -> bool:
    """Check if the database is empty or has minimal data."""
    collections_to_check = ["users", "buses", "bus_stops", "routes"]
    
    for collection_name in collections_to_check:
        count = await db[collection_name].count_documents({})
        if count > 0:
            return False
    
    return True

async def seed_minimal_data(db):
    """Seed minimal essential data for basic functionality."""
    print("🌱 Seeding minimal essential data...")
    
    # Import bus stops from GeoJSON
    bus_stops = await import_bus_stops_from_geojson(db)
    
    # Create essential users (at least one of each role)
    users = await create_users(db, count=10)
    
    # Create a few buses
    buses = await create_buses(db, count=5)
    
    # Create basic routes
    routes = await create_routes(db, bus_stops, count=3)
    
    # Create basic schedules
    drivers = [user for user in users if user["role"] == "BUS_DRIVER"]
    schedules = await create_schedules(db, routes, buses, drivers, count=5)
    
    # Create notification settings for all users
    notification_settings = await create_notification_settings(db, users)
    
    print(f"✅ Minimal seeding completed:")
    print(f"   🚏 Bus Stops: {len(bus_stops)}")
    print(f"   👥 Users: {len(users)}")
    print(f"   🚌 Buses: {len(buses)}")
    print(f"   🛣️ Routes: {len(routes)}")
    print(f"   📅 Schedules: {len(schedules)}")
    print(f"   ⚙️ Notification Settings: {len(notification_settings)}")

async def seed_complete_data(db):
    """Seed complete test data for comprehensive testing."""
    print("🌱 Seeding complete test data...")
    
    # Import bus stops from GeoJSON
    bus_stops = await import_bus_stops_from_geojson(db)
    
    # Create users
    users = await create_users(db, count=25)
    
    # Create buses
    buses = await create_buses(db, count=15)
    
    # Create routes
    routes = await create_routes(db, bus_stops, count=10)
    
    # Create schedules
    drivers = [user for user in users if user["role"] == "BUS_DRIVER"]
    schedules = await create_schedules(db, routes, buses, drivers, count=20)
    
    # Create trips
    trips = await create_trips(db, buses, routes, drivers, schedules, count=30)
    
    # Create payments
    payments = await create_payments(db, users, count=25)
    
    # Create tickets
    tickets = await create_tickets(db, payments, routes, bus_stops, count=30)
    
    # Create feedback
    feedback = await create_feedback(db, users, trips, buses, count=20)
    
    # Create incidents
    incidents = await create_incidents(db, users, buses, routes, bus_stops, count=10)
    
    # Create notifications
    notifications = await create_notifications(db, users, count=30)
    
    # Create notification settings
    notification_settings = await create_notification_settings(db, users)
    
    total_records = (len(bus_stops) + len(users) + len(buses) + len(routes) + 
                    len(schedules) + len(trips) + len(payments) + len(tickets) + 
                    len(feedback) + len(incidents) + len(notifications) + 
                    len(notification_settings))
    
    print(f"✅ Complete seeding finished - {total_records} total records created")

async def main():
    """Main startup seeding function."""
    parser = argparse.ArgumentParser(description='Seed database before server startup')
    parser.add_argument('--force', action='store_true', help='Force re-seed even if data exists')
    parser.add_argument('--minimal', action='store_true', help='Create minimal seed data only')
    parser.add_argument('--skip-geojson', action='store_true', help='Skip GeoJSON bus stop import')
    args = parser.parse_args()
    
    print("🚀 Database Startup Seeding")
    print(f"📡 MongoDB URL: {mongodb_url}")
    print(f"🗄️ Database: {database_name}")
    
    # Connect to MongoDB
    client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Check if database needs seeding
        is_empty = await check_database_empty(db)
        
        if not is_empty and not args.force:
            print("ℹ️ Database already contains data. Use --force to re-seed.")
            print("✨ Database is ready for server startup!")
            return
        
        if args.force:
            print("🗑️ Force flag detected - clearing existing data...")
            await clear_database(db)
        
        # Seed based on arguments
        if  args.minimal:
            await seed_minimal_data(db)
        else:
            await seed_complete_data(db)
        
        print("\n✨ Database seeding completed successfully!")
        print("🚀 Your GuzoSync database is ready for server startup!")
        
    except Exception as e:
        print(f"❌ Seeding failed: {str(e)}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())
