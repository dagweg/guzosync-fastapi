#!/usr/bin/env python
"""
Complete GuzoSync Database Seeding Script

This script provides comprehensive database initialization with:
1. Real bus stops and routes from CSV files (data/stops.txt & data/routes.txt)
2. Complete mock data for all collections
3. Proper data relationships and validation
4. Hybrid approach for performance and consistency

Data Sources:
- 1,340+ bus stops from data/stops.txt
- 190+ routes from data/routes.txt

Run this script with: python init_db_complete.py
"""

import asyncio
import json
import random
import os
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4, UUID

from dotenv import load_dotenv
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
database_name = os.getenv("DATABASE_NAME", "guzosync")

# Initialize Faker and password context
fake = Faker()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Constants
USER_ROLES = ["PASSENGER", "BUS_DRIVER", "QUEUE_REGULATOR", "CONTROL_STAFF", "CONTROL_ADMIN"]
BUS_TYPES = ["STANDARD", "ARTICULATED", "MINIBUS"]
BUS_STATUS = ["OPERATIONAL", "MAINTENANCE", "BREAKDOWN", "IDLE"]
PAYMENT_METHODS = ["telebirr", "mpesa", "cbebirr", "ebirr", "enat_bank"]
TICKET_TYPES = ["SINGLE_TRIP", "ROUND_TRIP", "DAILY_PASS", "WEEKLY_PASS", "MONTHLY_PASS"]
INCIDENT_SEVERITY = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
INCIDENT_TYPES = ["VEHICLE_ISSUE", "SAFETY_CONCERN", "OTHER"]
NOTIFICATION_TYPES = ["ALERT", "UPDATE", "PROMOTION", "REMINDER", "GENERAL", "TRIP_UPDATE", "SERVICE_ALERT"]
ATTENDANCE_STATUS = ["PRESENT", "ABSENT", "LATE"]
TRIP_STATUS = ["SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "DELAYED"]
PAYMENT_STATUS = ["PENDING", "COMPLETED", "FAILED", "CANCELLED", "REFUNDED"]
TICKET_STATUS = ["ACTIVE", "USED", "EXPIRED", "CANCELLED"]
APPROVAL_STATUS = ["PENDING", "APPROVED", "REJECTED"]
REALLOCATION_REASONS = ["OVERCROWDING", "ROUTE_DISRUPTION", "MAINTENANCE_REQUIRED", "EMERGENCY", "SCHEDULE_OPTIMIZATION", "OTHER"]
REALLOCATION_STATUS = ["PENDING", "APPROVED", "REJECTED", "COMPLETED"]
OVERCROWDING_SEVERITY = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
MESSAGE_TYPES = ["TEXT", "IMAGE", "FILE", "SYSTEM"]

# Addis Ababa area coordinates (latitude, longitude bounds)
ADDIS_ABABA_BOUNDS = {
    "lat_min": 8.9,
    "lat_max": 9.1,
    "lon_min": 38.7,
    "lon_max": 38.9
}

# Helper functions
def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid4())

def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def random_location():
    """Generate a random location in Addis Ababa area."""
    return {
        "latitude": random.uniform(ADDIS_ABABA_BOUNDS["lat_min"], ADDIS_ABABA_BOUNDS["lat_max"]),
        "longitude": random.uniform(ADDIS_ABABA_BOUNDS["lon_min"], ADDIS_ABABA_BOUNDS["lon_max"])
    }

def random_datetime(days_min: int, days_max: int) -> datetime:
    """Generate a random datetime between days_min and days_max from now."""
    delta = random.randint(days_min, days_max)
    return datetime.utcnow() + timedelta(days=delta)

