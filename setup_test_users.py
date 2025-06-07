"""
Setup script to create test users for all roles in the GuzoSync system
Creates: CONTROL_STAFF, PASSENGER, BUS_DRIVER, QUEUE_REGULATOR
(CONTROL_ADMIN already exists)
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000"

def get_admin_token():
    """Get authentication token for admin user"""
    admin_credentials = {
        "email": "admin@example.com",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/accounts/login", json=admin_credentials)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"Failed to get admin token: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting admin token: {str(e)}")
        return None

def create_admin_user():
    """Create a CONTROL_ADMIN user for testing"""
    print("Creating CONTROL_ADMIN user for testing...")
    
    admin_user = {
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@example.com",
        "password": "admin123",
        "role": "CONTROL_ADMIN",
        "phone_number": "+1234567890"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/accounts/register", json=admin_user)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            print("✓ Admin user created successfully!")
            user_data = response.json()
            print(f"   Email: {user_data.get('email')}")
            print(f"   Role: {user_data.get('role')}")
            print(f"   ID: {user_data.get('id')}")
            print("\nYou can now use these credentials to test the approval workflow:")
            print(f"   Email: {admin_user['email']}")
            print(f"   Password: {admin_user['password']}")
        else:
            print("✗ Failed to create admin user")
            response_data = response.json()
            print(f"   Error: {response_data.get('detail', 'Unknown error')}")
            
            if "already exists" in response_data.get('detail', ''):
                print("\n📝 Admin user already exists. You can use these credentials:")
                print(f"   Email: {admin_user['email']}")
                print(f"   Password: {admin_user['password']}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the FastAPI server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")

def create_staff_user():
    """Create a regular CONTROL_STAFF user (bypassing approval for comparison)"""
    print("\nCreating regular CONTROL_STAFF user for comparison...")
    
    staff_user = {
        "first_name": "Staff",
        "last_name": "User", 
        "email": "staff@example.com",
        "password": "staff123",
        "role": "CONTROL_STAFF",
        "phone_number": "+1234567891"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/accounts/register", json=staff_user)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            # This should now create an approval request instead of a user
            response_data = response.json()
            if "PENDING_APPROVAL" in response_data.get("status", ""):
                print("✓ Approval request created successfully!")
                print(f"   Request ID: {response_data.get('request_id')}")
                print("   Status: Pending approval from admin")
            else:
                print("✓ Staff user created directly (old behavior)")
                print(f"   Email: {response_data.get('email')}")
                print(f"   Role: {response_data.get('role')}")
        else:
            print("✗ Failed to create staff user")
            response_data = response.json()
            print(f"   Error: {response_data.get('detail', 'Unknown error')}")
            
            if "already exists" in response_data.get('detail', ''):
                print("\n📝 Staff user already exists. You can use these credentials:")
                print(f"   Email: {staff_user['email']}")
                print(f"   Password: {staff_user['password']}")
            
    except Exception as e:
        print(f"❌ Error creating staff user: {str(e)}")

def create_passenger_user():
    """Create a PASSENGER user for testing"""
    print("\nCreating PASSENGER user for testing...")
    
    passenger_user = {
        "first_name": "John",
        "last_name": "Passenger",
        "email": "passenger@example.com",
        "password": "passenger123",
        "role": "PASSENGER",
        "phone_number": "+1234567892"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/accounts/register", json=passenger_user)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            print("✓ Passenger user created successfully!")
            user_data = response.json()
            print(f"   Email: {user_data.get('email')}")
            print(f"   Role: {user_data.get('role')}")
        else:
            print("✗ Failed to create passenger user")
            response_data = response.json()
            print(f"   Error: {response_data.get('detail', 'Unknown error')}")
            
            if "already exists" in response_data.get('detail', ''):
                print("\n📝 Passenger user already exists. You can use these credentials:")
                print(f"   Email: {passenger_user['email']}")
                print(f"   Password: {passenger_user['password']}")
            
    except Exception as e:
        print(f"❌ Error creating passenger user: {str(e)}")

def create_bus_driver_user():
    """Create a BUS_DRIVER user using control center endpoint"""
    print("\nCreating BUS_DRIVER user via control center...")
    
    # Get admin token
    token = get_admin_token()
    if not token:
        print("❌ Could not get admin token. Make sure admin user exists and server is running.")
        return
    
    driver_user = {
        "first_name": "Mike",
        "last_name": "Driver",
        "email": "driver@example.com",
        "role": "BUS_DRIVER",
        "phone_number": "+1234567893",
        "profile_image": None
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/control-center/personnel/register", 
            json=driver_user,
            headers=headers
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            print("✓ Bus driver user created successfully!")
            user_data = response.json()
            print(f"   Email: {user_data.get('email')}")
            print(f"   Role: {user_data.get('role')}")
            print("   Note: User will receive login credentials via email")
        else:
            print("✗ Failed to create bus driver user")
            response_data = response.json()
            print(f"   Error: {response_data.get('detail', 'Unknown error')}")
            
            if "already exists" in response_data.get('detail', ''):
                print("\n📝 Bus driver user already exists.")
                print("   Email: driver@example.com")
            
    except Exception as e:
        print(f"❌ Error creating bus driver user: {str(e)}")

def create_queue_regulator_user():
    """Create a QUEUE_REGULATOR user using control center endpoint"""
    print("\nCreating QUEUE_REGULATOR user via control center...")
    
    # Get admin token
    token = get_admin_token()
    if not token:
        print("❌ Could not get admin token. Make sure admin user exists and server is running.")
        return
    
    regulator_user = {
        "first_name": "Sarah",
        "last_name": "Regulator",
        "email": "regulator@example.com",
        "role": "QUEUE_REGULATOR",
        "phone_number": "+1234567894",
        "profile_image": None
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/control-center/personnel/register", 
            json=regulator_user,
            headers=headers
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            print("✓ Queue regulator user created successfully!")
            user_data = response.json()
            print(f"   Email: {user_data.get('email')}")
            print(f"   Role: {user_data.get('role')}")
            print("   Note: User will receive login credentials via email")
        else:
            print("✗ Failed to create queue regulator user")
            response_data = response.json()
            print(f"   Error: {response_data.get('detail', 'Unknown error')}")
            
            if "already exists" in response_data.get('detail', ''):
                print("\n📝 Queue regulator user already exists.")
                print("   Email: regulator@example.com")
            
    except Exception as e:
        print(f"❌ Error creating queue regulator user: {str(e)}")

if __name__ == "__main__":
    print("GuzoSync Complete User Setup for Testing")
    print("=" * 45)
    print("Make sure the FastAPI server is running on localhost:8000")
    print()
    
    # Skip admin creation since it already exists
    print("⏭️  Skipping CONTROL_ADMIN creation (already exists)")
    print("   Email: admin@example.com")
    print("   Password: admin123")
    
    # Create all other user types
    create_staff_user()
    create_passenger_user()
    create_bus_driver_user()
    create_queue_regulator_user()
    
    print("\n" + "=" * 45)
    print("🎉 All test users setup complete!")
    print("\nTest User Credentials Summary:")
    print("━" * 35)
    print("1. CONTROL_ADMIN:")
    print("   Email: admin@example.com")
    print("   Password: admin123")
    print("\n2. CONTROL_STAFF:")
    print("   Email: staff@example.com")
    print("   Password: staff123")
    print("\n3. PASSENGER:")
    print("   Email: passenger@example.com")
    print("   Password: passenger123")
    print("\n4. BUS_DRIVER:")
    print("   Email: driver@example.com")
    print("   Password: (sent via email)")
    print("\n5. QUEUE_REGULATOR:")
    print("   Email: regulator@example.com")
    print("   Password: (sent via email)")
    print("━" * 35)
    print("\nYou can now test RBAC and other features with these users!")
