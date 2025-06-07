"""
Test script to verify the new approval workflow APIs
Run this after starting the FastAPI server
"""

import requests
import json
from datetime import datetime

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_registration_workflow():
    """Test the complete approval workflow"""
    print("Testing CONTROL_STAFF Registration and Approval Workflow")
    print("=" * 60)
      # Test data
    test_user = {
        "first_name": "John",
        "last_name": "Doe", 
        "email": f"john.doe.staff.{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
        "password": "TempPassword123!",
        "role": "CONTROL_STAFF",
        "phone_number": "+1234567890",
        "profile_image": None
    }
    
    admin_credentials = {
        "email": "admin@example.com",
        "password": "admin123"
    }
    
    # Step 1: Register as CONTROL_STAFF (should create approval request)
    print("1. Registering CONTROL_STAFF user...")
    response = requests.post(f"{BASE_URL}/api/accounts/register", json=test_user)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    if response.status_code == 201:
        print("✓ Approval request created successfully")
        request_data = response.json()
        request_id = request_data.get("request_id")
    else:
        print("✗ Failed to create approval request")
        return
    
    # Step 2: Login as admin (you'll need to create an admin user first)
    print("2. Logging in as admin...")
    response = requests.post(f"{BASE_URL}/api/accounts/login", json=admin_credentials)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Admin login successful")
        auth_data = response.json()
        auth_token = auth_data.get("access_token")
        headers = {"Authorization": f"Bearer {auth_token}"}
    else:
        print("✗ Admin login failed - you may need to create an admin user first")
        print("   You can create an admin by registering with role 'CONTROL_ADMIN'")
        return
    
    # Step 3: Get pending approval requests
    print("3. Getting pending approval requests...")
    response = requests.get(f"{BASE_URL}/api/approvals/requests?status_filter=PENDING", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        requests_list = response.json()
        print(f"✓ Found {len(requests_list)} pending requests")
        if requests_list:
            print("   First request:", json.dumps(requests_list[0], indent=2, default=str))
    else:
        print("✗ Failed to get approval requests")
    print()
    
    # Step 4: Approve the request
    if request_id:
        print("4. Approving the request...")
        approval_data = {
            "action": "APPROVED",
            "review_notes": "Application looks good, approved!"
        }
        response = requests.post(
            f"{BASE_URL}/api/approvals/requests/{request_id}/action", 
            json=approval_data, 
            headers=headers
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Request approved successfully")
            user_data = response.json()
            print("   Created user:", json.dumps(user_data, indent=2, default=str))
        else:
            print("✗ Failed to approve request")
            print("Response:", response.json())
    print()
    
    # Step 5: Test personnel endpoint
    print("5. Testing personnel endpoint...")
    response = requests.get(f"{BASE_URL}/api/control-center/personnel", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        personnel = response.json()
        print(f"✓ Retrieved {len(personnel)} personnel records")
        for person in personnel[:2]:  # Show first 2
            print(f"   - {person.get('first_name')} {person.get('last_name')} ({person.get('role')})")
    else:
        print("✗ Failed to get personnel")
        print("Response:", response.json())
    print()

def test_regular_user_registration():
    """Test regular user registration (non-CONTROL_STAFF)"""
    print("Testing Regular User Registration")
    print("=" * 40)
    
    test_user = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": f"jane.smith.{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com", 
        "password": "Password123!",
        "role": "PASSENGER",
        "phone_number": "+1234567891"
    }
    
    response = requests.post(f"{BASE_URL}/api/accounts/register", json=test_user)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print("✓ Regular user registered successfully")
        user_data = response.json()
        print(f"   User ID: {user_data.get('id')}")
        print(f"   Role: {user_data.get('role')}")
    else:
        print("✗ Regular user registration failed")
        print("Response:", response.json())
    print()

if __name__ == "__main__":
    print("GuzoSync Approval Workflow Test")
    print("Make sure the FastAPI server is running on localhost:8000")
    print()
    
    try:
        # Test regular user registration first
        test_regular_user_registration()
        
        # Test approval workflow
        test_registration_workflow()
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("   Make sure the FastAPI server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
