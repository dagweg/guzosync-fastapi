#!/usr/bin/env python3
"""
MongoDB UUID Migration Script

This script helps migrate your MongoDB collections to use consistent UUID storage.
It will:
1. Ensure all documents have proper UUID fields
2. Standardize UUID storage format (as strings)
3. Add missing 'id' fields where '_id' exists but 'id' doesn't
4. Convert ObjectId _id fields to UUID strings

Run this script once to fix your existing data.
"""

import asyncio
import os
import sys
from typing import Dict, Any
from uuid import uuid4, UUID
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Collections that contain models with UUID fields
COLLECTIONS_TO_MIGRATE = [
    'users',
    'buses', 
    'bus_stops',
    'routes',
    'trips',
    'payments',
    'tickets',
    'feedback',
    'incidents',
    'notifications',
    'conversations',
    'messages',
    'attendance',
    'schedules',
    'instructions',
    'route_change_requests'
]

def convert_objectid_to_uuid(oid: ObjectId) -> str:
    """Convert ObjectId to a deterministic UUID string."""
    # Use the ObjectId hex string and pad it to create a UUID
    hex_str = str(oid) + '0' * 8  # Pad to 32 characters
    try:
        return str(UUID(hex_str))
    except ValueError:
        # If conversion fails, generate a new UUID
        return str(uuid4())

def should_migrate_document(doc: Dict[str, Any]) -> bool:
    """Check if a document needs migration."""
    # Check if document has _id but no id field
    if '_id' in doc and 'id' not in doc:
        return True
    
    # Check if id field exists but is not a valid UUID string
    if 'id' in doc:
        try:
            UUID(str(doc['id']))
            return False  # Already a valid UUID
        except (ValueError, TypeError):
            return True  # Needs conversion
    
    return False

async def migrate_collection(db, collection_name: str) -> Dict[str, int]:
    """Migrate a single collection."""
    print(f"Migrating collection: {collection_name}")
    
    collection = db[collection_name]
    stats = {
        'total_docs': 0,
        'migrated_docs': 0,
        'errors': 0
    }
    
    try:
        # Get all documents
        cursor = collection.find({})
        async for doc in cursor:
            stats['total_docs'] += 1
            
            if should_migrate_document(doc):
                try:
                    # Create update operations
                    update_ops = {}
                    
                    # If no 'id' field exists, create one from '_id'
                    if 'id' not in doc and '_id' in doc:
                        if isinstance(doc['_id'], ObjectId):
                            # Convert ObjectId to UUID
                            new_uuid = convert_objectid_to_uuid(doc['_id'])
                            update_ops['id'] = new_uuid
                        elif isinstance(doc['_id'], str):
                            try:
                                # Try to parse as UUID
                                uuid_obj = UUID(doc['_id'])
                                update_ops['id'] = str(uuid_obj)
                            except ValueError:
                                # Generate new UUID if not valid
                                update_ops['id'] = str(uuid4())
                        else:
                            # Unknown _id type, generate new UUID
                            update_ops['id'] = str(uuid4())
                    
                    # Ensure 'id' field is a valid UUID string
                    elif 'id' in doc:
                        try:
                            # Validate and standardize UUID
                            uuid_obj = UUID(str(doc['id']))
                            update_ops['id'] = str(uuid_obj)
                        except (ValueError, TypeError):
                            # Generate new UUID if invalid
                            update_ops['id'] = str(uuid4())
                    
                    # Check for other UUID fields and standardize them
                    uuid_fields = [
                        'customer_id', 'payment_id', 'user_id', 'driver_id', 
                        'bus_id', 'route_id', 'trip_id', 'origin_stop_id',
                        'destination_stop_id', 'assigned_route_id', 'assigned_driver_id',
                        'reported_by_user_id', 'related_bus_id', 'related_route_id',
                        'current_route_id', 'requested_route_id', 'sender_id',
                        'conversation_id', 'target_driver_id', 'created_by',
                        'updated_by', 'submitted_by_user_id', 'related_trip_id',
                        'used_trip_id'
                    ]
                    
                    for field in uuid_fields:
                        if field in doc and doc[field] is not None:
                            try:
                                if isinstance(doc[field], str):
                                    # Validate UUID string
                                    uuid_obj = UUID(doc[field])
                                    update_ops[field] = str(uuid_obj)
                                elif isinstance(doc[field], UUID):
                                    # Convert UUID object to string
                                    update_ops[field] = str(doc[field])
                            except (ValueError, TypeError):
                                # Invalid UUID, could log this or handle differently
                                pass
                    
                    # Handle list fields that might contain UUIDs
                    list_uuid_fields = ['stop_ids', 'participants']
                    for field in list_uuid_fields:
                        if field in doc and isinstance(doc[field], list):
                            standardized_list = []
                            needs_update = False
                            
                            for item in doc[field]:
                                try:
                                    if isinstance(item, str):
                                        uuid_obj = UUID(item)
                                        standardized_list.append(str(uuid_obj))
                                    elif isinstance(item, UUID):
                                        standardized_list.append(str(item))
                                        needs_update = True
                                    else:
                                        standardized_list.append(item)
                                except (ValueError, TypeError):
                                    standardized_list.append(item)
                            
                            if needs_update or standardized_list != doc[field]:
                                update_ops[field] = standardized_list
                    
                    # Apply updates if any
                    if update_ops:
                        await collection.update_one(
                            {'_id': doc['_id']},
                            {'$set': update_ops}
                        )
                        stats['migrated_docs'] += 1
                        
                        if stats['migrated_docs'] % 100 == 0:
                            print(f"  Migrated {stats['migrated_docs']} documents...")
                
                except Exception as e:
                    print(f"  Error migrating document {doc.get('_id', 'unknown')}: {e}")
                    stats['errors'] += 1
    
    except Exception as e:
        print(f"Error accessing collection {collection_name}: {e}")
        stats['errors'] += 1
    
    return stats