def model_to_mongo_doc(model: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a model dict to a MongoDB document using UUID-only approach."""
    if "id" not in model:
        model["id"] = generate_uuid()

    if "created_at" not in model:
        model["created_at"] = datetime.utcnow()

    if "updated_at" not in model:
        model["updated_at"] = datetime.utcnow()

    # Ensure id is a string
    if "id" in model:
        model["id"] = str(model["id"])

    # Set _id to the same value as id for MongoDB compatibility
    model["_id"] = model["id"]

    return model

async def clear_database(db):
    """Clear all collections in the database."""
    print("🗑️ Clearing existing database...")
    
    collections = [
        "users", "buses", "bus_stops", "routes", "schedules", "trips",
        "payments", "tickets", "feedback", "incidents", "notifications",
        "notification_settings", "attendance",
        "approval_requests", "conversations", "messages", "reallocation_requests",
        "overcrowding_reports", "alerts"
    ]
    
    for collection_name in collections:
        try:
            await db[collection_name].delete_many({})
            print(f"✅ Cleared {collection_name}")
        except Exception as e:
            print(f"⚠️ Could not clear {collection_name}: {e}")

async def import_bus_stops_from_geojson(db, file_path: str = "busStops.geojson") -> List[Dict[str, Any]]:
    """Import bus stops from GeoJSON file."""
    print(f"🚏 Importing bus stops from {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ GeoJSON file not found: {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"❌ Invalid GeoJSON format in file: {file_path}")
        return []
    
    bus_stops = []
    imported_count = 0
    skipped_count = 0
    
    for feature in geojson_data.get('features', []):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        if geometry.get('type') != 'Point':
            continue
        
        coordinates = geometry.get('coordinates', [])
        if len(coordinates) < 2:
            continue
        
        # Extract name from properties
        name = properties.get('name')
        if not name:
            # Try alternative name fields
            name = properties.get('name:en') or properties.get('name:am')
            if not name:
                # Generate a name if none exists
                osm_id = properties.get('@id', '').split('/')[-1]
                name = f"Bus Stop {osm_id}"
        
        # Check if bus stop already exists
        existing_stop = await db.bus_stops.find_one({"name": name})
        if existing_stop:
            skipped_count += 1
            continue
        
        # Create bus stop model
        bus_stop = {
            "id": generate_uuid(),
            "name": name,
            "location": {
                "latitude": coordinates[1],  # GeoJSON uses [longitude, latitude]
                "longitude": coordinates[0]
            },
            "capacity": random.randint(20, 100),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        bus_stops.append(model_to_mongo_doc(bus_stop))
        imported_count += 1
    
    if bus_stops:
        result = await db.bus_stops.insert_many(bus_stops)
        print(f"✅ Imported {len(result.inserted_ids)} bus stops from GeoJSON")
    
    print(f"📊 Bus stops: {imported_count} imported, {skipped_count} skipped (already exist)")
    return bus_stops

async def import_bus_stops_from_csv(db, file_path: str = "data/stops.txt") -> List[Dict[str, Any]]:
    """Import bus stops from CSV file."""
    print(f"🚏 Importing bus stops from {file_path}...")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            csv_data = list(csv_reader)
    except FileNotFoundError:
        print(f"❌ CSV file not found: {file_path}")
        return []
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return []

    bus_stops = []
    imported_count = 0
    skipped_count = 0

    for row in csv_data:
        # Skip if essential data is missing
        if not row.get('stop_name') or not row.get('stop_lat') or not row.get('stop_lon'):
            continue

        try:
            latitude = float(row['stop_lat'])
            longitude = float(row['stop_lon'])
        except (ValueError, TypeError):
            continue

        # Only import stops (location_type = 0), skip stations
        location_type = row.get('location_type', '0')
        if location_type != '0':
            continue

        name = row['stop_name'].strip()

        # Check if bus stop already exists
        existing_stop = await db.bus_stops.find_one({"name": name})
        if existing_stop:
            skipped_count += 1
            continue

        # Create bus stop model
        bus_stop = {
            "id": generate_uuid(),
            "name": name,
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "capacity": random.randint(20, 100),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            # Store original CSV data for reference
            "csv_stop_id": row.get('stop_id', ''),
            "parent_station": row.get('parent_station', '')
        }

        bus_stops.append(model_to_mongo_doc(bus_stop))
        imported_count += 1

    if bus_stops:
        result = await db.bus_stops.insert_many(bus_stops)
        print(f"✅ Imported {len(result.inserted_ids)} bus stops from CSV")

    print(f"📊 Bus stops: {imported_count} imported, {skipped_count} skipped (already exist)")
    return bus_stops

async def import_routes_from_csv(db, bus_stops, file_path: str = "data/routes.txt") -> List[Dict[str, Any]]:
    """Import routes from CSV file."""
    print(f"🛣️ Importing routes from {file_path}...")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            csv_data = list(csv_reader)
    except FileNotFoundError:
        print(f"❌ CSV file not found: {file_path}")
        return []
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return []

    routes = []
    imported_count = 0
    skipped_count = 0

    # Get bus stop IDs for random assignment (since we don't have stop_times.txt)
    bus_stop_ids = [stop["id"] for stop in bus_stops] if bus_stops else []

    for row in csv_data:
        # Skip if essential data is missing
        if not row.get('route_long_name'):
            continue

        route_name = row['route_long_name'].strip()

        # Check if route already exists
        existing_route = await db.routes.find_one({"name": route_name})
        if existing_route:
            skipped_count += 1
            continue

        # Create description from available fields
        description_parts = []
        if row.get('route_desc'):
            description_parts.append(row['route_desc'].strip())
        if row.get('route_short_name'):
            description_parts.append(f"Route Code: {row['route_short_name'].strip()}")

        description = " | ".join(description_parts) if description_parts else f"Bus route: {route_name}"

        # Assign random stops since we don't have stop sequence data
        # In a real implementation, you'd need stop_times.txt to get the actual stops
        num_stops = min(random.randint(4, 12), len(bus_stop_ids)) if bus_stop_ids else 0
        selected_stops = random.sample(bus_stop_ids, num_stops) if num_stops > 0 else []

        # Create route model
        route = {
            "id": generate_uuid(),
            "name": route_name,
            "description": description,
            "stop_ids": selected_stops,
            "total_distance": round(random.uniform(8, 35), 2),  # km - estimated
            "estimated_duration": round(random.uniform(30, 120), 2),  # minutes - estimated
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            # Store original CSV data for reference
            "csv_route_id": row.get('route_id', ''),
            "route_short_name": row.get('route_short_name', ''),
            "route_type": row.get('route_type', ''),
            "agency_id": row.get('agency_id', ''),
            "route_color": row.get('route_color', ''),
            "route_text_color": row.get('route_text_color', '')
        }

        routes.append(model_to_mongo_doc(route))
        imported_count += 1

    if routes:
        result = await db.routes.insert_many(routes)
        print(f"✅ Imported {len(result.inserted_ids)} routes from CSV")

    print(f"📊 Routes: {imported_count} imported, {skipped_count} skipped (already exist)")
    return routes

async def create_users(db, count=25):
    """Create mock users with different roles."""
    print(f"👥 Creating {count} users...")
    users = []
    default_password = hash_password("Test123!")

    # Create users with different roles
    for i in range(count):
        role = random.choice(USER_ROLES)

        # Generate more PASSENGER roles than others
        if i < count * 0.6:
            role = "PASSENGER"
        elif i < count * 0.8:
            role = random.choice(["BUS_DRIVER", "QUEUE_REGULATOR"])

        # Generate gender for profile image consistency
        gender = random.choice(["MALE", "FEMALE"])
        portrait_gender = "men" if gender == "MALE" else "women"

        user = {
            "id": generate_uuid(),
            "first_name": fake.first_name_male() if gender == "MALE" else fake.first_name_female(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "password": default_password,
            "role": role,
            "phone_number": fake.phone_number(),

            # Profile Information
            "profile_image": None if random.random() > 0.3 else f"https://randomuser.me/api/portraits/{portrait_gender}/{random.randint(1, 99)}.jpg",
            "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=70) if random.random() > 0.2 else None,
            "gender": gender if random.random() > 0.1 else None,
            "nationality": "Ethiopian" if random.random() > 0.1 else fake.country(),
            "national_id": fake.bothify(text='##########') if random.random() > 0.3 else None,

            # Address Information
            "street_address": fake.street_address() if random.random() > 0.4 else None,
            "city": fake.city() if random.random() > 0.3 else None,
            "state_region": fake.state() if random.random() > 0.4 else None,
            "postal_code": fake.postcode() if random.random() > 0.5 else None,
            "country": "Ethiopia",

            # Contact Information
            "emergency_contact_name": fake.name() if random.random() > 0.3 else None,
            "emergency_contact_phone": fake.phone_number() if random.random() > 0.3 else None,
            "emergency_contact_relationship": random.choice(["Parent", "Spouse", "Sibling", "Friend", "Other"]) if random.random() > 0.3 else None,
            "secondary_phone": fake.phone_number() if random.random() > 0.7 else None,
            "work_phone": fake.phone_number() if random.random() > 0.8 else None,

            # Preferences and Settings
            "preferred_language": random.choice(["en", "am"]),
            "is_active": random.random() > 0.05,
            "is_verified": random.random() > 0.3,

            # Payment and Discounts
            "preferred_payment_method": random.choice(["cash", "card", "mobile", None]) if random.random() > 0.4 else None,
            "monthly_pass_active": random.random() > 0.7,
            "student_discount_eligible": random.random() > 0.8,
            "senior_discount_eligible": random.random() > 0.9,
            "disability_discount_eligible": random.random() > 0.95,

            # Analytics
            "total_trips": random.randint(0, 500) if role == "PASSENGER" else 0,
            "total_distance_traveled": round(random.uniform(0, 10000), 2) if role == "PASSENGER" else 0.0,

            # Timestamps
            "created_at": random_datetime(-90, -1),
            "updated_at": random_datetime(-30, 0),
        }
        users.append(model_to_mongo_doc(user))

    # Ensure at least one of each role exists
    for role in USER_ROLES:
        if not any(u['role'] == role for u in users):
            gender = random.choice(["MALE", "FEMALE"])
            user = {
                "id": generate_uuid(),
                "first_name": fake.first_name_male() if gender == "MALE" else fake.first_name_female(),
                "last_name": fake.last_name(),
                "email": f"{role.lower()}@example.com",
                "password": default_password,
                "role": role,
                "phone_number": fake.phone_number(),
                "profile_image": None,

                # Profile Information
                "date_of_birth": fake.date_of_birth(minimum_age=25, maximum_age=60),
                "gender": gender,
                "nationality": "Ethiopian",
                "country": "Ethiopia",

                # Preferences and Settings
                "preferred_language": "en",
                "is_active": True,
                "is_verified": True,

                # Analytics
                "total_trips": 0,
                "total_distance_traveled": 0.0,

                # Timestamps
                "created_at": random_datetime(-90, -1),
                "updated_at": random_datetime(-30, 0),
            }
            users.append(model_to_mongo_doc(user))

    # Add test users for each role with predictable credentials
    test_users = []
    for role in USER_ROLES:
        # Check if test user already exists
        existing_user = await db.users.find_one({"email": f"test_{role.lower()}@guzosync.com"})
        if existing_user:
            print(f"⏭️ Test {role} user already exists")
            continue

        test_user = {
            "id": generate_uuid(),
            "first_name": f"Test",
            "last_name": f"{role.capitalize()}",
            "email": f"test_{role.lower()}@guzosync.com",
            "password": hash_password("Test123!"),
            "role": role,
            "phone_number": "123456789",
            "profile_image": None,

            # Profile Information
            "date_of_birth": fake.date_of_birth(minimum_age=25, maximum_age=45),
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

            # Timestamps
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        test_users.append(model_to_mongo_doc(test_user))

        # Print temporary password for debugging (as per user preference)
        if role in ["QUEUE_REGULATOR", "BUS_DRIVER"]:
            print(f"🔑 Temporary password for {role}: Test123!")

    users.extend(test_users)

    if users:
        result = await db.users.insert_many(users)
        print(f"✅ Created {len(result.inserted_ids)} users")

    return users

async def create_buses(db, count=15):
    """Create mock buses."""
    print(f"🚌 Creating {count} buses...")
    buses = []

    for i in range(count):
        bus_type = random.choice(BUS_TYPES)

        # Set capacity based on bus type
        if bus_type == "STANDARD":
            capacity = random.randint(40, 60)
        elif bus_type == "ARTICULATED":
            capacity = random.randint(80, 120)
        else:  # MINIBUS
            capacity = random.randint(12, 20)

        bus = {
            "id": generate_uuid(),
            "license_plate": f"AA-{random.randint(1000, 9999)}",
            "bus_type": bus_type,
            "capacity": capacity,
            "current_location": random_location() if random.random() > 0.2 else None,
            "last_location_update": datetime.utcnow() - timedelta(minutes=random.randint(1, 120)) if random.random() > 0.2 else None,
            "heading": random.uniform(0, 359) if random.random() > 0.2 else None,
            "speed": random.uniform(0, 80) if random.random() > 0.2 else None,
            "location_accuracy": random.uniform(3, 15) if random.random() > 0.2 else None,
            "current_address": fake.street_address() if random.random() > 0.2 else None,
            "assigned_route_id": None,  # Will be assigned later
            "assigned_driver_id": None,  # Will be assigned later
            "bus_status": random.choice(BUS_STATUS),
            "manufacture_year": random.randint(2010, 2023),
            "bus_model": random.choice(["Volvo 7900", "Mercedes-Benz Citaro", "MAN Lion's City", "Scania Citywide"]),
            "created_at": random_datetime(-180, -30),
            "updated_at": random_datetime(-30, -1)
        }
        buses.append(model_to_mongo_doc(bus))

    if buses:
        result = await db.buses.insert_many(buses)
        print(f"✅ Created {len(result.inserted_ids)} buses")

    return buses

async def create_routes(db, bus_stops, count=10):
    """Create mock routes using existing bus stops."""
    print(f"🛣️ Creating {count} routes...")
    routes: List[Dict[str, Any]] = []

    # Common route names in Addis Ababa
    route_names = [
        "Megenagna-Bole", "Mexico-Lebu", "Piazza-Mexico", "Stadium-CMC",
        "Ayat-Tor Hailoch", "Jemo-Megenagna", "Kaliti-Wingate", "Saris-Bethel",
        "Meskel Square-Ayat", "Kazanchis-Ayer Tena", "Lideta-Gerji", "Shiro Meda-Bole"
    ]

    if not bus_stops:
        print("⚠️ No bus stops available to create routes")
        return routes

    bus_stop_ids = [stop["id"] for stop in bus_stops]

    for i in range(count):
        # Select 3-8 random stops for each route
        num_stops = min(random.randint(3, 8), len(bus_stop_ids))
        selected_stops = random.sample(bus_stop_ids, num_stops)

        route_name = route_names[i % len(route_names)]
        if i >= len(route_names):
            route_name = f"Route {i + 1}"

        route = {
            "id": generate_uuid(),
            "name": route_name,
            "description": f"Route connecting {num_stops} destinations",
            "stop_ids": selected_stops,
            "total_distance": round(random.uniform(5, 30), 2),  # km
            "estimated_duration": round(random.uniform(20, 90), 2),  # minutes
            "is_active": random.random() > 0.1,
            "created_at": random_datetime(-180, -30),
            "updated_at": random_datetime(-30, -1)
        }
        routes.append(model_to_mongo_doc(route))

    if routes:
        result = await db.routes.insert_many(routes)
        print(f"✅ Created {len(result.inserted_ids)} routes")

    return routes

async def create_schedules(db, routes, buses, drivers, count=20):
    """Create mock schedules."""
    print(f"📅 Creating {count} schedules...")
    schedules: List[Dict[str, Any]] = []

    if not routes or not buses:
        print("⚠️ No routes or buses available to create schedules")
        return schedules

    route_ids = [route["id"] for route in routes]
    bus_ids = [bus["id"] for bus in buses]
    driver_ids = [driver["id"] for driver in drivers if driver["role"] == "BUS_DRIVER"]

    for i in range(count):
        # Create schedule patterns
        patterns = ["DAILY", "WEEKDAYS", "WEEKENDS", "CUSTOM"]
        pattern = random.choice(patterns)

        # Generate departure times
        start_hour = random.randint(5, 8)  # Early morning start
        end_hour = random.randint(20, 23)  # Late evening end
        interval = random.randint(15, 60)  # Minutes between departures

        departure_times = []
        current_time = start_hour * 60  # Convert to minutes
        end_time = end_hour * 60

        while current_time <= end_time:
            hours = current_time // 60
            minutes = current_time % 60
            departure_times.append(f"{hours:02d}:{minutes:02d}")
            current_time += interval

        schedule = {
            "id": generate_uuid(),
            "route_id": random.choice(route_ids),
            "schedule_pattern": pattern,
            "departure_times": departure_times,
            "assigned_bus_id": random.choice(bus_ids) if random.random() > 0.2 else None,
            "assigned_driver_id": random.choice(driver_ids) if driver_ids and random.random() > 0.3 else None,
            "valid_from": random_datetime(-30, -7),
            "valid_until": random_datetime(30, 90) if random.random() > 0.3 else None,
            "is_active": random.random() > 0.1,
            "created_at": random_datetime(-90, -30),
            "updated_at": random_datetime(-30, -1)
        }
        schedules.append(model_to_mongo_doc(schedule))

    if schedules:
        result = await db.schedules.insert_many(schedules)
        print(f"✅ Created {len(result.inserted_ids)} schedules")

    return schedules

async def create_trips(db, buses, routes, drivers, schedules, count=35):
    """Create mock trips."""
    print(f"🚐 Creating {count} trips...")
    trips: List[Dict[str, Any]] = []

    if not buses or not routes:
        print("⚠️ No buses or routes available to create trips")
        return trips

    driver_ids = [driver["id"] for driver in drivers if driver["role"] == "BUS_DRIVER"]
    bus_ids = [bus["id"] for bus in buses]
    route_ids = [route["id"] for route in routes]
    schedule_ids = [schedule["id"] for schedule in schedules]

    for i in range(count):
        # Generate random times for the trip
        base_time = datetime.utcnow() - timedelta(days=random.randint(0, 30))

        # Determine trip status and times based on random factors
        status_options = TRIP_STATUS
        status_weights = [0.15, 0.25, 0.45, 0.05, 0.1]  # Weights for each status
        status = random.choices(status_options, weights=status_weights, k=1)[0]

        # Set times based on status
        actual_departure = base_time if status != "SCHEDULED" else None

        if status == "COMPLETED":
            actual_arrival = actual_departure + timedelta(minutes=random.randint(30, 120)) if actual_departure else None
        else:
            actual_arrival = None

        estimated_arrival = base_time + timedelta(minutes=random.randint(30, 120))

        trip = {
            "id": generate_uuid(),
            "bus_id": random.choice(bus_ids),
            "route_id": random.choice(route_ids),
            "driver_id": random.choice(driver_ids) if driver_ids and random.random() > 0.1 else None,
            "schedule_id": random.choice(schedule_ids) if schedule_ids and random.random() > 0.3 else None,
            "actual_departure_time": actual_departure,
            "actual_arrival_time": actual_arrival,
            "estimated_arrival_time": estimated_arrival,
            "status": status,
            "passenger_ids": [],  # Will be populated later
            "feedback_ids": [],   # Will be populated later
            "created_at": random_datetime(-30, -1),
            "updated_at": random_datetime(-7, 0)
        }
        trips.append(model_to_mongo_doc(trip))

    if trips:
        result = await db.trips.insert_many(trips)
        print(f"✅ Created {len(result.inserted_ids)} trips")

    return trips

async def create_payments(db, users, count=25):
    """Create mock payments."""
    print(f"💳 Creating {count} payments...")
    payments: List[Dict[str, Any]] = []

    # Filter passengers
    passengers = [user for user in users if user["role"] == "PASSENGER"]

    if not passengers:
        print("⚠️ No passengers available to create payments")
        return payments

    for i in range(count):
        passenger = random.choice(passengers)

        # Generate random payment details
        amount = random.choice([15, 25, 50, 100, 200, 500])

        # Determine payment status
        status_options = PAYMENT_STATUS
        status_weights = [0.1, 0.75, 0.08, 0.02, 0.05]  # Most payments are completed
        status = random.choices(status_options, weights=status_weights, k=1)[0]

        payment = {
            "id": generate_uuid(),
            "tx_ref": f"GS-{str(uuid4())[:8].upper()}",
            "amount": amount,
            "currency": "ETB",
            "payment_method": random.choice(PAYMENT_METHODS),
            "mobile_number": passenger["phone_number"],
            "customer_id": passenger["id"],
            "customer_email": passenger["email"],
            "customer_first_name": passenger["first_name"],
            "customer_last_name": passenger["last_name"],
            "status": status,
            "chapa_tx_ref": f"CHAPA-{str(uuid4())[:8].upper()}",
            "description": f"Payment for bus ticket - {random.choice(['Single Trip', 'Round Trip', 'Daily Pass'])}",
            "paid_at": datetime.utcnow() - timedelta(minutes=random.randint(1, 1440)) if status == "COMPLETED" else None,
            "failed_reason": "Network timeout" if status == "FAILED" else None,
            "created_at": random_datetime(-30, -1),
            "updated_at": random_datetime(-7, 0)
        }
        payments.append(model_to_mongo_doc(payment))

    if payments:
        result = await db.payments.insert_many(payments)
        print(f"✅ Created {len(result.inserted_ids)} payments")

    return payments

async def create_tickets(db, payments, routes, bus_stops, count=30):
    """Create mock tickets."""
    print(f"🎫 Creating {count} tickets...")
    tickets: List[Dict[str, Any]] = []

    # Filter completed payments
    completed_payments = [p for p in payments if p["status"] == "COMPLETED"]

    if not completed_payments:
        print("⚠️ No completed payments available to create tickets")
        return tickets

    route_ids = [route["id"] for route in routes] if routes else []
    bus_stop_ids = [stop["id"] for stop in bus_stops] if bus_stops else []

    for i in range(min(count, len(completed_payments))):
        payment = completed_payments[i]

        # Generate ticket details
        ticket_type = random.choice(TICKET_TYPES)
        valid_from = datetime.utcnow() - timedelta(days=random.randint(0, 7))

        # Set validity period based on ticket type
        if ticket_type == "SINGLE_TRIP":
            valid_until = valid_from + timedelta(hours=24)
        elif ticket_type == "ROUND_TRIP":
            valid_until = valid_from + timedelta(days=1)
        elif ticket_type == "DAILY_PASS":
            valid_until = valid_from + timedelta(days=1)
        elif ticket_type == "WEEKLY_PASS":
            valid_until = valid_from + timedelta(days=7)
        else:  # MONTHLY_PASS
            valid_until = valid_from + timedelta(days=30)

        # Determine if ticket is used
        is_used = random.random() > 0.3
        status = random.choice(TICKET_STATUS) if is_used else "ACTIVE"

        ticket = {
            "id": generate_uuid(),
            "ticket_number": f"TKT-{str(uuid4())[:8].upper()}",
            "customer_id": payment["customer_id"],
            "payment_id": payment["id"],
            "ticket_type": ticket_type,
            "origin_stop_id": random.choice(bus_stop_ids) if bus_stop_ids else None,
            "destination_stop_id": random.choice(bus_stop_ids) if bus_stop_ids else None,
            "route_id": random.choice(route_ids) if route_ids else None,
            "trip_id": None,  # Will be populated when trips are created
            "status": status,
            "price": payment["amount"],
            "currency": "ETB",
            "valid_from": valid_from,
            "valid_until": valid_until,
            "used_at": datetime.utcnow() - timedelta(hours=random.randint(1, 48)) if status == "USED" else None,
            "used_trip_id": None,
            "qr_code": f"QR-{str(uuid4())[:12].upper()}",
            "metadata": {
                "purchase_location": "Mobile App",
                "device_id": f"device_{random.randint(1000, 9999)}"
            },
            "created_at": valid_from,
            "updated_at": datetime.utcnow()
        }
        tickets.append(model_to_mongo_doc(ticket))

    if tickets:
        result = await db.tickets.insert_many(tickets)
        print(f"✅ Created {len(result.inserted_ids)} tickets")

    return tickets

async def create_feedback(db, users, trips, buses, count=20):
    """Create mock feedback."""
    print(f"💬 Creating {count} feedback records...")
    feedback_records: List[Dict[str, Any]] = []

    # Filter passengers
    passengers = [user for user in users if user["role"] == "PASSENGER"]
    trip_ids = [trip["id"] for trip in trips] if trips else []
    bus_ids = [bus["id"] for bus in buses] if buses else []

    if not passengers:
        print("⚠️ No passengers available to create feedback")
        return feedback_records

    feedback_content = [
        "Great service, bus was on time!",
        "Driver was very professional and courteous.",
        "Bus was clean and comfortable.",
        "Could improve punctuality.",
        "Excellent experience overall.",
        "Bus was overcrowded during rush hour.",
        "Good route coverage in the city.",
        "Air conditioning wasn't working properly.",
        "Staff was helpful and friendly.",
        "Need more frequent buses on this route.",
        "Smooth ride and comfortable seats.",
        "Bus arrived exactly on schedule.",
        "Driver followed traffic rules well.",
        "Clean interior and good maintenance.",
        "Could use better ventilation system."
    ]

    for i in range(count):
        passenger = random.choice(passengers)

        feedback = {
            "id": generate_uuid(),
            "submitted_by_user_id": passenger["id"],
            "content": random.choice(feedback_content),
            "rating": round(random.uniform(2.5, 5.0), 1),
            "related_trip_id": random.choice(trip_ids) if trip_ids and random.random() > 0.3 else None,
            "related_bus_id": random.choice(bus_ids) if bus_ids and random.random() > 0.5 else None,
            "created_at": random_datetime(-30, -1),
            "updated_at": random_datetime(-7, 0)
        }
        feedback_records.append(model_to_mongo_doc(feedback))

    if feedback_records:
        result = await db.feedback.insert_many(feedback_records)
        print(f"✅ Created {len(result.inserted_ids)} feedback records")

    return feedback_records

async def create_incidents(db, users, buses, routes, bus_stops, count=12):
    """Create mock incidents."""
    print(f"🚨 Creating {count} incidents...")
    incidents: List[Dict[str, Any]] = []

    # Get all users who can report incidents
    reporters = [user for user in users if user["role"] in ["PASSENGER", "BUS_DRIVER", "QUEUE_REGULATOR"]]
    bus_ids = [bus["id"] for bus in buses] if buses else []
    route_ids = [route["id"] for route in routes] if routes else []

    if not reporters:
        print("⚠️ No users available to create incidents")
        return incidents

    incident_descriptions = [
        "Bus breakdown on main road",
        "Traffic accident causing delays",
        "Overcrowding at bus stop",
        "Mechanical issue with bus doors",
        "Route deviation due to road construction",
        "Passenger safety concern",
        "Bus running significantly behind schedule",
        "Equipment malfunction",
        "Driver reported sick during shift",
        "Bus tire puncture",
        "Engine overheating issue",
        "Electrical system failure"
    ]

    for i in range(count):
        reporter = random.choice(reporters)
        severity = random.choice(INCIDENT_SEVERITY)
        incident_type = random.choice(INCIDENT_TYPES)
        is_resolved = random.random() > 0.4

        incident = {
            "id": generate_uuid(),
            "reported_by_user_id": reporter["id"],
            "description": random.choice(incident_descriptions),
            "incident_type": incident_type,
            "location": random_location() if random.random() > 0.3 else None,
            "related_bus_id": random.choice(bus_ids) if bus_ids and random.random() > 0.4 else None,
            "related_route_id": random.choice(route_ids) if route_ids and random.random() > 0.3 else None,
            "is_resolved": is_resolved,
            "resolution_notes": "Issue resolved by maintenance team" if is_resolved else None,
            "severity": severity,
            "created_at": random_datetime(-15, -1),
            "updated_at": random_datetime(-7, 0) if is_resolved else random_datetime(-3, 0)
        }
        incidents.append(model_to_mongo_doc(incident))

    if incidents:
        result = await db.incidents.insert_many(incidents)
        print(f"✅ Created {len(result.inserted_ids)} incidents")

    return incidents

async def create_notifications(db, users, count=30):
    """Create mock notifications."""
    print(f"🔔 Creating {count} notifications...")
    notifications: List[Dict[str, Any]] = []

    if not users:
        print("⚠️ No users available to create notifications")
        return notifications

    notification_templates = [
        {"title": "Trip Update", "message": "Your bus is running 5 minutes late", "type": "TRIP_UPDATE"},
        {"title": "Service Alert", "message": "Route temporarily diverted due to construction", "type": "SERVICE_ALERT"},
        {"title": "Payment Confirmation", "message": "Your payment has been processed successfully", "type": "UPDATE"},
        {"title": "Welcome!", "message": "Welcome to GuzoSync! Start your journey with us.", "type": "GENERAL"},
        {"title": "Schedule Change", "message": "Bus schedule has been updated for your route", "type": "ALERT"},
        {"title": "Maintenance Notice", "message": "Scheduled maintenance on your regular route", "type": "ALERT"},
        {"title": "New Feature", "message": "Check out our new real-time tracking feature!", "type": "PROMOTION"},
        {"title": "Reminder", "message": "Don't forget to validate your ticket", "type": "REMINDER"},
        {"title": "Route Optimization", "message": "We've optimized your route for better efficiency", "type": "UPDATE"},
        {"title": "Safety Update", "message": "New safety measures implemented on all buses", "type": "GENERAL"}
    ]

    for i in range(count):
        user = random.choice(users)
        template = random.choice(notification_templates)

        notification = {
            "id": generate_uuid(),
            "user_id": user["id"],
            "title": template["title"],
            "message": template["message"],
            "type": template["type"],
            "is_read": random.random() > 0.4,
            "related_entity": {
                "entity_type": random.choice(["trip", "route", "bus", "payment"]),
                "entity_id": generate_uuid()
            } if random.random() > 0.5 else None,
            "created_at": random_datetime(-30, -1),
            "updated_at": random_datetime(-7, 0)
        }
        notifications.append(model_to_mongo_doc(notification))

    if notifications:
        result = await db.notifications.insert_many(notifications)
        print(f"✅ Created {len(result.inserted_ids)} notifications")

    return notifications

async def create_notification_settings(db, users):
    """Create notification settings for users."""
    print(f"⚙️ Creating notification settings...")
    settings = []

    for user in users:
        setting = {
            "id": generate_uuid(),
            "user_id": user["id"],
            "email_enabled": random.random() > 0.3,
            "created_at": user["created_at"],
            "updated_at": random_datetime(-30, 0)
        }
        settings.append(model_to_mongo_doc(setting))

    if settings:
        result = await db.notification_settings.insert_many(settings)
        print(f"✅ Created {len(result.inserted_ids)} notification settings")

    return settings

async def create_attendance(db, users, months=2):
    """Create mock attendance records for bus drivers and queue regulators over multiple months."""
    print(f"📅 Creating attendance records for {months} months...")
    attendance_records: List[Dict[str, Any]] = []

    # Filter staff users
    staff_users = [user for user in users if user["role"] in ["BUS_DRIVER", "QUEUE_REGULATOR"]]

    if not staff_users:
        print("⚠️ No staff users available to create attendance records")
        return attendance_records

    # Calculate date range (couple of months back from now)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=months * 30)  # Approximate months to days

    print(f"📊 Generating attendance from {start_date} to {end_date}")
    print(f"👥 Staff members: {len(staff_users)} ({[u['role'] for u in staff_users].count('BUS_DRIVER')} drivers, {[u['role'] for u in staff_users].count('QUEUE_REGULATOR')} regulators)")

    # Create attendance patterns for each staff member
    staff_patterns = {}
    for user in staff_users:
        # Assign attendance patterns to make data more realistic
        patterns = {
            "reliable": {"present": 0.85, "late": 0.10, "absent": 0.05},  # Very reliable
            "average": {"present": 0.75, "late": 0.15, "absent": 0.10},   # Average reliability
            "problematic": {"present": 0.60, "late": 0.25, "absent": 0.15}  # More issues
        }

        # Assign pattern based on random distribution
        pattern_choice = random.choices(
            list(patterns.keys()),
            weights=[0.4, 0.5, 0.1],  # 40% reliable, 50% average, 10% problematic
            k=1
        )[0]
        staff_patterns[user["id"]] = patterns[pattern_choice]

    # Track existing records to avoid duplicates
    existing_records = set()

    # Generate attendance for each day in the range
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends (assuming 5-day work week)
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4

            for user in staff_users:
                user_id = user["id"]

                # Check if record already exists for this user and date
                record_key = (user_id, current_date)
                if record_key in existing_records:
                    continue

                # Determine if user should have attendance record (90% chance)
                if random.random() > 0.9:
                    continue  # Skip this day for this user

                # Get user's attendance pattern
                pattern = staff_patterns[user_id]

                # Determine status based on pattern
                status_choice = random.choices(
                    ["PRESENT", "LATE", "ABSENT"],
                    weights=[pattern["present"], pattern["late"], pattern["absent"]],
                    k=1
                )[0]

                # Generate times based on status
                check_in_time = None
                check_out_time = None
                base_datetime = datetime.combine(current_date, datetime.min.time())

                if status_choice == "PRESENT":
                    # On time arrival (6:00-8:30 AM)
                    check_in_time = base_datetime.replace(
                        hour=random.randint(6, 8),
                        minute=random.randint(0, 30 if random.randint(6, 8) == 8 else 59),
                        second=0, microsecond=0
                    )
                    # Normal departure (5:00-8:00 PM)
                    check_out_time = base_datetime.replace(
                        hour=random.randint(17, 20),
                        minute=random.randint(0, 59),
                        second=0, microsecond=0
                    )
                elif status_choice == "LATE":
                    # Late arrival (8:31 AM - 11:00 AM)
                    check_in_time = base_datetime.replace(
                        hour=random.randint(8, 11),
                        minute=random.randint(31 if random.randint(8, 11) == 8 else 0, 59),
                        second=0, microsecond=0
                    )
                    # May leave later to compensate
                    check_out_time = base_datetime.replace(
                        hour=random.randint(17, 21),
                        minute=random.randint(0, 59),
                        second=0, microsecond=0
                    )
                # ABSENT status has no check-in/check-out times

                # Generate realistic notes
                notes_options: Dict[str, List[Optional[str]]] = {
                    "PRESENT": [None, "On time", "Good day", "Regular shift"],
                    "LATE": ["Traffic delay", "Personal emergency", "Bus breakdown", "Family issue", "Medical appointment"],
                    "ABSENT": ["Sick leave", "Personal emergency", "Family emergency", "Medical appointment", "Unauthorized absence"]
                }

                notes_list = notes_options.get(status_choice, [None])
                notes: Optional[str] = random.choice(notes_list)

                # Determine who marked the attendance
                marked_by = None
                control_staff = [u["id"] for u in users if u["role"] in ["CONTROL_STAFF", "CONTROL_ADMIN"]]
                if control_staff and random.random() > 0.3:  # 70% chance of being marked by control staff
                    marked_by = random.choice(control_staff)

                # Set marked_at time
                if check_in_time:
                    marked_at = check_in_time + timedelta(minutes=random.randint(0, 30))
                else:
                    # For absent records, marked during work hours
                    marked_at = base_datetime.replace(
                        hour=random.randint(9, 17),
                        minute=random.randint(0, 59),
                        second=0, microsecond=0
                    )

                record = {
                    "id": generate_uuid(),
                    "user_id": user_id,
                    "date": base_datetime,  # Store as datetime for MongoDB compatibility
                    "status": status_choice,
                    "check_in_time": check_in_time,
                    "check_out_time": check_out_time,
                    "location": random_location() if random.random() > 0.4 else None,
                    "notes": notes,
                    "marked_by": marked_by,
                    "marked_at": marked_at,
                    "created_at": base_datetime,
                    "updated_at": marked_at
                }

                attendance_records.append(model_to_mongo_doc(record))
                existing_records.add(record_key)

        current_date += timedelta(days=1)

    if attendance_records:
        result = await db.attendance.insert_many(attendance_records)
        print(f"✅ Created {len(result.inserted_ids)} attendance records")

        # Print summary statistics
        status_counts: Dict[str, int] = {}
        for record in attendance_records:
            status = record["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        print(f"📊 Attendance Summary:")
        for status, count in status_counts.items():
            percentage = (count / len(attendance_records)) * 100
            print(f"   {status}: {count} records ({percentage:.1f}%)")

    return attendance_records

async def create_approval_requests(db, count=8):
    """Create mock approval requests."""
    print(f"📝 Creating {count} approval requests...")
    approval_requests = []

    for _ in range(count):
        status = random.choice(APPROVAL_STATUS)
        requested_at = random_datetime(-30, -1)

        # Generate review details if approved/rejected
        reviewed_at = None
        reviewed_by = None
        review_notes = None

        if status != "PENDING":
            reviewed_at = requested_at + timedelta(days=random.randint(1, 7))
            reviewed_by = generate_uuid()  # Admin user ID
            review_notes = random.choice([
                "Application approved after verification",
                "Rejected due to incomplete documentation",
                "Approved with conditions",
                "Background check completed successfully"
            ])

        request = {
            "id": generate_uuid(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "phone_number": fake.phone_number(),
            "profile_image": None,
            "role": "CONTROL_STAFF",
            "status": status,
            "requested_at": requested_at,
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at,
            "review_notes": review_notes,
            "created_at": requested_at,
            "updated_at": reviewed_at if reviewed_at else requested_at
        }
        approval_requests.append(model_to_mongo_doc(request))

    if approval_requests:
        result = await db.approval_requests.insert_many(approval_requests)
        print(f"✅ Created {len(result.inserted_ids)} approval requests")

    return approval_requests

async def create_conversations_and_messages(db, users, count=15):
    """Create mock conversations and messages."""
    print(f"💬 Creating {count} conversations with messages...")
    conversations: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []

    if len(users) < 2:
        print("⚠️ Need at least 2 users to create conversations")
        return conversations, messages

    for _ in range(count):
        # Select 2-4 participants for each conversation
        num_participants = random.randint(2, min(4, len(users)))
        participants = random.sample([user["id"] for user in users], num_participants)

        conversation_id = generate_uuid()
        last_message_time = random_datetime(-30, -1)

        conversation = {
            "id": conversation_id,
            "participants": participants,
            "last_message_at": last_message_time,
            "created_at": random_datetime(-30, -7),
            "updated_at": last_message_time
        }
        conversations.append(model_to_mongo_doc(conversation))

        # Create 3-10 messages for each conversation
        num_messages = random.randint(3, 10)
        message_contents = [
            "Hello, how are you?",
            "When is the next bus arriving?",
            "The route has been updated.",
            "Thanks for the information!",
            "Is there any delay on Route 5?",
            "Bus is running 10 minutes late.",
            "Have a great day!",
            "Please check the new schedule.",
            "The bus stop has been relocated.",
            "Thank you for using our service."
        ]

        for _ in range(num_messages):
            sender = random.choice(participants)
            sent_time = last_message_time - timedelta(hours=random.randint(0, 24 * 7))

            message = {
                "id": generate_uuid(),
                "conversation_id": conversation_id,
                "sender_id": sender,
                "content": random.choice(message_contents),
                "message_type": random.choice(MESSAGE_TYPES),
                "sent_at": sent_time,
                "created_at": sent_time,
                "updated_at": sent_time
            }
            messages.append(model_to_mongo_doc(message))

    if conversations:
        result = await db.conversations.insert_many(conversations)
        print(f"✅ Created {len(result.inserted_ids)} conversations")

    if messages:
        result = await db.messages.insert_many(messages)
        print(f"✅ Created {len(result.inserted_ids)} messages")

    return conversations, messages

async def create_reallocation_requests(db, users, buses, routes, count=10):
    """Create mock reallocation requests."""
    print(f"🔄 Creating {count} reallocation requests...")
    reallocation_requests: List[Dict[str, Any]] = []

    # Filter regulators who can make requests
    regulators = [user for user in users if user["role"] == "QUEUE_REGULATOR"]
    bus_ids = [bus["id"] for bus in buses] if buses else []
    route_ids = [route["id"] for route in routes] if routes else []

    if not regulators or not bus_ids or not route_ids:
        print("⚠️ Need regulators, buses, and routes to create reallocation requests")
        return reallocation_requests

    for _ in range(count):
        regulator = random.choice(regulators)
        status = random.choice(REALLOCATION_STATUS)

        request = {
            "id": generate_uuid(),
            "requested_by_user_id": regulator["id"],
            "bus_id": random.choice(bus_ids),
            "current_route_id": random.choice(route_ids),
            "requested_route_id": random.choice(route_ids),
            "reason": random.choice(REALLOCATION_REASONS),
            "description": random.choice([
                "Bus overcrowding reported on current route",
                "Route disruption due to construction",
                "Emergency reallocation needed",
                "Schedule optimization request",
                "Maintenance required on current route"
            ]),
            "priority": random.choice(["NORMAL", "HIGH", "URGENT"]),
            "status": status,
            "reviewed_by": random.choice([user["id"] for user in users if user["role"] in ["CONTROL_STAFF", "CONTROL_ADMIN"]]) if status != "PENDING" else None,
            "reviewed_at": random_datetime(-7, -1) if status != "PENDING" else None,
            "review_notes": "Request approved for implementation" if status == "APPROVED" else None,
            "created_at": random_datetime(-15, -1),
            "updated_at": random_datetime(-7, 0)
        }
        reallocation_requests.append(model_to_mongo_doc(request))

    if reallocation_requests:
        result = await db.reallocation_requests.insert_many(reallocation_requests)
        print(f"✅ Created {len(result.inserted_ids)} reallocation requests")

    return reallocation_requests

async def create_overcrowding_reports(db, users, buses, routes, bus_stops, count=8):
    """Create mock overcrowding reports."""
    print(f"👥 Creating {count} overcrowding reports...")
    overcrowding_reports: List[Dict[str, Any]] = []

    # Filter regulators and passengers who can report
    reporters = [user for user in users if user["role"] in ["QUEUE_REGULATOR", "PASSENGER"]]
    bus_ids = [bus["id"] for bus in buses] if buses else []
    route_ids = [route["id"] for route in routes] if routes else []
    bus_stop_ids = [stop["id"] for stop in bus_stops] if bus_stops else []

    if not reporters or not bus_stop_ids:
        print("⚠️ Need reporters and bus stops to create overcrowding reports")
        return overcrowding_reports

    for _ in range(count):
        reporter = random.choice(reporters)
        severity = random.choice(OVERCROWDING_SEVERITY)
        is_resolved = random.random() > 0.5

        report = {
            "id": generate_uuid(),
            "reported_by_user_id": reporter["id"],
            "bus_stop_id": random.choice(bus_stop_ids),
            "bus_id": random.choice(bus_ids) if bus_ids and random.random() > 0.3 else None,
            "route_id": random.choice(route_ids) if route_ids and random.random() > 0.4 else None,
            "severity": severity,
            "passenger_count": random.randint(50, 200) if random.random() > 0.3 else None,
            "description": random.choice([
                "Extremely crowded bus stop during rush hour",
                "Passengers unable to board due to overcrowding",
                "Safety concern due to excessive crowding",
                "Need additional buses on this route",
                "Long queues forming at bus stop"
            ]),
            "location": random_location(),
            "is_resolved": is_resolved,
            "resolution_notes": "Additional buses deployed to route" if is_resolved else None,
            "resolved_by": random.choice([user["id"] for user in users if user["role"] in ["CONTROL_STAFF", "CONTROL_ADMIN"]]) if is_resolved else None,
            "resolved_at": random_datetime(-3, -1) if is_resolved else None,
            "created_at": random_datetime(-10, -1),
            "updated_at": random_datetime(-3, 0)
        }
        overcrowding_reports.append(model_to_mongo_doc(report))

    if overcrowding_reports:
        result = await db.overcrowding_reports.insert_many(overcrowding_reports)
        print(f"✅ Created {len(result.inserted_ids)} overcrowding reports")

    return overcrowding_reports

async def main():
    """Main function to execute complete database seeding."""
    print("🚀 Starting complete GuzoSync database seeding...")
    print(f"📡 MongoDB URL: {mongodb_url}")
    print(f"🗄️ Database: {database_name}")

    # Connect to MongoDB
    client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]

    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")

        # Clear existing data (optional - comment out if you want to preserve existing data)
        await clear_database(db)

        print("\n" + "="*60)
        print("🌱 STARTING DATABASE SEEDING")
        print("="*60)

        # Step 1: Import bus stops from CSV
        print("\n📍 IMPORTING BUS STOPS...")
        bus_stops = await import_bus_stops_from_csv(db)

        # Step 2: Import routes from CSV
        print("\n🛣️ IMPORTING ROUTES...")
        routes_csv = await import_routes_from_csv(db, bus_stops)

        # Step 3: Create additional mock routes if needed
        additional_routes = await create_routes(db, bus_stops, count=5)
        routes = routes_csv + additional_routes

        # Step 4: Create users
        users = await create_users(db, count=30)

        # Step 5: Create buses
        buses = await create_buses(db, count=18)

        # Step 6: Create schedules
        drivers = [user for user in users if user["role"] == "BUS_DRIVER"]
        schedules = await create_schedules(db, routes, buses, drivers, count=25)

        # Step 7: Create trips
        trips = await create_trips(db, buses, routes, drivers, schedules, count=40)

        # Step 8: Create payments
        payments = await create_payments(db, users, count=35)

        # Step 9: Create tickets
        tickets = await create_tickets(db, payments, routes, bus_stops, count=40)

        # Step 10: Create feedback
        feedback = await create_feedback(db, users, trips, buses, count=25)

        # Step 11: Create incidents
        incidents = await create_incidents(db, users, buses, routes, bus_stops, count=15)

        # Step 12: Create notifications
        notifications = await create_notifications(db, users, count=40)

        # Step 13: Create notification settings
        notification_settings = await create_notification_settings(db, users)

        # Step 14: Create attendance records (2 months of data)
        attendance_records = await create_attendance(db, users, months=2)

        # Step 15: Create approval requests
        approval_requests = await create_approval_requests(db, count=10)

        # Step 16: Create conversations and messages
        conversations, messages = await create_conversations_and_messages(db, users, count=20)

        # Step 17: Create reallocation requests
        reallocation_requests = await create_reallocation_requests(db, users, buses, routes, count=12)

        # Step 18: Create overcrowding reports
        overcrowding_reports = await create_overcrowding_reports(db, users, buses, routes, bus_stops, count=10)

        print("\n" + "="*60)
        print("🎉 DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("="*60)

        # Print summary
        print(f"\n📊 SEEDING SUMMARY:")
        print(f"   🚏 Bus Stops: {len(bus_stops)} (from CSV)")
        print(f"   🛣️ Routes: {len(routes)} (CSV: {len(routes_csv)}, Mock: {len(additional_routes)})")
        print(f"   👥 Users: {len(users)}")
        print(f"   🚌 Buses: {len(buses)}")
        print(f"   📅 Schedules: {len(schedules)}")
        print(f"   🚐 Trips: {len(trips)}")
        print(f"   💳 Payments: {len(payments)}")
        print(f"   🎫 Tickets: {len(tickets)}")
        print(f"   💬 Feedback: {len(feedback)}")
        print(f"   🚨 Incidents: {len(incidents)}")
        print(f"   🔔 Notifications: {len(notifications)}")
        print(f"   ⚙️ Notification Settings: {len(notification_settings)}")
        print(f"   📅 Attendance Records: {len(attendance_records)}")
        print(f"   📝 Approval Requests: {len(approval_requests)}")
        print(f"   💬 Conversations: {len(conversations)}")
        print(f"   📨 Messages: {len(messages)}")
        print(f"   🔄 Reallocation Requests: {len(reallocation_requests)}")
        print(f"   👥 Overcrowding Reports: {len(overcrowding_reports)}")

        total_records = (len(bus_stops) + len(users) + len(buses) + len(routes) +
                        len(schedules) + len(trips) + len(payments) + len(tickets) +
                        len(feedback) + len(incidents) + len(notifications) +
                        len(notification_settings) + len(attendance_records) +
                        len(approval_requests) + len(conversations) +
                        len(messages) + len(reallocation_requests) + len(overcrowding_reports))

        print(f"\n🎯 TOTAL RECORDS CREATED: {total_records}")
        print("\n✨ Your GuzoSync database is now ready for testing with realistic data!")
        print("🔑 Test user credentials: test_[role]@guzosync.com / Test123!")

    except Exception as e:
        print(f"❌ An error occurred during seeding: {str(e)}")
        raise
    finally:
        # Close the connection
        client.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())
