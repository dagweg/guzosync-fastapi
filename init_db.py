#!/usr/bin/env python
"""
Initialize GuzoSync database with mock data.

This script connects to MongoDB and creates sample data for all collections
required by the application, including users, buses, routes, bus stops, payments, etc.

Run this script with: python init_db.py
"""

import os
import asyncio
import argparse
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
from motor.motor_asyncio import AsyncIOMotorClient
from bson import UuidRepresentation
from dotenv import load_dotenv
from passlib.context import CryptContext
import uuid
from faker import Faker

# Configure faker
fake = Faker()

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_url = os.getenv("MONGODB_URL")
database_name = os.getenv("DATABASE_NAME")

# User roles
USER_ROLES = [
    "PASSENGER",
    "BUS_DRIVER",
    "QUEUE_REGULATOR",
    "CONTROL_STAFF",
    "CONTROL_ADMIN"
]

# Bus types and status
BUS_TYPES = ["STANDARD", "ARTICULATED", "MINIBUS"]
BUS_STATUS = ["OPERATIONAL", "MAINTENANCE", "BREAKDOWN", "IDLE"]

# Payment methods and status
PAYMENT_METHODS = ["telebirr", "mpesa", "cbebirr", "ebirr", "enat_bank"]
PAYMENT_STATUS = ["PENDING", "COMPLETED", "FAILED", "CANCELLED", "REFUNDED"]

# Ticket types and status
TICKET_TYPES = ["SINGLE_TRIP", "ROUND_TRIP", "DAILY_PASS", "WEEKLY_PASS", "MONTHLY_PASS"]
TICKET_STATUS = ["ACTIVE", "USED", "EXPIRED", "CANCELLED"]

