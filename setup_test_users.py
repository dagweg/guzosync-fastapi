"""
Setup script to create test users for all roles in the GuzoSync system
Creates: CONTROL_ADMIN, CONTROL_STAFF, PASSENGER, BUS_DRIVER, QUEUE_REGULATOR
Directly inserts into MongoDB database for faster setup
"""

import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from dotenv import load_dotenv
from uuid import uuid4

# Load environment variables
load_dotenv()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "guzosync")

def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid4())

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def model_to_mongo_doc(user_dict: dict) -> dict:
    """Convert user dict to MongoDB document format"""
    # Ensure required fields
    if "id" not in user_dict:
        user_dict["id"] = generate_uuid()

    if "created_at" not in user_dict:
        user_dict["created_at"] = datetime.now(timezone.utc)

    if "updated_at" not in user_dict:
        user_dict["updated_at"] = datetime.now(timezone.utc)

    # Set _id to the same value as id for MongoDB compatibility
    user_dict["_id"] = user_dict["id"]

    return user_dict

async def create_admin_user(db):
    """Create a CONTROL_ADMIN user for testing"""
    print("Creating CONTROL_ADMIN user for testing...")

    email = "admin@example.com"
    password = "admin123"

    # Check if user already exists
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        print("⏭️ Admin user already exists")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        return password

    admin_user = {
        "id": generate_uuid(),
        "first_name": "Admin",
        "last_name": "User",
        "email": email,
        "password": hash_password(password),
        "role": "CONTROL_ADMIN",
        "phone_number": "+1234567890",
        "profile_image": None,

        # Profile Information
        "gender": "MALE",
        "nationality": "Ethiopian",
        "country": "Ethiopia",

        # Preferences and Settings
        "preferred_language": "en",
        "is_active": True,
        "is_verified": True,

        # Analytics
        "total_trips": 0,
        "total_distance_traveled": 0.0,
    }

    try:
        user_doc = model_to_mongo_doc(admin_user)
        result = await db.users.insert_one(user_doc)
        print("✓ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: CONTROL_ADMIN")
        print(f"   ID: {admin_user['id']}")
        return password

    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        return password

async def create_staff_user(db):
    """Create a regular CONTROL_STAFF user"""
    print("\nCreating CONTROL_STAFF user...")

    email = "staff@example.com"
    password = "staff123"

    # Check if user already exists
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        print("⏭️ Staff user already exists")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        return password

    staff_user = {
        "id": generate_uuid(),
        "first_name": "Staff",
        "last_name": "User",
        "email": email,
        "password": hash_password(password),
        "role": "CONTROL_STAFF",
        "phone_number": "+1234567891",
        "profile_image": None,

        # Profile Information
        "gender": "FEMALE",
        "nationality": "Ethiopian",
        "country": "Ethiopia",

        # Preferences and Settings
        "preferred_language": "en",
        "is_active": True,
        "is_verified": True,

        # Analytics
        "total_trips": 0,
        "total_distance_traveled": 0.0,
    }

    try:
        user_doc = model_to_mongo_doc(staff_user)
        result = await db.users.insert_one(user_doc)
        print("✓ Staff user created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: CONTROL_STAFF")
        print(f"   ID: {staff_user['id']}")
        return password

    except Exception as e:
        print(f"❌ Error creating staff user: {str(e)}")
        return password

async def create_passenger_user(db):
    """Create a PASSENGER user for testing"""
    print("\nCreating PASSENGER user...")

    email = "passenger@example.com"
    password = "passenger123"

    # Check if user already exists
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        print("⏭️ Passenger user already exists")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        return password

    passenger_user = {
        "id": generate_uuid(),
        "first_name": "John",
        "last_name": "Passenger",
        "email": email,
        "password": hash_password(password),
        "role": "PASSENGER",
        "phone_number": "+1234567892",
        "profile_image": None,

        # Profile Information
        "gender": "MALE",
        "nationality": "Ethiopian",
        "country": "Ethiopia",

        # Preferences and Settings
        "preferred_language": "en",
        "is_active": True,
        "is_verified": True,

        # Payment and Discounts
        "preferred_payment_method": "mobile",
        "monthly_pass_active": False,
        "student_discount_eligible": False,
        "senior_discount_eligible": False,
        "disability_discount_eligible": False,

        # Analytics
        "total_trips": 0,
        "total_distance_traveled": 0.0,
    }

    try:
        user_doc = model_to_mongo_doc(passenger_user)
        result = await db.users.insert_one(user_doc)
        print("✓ Passenger user created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: PASSENGER")
        print(f"   ID: {passenger_user['id']}")
        return password

    except Exception as e:
        print(f"❌ Error creating passenger user: {str(e)}")
        return password

