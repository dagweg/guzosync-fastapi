#!/usr/bin/env python
"""
Initialize GuzoSync database with mock data using API endpoints.

This script creates sample data by calling the application's API endpoints,
ensuring all validation, data transformation, and business logic is properly applied.

Run this script with: python init_db_api.py
"""

import os
import asyncio
import argparse
import random
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from faker import Faker

# Configure faker
fake = Faker()

# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = 30

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
TICKET_TYPES = ["SINGLE_TRIP", "ROUND_TRIP", "DAILY_PASS", "WEEKLY_PASS", "MONTHLY_PASS"]

# Addis Ababa area coordinates (latitude, longitude bounds)
ADDIS_ABABA_BOUNDS = {
    "lat_min": 8.9,
    "lat_max": 9.1,
    "lon_min": 38.7,
    "lon_max": 38.9
}


def random_location():
    """Generate a random location in Addis Ababa area."""
    return {
        "latitude": random.uniform(ADDIS_ABABA_BOUNDS["lat_min"], ADDIS_ABABA_BOUNDS["lat_max"]),
        "longitude": random.uniform(ADDIS_ABABA_BOUNDS["lon_min"], ADDIS_ABABA_BOUNDS["lon_max"])
    }


class APIClient:
    """HTTP client for making API calls using httpx."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        self.access_token: Optional[str] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to the API."""
        if self.client is None:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers()
        
        response = await self.client.post(url, json=data, headers=headers)
        
        if response.status_code >= 400:
            print(f"❌ POST {endpoint} failed with status {response.status_code}")
            print(f"Response: {response.text}")
            raise httpx.HTTPStatusError(
                message=f"HTTP {response.status_code}: {response.text}",
                request=response.request,
                response=response
            )
        
        return response.json() if response.text else {}
    
    async def login(self, email: str, password: str) -> bool:
        """Login and store access token."""
        try:
            response = await self.post("/api/accounts/login", {
                "email": email,
                "password": password
            })
            self.access_token = response.get("access_token")
            return self.access_token is not None
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False


async def create_admin_user(client: APIClient) -> Dict[str, Any]:
    """Create admin user if it doesn't exist."""
    print("🔧 Creating admin user...")
    
    admin_data = {
        "first_name": "System",
        "last_name": "Admin",
        "email": "admin@guzosync.com",
        "password": "Admin123!",
        "phone_number": "+251911000001",
        "role": "CONTROL_ADMIN"
    }
    try:
        response = await client.post("/api/accounts/register", admin_data)
        print(f"✅ Admin user created: {response['email']}")
        return response
    except httpx.HTTPStatusError as e:
        if "already exists" in str(e.response.text).lower():
            print("ℹ️ Admin user already exists")
            return admin_data
        else:
            raise


async def create_users(client: APIClient, count: int = 20) -> List[Dict[str, Any]]:
    """Create mock users using API endpoints."""
    print(f"👥 Creating {count} users...")
    users = []
    
    # Create different types of users
    for i in range(count):
        role = random.choice(USER_ROLES)
        
        # Generate more PASSENGER roles than others
        if i < count * 0.7:
            role = "PASSENGER"
        
        user_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "password": "Password123!",
            "phone_number": fake.phone_number(),
            "role": role
        }
        
        try:
            if role in ["BUS_DRIVER", "QUEUE_REGULATOR"]:
                # Use control center endpoint for staff
                if not client.access_token:
                    continue  # Skip if not logged in as admin
                
                response = await client.post("/api/control-center/personnel/register", user_data)
            else:
                # Use regular registration for passengers and admin
                response = await client.post("/api/accounts/register", user_data)
            
            users.append(response)
            print(f"✅ Created {role} user: {response.get('email', 'Unknown')}")
        
        except Exception as e:
            print(f"❌ Failed to create user {user_data['email']}: {e}")
            continue
    
    # Create test users with predictable credentials
    test_users = []
    for role in USER_ROLES:
        test_user_data = {
            "first_name": "Test",
            "last_name": role.capitalize(),
            "email": f"test_{role.lower()}@guzosync.com",
            "password": "Test123!",
            "phone_number": "+251911000000",
            "role": role
        }
        
        try:
            if role in ["BUS_DRIVER", "QUEUE_REGULATOR"] and client.access_token:
                response = await client.post("/api/control-center/personnel/register", test_user_data)
            else:
                response = await client.post("/api/accounts/register", test_user_data)
            
            test_users.append(response)
            print(f"✅ Created test {role} user: {response.get('email', 'Unknown')}")
        
        except Exception as e:
            print(f"⚠️ Test user {test_user_data['email']} might already exist: {e}")
            continue
    
    users.extend(test_users)
    print(f"📊 Total users created: {len(users)}")
    return users


