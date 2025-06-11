from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from .base import BaseDBModel, Location

class UserRole(str, Enum):
    PASSENGER = "PASSENGER"
    BUS_DRIVER = "BUS_DRIVER"
    QUEUE_REGULATOR = "QUEUE_REGULATOR"
    CONTROL_STAFF = "CONTROL_STAFF"
    CONTROL_ADMIN = "CONTROL_ADMIN"

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class User(BaseDBModel):
    # Basic Information
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: UserRole
    phone_number: str
    
    # Profile Information
    profile_image: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    nationality: Optional[str] = None
    national_id: Optional[str] = None  # ID card number
    
    # Address Information
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "Ethiopia"  # Default to Ethiopia for local transport
    
    # Contact Information
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    secondary_phone: Optional[str] = None
    work_phone: Optional[str] = None
    
    # Preferences and Settings
    preferred_language: Optional[str] = "en"
    
    # Account Status and Security
    is_active: bool = True
    is_verified: bool = False  # Email/phone verification status
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    email_verification_token: Optional[str] = None
    email_verified_at: Optional[datetime] = None
    phone_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    account_locked_until: Optional[datetime] = None
    
   
    preferred_payment_method: Optional[str] = None
    monthly_pass_active: bool = False
    student_discount_eligible: bool = False
    senior_discount_eligible: bool = False
    disability_discount_eligible: bool = False    
    
    # Analytics and Tracking
    total_trips: int = 0
    total_distance_traveled: float = 0.0

    # Location Tracking (for passengers)
    current_location: Optional[Location] = None
    last_location_update: Optional[datetime] = None
    location_sharing_enabled: bool = False  # Privacy control for passengers