async def create_bus_driver_user(db):
    """Create a BUS_DRIVER user"""
    print("\nCreating BUS_DRIVER user...")

    email = "driver@example.com"
    password = str(uuid4())  # Generate temporary password like the API does

    # Check if user already exists
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        print("⏭️ Bus driver user already exists")
        print(f"   Email: {email}")
        print("   Password: (check previous run output)")
        return "driver123"  # Return a placeholder for existing users

    driver_user = {
        "id": generate_uuid(),
        "first_name": "Mike",
        "last_name": "Driver",
        "email": email,
        "password": hash_password(password),
        "role": "BUS_DRIVER",
        "phone_number": "+1234567893",
        "profile_image": None,

        # Profile Information
        "gender": "MALE",
        "nationality": "Ethiopian",
        "country": "Ethiopia",

        # Preferences and Settings
        "preferred_language": "en",
        "is_active": True,
        "is_verified": True,

        # Analytics
        "total_trips": 0,
        "total_distance_traveled": 0.0,
    }

    try:
        user_doc = model_to_mongo_doc(driver_user)
        result = await db.users.insert_one(user_doc)
        print("✓ Bus driver user created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: BUS_DRIVER")
        print(f"   ID: {driver_user['id']}")
        return password

    except Exception as e:
        print(f"❌ Error creating bus driver user: {str(e)}")
        return password

async def create_queue_regulator_user(db):
    """Create a QUEUE_REGULATOR user"""
    print("\nCreating QUEUE_REGULATOR user...")

    email = "regulator@example.com"
    password = str(uuid4())  # Generate temporary password like the API does

    # Check if user already exists
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        print("⏭️ Queue regulator user already exists")
        print(f"   Email: {email}")
        print("   Password: (check previous run output)")
        return "regulator123"  # Return a placeholder for existing users

    regulator_user = {
        "id": generate_uuid(),
        "first_name": "Sarah",
        "last_name": "Regulator",
        "email": email,
        "password": hash_password(password),
        "role": "QUEUE_REGULATOR",
        "phone_number": "+1234567894",
        "profile_image": None,

        # Profile Information
        "gender": "FEMALE",
        "nationality": "Ethiopian",
        "country": "Ethiopia",

        # Preferences and Settings
        "preferred_language": "en",
        "is_active": True,
        "is_verified": True,

        # Analytics
        "total_trips": 0,
        "total_distance_traveled": 0.0,
    }

    try:
        user_doc = model_to_mongo_doc(regulator_user)
        result = await db.users.insert_one(user_doc)
        print("✓ Queue regulator user created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: QUEUE_REGULATOR")
        print(f"   ID: {regulator_user['id']}")
        return password

    except Exception as e:
        print(f"❌ Error creating queue regulator user: {str(e)}")
        return password

async def setup_all_users():
    """Setup all test users by directly inserting into database"""
    print("GuzoSync Complete User Setup for Testing")
    print("=" * 45)
    print("Connecting directly to MongoDB database...")
    print("🔑 All passwords will be printed to console for easy testing.")
    print()

    # Store passwords for summary
    passwords = {}

    # Connect to MongoDB
    try:
        client: AsyncIOMotorClient = AsyncIOMotorClient(MONGODB_URL, uuidRepresentation="unspecified")
        db = client[DATABASE_NAME]

        # Test connection
        await db.command('ping')
        print("✓ Successfully connected to MongoDB")
        print()

        # Create all user types and collect passwords
        passwords['admin'] = await create_admin_user(db)
        passwords['staff'] = await create_staff_user(db)
        passwords['passenger'] = await create_passenger_user(db)
        passwords['driver'] = await create_bus_driver_user(db)
        passwords['regulator'] = await create_queue_regulator_user(db)

        print("\n" + "=" * 45)
        print("🎉 All test users setup complete!")
        print("\nTest User Credentials Summary:")
        print("━" * 50)
        print("1. CONTROL_ADMIN:")
        print("   Email: admin@example.com")
        print(f"   Password: {passwords['admin']}")
        print("\n2. CONTROL_STAFF:")
        print("   Email: staff@example.com")
        print(f"   Password: {passwords['staff']}")
        print("\n3. PASSENGER:")
        print("   Email: passenger@example.com")
        print(f"   Password: {passwords['passenger']}")
        print("\n4. BUS_DRIVER:")
        print("   Email: driver@example.com")
        print(f"   Password: {passwords['driver']}")
        print("\n5. QUEUE_REGULATOR:")
        print("   Email: regulator@example.com")
        print(f"   Password: {passwords['regulator']}")
        print("━" * 50)
        print("\n🔑 All passwords are printed above for easy copy-paste!")
        print("You can now test RBAC and other features with these users!")

        # Close connection
        client.close()

    except Exception as e:
        print(f"❌ Error connecting to database: {str(e)}")
        print("Make sure MongoDB is running and connection details are correct.")

if __name__ == "__main__":
    asyncio.run(setup_all_users())
