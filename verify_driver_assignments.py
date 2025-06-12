#!/usr/bin/env python3
"""
Verification script to check bus driver assignments in the database.
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

async def verify_assignments():
    """Verify bus driver assignments in the database."""
    print("🔍 Verifying bus driver assignments...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Get assignment statistics
        total_buses = await db.buses.count_documents({})
        assigned_buses = await db.buses.count_documents({'assigned_driver_id': {'$ne': None}})
        unassigned_buses = total_buses - assigned_buses
        
        print(f"\n📊 Bus Assignment Statistics:")
        print(f"   🚌 Total buses: {total_buses}")
        print(f"   ✅ Buses with assigned drivers: {assigned_buses}")
        print(f"   ⚪ Buses without drivers: {unassigned_buses}")
        print(f"   📈 Assignment percentage: {(assigned_buses/total_buses*100):.1f}%")
        
        # Get detailed assignments
        buses_with_drivers = await db.buses.find(
            {'assigned_driver_id': {'$ne': None}},
            {'license_plate': 1, 'assigned_driver_id': 1}
        ).to_list(length=None)
        
        print(f"\n🚌 Assigned Buses:")
        for bus in buses_with_drivers:
            # Get driver info
            driver = await db.users.find_one(
                {'id': bus['assigned_driver_id']},
                {'first_name': 1, 'last_name': 1, 'email': 1}
            )
            if driver:
                driver_name = f"{driver['first_name']} {driver['last_name']}"
                print(f"   {bus['license_plate']} → {driver_name} ({driver['email']})")
            else:
                print(f"   {bus['license_plate']} → Driver not found (ID: {bus['assigned_driver_id']})")
        
        # Show some unassigned buses
        unassigned_sample = await db.buses.find(
            {'assigned_driver_id': None},
            {'license_plate': 1}
        ).limit(5).to_list(length=5)
        
        if unassigned_sample:
            print(f"\n⚪ Sample Unassigned Buses:")
            for bus in unassigned_sample:
                print(f"   {bus['license_plate']} (no driver)")
            if unassigned_buses > 5:
                print(f"   ... and {unassigned_buses - 5} more")
        
        # Check for duplicate assignments
        pipeline = [
            {'$match': {'assigned_driver_id': {'$ne': None}}},
            {'$group': {'_id': '$assigned_driver_id', 'count': {'$sum': 1}, 'buses': {'$push': '$license_plate'}}},
            {'$match': {'count': {'$gt': 1}}}
        ]
        
        duplicates = await db.buses.aggregate(pipeline).to_list(length=None)
        
        if duplicates:
            print(f"\n⚠️ Duplicate Driver Assignments Found:")
            for dup in duplicates:
                print(f"   Driver {dup['_id']} assigned to {dup['count']} buses: {', '.join(dup['buses'])}")
        else:
            print(f"\n✅ No duplicate driver assignments found")
        
        print(f"\n✨ Verification complete!")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(verify_assignments())
