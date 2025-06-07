"""
Admin utilities for managing Control Center personnel, Bus Drivers, and Queue Regulators.

This module provides utility functions for creating, managing, and validating
admin-related models in the GuzoSync application.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from models.admin import (
    ControlAdmin, ControlStaff, BusDriver, QueueRegulator,
    AdminPermission, StaffPermission, DriverStatus, RegulatorStatus,
    RolePermissions
)
from models.user import User, UserRole
from core.custom_types import generate_uuid


class AdminManager:
    """Utility class for managing admin personnel operations."""
    
    def __init__(self, db: AsyncIOMotorClient):
        self.db = db
    
    # Control Admin Operations
    async def create_control_admin(
        self, 
        user_id: str, 
        employee_id: str,
        permissions: Optional[List[AdminPermission]] = None,
        department: Optional[str] = None,
        hire_date: Optional[datetime] = None,
        emergency_contact: Optional[str] = None
    ) -> str:
        """Create a new Control Admin record."""
        admin_data = {
            "_id": generate_uuid(),
            "user_id": user_id,
            "employee_id": employee_id,
            "permissions": permissions or list(AdminPermission),
            "department": department,
            "hire_date": hire_date or datetime.utcnow(),
            "last_login": None,
            "access_level": 10,
            "can_manage_staff": True,
            "can_approve_major_changes": True,
            "emergency_contact": emergency_contact,            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = await self.db.control_admins.insert_one(admin_data)
        return str(result.inserted_id)
    
    async def get_control_admin_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get Control Admin by user ID."""
        result = await self.db.control_admins.find_one({"user_id": user_id})
        return result  # type: ignore
    
    async def update_admin_last_login(self, admin_id: str) -> bool:
        """Update admin's last login timestamp."""
        result = await self.db.control_admins.update_one(
            {"_id": admin_id},
            {"$set": {"last_login": datetime.utcnow(), "updated_at": datetime.utcnow()}}
        )
        return bool(result.modified_count > 0)
    
    # Control Staff Operations
    async def create_control_staff(
        self,
        user_id: str,
        employee_id: str,
        permissions: Optional[List[StaffPermission]] = None,
        supervisor_id: Optional[str] = None,
        department: Optional[str] = None,
        hire_date: Optional[datetime] = None,
        emergency_contact: Optional[str] = None
    ) -> Any:
        """Create a new Control Staff record."""
        staff_data = {
            "_id": generate_uuid(),
            "user_id": user_id,
            "employee_id": employee_id,
            "permissions": permissions or [],
            "supervisor_id": supervisor_id,
            "department": department,
            "hire_date": hire_date or datetime.utcnow(),
            "last_login": None,
            "access_level": 5,
            "shift_schedule": None,
            "emergency_contact": emergency_contact,            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = await self.db.control_staff.insert_one(staff_data)
        return str(result.inserted_id)
    
    async def get_control_staff_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get Control Staff by user ID."""
        result = await self.db.control_staff.find_one({"user_id": user_id})
        return result  # type: ignore
    
    # Bus Driver Operations
    async def create_bus_driver(
        self,
        user_id: str,
        employee_id: str,
        driver_license_number: str,
        license_expiry_date: datetime,
        medical_cert_expiry: Optional[datetime] = None,
        hire_date: Optional[datetime] = None,
        emergency_contact: Optional[str] = None,
        preferred_routes: Optional[List[str]] = None
    ) -> str:
        """Create a new Bus Driver record."""
        driver_data = {
            "_id": generate_uuid(),
            "user_id": user_id,
            "employee_id": employee_id,
            "driver_license_number": driver_license_number,
            "license_expiry_date": license_expiry_date,
            "medical_cert_expiry": medical_cert_expiry,
            "hire_date": hire_date or datetime.utcnow(),
            "status": DriverStatus.AVAILABLE,
            "current_bus_id": None,
            "current_route_id": None,
            "shift_start": None,
            "shift_end": None,
            "total_driving_hours": 0.0,
            "safety_score": 100.0,
            "violations_count": 0,
            "last_violation_date": None,
            "emergency_contact": emergency_contact,
            "preferred_routes": preferred_routes or [],
            "on_time_percentage": 100.0,
            "passenger_rating": 5.0,
            "fuel_efficiency_score": 100.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = await self.db.bus_drivers.insert_one(driver_data)
        return str(result.inserted_id)
    
    async def update_driver_status(
        self, 
        driver_id: str, 
        status: DriverStatus,
        current_bus_id: Optional[str] = None,
        current_route_id: Optional[str] = None
    ) -> bool:
        """Update driver status and current assignments."""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        if status == DriverStatus.ON_DUTY:
            update_data["shift_start"] = datetime.utcnow()
            if current_bus_id:
                update_data["current_bus_id"] = current_bus_id
            if current_route_id:
                update_data["current_route_id"] = current_route_id
        elif status == DriverStatus.OFF_DUTY:
            update_data["shift_end"] = datetime.utcnow()
            update_data["current_bus_id"] = None
            update_data["current_route_id"] = None
            result = await self.db.bus_drivers.update_one(
            {"_id": driver_id},
            {"$set": update_data}        )
        return bool(result.modified_count > 0)
    
    async def get_available_drivers(self) -> List[Dict[str, Any]]:
        """Get all available drivers."""
        cursor = self.db.bus_drivers.find({"status": DriverStatus.AVAILABLE})
        result = await cursor.to_list(length=None)
        return result  # type: ignore
    
    async def assign_driver_to_bus(self, driver_id: str, bus_id: str) -> bool:
        """Assign a driver to a bus."""
        result = await self.db.bus_drivers.update_one(
            {"_id": driver_id},
            {"$set": {
                "current_bus_id": bus_id,
                "status": DriverStatus.ON_DUTY,
                "updated_at": datetime.utcnow()
            }}
        )
        return bool(result.modified_count > 0)
    
    # Queue Regulator Operations
    async def create_queue_regulator(
        self,
        user_id: str,
        employee_id: str,
        assigned_bus_stop_ids: Optional[List[str]] = None,
        supervisor_id: Optional[str] = None,
        hire_date: Optional[datetime] = None,
        emergency_contact: Optional[str] = None
    ) -> str:
        """Create a new Queue Regulator record."""
        regulator_data: Dict[str, Any] = {
            "_id": generate_uuid(),
            "user_id": user_id,
            "employee_id": employee_id,
            "assigned_bus_stop_ids": assigned_bus_stop_ids or [],
            "supervisor_id": supervisor_id,
            "hire_date": hire_date or datetime.utcnow(),
            "status": RegulatorStatus.ACTIVE,
            "shift_start": None,
            "shift_end": None,
            "current_location": None,
            "incidents_resolved": 0,
            "average_response_time": 0.0,
            "passenger_satisfaction_score": 5.0,
            "violations_reported": 0,
            "has_radio": True,
            "has_tablet": False,
            "equipment_status": {},
            "emergency_contact": emergency_contact,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = await self.db.queue_regulators.insert_one(regulator_data)
        return str(result.inserted_id)
    
    async def assign_regulator_to_bus_stops(
        self, 
        regulator_id: str, 
        bus_stop_ids: List[str]
    ) -> bool:
        """Assign regulator to multiple bus stops."""
        result = await self.db.queue_regulators.update_one(
            {"_id": regulator_id},
            {"$set": {
                "assigned_bus_stop_ids": bus_stop_ids,
                "updated_at": datetime.utcnow()
            }}
        )
        return bool(result.modified_count > 0)
    
    async def update_regulator_location(
        self, 
        regulator_id: str, 
        latitude: float, 
        longitude: float
    ) -> bool:
        """Update regulator's current location."""
        result = await self.db.queue_regulators.update_one(
            {"_id": regulator_id},
            {"$set": {
                "current_location": {"latitude": latitude, "longitude": longitude},
                "updated_at": datetime.utcnow()
            }}
        )
        return bool(result.modified_count > 0)
    
    # Permission checking utilities
    async def check_admin_permission(
        self, 
        user_id: str, 
        permission: AdminPermission
    ) -> bool:
        """Check if a user has specific admin permission."""
        admin = await self.get_control_admin_by_user_id(user_id)
        if not admin:
            return False
        return permission in admin.get("permissions", [])
    
    async def check_staff_permission(
        self, 
        user_id: str, 
        permission: StaffPermission
    ) -> bool:
        """Check if a staff member has specific permission."""
        staff = await self.get_control_staff_by_user_id(user_id)
        if not staff:
            return False
        return permission in staff.get("permissions", [])
    
    # Analytics and reporting
    async def get_driver_performance_metrics(
        self, 
        driver_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get performance metrics for a driver."""
        driver = await self.db.bus_drivers.find_one({"_id": driver_id})
        if not driver:
            return {}
        
        # You can enhance this with actual trip data analysis
        return {
            "driver_id": driver_id,
            "period_start": start_date,
            "period_end": end_date,
            "safety_score": driver.get("safety_score", 0),
            "on_time_percentage": driver.get("on_time_percentage", 0),
            "passenger_rating": driver.get("passenger_rating", 0),
            "fuel_efficiency_score": driver.get("fuel_efficiency_score", 0),
            "violations_count": driver.get("violations_count", 0),
            "total_driving_hours": driver.get("total_driving_hours", 0)
        }
    
    async def get_regulator_performance_metrics(
        self, 
        regulator_id: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get performance metrics for a regulator."""
        regulator = await self.db.queue_regulators.find_one({"_id": regulator_id})
        if not regulator:
            return {}
        
        return {
            "regulator_id": regulator_id,
            "period_start": start_date,
            "period_end": end_date,
            "incidents_resolved": regulator.get("incidents_resolved", 0),
            "average_response_time": regulator.get("average_response_time", 0),
            "passenger_satisfaction_score": regulator.get("passenger_satisfaction_score", 0),
            "violations_reported": regulator.get("violations_reported", 0)
        }


# Helper functions for creating admin personnel
async def create_admin_user_and_profile(
    db: AsyncIOMotorClient,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    role: UserRole,
    employee_id: str,
    **kwargs
) -> Dict[str, str]:
    """
    Create both User and corresponding admin profile records.
    
    Returns:
        Dict with user_id and profile_id
    """
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Create user first
    user_data = {
        "_id": generate_uuid(),
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": pwd_context.hash(password),
        "role": role,
        "phone_number": kwargs.get("phone_number", ""),
        "profile_image": None,
        "password_reset_token": None,
        "password_reset_expires": None,
        "is_active": True,
        "preferred_language": kwargs.get("preferred_language", "en"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    user_result = await db.users.insert_one(user_data)
    user_id = str(user_result.inserted_id)
    
    # Create corresponding admin profile
    admin_manager = AdminManager(db)
    profile_id = None
    
    if role == UserRole.CONTROL_ADMIN:
        profile_id = await admin_manager.create_control_admin(
            user_id=user_id,
            employee_id=employee_id,
            **kwargs
        )
    elif role == UserRole.CONTROL_STAFF:
        profile_id = await admin_manager.create_control_staff(
            user_id=user_id,
            employee_id=employee_id,
            **kwargs
        )
    elif role == UserRole.BUS_DRIVER:
        profile_id = await admin_manager.create_bus_driver(
            user_id=user_id,
            employee_id=employee_id,
            **kwargs
        )
    elif role == UserRole.QUEUE_REGULATOR:
        profile_id = await admin_manager.create_queue_regulator(
            user_id=user_id,
            employee_id=employee_id,
            **kwargs
        )
    
    return {
        "user_id": user_id,
        "profile_id": profile_id or ""
    }
