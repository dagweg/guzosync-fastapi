from typing import Literal, Optional
from pydantic import BaseModel, EmailStr
from datetime import date, datetime

from enum import Enum
from .base import DateTimeModelMixin

class UserRole(str, Enum):
    PASSENGER = "PASSENGER"
    BUS_DRIVER = "BUS_DRIVER"
    QUEUE_REGULATOR = "QUEUE_REGULATOR"
    CONTROL_STAFF = "CONTROL_STAFF"
    CONTROL_ADMIN = "CONTROL_ADMIN"

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class RegisterUserRequest(BaseModel):
    # Basic Information (required)
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: Literal[UserRole.PASSENGER, UserRole.CONTROL_STAFF, UserRole.CONTROL_ADMIN] = UserRole.PASSENGER
    phone_number: str

    # Optional profile information
    profile_image: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    nationality: Optional[str] = None
    national_id: Optional[str] = None

    # Optional address information
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "Ethiopia"

    # Optional contact information
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    secondary_phone: Optional[str] = None
    work_phone: Optional[str] = None

    # Optional preferences
    preferred_language: Optional[str] = "en"
    preferred_payment_method: Optional[str] = None

    # Optional discount eligibility
    student_discount_eligible: Optional[bool] = False
    senior_discount_eligible: Optional[bool] = False
    disability_discount_eligible: Optional[bool] = False

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class UpdateUserRequest(BaseModel):
    # Basic Information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    profile_image: Optional[str] = None

    # Profile Information
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    nationality: Optional[str] = None
    national_id: Optional[str] = None

    # Address Information
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    # Contact Information
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    secondary_phone: Optional[str] = None
    work_phone: Optional[str] = None

    # Preferences
    preferred_language: Optional[str] = None
    preferred_payment_method: Optional[str] = None

    # Discount eligibility
    student_discount_eligible: Optional[bool] = None
    senior_discount_eligible: Optional[bool] = None
    disability_discount_eligible: Optional[bool] = None

class UserResponse(DateTimeModelMixin):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole
    phone_number: str
    profile_image: Optional[str] = None
    is_active: bool

    # Profile Information
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    nationality: Optional[str] = None
    national_id: Optional[str] = None

    # Address Information
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    # Contact Information
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    secondary_phone: Optional[str] = None
    work_phone: Optional[str] = None

    # Preferences and Settings
    preferred_language: Optional[str] = None
    is_verified: Optional[bool] = None

    # Payment and Discounts
    preferred_payment_method: Optional[str] = None
    monthly_pass_active: Optional[bool] = None
    student_discount_eligible: Optional[bool] = None
    senior_discount_eligible: Optional[bool] = None
    disability_discount_eligible: Optional[bool] = None

    # Analytics
    total_trips: Optional[int] = None
    total_distance_traveled: Optional[float] = None

class AssignedBusInfo(BaseModel):
    """Simplified bus information for driver responses"""
    id: str
    license_plate: str
    bus_type: str
    capacity: int
    bus_status: str
    assigned_route_id: Optional[str] = None
    current_location: Optional[dict] = None
    last_location_update: Optional[datetime] = None

class DriverWithBusResponse(UserResponse):
    """Driver response with associated bus information"""
    assigned_bus: Optional[AssignedBusInfo] = None