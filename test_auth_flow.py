#!/usr/bin/env python3
"""
Authentication Flow Test

This script tests the actual authentication flow to ensure the UUID fixes work
with your real application endpoints.
"""

import asyncio
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"

async def test_auth_flow():
    """Test the complete authentication flow."""
    print("Testing Authentication Flow...")
    
    # Test data
    test_user = {
        "first_name": "Test",
        "last_name": "UUID",
        "email": "test-uuid@example.com",
        "password": "testpassword123",
        "role": "PASSENGER",
        "phone_number": "+1234567890"
    }
    
    try:
        # 1. Test Registration
        print("\n1. Testing User Registration...")
        register_response = requests.post(
            f"{BASE_URL}/api/accounts/register",
            json=test_user,
            headers={"Content-Type": "application/json"}
        )
        
        if register_response.status_code == 201:
            print("✓ Registration successful")
            user_data = register_response.json()
            print(f"  User ID: {user_data.get('id', 'NOT_FOUND')}")
        else:
            print(f"✗ Registration failed: {register_response.status_code}")
            print(f"  Error: {register_response.text}")
            return False
        
        # 2. Test Login
        print("\n2. Testing User Login...")
        login_response = requests.post(
            f"{BASE_URL}/api/accounts/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            },
            headers={"Content-Type": "application/json"}
        )
        
        if login_response.status_code == 200:
            print("✓ Login successful")
            login_data = login_response.json()
            access_token = login_data.get("access_token")
            print(f"  Token received: {access_token[:20]}..." if access_token else "  No token received")
        else:
            print(f"✗ Login failed: {login_response.status_code}")
            print(f"  Error: {login_response.text}")
            return False
        
        # 3. Test Protected Endpoint
        print("\n3. Testing Protected Endpoint...")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        profile_response = requests.get(
            f"{BASE_URL}/api/account/me",
            headers=headers
        )
        
        if profile_response.status_code == 200:
            print("✓ Protected endpoint access successful")
            profile_data = profile_response.json()
            print(f"  Profile ID: {profile_data.get('id', 'NOT_FOUND')}")
            print(f"  Email: {profile_data.get('email', 'NOT_FOUND')}")
        else:
            print(f"✗ Protected endpoint failed: {profile_response.status_code}")
            print(f"  Error: {profile_response.text}")
            return False
        
        print("\n✅ All authentication tests passed!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("✗ Connection error: Make sure your FastAPI server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    
    finally:
        # Cleanup: Try to delete the test user (this might fail if the endpoint doesn't exist)
        try:
            print("\n4. Cleaning up test data...")
            # Note: You might need to implement a cleanup endpoint or do this manually
            print("  Manual cleanup may be required for test user")
        except:
            pass

if __name__ == "__main__":
    print("Make sure your FastAPI server is running with: python main.py")
    print("Press Enter to continue or Ctrl+C to cancel...")
    try:
        input()
        success = asyncio.run(test_auth_flow())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled by user")
        exit(1)