async def create_bus_stops(client: APIClient, count: int = 15) -> List[Dict[str, Any]]:
    """Create mock bus stops using API endpoints."""
    print(f"🚏 Creating {count} bus stops...")
    bus_stops = []
    
    # Use common names for bus stops in Addis Ababa
    common_stops = [
        "Megenagna", "Bole", "Mexico Square", "Piazza", "Lebu",
        "CMC", "Ayat", "Tor Hailoch", "Lideta", "Kazanchis",
        "Stadium", "Meskel Square", "Kaliti", "Ayer Tena", "Saris",
        "Bethel", "Jemo", "Shiro Meda", "Wingate", "Gotera",
        "Lancha", "Gerji", "Hayahulet", "Haya Arat", "Teklehaimanot"
    ]
    
    for i in range(count):
        name = common_stops[i % len(common_stops)]
        if i >= len(common_stops):
            name = f"{name} {i - len(common_stops) + 1}"
        
        bus_stop_data = {
            "name": name,
            "location": random_location(),
            "capacity": random.randint(20, 100),
            "is_active": random.random() > 0.1
        }
        
        try:
            response = await client.post("/api/buses/stops", bus_stop_data)
            bus_stops.append(response)
            print(f"✅ Created bus stop: {response.get('name', 'Unknown')}")
        
        except Exception as e:
            print(f"❌ Failed to create bus stop {bus_stop_data['name']}: {e}")
            continue
    
    print(f"📊 Total bus stops created: {len(bus_stops)}")
    return bus_stops


