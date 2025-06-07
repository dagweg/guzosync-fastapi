"""
Setup script to create an admin user for testing the approval workflow
Run this before testing the approval APIs
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000"

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
            
    except Exception as e:
        print(f"❌ Error creating staff user: {str(e)}")

if __name__ == "__main__":
    print("GuzoSync Admin Setup for Approval Workflow Testing")
    print("=" * 55)
    print("Make sure the FastAPI server is running on localhost:8000")
    print()
    
    create_admin_user()
    create_staff_user()
    
    print("\n" + "=" * 55)
    print("Setup complete! You can now run test_approval_workflow.py")
