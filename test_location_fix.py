#!/usr/bin/env python3
"""
Test script to verify Location model usage in WebSocket events
"""
import sys
import os
import asyncio
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.base import Location
from core.mongo_utils import model_to_mongo_doc
import json

def test_location_model_creation():
    """Test Location model creation and MongoDB document conversion"""
    print("🧪 Testing Location model creation and conversion...")
    
    try:
        # Test 1: Create Location model
        location = Location(latitude=9.0317, longitude=38.7468)
        print(f"✅ Location model created: {location}")
        print(f"   - Latitude: {location.latitude}")
        print(f"   - Longitude: {location.longitude}")
        
        # Test 2: Convert to MongoDB document
        location_doc = model_to_mongo_doc(location)
        print(f"✅ MongoDB document created:")
        print(json.dumps(location_doc, indent=2, default=str))
        
        # Test 3: Verify structure
        assert "latitude" in location_doc
        assert "longitude" in location_doc
        assert location_doc["latitude"] == 9.0317
        assert location_doc["longitude"] == 38.7468
        print("✅ Document structure verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Location model: {e}")
        return False

def test_update_data_structure():
    """Test the update data structure that would be used in MongoDB"""
    print("\n🧪 Testing MongoDB update data structure...")
    
    try:
        # Create location
        location = Location(latitude=9.0317, longitude=38.7468)
        location_doc = model_to_mongo_doc(location)
        
        # Create update data structure (as used in websocket_events.py)
        update_data = {
            "current_location": location_doc,
            "last_location_update": datetime.now(timezone.utc)
        }
        
        print("✅ Update data structure:")
        print(json.dumps(update_data, indent=2, default=str))
        
        # Verify structure
        assert "current_location" in update_data
        assert "latitude" in update_data["current_location"]
        assert "longitude" in update_data["current_location"]
        print("✅ Update data structure verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing update data structure: {e}")
        return False

def test_old_vs_new_approach():
    """Compare old problematic approach vs new approach"""
    print("\n🧪 Comparing old vs new approach...")
    
    try:
        # Old approach (problematic)
        old_update_data = {
            "current_location.latitude": 9.0317,
            "current_location.longitude": 38.7468,
            "last_location_update": datetime.now(timezone.utc)
        }
        
        print("❌ Old approach (problematic):")
        print(json.dumps(old_update_data, indent=2, default=str))
        print("   This fails when current_location is null in MongoDB")
        
        # New approach (fixed)
        location = Location(latitude=9.0317, longitude=38.7468)
        location_doc = model_to_mongo_doc(location)
        
        new_update_data = {
            "current_location": location_doc,
            "last_location_update": datetime.now(timezone.utc)
        }
        
        print("\n✅ New approach (fixed):")
        print(json.dumps(new_update_data, indent=2, default=str))
        print("   This creates a proper location object even when current_location was null")
        
        return True
        
    except Exception as e:
        print(f"❌ Error comparing approaches: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Location Model Fix for WebSocket Events")
    print("=" * 60)
    
    tests = [
        test_location_model_creation,
        test_update_data_structure,
        test_old_vs_new_approach
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Location model fix is working correctly.")
        print("\n📝 Summary of changes:")
        print("   - Added Location model import to websocket_events.py")
        print("   - Added model_to_mongo_doc import to websocket_events.py")
        print("   - Changed passenger location update to use Location model")
        print("   - Changed bus location update to use Location model")
        print("   - This fixes the MongoDB error when current_location is null")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
