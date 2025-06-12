#!/usr/bin/env python3
"""
Database initialization script for payment methods and configurations
Run this script to set up initial payment method configurations in the database
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Payment method configurations
DEFAULT_PAYMENT_METHODS = [
    {
        "method": "telebirr",
        "is_active": True,
        "display_name": "Telebirr",
        "description": "Pay using Telebirr mobile wallet",
        "icon_url": "https://example.com/icons/telebirr.png",
        "processing_fee": 0.0,
        "processing_fee_percentage": 2.0,
        "min_amount": 10.0,
        "max_amount": 10000.0,
        "configuration": {
            "ussd_code": "*127#",
            "supports_otp": True
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "method": "mpesa",
        "is_active": True,
        "display_name": "M-Pesa",
        "description": "Pay using M-Pesa mobile money",
        "icon_url": "https://example.com/icons/mpesa.png",
        "processing_fee": 0.0,
        "processing_fee_percentage": 2.5,
        "min_amount": 5.0,
        "max_amount": 5000.0,
        "configuration": {
            "ussd_code": "*151#",
            "supports_otp": True
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "method": "cbebirr",
        "is_active": True,
        "display_name": "CBE Birr",
        "description": "Pay using Commercial Bank of Ethiopia Birr",
        "icon_url": "https://example.com/icons/cbebirr.png",
        "processing_fee": 0.0,
        "processing_fee_percentage": 1.5,
        "min_amount": 10.0,
        "max_amount": 50000.0,
        "configuration": {
            "ussd_code": "*847#",
            "supports_otp": True
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "method": "ebirr",
        "is_active": True,
        "display_name": "eBirr",
        "description": "Pay using eBirr digital wallet",
        "icon_url": "https://example.com/icons/ebirr.png",
        "processing_fee": 0.0,
        "processing_fee_percentage": 2.0,
        "min_amount": 5.0,
        "max_amount": 25000.0,
        "configuration": {
            "supports_otp": True
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "method": "enat_bank",
        "is_active": True,
        "display_name": "Enat Bank",
        "description": "Pay using Enat Bank portal",
        "icon_url": "https://example.com/icons/enat.png",
        "processing_fee": 5.0,
        "processing_fee_percentage": 0.0,
        "min_amount": 50.0,
        "max_amount": 100000.0,
        "configuration": {
            "portal_view": True,
            "requires_redirect": True
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]


async def init_payment_methods():
    """Initialize payment method configurations in the database"""
    try:
        # Connect to MongoDB
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME")
        
        if not mongodb_url or not database_name:
            print("❌ MongoDB configuration not found in environment variables")
            return False
        
        mongodb_url = str(mongodb_url)
        database_name = str(database_name)
        
        print("🔌 Connecting to MongoDB...")
        from motor.motor_asyncio import AsyncIOMotorClient
        client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_url)
        db = client[database_name]
        
        # Test connection
        await db.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Get payment methods collection
        payment_methods_collection = db.payment_method_configs
        
        # Check if payment methods already exist
        existing_count = await payment_methods_collection.count_documents({})
        if existing_count > 0:
            print(f"⚠️  Found {existing_count} existing payment methods. Skipping initialization.")
            print("   Use --force flag to overwrite existing data")
            return True
        
        # Insert payment methods
        print("💳 Inserting default payment methods...")
        result = await payment_methods_collection.insert_many(DEFAULT_PAYMENT_METHODS)
        
        print(f"✅ Successfully inserted {len(result.inserted_ids)} payment methods:")
        for method in DEFAULT_PAYMENT_METHODS:
            status = "🟢 Active" if method["is_active"] else "🔴 Inactive"
            print(f"   - {method['display_name']} ({method['method']}) {status}")
        
        # Create indexes for better performance
        print("🔍 Creating database indexes...")
        await payment_methods_collection.create_index("method", unique=True)
        await payment_methods_collection.create_index("is_active")
        
        # Create indexes for payments and tickets collections
        payments_collection = db.payments
        tickets_collection = db.tickets
        
        await payments_collection.create_index("tx_ref", unique=True)
        await payments_collection.create_index("customer_id")
        await payments_collection.create_index("status")
        await payments_collection.create_index("created_at")
        
        await tickets_collection.create_index("ticket_number", unique=True)
        await tickets_collection.create_index("customer_id")
        await tickets_collection.create_index("payment_id")
        await tickets_collection.create_index("status")
        await tickets_collection.create_index("valid_until")
        
        print("✅ Database indexes created successfully")
        
        # Close connection
        client.close()
        print("🎉 Payment system initialization completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during initialization: {str(e)}")
        return False


async def force_init_payment_methods():
    """Force initialize payment methods (overwrites existing data)"""
    try:
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME")
        
        if not mongodb_url or not database_name:
            print("❌ MongoDB configuration not found in environment variables")
            return False
        
        mongodb_url = str(mongodb_url)
        database_name = str(database_name)
        
        client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_url)
        db = client[database_name]
        
        payment_methods_collection = db.payment_method_configs
        
        # Delete existing payment methods
        delete_result = await payment_methods_collection.delete_many({})
        print(f"🗑️  Deleted {delete_result.deleted_count} existing payment methods")
        
        # Insert new payment methods
        result = await payment_methods_collection.insert_many(DEFAULT_PAYMENT_METHODS)
        print(f"✅ Successfully inserted {len(result.inserted_ids)} payment methods")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during force initialization: {str(e)}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🔄 Force initializing payment methods...")
        success = asyncio.run(force_init_payment_methods())
    else:
        print("🚀 Initializing GuzoSync payment system...")
        success = asyncio.run(init_payment_methods())
    
    if success:
        print("\n💡 Next steps:")
        print("   1. Set up your Chapa API credentials in .env file")
        print("   2. Start the FastAPI server: uvicorn main:app --reload")
        print("   3. Test payment endpoints using the API documentation")
        sys.exit(0)
    else:
        print("\n❌ Initialization failed. Please check the error messages above.")
        sys.exit(1)
