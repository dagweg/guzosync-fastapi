"""
Quick test to verify CONTROL_STAFF can also access personnel endpoint
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_staff_personnel_access():
    """Test that CONTROL_STAFF can access personnel endpoint"""
    print("Testing CONTROL_STAFF Personnel Access")
    print("=" * 40)
    
    # Login as the newly created CONTROL_STAFF user
    staff_credentials = {
        "email": "john.doe.staff.20250607123658@example.com",  # Update with actual email from test
        "password": "TempPassword123!"
    }
    
    try:
        # Login as staff
        response = requests.post(f"{BASE_URL}/api/accounts/login", json=staff_credentials)
        print(f"Staff login status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Staff login successful")
            auth_data = response.json()
            auth_token = auth_data.get("access_token")
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            # Test personnel endpoint
            response = requests.get(f"{BASE_URL}/api/control-center/personnel", headers=headers)
            print(f"Personnel endpoint status: {response.status_code}")
            
            if response.status_code == 200:
                personnel = response.json()
                print(f"✓ CONTROL_STAFF can access personnel endpoint")
                print(f"   Retrieved {len(personnel)} personnel records")
                print("   Access control working correctly!")
            else:
                print("✗ CONTROL_STAFF cannot access personnel endpoint")
                print("Response:", response.json())
        else:
            print("✗ Staff login failed")
            print("Response:", response.json())
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")

if __name__ == "__main__":
    test_staff_personnel_access()
