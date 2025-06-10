#!/usr/bin/env python3
"""
Example of how to use the new attendance heatmap endpoint.
This demonstrates how to fetch and visualize attendance data like GitHub commit heatmaps.
"""

import json
from datetime import date, timedelta
from typing import Dict, Any


def example_heatmap_response() -> Dict[str, Any]:
    """Example response from the /api/attendance/heatmap endpoint."""
    
    # Generate sample data for the last 365 days
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    
    # Sample attendance data (in real usage, this comes from the API)
    attendance_data = {}
    
    # Generate realistic attendance pattern
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.isoformat()
        
        # Skip weekends (realistic for work attendance)
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            # Simulate realistic attendance patterns
            day_of_week = current_date.weekday()
            
            if day_of_week == 0:  # Monday - higher chance of being late
                status = "LATE" if current_date.day % 7 == 0 else "PRESENT"
            elif day_of_week == 4:  # Friday - occasional absences
                status = "ABSENT" if current_date.day % 15 == 0 else "PRESENT"
            else:  # Tuesday-Thursday - mostly present
                status = "ABSENT" if current_date.day % 20 == 0 else "PRESENT"
                
            attendance_data[date_str] = status
        
        current_date += timedelta(days=1)
    
    return {
        "user_id": "user-12345",
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
        "attendance_data": attendance_data
    }


def calculate_attendance_stats(attendance_data: Dict[str, str]) -> Dict[str, Any]:
    """Calculate attendance statistics from heatmap data."""
    
    total_days = len(attendance_data)
    present_days = sum(1 for status in attendance_data.values() if status == "PRESENT")
    late_days = sum(1 for status in attendance_data.values() if status == "LATE")
    absent_days = sum(1 for status in attendance_data.values() if status == "ABSENT")
    
    attendance_rate = (present_days + late_days) / total_days * 100 if total_days > 0 else 0
    punctuality_rate = present_days / total_days * 100 if total_days > 0 else 0
    
    return {
        "total_days": total_days,
        "present_days": present_days,
        "late_days": late_days,
        "absent_days": absent_days,
        "attendance_rate": round(attendance_rate, 1),
        "punctuality_rate": round(punctuality_rate, 1)
    }


def generate_weekly_summary(attendance_data: Dict[str, str]) -> Dict[str, Dict[str, int]]:
    """Generate weekly attendance summary for better insights."""
    
    weekly_data = {}
    
    for date_str, status in attendance_data.items():
        # Parse date and get week number
        date_obj = date.fromisoformat(date_str)
        year_week = f"{date_obj.year}-W{date_obj.isocalendar()[1]:02d}"
        
        if year_week not in weekly_data:
            weekly_data[year_week] = {"PRESENT": 0, "LATE": 0, "ABSENT": 0}
        
        weekly_data[year_week][status] += 1
    
    return weekly_data


def format_heatmap_for_frontend(attendance_data: Dict[str, str]) -> Dict[str, Any]:
    """Format heatmap data for frontend consumption (similar to GitHub)."""
    
    # Group data by month for easier frontend rendering
    monthly_data: dict = {}
    
    for date_str, status in attendance_data.items():
        date_obj = date.fromisoformat(date_str)
        month_key = f"{date_obj.year}-{date_obj.month:02d}"
        
        if month_key not in monthly_data:
            monthly_data[month_key] = []
        
        monthly_data[month_key].append({
            "date": date_str,
            "status": status,
            "day_of_week": date_obj.weekday(),
            "week_of_year": date_obj.isocalendar()[1]
        })
    
    return {
        "monthly_data": monthly_data,
        "status_colors": {
            "PRESENT": "#22c55e",    # Green
            "LATE": "#f59e0b",       # Amber
            "ABSENT": "#ef4444",     # Red
            "NO_DATA": "#f3f4f6"     # Gray
        }
    }


def main():
    """Demonstrate the attendance heatmap functionality."""
    
    print("📊 Attendance Heatmap Example")
    print("=" * 50)
    
    # Get example heatmap data
    heatmap_response = example_heatmap_response()
    attendance_data = heatmap_response["attendance_data"]
    
    print(f"👤 User ID: {heatmap_response['user_id']}")
    print(f"📅 Date Range: {heatmap_response['date_from']} to {heatmap_response['date_to']}")
    print(f"📊 Total Records: {len(attendance_data)}")
    
    # Calculate statistics
    stats = calculate_attendance_stats(attendance_data)
    print(f"\n📈 Attendance Statistics:")
    print(f"   Total Days: {stats['total_days']}")
    print(f"   Present: {stats['present_days']} days")
    print(f"   Late: {stats['late_days']} days") 
    print(f"   Absent: {stats['absent_days']} days")
    print(f"   Attendance Rate: {stats['attendance_rate']}%")
    print(f"   Punctuality Rate: {stats['punctuality_rate']}%")
    
    # Generate weekly summary
    weekly_summary = generate_weekly_summary(attendance_data)
    print(f"\n📅 Weekly Summary (last 4 weeks):")
    
    # Show last 4 weeks
    recent_weeks = sorted(weekly_summary.keys())[-4:]
    for week in recent_weeks:
        week_data = weekly_summary[week]
        total_week_days = sum(week_data.values())
        print(f"   {week}: {week_data['PRESENT']}P {week_data['LATE']}L {week_data['ABSENT']}A (Total: {total_week_days})")
    
    # Format for frontend
    frontend_data = format_heatmap_for_frontend(attendance_data)
    print(f"\n🎨 Frontend Data Structure:")
    print(f"   Months: {len(frontend_data['monthly_data'])}")
    print(f"   Status Colors: {frontend_data['status_colors']}")
    
    # Show sample month data
    sample_month = list(frontend_data['monthly_data'].keys())[0]
    sample_data = frontend_data['monthly_data'][sample_month][:5]  # First 5 days
    print(f"\n📋 Sample Month Data ({sample_month}):")
    for day_data in sample_data:
        print(f"   {day_data['date']}: {day_data['status']} (Day {day_data['day_of_week']})")
    
    print(f"\n🔗 API Endpoint Usage:")
    print(f"   GET /api/attendance/heatmap?user_id={heatmap_response['user_id']}")
    print(f"   GET /api/attendance/heatmap?date_from=2024-01-01&date_to=2024-12-31")
    print(f"   GET /api/attendance/heatmap  # (defaults to last 365 days for current user)")
    
    print(f"\n💡 Frontend Integration Tips:")
    print(f"   - Use the attendance_data dict to create a calendar grid")
    print(f"   - Apply status_colors for visual representation")
    print(f"   - Group by weeks/months for better UX")
    print(f"   - Add tooltips showing date and status on hover")
    print(f"   - Consider using libraries like D3.js or Chart.js for visualization")


if __name__ == "__main__":
    main()
