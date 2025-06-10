#!/usr/bin/env python3
"""
Simple test script to verify the reallocation history endpoint works correctly.
This script can be run independently to test the endpoint functionality.
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "admin@example.com"  # Replace with actual admin credentials
TEST_PASSWORD = "password123"     # Replace with actual admin password

async def test_reallocation_history_endpoint():
    """Test the reallocation history endpoint"""
    
    async with httpx.AsyncClient() as client:
        # Step 1: Login to get access token
        print("🔐 Logging in...")
        login_response = await client.post(
            f"{BASE_URL}/api/auth/login",
            data={
                "username": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return
        
        token_data = login_response.json()
        access_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        print("✅ Login successful")
        
        # Step 2: Test the reallocation history endpoint
        print("\n📊 Testing reallocation history endpoint...")
        
        # Test basic endpoint
        history_response = await client.get(
            f"{BASE_URL}/api/control-center/reallocation-history",
            headers=headers
        )
        
        print(f"Status Code: {history_response.status_code}")
        
        if history_response.status_code == 200:
            history_data = history_response.json()
            print(f"✅ Endpoint works! Retrieved {len(history_data)} reallocation records")
            
            # Print first record if available
            if history_data:
                print("\n📋 Sample record:")
                print(json.dumps(history_data[0], indent=2, default=str))
            else:
                print("📝 No reallocation records found (this is normal if no reallocations have been made)")
                
        else:
            print(f"❌ Endpoint failed: {history_response.status_code}")
            print(f"Response: {history_response.text}")
            return
        
        # Step 3: Test with filters
        print("\n🔍 Testing with filters...")
        
        # Test with limit
        filtered_response = await client.get(
            f"{BASE_URL}/api/control-center/reallocation-history?limit=5",
            headers=headers
        )
        
        if filtered_response.status_code == 200:
            filtered_data = filtered_response.json()
            print(f"✅ Filtered endpoint works! Retrieved {len(filtered_data)} records (limit=5)")
        else:
            print(f"❌ Filtered endpoint failed: {filtered_response.status_code}")
        
        # Test with status filter
        status_response = await client.get(
            f"{BASE_URL}/api/control-center/reallocation-history?status_filter=COMPLETED",
            headers=headers
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"✅ Status filter works! Retrieved {len(status_data)} COMPLETED records")
        else:
            print(f"❌ Status filter failed: {status_response.status_code}")
        
        # Test with date range (last 30 days)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        date_response = await client.get(
            f"{BASE_URL}/api/control-center/reallocation-history?start_date={start_date}&end_date={end_date}",
            headers=headers
        )
        
        if date_response.status_code == 200:
            date_data = date_response.json()
            print(f"✅ Date filter works! Retrieved {len(date_data)} records from last 30 days")
        else:
            print(f"❌ Date filter failed: {date_response.status_code}")
        
        print("\n🎉 All tests completed!")

if __name__ == "__main__":
    print("🚀 Starting reallocation history endpoint test...")
    print("⚠️  Make sure the FastAPI server is running on http://localhost:8000")
    print("⚠️  Update TEST_EMAIL and TEST_PASSWORD with valid admin credentials")
    print()
    
    asyncio.run(test_reallocation_history_endpoint())