async def create_routes(client: APIClient, bus_stops: List[Dict[str, Any]], count: int = 8) -> List[Dict[str, Any]]:
    """Create mock routes using API endpoints."""
    print(f"🛣️ Creating {count} routes...")
    routes: List[Dict[str, Any]] = []
    
    # Common route names in Addis Ababa
    route_names = [
        "Megenagna-Bole", "Mexico-Lebu", "Piazza-Mexico", "Stadium-CMC",
        "Ayat-Tor Hailoch", "Jemo-Megenagna", "Kaliti-Wingate", "Saris-Bethel",
        "Meskel Square-Ayat", "Kazanchis-Ayer Tena"
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
        
        route_data = {
            "name": route_name,
            "description": f"Route connecting {num_stops} destinations",
            "stop_ids": selected_stops,
            "total_distance": round(random.uniform(5.0, 30.0), 2),
            "estimated_duration": round(random.uniform(20.0, 90.0), 2),
            "is_active": True
        }
        
        try:
            response = await client.post("/api/routes/", route_data)
            routes.append(response)
            print(f"✅ Created route: {response.get('name', 'Unknown')}")
        
        except Exception as e:
            print(f"❌ Failed to create route {route_data['name']}: {e}")
            continue
    
    print(f"📊 Total routes created: {len(routes)}")
    return routes


async def create_buses(client: APIClient, count: int = 12) -> List[Dict[str, Any]]:
    """Create mock buses using API endpoints."""
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
        
        bus_data = {
            "license_plate": f"AA-{random.randint(1000, 9999)}",
            "bus_type": bus_type,
            "capacity": capacity,
            "bus_status": random.choice(BUS_STATUS),
            "manufacture_year": random.randint(2010, 2023),
            "bus_model": random.choice(["Volvo 7900", "Mercedes-Benz Citaro", "MAN Lion's City", "Scania Citywide"])
        }
        
        try:
            response = await client.post("/api/buses/", bus_data)
            buses.append(response)
            print(f"✅ Created bus: {response.get('license_plate', 'Unknown')}")
        
        except Exception as e:
            print(f"❌ Failed to create bus {bus_data['license_plate']}: {e}")
            continue
    
    print(f"📊 Total buses created: {len(buses)}")
    return buses


async def create_payments_and_tickets(client: APIClient, users: List[Dict[str, Any]], 
                                     routes: List[Dict[str, Any]], count: int = 20) -> List[Dict[str, Any]]:
    """Create mock payments and tickets using API endpoints."""
    print(f"💳 Creating {count} payments and tickets...")
    payments: List[Dict[str, Any]] = []
    
    # Get passenger users only
    passengers = [user for user in users if user.get("role") == "PASSENGER"]
    if not passengers:
        print("⚠️ No passenger users available to create payments")
        return payments
    
    if not routes:
        print("⚠️ No routes available to create tickets")
        return payments
    
    for i in range(count):
        passenger = random.choice(passengers)
        route = random.choice(routes)
          # Login as the passenger to create payment
        passenger_client = APIClient(client.base_url, client.timeout)
        passenger_client.client = client.client
        
        # Use test password for passengers
        login_success = await passenger_client.login(passenger["email"], "Password123!")
        if not login_success:
            print(f"⚠️ Could not login as passenger {passenger['email']}")
            continue
        
        payment_data = {
            "amount": random.choice([15, 25, 50, 100, 200]),
            "payment_method": random.choice(PAYMENT_METHODS),
            "mobile_number": passenger.get("phone_number", "+251911000000"),
            "ticket_type": random.choice(TICKET_TYPES),
            "origin_stop_id": random.choice(route["stop_ids"]),
            "destination_stop_id": random.choice(route["stop_ids"]),
            "route_id": route["id"],
            "description": f"Bus ticket for {route['name']}",
            "return_url": f"{client.base_url}/payment/success"
        }
        
        try:
            response = await passenger_client.post("/api/payments/initiate", payment_data)
            payments.append(response)
            print(f"✅ Created payment: {response.get('tx_ref', 'Unknown')}")
        
        except Exception as e:
            print(f"❌ Failed to create payment for {passenger['email']}: {e}")
            continue
    
    print(f"📊 Total payments created: {len(payments)}")
    return payments


async def populate_db_via_api():
    """Main function to populate the database using API endpoints."""
    parser = argparse.ArgumentParser(description='Initialize database with mock data via API.')
    parser.add_argument('--api-url', default=API_BASE_URL, help='Base URL for API endpoints')
    parser.add_argument('--timeout', type=int, default=API_TIMEOUT, help='Request timeout in seconds')
    args = parser.parse_args()
    
    print("🚀 Starting database initialization via API endpoints...")
    print(f"📡 API Base URL: {args.api_url}")
    
    async with APIClient(args.api_url, args.timeout) as client:
        try:
            # Step 1: Create admin user
            admin_user = await create_admin_user(client)
            
            # Step 2: Login as admin
            login_success = await client.login("admin@guzosync.com", "Admin123!")
            if not login_success:
                print("❌ Failed to login as admin. Cannot create staff users.")
                return
            
            print("✅ Logged in as admin")
            
            # Step 3: Create users
            users = await create_users(client, count=20)
            
            # Step 4: Create bus stops
            bus_stops = await create_bus_stops(client, count=15)
            
            # Step 5: Create routes
            routes = await create_routes(client, bus_stops, count=8)
            
            # Step 6: Create buses
            buses = await create_buses(client, count=12)
            
            # Step 7: Create payments and tickets
            payments = await create_payments_and_tickets(client, users, routes, count=20)
            
            print("\n🎉 Database initialization completed successfully!")
            print(f"📊 Summary:")
            print(f"   👥 Users: {len(users)}")
            print(f"   🚏 Bus Stops: {len(bus_stops)}")
            print(f"   🛣️ Routes: {len(routes)}")
            print(f"   🚌 Buses: {len(buses)}")
            print(f"   💳 Payments: {len(payments)}")
            
        except Exception as e:
            print(f"❌ An error occurred: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(populate_db_via_api())