# Trip status
TRIP_STATUS = ["SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "DELAYED"]

# Notification types
NOTIFICATION_TYPES = [
    "ALERT", "UPDATE", "PROMOTION", "REMINDER", "GENERAL", 
    "TRIP_UPDATE", "SERVICE_ALERT"
]

# Incident severity
INCIDENT_SEVERITY = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Addis Ababa area coordinates (latitude, longitude bounds)
ADDIS_ABABA_BOUNDS = {
    "lat_min": 8.9,
    "lat_max": 9.1,
    "lon_min": 38.7,
    "lon_max": 38.9
}


def generate_uuid():
    """Generate a random UUID."""
    return uuid.uuid4()


def hash_password(password: str) -> str:
    """Hash a password."""
    hashed_password: str = pwd_context.hash(password)
    return hashed_password


def random_location():
    """Generate a random location in Addis Ababa area."""
    return {
        "latitude": random.uniform(ADDIS_ABABA_BOUNDS["lat_min"], ADDIS_ABABA_BOUNDS["lat_max"]),
        "longitude": random.uniform(ADDIS_ABABA_BOUNDS["lon_min"], ADDIS_ABABA_BOUNDS["lon_max"])
    }


def random_datetime(start_days=-30, end_days=1):
    """Generate a random datetime between start_days and end_days from now."""
    start = datetime.utcnow() + timedelta(days=start_days)
    end = datetime.utcnow() + timedelta(days=end_days)
    return start + (end - start) * random.random()


def model_to_mongo_doc(model_dict):
    """Convert a model dictionary to a MongoDB document."""
    doc = model_dict.copy()
    if 'id' in doc:
        doc['_id'] = doc.pop('id')
    return doc


async def drop_collections(db):
    """Drop existing collections to start fresh."""
    collections = await db.list_collection_names()
    for collection in collections:
        await db[collection].drop()
    print("Dropped existing collections")


async def create_users(db, count=20):
    """Create mock users."""
    default_password = hash_password("password123")
    
    print(f"Creating {count} users...")
    users = []

    # Create users with different roles
    for i in range(count):
        role = random.choice(USER_ROLES)
        
        # Generate more PASSENGER roles than others
        if i < count * 0.7:
            role = "PASSENGER"
        
        user = {
            "id": generate_uuid(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "password": default_password,
            "role": role,
            "phone_number": fake.phone_number(),
            "profile_image": None if random.random() > 0.3 else f"https://randomuser.me/api/portraits/{random.choice(['men', 'women'])}/{random.randint(1, 99)}.jpg",
            "created_at": random_datetime(-90, -1),
            "updated_at": random_datetime(-30, 0),
            "is_active": random.random() > 0.1,
            "preferred_language": random.choice(["en", "am", None])
        }
        users.append(model_to_mongo_doc(user))
    
    # Ensure at least one of each role exists
    for role in USER_ROLES:
        if not any(u['role'] == role for u in users):
            user = {
                "id": generate_uuid(),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": f"{role.lower()}@example.com",
                "password": default_password,
                "role": role,
                "phone_number": fake.phone_number(),
                "profile_image": None,
                "created_at": random_datetime(-90, -1),
                "updated_at": random_datetime(-30, 0),
                "is_active": True,
                "preferred_language": "en"
            }
            users.append(model_to_mongo_doc(user))
    
    # Add a test user for each role with predictable credentials
    test_users = []
    for role in USER_ROLES:
        test_user = {
            "id": generate_uuid(),
            "first_name": f"Test",
            "last_name": f"{role.capitalize()}",
            "email": f"test_{role.lower()}@guzosync.com",
            "password": hash_password("Test123!"),
            "role": role,
            "phone_number": "123456789",
            "profile_image": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "preferred_language": "en"
        }
        test_users.append(model_to_mongo_doc(test_user))
    
    users.extend(test_users)
    result = await db.users.insert_many(users)
    print(f"Created {len(result.inserted_ids)} users")
    return users


async def create_bus_stops(db, count=15):
    """Create mock bus stops."""
    print(f"Creating {count} bus stops...")
    bus_stops = []
    
    # Use common names for bus stops in Addis Ababa
    common_stops = [
        "Megenagna", "Bole", "Mexico Square", "Piazza", "Lebu",
        "CMC", "Ayat", "Tor Hailoch", "Lideta", "Kazanchis",
        "Stadium", "Meskel Square", "Kaliti", "Ayer Tena", "Saris",
        "Bethel", "Jemo", "Shiro Meda", "Wingate", "Gotera",
        "Lancha", "Gerji", "Hayahulet", "Haya Arat", "Teklehaimanot"
    ]
    
    # Use names from the list first, then generate random ones if needed
    for i in range(count):
        name = common_stops[i % len(common_stops)]
        if i >= len(common_stops):
            name = f"{name} {i - len(common_stops) + 1}"
            
        bus_stop = {
            "id": generate_uuid(),
            "name": name,
            "location": random_location(),
            "capacity": random.randint(20, 100),
            "is_active": random.random() > 0.1,
            "created_at": random_datetime(-180, -30),
            "updated_at": random_datetime(-30, -1)
        }
        bus_stops.append(model_to_mongo_doc(bus_stop))
    
    result = await db.bus_stops.insert_many(bus_stops)
    print(f"Created {len(result.inserted_ids)} bus stops")
    return bus_stops


async def create_routes(db, bus_stops, count=8):
    """Create mock routes using existing bus stops."""
    print(f"Creating {count} routes...")
    routes = []
    
    # Common route names in Addis Ababa
    route_names = [
        "Megenagna-Bole", "Mexico-Lebu", "Piazza-Mexico", "Stadium-CMC",
        "Ayat-Tor Hailoch", "Jemo-Megenagna", "Kaliti-Wingate", "Saris-Bethel",
        "Meskel Square-Ayat", "Kazanchis-Ayer Tena"
    ]
    
    bus_stop_ids = [stop["_id"] for stop in bus_stops]
    
    for i in range(count):
        # Select 3-8 random stops for each route
        num_stops = random.randint(3, 8)
        selected_stops = random.sample(bus_stop_ids, num_stops)
        
        route_name = route_names[i % len(route_names)]
        if i >= len(route_names):
            route_name = f"Route {i + 1}"
            
        route = {
            "id": generate_uuid(),
            "name": route_name,
            "description": f"Route connecting {num_stops} destinations",
            "stop_ids": selected_stops,
            "total_distance": random.uniform(5, 30),  # km
            "estimated_duration": random.uniform(20, 90),  # minutes
            "created_at": random_datetime(-180, -30),
            "updated_at": random_datetime(-30, -1)
        }
        routes.append(model_to_mongo_doc(route))
    
    result = await db.routes.insert_many(routes)
    print(f"Created {len(result.inserted_ids)} routes")
    return routes


async def create_buses(db, count=12):
    """Create mock buses."""
    print(f"Creating {count} buses...")
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
            "bus_status": random.choice(BUS_STATUS),
            "manufacture_year": random.randint(2010, 2023),
            "bus_model": random.choice(["Volvo 7900", "Mercedes-Benz Citaro", "MAN Lion's City", "Scania Citywide"]),
            "created_at": random_datetime(-180, -30),
            "updated_at": random_datetime(-30, -1)
        }
        buses.append(model_to_mongo_doc(bus))
    
    result = await db.buses.insert_many(buses)
    print(f"Created {len(result.inserted_ids)} buses")
    return buses


async def create_schedules(db, routes, buses, drivers, count=15):
    """Create mock schedules."""
    print(f"Creating {count} schedules...")
    schedules = []
    
    driver_ids = [driver["_id"] for driver in drivers if driver["role"] == "BUS_DRIVER"]
    bus_ids = [bus["_id"] for bus in buses]
    route_ids = [route["_id"] for route in routes]
    
    # Different schedule patterns
    schedule_patterns = ["DAILY", "WEEKDAY", "WEEKEND", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    
    for i in range(count):
        # Generate departure times (24-hour format)
        num_departures = random.randint(3, 10)
        departure_times = []
        
        start_hour = random.randint(5, 9)  # Start between 5 AM and 9 AM
        for j in range(num_departures):
            hour = (start_hour + j * random.randint(1, 3)) % 24
            minute = random.choice([0, 15, 30, 45])
            departure_times.append(f"{hour:02d}:{minute:02d}")
        
        schedule = {
            "id": generate_uuid(),
            "route_id": random.choice(route_ids),
            "schedule_pattern": random.choice(schedule_patterns),
            "departure_times": departure_times,
            "assigned_bus_id": random.choice(bus_ids) if random.random() > 0.2 else None,
            "assigned_driver_id": random.choice(driver_ids) if random.random() > 0.2 else None,
            "valid_from": datetime.utcnow() - timedelta(days=random.randint(1, 90)),
            "valid_until": datetime.utcnow() + timedelta(days=random.randint(30, 365)) if random.random() > 0.2 else None,
            "is_active": random.random() > 0.1,
            "created_at": random_datetime(-90, -30),
            "updated_at": random_datetime(-30, -1)
        }
        schedules.append(model_to_mongo_doc(schedule))
    
    result = await db.schedules.insert_many(schedules)
    print(f"Created {len(result.inserted_ids)} schedules")
    return schedules


async def create_trips(db, buses, routes, drivers, schedules, count=30):
    """Create mock trips."""
    print(f"Creating {count} trips...")
    trips = []
    
    driver_ids = [driver["_id"] for driver in drivers if driver["role"] == "BUS_DRIVER"]
    bus_ids = [bus["_id"] for bus in buses]
    route_ids = [route["_id"] for route in routes]
    schedule_ids = [schedule["_id"] for schedule in schedules]
    
    for i in range(count):
        # Generate trips with different statuses
        status = random.choice(TRIP_STATUS)
        
        # Based on status, set appropriate times
        actual_departure = None
        actual_arrival = None
        estimated_arrival = None
        
        if status in ["IN_PROGRESS", "COMPLETED"]:
            actual_departure = random_datetime(-1, 0)
            
            if status == "COMPLETED":
                actual_arrival = actual_departure + timedelta(hours=random.uniform(0.5, 2))
            else:  # IN_PROGRESS
                estimated_arrival = datetime.utcnow() + timedelta(minutes=random.randint(5, 60))
        
        elif status == "SCHEDULED":
            estimated_arrival = datetime.utcnow() + timedelta(hours=random.randint(1, 24))
        
        trip = {
            "id": generate_uuid(),
            "bus_id": random.choice(bus_ids),
            "route_id": random.choice(route_ids),
            "driver_id": random.choice(driver_ids) if random.random() > 0.1 else None,
            "schedule_id": random.choice(schedule_ids) if random.random() > 0.3 else None,
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
    
    result = await db.trips.insert_many(trips)
    print(f"Created {len(result.inserted_ids)} trips")
    return trips


async def create_payments(db, users, count=40):
    """Create mock payments."""
    print(f"Creating {count} payments...")
    payments = []
    
    passenger_ids = [user["_id"] for user in users if user["role"] == "PASSENGER"]
    
    # Generate transaction references
    for i in range(count):
        passenger = random.choice(users)
        amount = random.choice([15, 25, 50, 100, 200, 300])  # Common fare amounts in ETB
        status = random.choices(
            PAYMENT_STATUS, 
            weights=[0.1, 0.7, 0.1, 0.05, 0.05],  # More completed payments than others
            k=1
        )[0]
        
        payment = {
            "id": generate_uuid(),
            "tx_ref": f"GS-{str(fake.uuid4())[:8].upper()}",
            "amount": amount,
            "currency": "ETB",
            "payment_method": random.choice(PAYMENT_METHODS),
            "mobile_number": passenger["phone_number"],
            "customer_id": passenger["_id"],
            "customer_email": passenger["email"],
            "customer_first_name": passenger["first_name"],
            "customer_last_name": passenger["last_name"],
            "status": status,
            "chapa_tx_ref": f"CHAPA-{str(fake.uuid4())[:8].upper()}" if status == "COMPLETED" else None,
            "created_at": random_datetime(-30, 0),
            "updated_at": random_datetime(-2, 0)
        }
        payments.append(model_to_mongo_doc(payment))
    
    result = await db.payments.insert_many(payments)
    print(f"Created {len(result.inserted_ids)} payments")
    return payments


async def create_tickets(db, payments, users, trips, count=35):
    """Create mock tickets based on payments."""
    print(f"Creating {count} tickets...")
    tickets = []
    
    completed_payments = [p for p in payments if p["status"] == "COMPLETED"]
    passenger_ids = [user["_id"] for user in users if user["role"] == "PASSENGER"]
    trip_ids = [trip["_id"] for trip in trips]
    
    # Generate tickets
    for i in range(count):
        # Use a completed payment if available, otherwise create a ticket without payment
        if i < len(completed_payments):
            payment = completed_payments[i]
            passenger_id = payment["customer_id"]
        else:
            payment = None
            passenger_id = random.choice(passenger_ids)
        
        status = random.choice(TICKET_STATUS)
        ticket_type = random.choice(TICKET_TYPES)
        
        # Set validity based on ticket type
        valid_from = random_datetime(-30, 0)
        valid_until = None
        
        if ticket_type == "SINGLE_TRIP":
            valid_until = valid_from + timedelta(days=1)
        elif ticket_type == "ROUND_TRIP":
            valid_until = valid_from + timedelta(days=1)
        elif ticket_type == "DAILY_PASS":
            valid_until = valid_from + timedelta(days=1)
        elif ticket_type == "WEEKLY_PASS":
            valid_until = valid_from + timedelta(days=7)
        elif ticket_type == "MONTHLY_PASS":
            valid_until = valid_from + timedelta(days=30)
        
        ticket = {
            "id": generate_uuid(),
            "passenger_id": passenger_id,
            "payment_id": payment["_id"] if payment else None,
            "ticket_type": ticket_type,
            "status": status,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "linked_trip_ids": [random.choice(trip_ids)] if random.random() > 0.5 else [],
            "created_at": valid_from,
            "updated_at": random_datetime(-5, 0)
        }
        tickets.append(model_to_mongo_doc(ticket))
    
    result = await db.tickets.insert_many(tickets)
    print(f"Created {len(result.inserted_ids)} tickets")
    return tickets


async def create_feedback(db, users, trips, buses, count=25):
    """Create mock feedback."""
    print(f"Creating {count} feedback items...")
    feedback_items = []
    
    passenger_ids = [user["_id"] for user in users if user["role"] == "PASSENGER"]
    trip_ids = [trip["_id"] for trip in trips]
    bus_ids = [bus["_id"] for bus in buses]
    
    # Common feedback templates
    feedback_templates = [
        "The bus was {adj}. {comment}",
        "Driver was {adj}. {comment}",
        "Trip was {adj} overall. {comment}",
        "Bus arrived {adj}. {comment}",
        "{adj} experience. {comment}"
    ]
    
    positive_adjs = ["excellent", "comfortable", "clean", "on time", "well-maintained", "pleasant"]
    negative_adjs = ["delayed", "uncomfortable", "dirty", "late", "crowded", "rough"]
    
    positive_comments = [
        "Would recommend.",
        "Thank you for the service.",
        "Very satisfied.",
        "Will use again.",
        "Great service."
    ]
    
    negative_comments = [
        "Needs improvement.",
        "Please address this issue.",
        "Not satisfied.",
        "Will think twice before using again.",
        "Service needs to be better."
    ]
    
    for i in range(count):
        # Determine if this is positive or negative feedback
        is_positive = random.random() > 0.3
        
        rating = random.randint(4, 5) if is_positive else random.randint(1, 3)
        adj = random.choice(positive_adjs) if is_positive else random.choice(negative_adjs)
        comment = random.choice(positive_comments) if is_positive else random.choice(negative_comments)
        
        content = random.choice(feedback_templates).format(adj=adj, comment=comment)
        
        # Randomly select if this feedback is related to a trip or bus
        has_trip = random.random() > 0.3
        has_bus = random.random() > 0.5
        
        feedback = {
            "id": generate_uuid(),
            "submitted_by_user_id": random.choice(passenger_ids),
            "content": content,
            "rating": rating,
            "related_trip_id": random.choice(trip_ids) if has_trip else None,
            "related_bus_id": random.choice(bus_ids) if has_bus else None,
            "created_at": random_datetime(-90, 0),
            "updated_at": random_datetime(-10, 0)
        }
        feedback_items.append(model_to_mongo_doc(feedback))
    
    result = await db.feedback.insert_many(feedback_items)
    print(f"Created {len(result.inserted_ids)} feedback items")
    return feedback_items


async def create_incidents(db, users, buses, routes, count=15):
    """Create mock incidents."""
    print(f"Creating {count} incidents...")
    incidents = []
    
    user_ids = [user["_id"] for user in users]
    bus_ids = [bus["_id"] for bus in buses]
    route_ids = [route["_id"] for route in routes]
    
    # Common incident descriptions
    incident_templates = [
        "Bus breakdown at {location}",
        "Traffic jam on {route_name}",
        "Accident near {location}",
        "Road construction causing delays on {route_name}",
        "Bus overcrowding issue",
        "Passenger medical emergency",
        "Missing scheduled stop at {location}",
        "Route diversion due to {reason}",
        "Driver reported {issue}",
        "Safety concern at {location}"
    ]
    
    locations = [
        "Megenagna", "Bole", "Mexico Square", "Piazza", "Meskel Square",
        "Stadium", "Jemo", "Ayat", "CMC", "Lebu"
    ]
    
    reasons = [
        "road construction", "traffic accident", "protest", "flooding",
        "police checkpoint", "fallen tree", "power line issue"
    ]
    
    issues = [
        "brake problem", "engine issue", "fuel leak", "flat tire",
        "electrical problem", "steering issue", "transmission failure"
    ]
    
    for i in range(count):
        # Generate a random description
        template = random.choice(incident_templates)
        description = template.format(
            location=random.choice(locations),
            route_name=f"Route {random.randint(1, 10)}",
            reason=random.choice(reasons),
            issue=random.choice(issues)
        )
        
        # Higher severity issues are less common
        severity_weights = [0.4, 0.3, 0.2, 0.1]  # LOW to CRITICAL
        severity = random.choices(INCIDENT_SEVERITY, weights=severity_weights, k=1)[0]
        
        # Resolved status depends on severity and age
        created_date = random_datetime(-30, 0)
        is_resolved = random.random() > 0.5
        
        # Critical incidents are less likely to be resolved
        if severity == "CRITICAL":
            is_resolved = random.random() > 0.7
        
        incident = {
            "id": generate_uuid(),
            "reported_by_user_id": random.choice(user_ids),
            "description": description,
            "location": random_location(),
            "related_bus_id": random.choice(bus_ids) if random.random() > 0.2 else None,
            "related_route_id": random.choice(route_ids) if random.random() > 0.2 else None,
            "is_resolved": is_resolved,
            "resolution_notes": fake.paragraph() if is_resolved else None,
            "severity": severity,
            "created_at": created_date,
            "updated_at": created_date + timedelta(days=random.randint(1, 5)) if is_resolved else created_date
        }
        incidents.append(model_to_mongo_doc(incident))
    
    result = await db.incidents.insert_many(incidents)
    print(f"Created {len(result.inserted_ids)} incidents")
    return incidents


async def create_notifications(db, users, count=50):
    """Create mock notifications for users."""
    print(f"Creating {count} notifications...")
    notifications = []
    
    # Get all user IDs
    user_ids = [user["_id"] for user in users]
    
    # Common notification templates
    notification_templates = {
        "ALERT": [
            "Service disruption on your route",
            "Urgent: Bus {bus_number} delayed",
            "Safety alert: Route changes ahead"
        ],
        "UPDATE": [
            "Schedule update for Route {route_number}",
            "Your trip details have been updated",
            "New stop added to your regular route"
        ],
        "PROMOTION": [
            "Special discount on monthly passes",
            "Earn bonus points this weekend",
            "Invite friends and get free rides"
        ],
        "REMINDER": [
            "Your pass expires tomorrow",
            "Don't forget to rate your recent trip",
            "Complete your profile for better service"
        ],
        "GENERAL": [
            "Welcome to GuzoSync",
            "Thank you for using our service",
            "System maintenance scheduled"
        ],
        "TRIP_UPDATE": [
            "Your bus will arrive in {minutes} minutes",
            "Your bus is approaching {stop_name}",
            "Your trip has been completed"
        ],
        "SERVICE_ALERT": [
            "Route {route_number} is experiencing delays",
            "Service suspended on {route_name}",
            "Alternative routes available for your journey"
        ]
    }
    
    for i in range(count):
        # Select a random user
        user_id = random.choice(user_ids)
        
        # Select notification type and template
        notification_type = random.choice(NOTIFICATION_TYPES)
        title_template = random.choice(notification_templates[notification_type])
        
        # Fill in template variables
        title = title_template.format(
            bus_number=f"AA-{random.randint(1000, 9999)}",
            route_number=random.randint(1, 10),
            route_name=f"Route {random.randint(1, 10)}",
            stop_name=random.choice(["Megenagna", "Bole", "Mexico", "Piazza", "Stadium"]),
            minutes=random.randint(2, 15)
        )
        
        # Generate message based on title
        message = fake.paragraph()
        
        # Create notification document
        notification = {
            "id": generate_uuid(),
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "is_read": random.random() > 0.6,  # 40% unread
            "created_at": random_datetime(-30, 0),
            "updated_at": random_datetime(-7, 0)
        }
        
        # Add related entity for some notifications
        if random.random() > 0.5:
            entity_types = ["trip", "bus", "route", "payment"]
            notification["related_entity"] = {
                "entity_type": random.choice(entity_types),
                "entity_id": str(generate_uuid())
            }
            
        notifications.append(model_to_mongo_doc(notification))
    
    result = await db.notifications.insert_many(notifications)
    print(f"Created {len(result.inserted_ids)} notifications")
    return notifications


async def create_notification_settings(db, users):
    """Create notification settings for users."""
    print(f"Creating notification settings for users...")
    settings = []
    
    for user in users:
        # Most users prefer notifications enabled
        email_enabled = random.random() > 0.2
        
        setting = {
            "id": generate_uuid(),
            "user_id": user["_id"],
            "email_enabled": email_enabled,
            "created_at": user["created_at"],
            "updated_at": random_datetime(-10, 0)
        }
        settings.append(model_to_mongo_doc(setting))
    
    result = await db.notification_settings.insert_many(settings)
    print(f"Created {len(result.inserted_ids)} notification settings")
    return settings


async def create_attendance_records(db, drivers, regulators, count=40):
    """Create mock attendance records for drivers and regulators."""
    print(f"Creating {count} attendance records...")
    attendance_records = []
    
    driver_ids = [user["_id"] for user in drivers if user["role"] == "BUS_DRIVER"]
    regulator_ids = [user["_id"] for user in regulators if user["role"] == "QUEUE_REGULATOR"]
    
    staff_ids = driver_ids + regulator_ids
    
    for i in range(count):
        staff_id = random.choice(staff_ids)
        
        # Generate clock in and out times
        attendance_date = random_datetime(-30, 0).replace(hour=0, minute=0, second=0, microsecond=0)
        clock_in = attendance_date + timedelta(hours=random.randint(6, 9), minutes=random.randint(0, 59))
        
        # Some might not have clocked out yet
        has_clocked_out = random.random() > 0.2
        clock_out = None
        if has_clocked_out:
            # Clock out 8-12 hours after clock in
            clock_out = clock_in + timedelta(hours=random.randint(8, 12), minutes=random.randint(0, 59))
        
        attendance = {
            "id": generate_uuid(),
            "staff_id": staff_id,
            "date": attendance_date,
            "clock_in": clock_in,
            "clock_out": clock_out,
            "notes": fake.sentence() if random.random() > 0.7 else None,
            "created_at": clock_in,
            "updated_at": clock_out if clock_out else clock_in
        }
        attendance_records.append(model_to_mongo_doc(attendance))
    
    result = await db.attendance.insert_many(attendance_records)
    print(f"Created {len(result.inserted_ids)} attendance records")
    return attendance_records


async def populate_db():
    """Main function to populate the database with mock data."""
    if not mongodb_url or not database_name:
        print("Error: MongoDB configuration not found. Please check your .env file.")
        return
    
    # Connect to MongoDB
    client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_url, uuidRepresentation="pythonLegacy")
    db = client[database_name]
    
    try:
        # Drop existing collections if specified
        parser = argparse.ArgumentParser(description='Initialize database with mock data.')
        parser.add_argument('--drop', action='store_true', help='Drop existing collections before creating mock data')
        args = parser.parse_args()
        
        if args.drop:
            await drop_collections(db)
        
        # Create mock data
        users = await create_users(db)
        bus_stops = await create_bus_stops(db)
        routes = await create_routes(db, bus_stops)
        buses = await create_buses(db)
        
        # Filter users by role
        drivers = [user for user in users if user["role"] == "BUS_DRIVER"]
        regulators = [user for user in users if user["role"] == "QUEUE_REGULATOR"]
        
        # Create schedules with buses and drivers
        schedules = await create_schedules(db, routes, buses, drivers)
        
        # Create trips
        trips = await create_trips(db, buses, routes, drivers, schedules)
        
        # Create payments and tickets
        payments = await create_payments(db, users)
        tickets = await create_tickets(db, payments, users, trips)
        
        # Create feedback and incidents
        feedback = await create_feedback(db, users, trips, buses)
        incidents = await create_incidents(db, users, buses, routes)
        
        # Create notifications and settings
        notifications = await create_notifications(db, users)
        notification_settings = await create_notification_settings(db, users)
        
        # Create attendance records
        attendance = await create_attendance_records(db, drivers, regulators)
        
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Close the MongoDB connection
        client.close()


if __name__ == "__main__":
    asyncio.run(populate_db())
