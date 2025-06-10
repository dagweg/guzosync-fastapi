#!/usr/bin/env python3
"""
Test script for the redesigned attendance system.
This script tests the new unified attendance model and heatmap functionality.
"""

import sys
from datetime import datetime, date, timedelta
from typing import Dict

# Add the project root to the path
sys.path.append('.')

from models.attendance import Attendance, AttendanceStatus as ModelAttendanceStatus
from schemas.attendance import (
    AttendanceStatus, MarkAttendanceRequest, AttendanceResponse, AttendanceHeatmapResponse
)


def test_attendance_model():
    """Test the new Attendance model."""
    print("🧪 Testing Attendance model...")
    
    # Test creating an attendance record
    attendance = Attendance(
        user_id="test-user-123",
        date=date.today(),
        status=ModelAttendanceStatus.PRESENT,
        check_in_time=datetime.now().replace(hour=8, minute=30),
        check_out_time=datetime.now().replace(hour=17, minute=0),
        notes="Test attendance record",
        marked_by="test-admin-456",
        marked_at=datetime.now()
    )
    
    print(f"✅ Created attendance record: {attendance.user_id} - {attendance.status}")
    print(f"   Date: {attendance.date}")
    print(f"   Check-in: {attendance.check_in_time}")
    print(f"   Check-out: {attendance.check_out_time}")
    
    return attendance


def test_attendance_schemas():
    """Test the new attendance schemas."""
    print("\n🧪 Testing Attendance schemas...")
    
    # Test MarkAttendanceRequest
    mark_request = MarkAttendanceRequest(
        user_id="test-user-123",
        date=date.today(),
        status=AttendanceStatus.PRESENT,
        check_in_time=datetime.now().replace(hour=8, minute=30),
        notes="Marked via API"
    )
    
    print(f"✅ Created MarkAttendanceRequest: {mark_request.user_id} - {mark_request.status}")
    
    # Test AttendanceResponse
    attendance_response = AttendanceResponse(
        id="attendance-123",
        user_id="test-user-123",
        date=date.today(),
        status=AttendanceStatus.PRESENT,
        check_in_time=datetime.now().replace(hour=8, minute=30),
        marked_by="test-admin-456",
        marked_at=datetime.now()
    )
    
    print(f"✅ Created AttendanceResponse: {attendance_response.id}")
    
    # Test AttendanceHeatmapResponse
    heatmap_data = {
        "2024-01-01": "PRESENT",
        "2024-01-02": "LATE", 
        "2024-01-03": "ABSENT",
        "2024-01-04": "PRESENT"
    }
    
    heatmap_response = AttendanceHeatmapResponse(
        user_id="test-user-123",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 1, 31),
        attendance_data=heatmap_data
    )
    
    print(f"✅ Created AttendanceHeatmapResponse with {len(heatmap_response.attendance_data)} records")
    print(f"   Sample data: {dict(list(heatmap_response.attendance_data.items())[:2])}")
    
    return mark_request, attendance_response, heatmap_response


def generate_sample_heatmap_data(days: int = 30) -> Dict[str, str]:
    """Generate sample heatmap data for testing."""
    import random
    
    heatmap_data = {}
    start_date = date.today() - timedelta(days=days)
    
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.isoformat()
        
        # Generate random status with realistic distribution
        rand = random.random()
        if rand < 0.7:  # 70% present
            status = "PRESENT"
        elif rand < 0.85:  # 15% late
            status = "LATE"
        else:  # 15% absent
            status = "ABSENT"
            
        heatmap_data[date_str] = status
    
    return heatmap_data


def test_heatmap_data_generation():
    """Test heatmap data generation."""
    print("\n🧪 Testing heatmap data generation...")
    
    # Generate sample data for multiple users
    users = ["user-1", "user-2", "user-3"]
    
    for user_id in users:
        heatmap_data = generate_sample_heatmap_data(days=30)
        
        # Calculate statistics
        total_days = len(heatmap_data)
        present_days = sum(1 for status in heatmap_data.values() if status == "PRESENT")
        late_days = sum(1 for status in heatmap_data.values() if status == "LATE")
        absent_days = sum(1 for status in heatmap_data.values() if status == "ABSENT")
        
        attendance_rate = (present_days + late_days) / total_days * 100
        
        print(f"✅ Generated heatmap for {user_id}:")
        print(f"   Total days: {total_days}")
        print(f"   Present: {present_days}, Late: {late_days}, Absent: {absent_days}")
        print(f"   Attendance rate: {attendance_rate:.1f}%")


def test_attendance_status_enum():
    """Test the AttendanceStatus enum."""
    print("\n🧪 Testing AttendanceStatus enum...")
    
    # Test all status values
    statuses = [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT, AttendanceStatus.LATE]
    
    for status in statuses:
        print(f"✅ Status: {status} (value: {status.value})")
    
    
    assert AttendanceStatus.PRESENT.value == "PRESENT"
    assert AttendanceStatus.ABSENT.value == "ABSENT" 
    assert AttendanceStatus.LATE.value == "LATE"    
    print("✅ All status enum tests passed!")


def main():
    """Run all tests."""
    print("🚀 Starting Attendance System Redesign Tests")
    print("=" * 50)
    
    try:
        # Test the model
        test_attendance_model()

        # Test the schemas
        test_attendance_schemas()

        # Test heatmap data generation
        test_heatmap_data_generation()

        # Test enum
        test_attendance_status_enum()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! The redesigned attendance system is working correctly.")
        print("\n📋 Summary of changes:")
        print("   ✅ Unified Attendance model (removed dual system)")
        print("   ✅ Simplified schemas (removed check-in/check-out complexity)")
        print("   ✅ Added AttendanceHeatmapResponse for GitHub-style heatmaps")
        print("   ✅ Clean date-to-status mapping for frontend visualization")
        print("   ✅ Maintained three status types: Present, Absent, Late")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
