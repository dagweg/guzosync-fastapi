from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from enum import Enum
from .base import DateTimeModelMixin


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, Enum):
    TELEBIRR = "telebirr"
    MPESA = "mpesa"
    CBEBIRR = "cbebirr"
    EBIRR = "ebirr"
    ENAT_BANK = "enat_bank"


class TicketStatus(str, Enum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class TicketType(str, Enum):
    SINGLE_TRIP = "SINGLE_TRIP"
    ROUND_TRIP = "ROUND_TRIP"
    DAILY_PASS = "DAILY_PASS"
    WEEKLY_PASS = "WEEKLY_PASS"
    MONTHLY_PASS = "MONTHLY_PASS"


# Payment Requests
class InitiatePaymentRequest(BaseModel):
    amount: float
    payment_method: PaymentMethod
    mobile_number: Optional[str] = None
    ticket_type: TicketType
    origin_stop_id: Optional[UUID] = None
    destination_stop_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    trip_id: Optional[UUID] = None
    description: Optional[str] = None
    return_url: Optional[str] = None


class AuthorizePaymentRequest(BaseModel):
    tx_ref: str
    otp: Optional[str] = None
    auth_data: Optional[Dict[str, Any]] = None


class VerifyPaymentRequest(BaseModel):
    tx_ref: str


# Payment Responses
class PaymentResponse(DateTimeModelMixin):
    id: str
    tx_ref: str
    amount: float
    currency: str
    payment_method: PaymentMethod
    customer_id: UUID
    status: PaymentStatus
    description: Optional[str] = None
    paid_at: Optional[datetime] = None
    failed_reason: Optional[str] = None


class InitiatePaymentResponse(BaseModel):
    tx_ref: str
    payment_id: str
    status: str
    auth_url: Optional[str] = None  # For portal view methods like Enat Bank
    message: str
    requires_authorization: bool = False


class AuthorizePaymentResponse(BaseModel):
    tx_ref: str
    status: str
    message: str
    authorization_completed: bool


class VerifyPaymentResponse(BaseModel):
    tx_ref: str
    status: PaymentStatus
    amount: float
    currency: str
    paid_at: Optional[datetime] = None
    chapa_reference: Optional[str] = None


# Ticket Requests
class CreateTicketRequest(BaseModel):
    ticket_type: TicketType
    origin_stop_id: Optional[UUID] = None
    destination_stop_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    trip_id: Optional[UUID] = None
    price: float


class ValidateTicketRequest(BaseModel):
    ticket_number: str
    trip_id: Optional[UUID] = None


# Ticket Responses
class TicketResponse(DateTimeModelMixin):
    id: str
    ticket_number: str
    customer_id: UUID
    payment_id: UUID
    ticket_type: TicketType
    origin_stop_id: Optional[UUID] = None
    destination_stop_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    trip_id: Optional[UUID] = None
    status: TicketStatus
    price: float
    currency: str
    valid_from: datetime
    valid_until: datetime
    used_at: Optional[datetime] = None
    qr_code: Optional[str] = None


class TicketQRResponse(BaseModel):
    ticket_number: str
    qr_code: str
    qr_image_url: Optional[str] = None


class ValidateTicketResponse(BaseModel):
    ticket_number: str
    is_valid: bool
    status: TicketStatus
    customer_name: str
    ticket_type: TicketType
    valid_until: datetime
    message: str


# Payment Method Requests
class CreatePaymentMethodRequest(BaseModel):
    method: PaymentMethod
    display_name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    processing_fee: Optional[float] = None
    processing_fee_percentage: Optional[float] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    is_active: bool = True


class UpdatePaymentMethodRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    processing_fee: Optional[float] = None
    processing_fee_percentage: Optional[float] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    is_active: Optional[bool] = None


# Payment Method Responses
class PaymentMethodResponse(DateTimeModelMixin):
    id: str
    method: PaymentMethod
    display_name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    processing_fee: Optional[float] = None
    processing_fee_percentage: Optional[float] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    is_active: bool


# Webhook and Callback schemas
class ChapaWebhookEvent(BaseModel):
    event: str  # payment.success, payment.failed, etc.
    data: Dict[str, Any]
    timestamp: datetime


class PaymentCallbackResponse(BaseModel):
    success: bool
    message: str
    payment_status: Optional[PaymentStatus] = None