async def main():
    """Main migration function."""
    print("Starting MongoDB UUID Migration...")
    
    # Get MongoDB connection details
    mongodb_url = os.getenv("MONGODB_URL")
    database_name = os.getenv("DATABASE_NAME")
    
    if not mongodb_url or not database_name:
        print("Error: MONGODB_URL and DATABASE_NAME environment variables must be set")
        sys.exit(1)
    
    # Connect to MongoDB
    try:
        client = AsyncIOMotorClient(mongodb_url)
        db = client[database_name]
        
        # Test connection
        await db.command('ping')
        print(f"Connected to MongoDB: {database_name}")
        
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)
    
    # Migrate each collection
    total_stats = {
        'total_docs': 0,
        'migrated_docs': 0,
        'errors': 0
    }
    
    for collection_name in COLLECTIONS_TO_MIGRATE:
        print(f"\nProcessing collection: {collection_name}")
        try:
            stats = await migrate_collection(db, collection_name)
            print(f"  Total documents: {stats['total_docs']}")
            print(f"  Migrated documents: {stats['migrated_docs']}")
            print(f"  Errors: {stats['errors']}")
            
            # Update totals
            for key in total_stats:
                total_stats[key] += stats[key]
                
        except Exception as e:
            print(f"  Error processing collection {collection_name}: {e}")
            total_stats['errors'] += 1
    
    # Print final summary
    print(f"\n{'='*50}")
    print("Migration Summary:")
    print(f"Total documents processed: {total_stats['total_docs']}")
    print(f"Total documents migrated: {total_stats['migrated_docs']}")
    print(f"Total errors: {total_stats['errors']}")
    print(f"{'='*50}")
    
    # Close connection
    client.close()
    print("Migration completed!")

if __name__ == "__main__":
    # Run the migration
    asyncio.run(main())
