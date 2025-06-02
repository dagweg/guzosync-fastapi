#!/usr/bin/env python3
"""
UUID Testing Utility

This script helps test UUID functionality with MongoDB.
It creates test documents and verifies they can be read back correctly.
"""

import asyncio
import os
import sys
from uuid import uuid4
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.user import User, UserRole
from core.mongo_utils import transform_mongo_doc, model_to_mongo_doc

load_dotenv()

async def test_uuid_operations():
    """Test UUID operations with MongoDB."""
    print("Testing UUID operations...")
    
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL")
    database_name = os.getenv("DATABASE_NAME")
    
    if not mongodb_url or not database_name:
        print("Error: MONGODB_URL and DATABASE_NAME must be set")
        return False
    
    try:
        client = AsyncIOMotorClient(mongodb_url)
        db = client[database_name]
        collection = db.test_users
        
        # Test connection
        await db.command('ping')
        print("✓ Connected to MongoDB")
        
        # Create a test user
        test_user = User(
            first_name="Test",
            last_name="User", 
            email="test@example.com",
            password="testpass",
            role=UserRole.PASSENGER,
            phone_number="+1234567890"
        )
        
        print(f"✓ Created test user with ID: {test_user.id}")
        
        # Convert to MongoDB document
        user_doc = model_to_mongo_doc(test_user)
        print(f"✓ Converted to MongoDB doc: {user_doc.get('_id', 'NO_ID')}")
        
        # Insert into database
        result = await collection.insert_one(user_doc)
        print(f"✓ Inserted document with _id: {result.inserted_id}")
        
        # Try to find by different methods
        print("\nTesting retrieval methods:")
        
        # Method 1: Find by id field
        found1 = await collection.find_one({"id": str(test_user.id)})
        print(f"Find by id field: {'✓ Found' if found1 else '✗ Not found'}")
        
        # Method 2: Find by _id field
        found2 = await collection.find_one({"_id": str(test_user.id)})
        print(f"Find by _id field: {'✓ Found' if found2 else '✗ Not found'}")
        
        # Method 3: Find by inserted_id
        found3 = await collection.find_one({"_id": result.inserted_id})
        print(f"Find by inserted_id: {'✓ Found' if found3 else '✗ Not found'}")
        
        # Test document transformation
        if found1 or found2 or found3:
            test_doc = found1 or found2 or found3
            try:
                transformed_user = transform_mongo_doc(test_doc, User)
                print(f"✓ Successfully transformed document back to User model")
                print(f"  Transformed user ID: {transformed_user.id}")
                print(f"  Email: {transformed_user.email}")
            except Exception as e:
                print(f"✗ Error transforming document: {e}")
        
        # Clean up
        await collection.delete_many({"email": "test@example.com"})
        print("✓ Cleaned up test data")
        
        client.close()
        print("✓ Test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_uuid_operations())
    sys.exit(0 if success else 1)
