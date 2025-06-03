from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from enum import Enum

from .base import BaseDBModel


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


class Payment(BaseDBModel):
    tx_ref: str  # Unique transaction reference
    amount: float
    currency: str = "ETB"
    payment_method: PaymentMethod
    mobile_number: Optional[str] = None
    customer_id: str  # User who made the payment
    customer_email: str
    customer_first_name: str
    customer_last_name: str
    status: PaymentStatus = PaymentStatus.PENDING
    chapa_tx_ref: Optional[str] = None  # Chapa's transaction reference
    chapa_response: Optional[Dict[str, Any]] = None  # Full Chapa response
    description: Optional[str] = None
    callback_url: Optional[str] = None
    return_url: Optional[str] = None
    webhook_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    failed_reason: Optional[str] = None


class Ticket(BaseDBModel):
    ticket_number: str  # Unique ticket identifier
    customer_id: str
    payment_id: str
    ticket_type: TicketType
    origin_stop_id: Optional[str] = None
    destination_stop_id: Optional[str] = None
    route_id: Optional[str] = None
    trip_id: Optional[str] = None
    status: TicketStatus = TicketStatus.ACTIVE
    price: float
    currency: str = "ETB"
    valid_from: datetime
    valid_until: datetime
    used_at: Optional[datetime] = None
    used_trip_id: Optional[str] = None
    qr_code: Optional[str] = None  # QR code data for validation
    metadata: Optional[Dict[str, Any]] = None  # Additional ticket data


class PaymentMethodConfig(BaseDBModel):
    method: PaymentMethod
    is_active: bool = True
    display_name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    processing_fee: Optional[float] = None
    processing_fee_percentage: Optional[float] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    configuration: Optional[Dict[str, Any]] = None  # Method-specific config
