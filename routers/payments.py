from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Header
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timedelta
import json

from core.dependencies import get_current_user
from models import User
from models.payment import Payment, Ticket, PaymentMethodConfig
from models.payment import PaymentStatus as ModelPaymentStatus, TicketStatus as ModelTicketStatus
from models.payment import PaymentMethod as ModelPaymentMethod, TicketType as ModelTicketType
from schemas.payment import (
    InitiatePaymentRequest, InitiatePaymentResponse,
    AuthorizePaymentRequest, AuthorizePaymentResponse,
    VerifyPaymentRequest, VerifyPaymentResponse,
    PaymentResponse, TicketResponse, TicketQRResponse,
    ValidateTicketRequest, ValidateTicketResponse,
    CreatePaymentMethodRequest, UpdatePaymentMethodRequest, PaymentMethodResponse,
    ChapaWebhookEvent, PaymentCallbackResponse,
    PaymentStatus, TicketStatus, PaymentMethod, TicketType
)


from core import transform_mongo_doc
from core.mongo_utils import model_to_mongo_doc
from core.chapa_service import chapa_service
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["payments"])

# Payment endpoints
@router.post("/payments/initiate", response_model=InitiatePaymentResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    request: Request,
    payment_request: InitiatePaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Initiate a payment for a bus ticket"""
    
    # Validate payment method is active
    payment_method_config = await request.app.state.mongodb.payment_method_configs.find_one({
        "method": payment_request.payment_method.value,
        "is_active": True
    })
    
    if not payment_method_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment method {payment_request.payment_method.value} is not available"
        )
    
    # Validate amount limits
    if payment_method_config.get("min_amount") and payment_request.amount < payment_method_config["min_amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount is below minimum limit of {payment_method_config['min_amount']} ETB"
        )
    
    if payment_method_config.get("max_amount") and payment_request.amount > payment_method_config["max_amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount exceeds maximum limit of {payment_method_config['max_amount']} ETB"
        )
    
    # Validate mobile number for USSD methods
    ussd_methods = [PaymentMethod.TELEBIRR, PaymentMethod.MPESA, PaymentMethod.CBEBIRR]
    if payment_request.payment_method in ussd_methods and not payment_request.mobile_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile number is required for this payment method"
        )
    
    try:
        # Initiate payment with Chapa
        chapa_response = await chapa_service.initiate_payment(
            payment_request,
            current_user.email,
            current_user.first_name,
            current_user.last_name
        )
          # Create payment record using Payment model
        payment = Payment(
            tx_ref=chapa_response["tx_ref"],
            amount=payment_request.amount,
            currency="ETB",
            payment_method=ModelPaymentMethod(payment_request.payment_method.value),
            mobile_number=payment_request.mobile_number,
            customer_id=current_user.id,
            customer_email=current_user.email,
            customer_first_name=current_user.first_name,
            customer_last_name=current_user.last_name,
            status=ModelPaymentStatus.PENDING,
            chapa_response=chapa_response.get("chapa_response"),
            description=payment_request.description,
            return_url=payment_request.return_url,
            webhook_url=chapa_service.webhook_url,
            created_at=datetime.utcnow()
        )
        
        # Convert model to MongoDB document
        payment_doc = model_to_mongo_doc(payment)
        result = await request.app.state.mongodb.payments.insert_one(payment_doc)
        payment_id = str(result.inserted_id)
          # Create pending ticket using Ticket model
        if chapa_response["status"] == "success" or chapa_response.get("requires_authorization"):
            ticket = Ticket(
                ticket_number=f"TKT-{uuid4().hex[:8].upper()}",
                customer_id=current_user.id,
                payment_id=payment_id,
                ticket_type=ModelTicketType(payment_request.ticket_type.value),
                origin_stop_id=payment_request.origin_stop_id,
                destination_stop_id=payment_request.destination_stop_id,
                route_id=payment_request.route_id,
                trip_id=payment_request.trip_id,
                status=ModelTicketStatus.ACTIVE,
                price=payment_request.amount,
                currency="ETB",
                valid_from=datetime.utcnow(),
                valid_until=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow()
            )
            
            # Convert model to MongoDB document
            ticket_doc = model_to_mongo_doc(ticket)
            await request.app.state.mongodb.tickets.insert_one(ticket_doc)
        
        return InitiatePaymentResponse(
            tx_ref=chapa_response["tx_ref"],
            payment_id=payment_id,
            status=chapa_response["status"],
            auth_url=chapa_response.get("auth_url"),
            message=chapa_response["message"],
            requires_authorization=chapa_response.get("requires_authorization", False)
        )
        
    except Exception as e:
        logger.error(f"Payment initiation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initiation failed: {str(e)}"
        )


@router.post("/payments/authorize", response_model=AuthorizePaymentResponse)
async def authorize_payment(
    request: Request,
    auth_request: AuthorizePaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Authorize a payment with OTP or other auth data"""
    
    # Find payment record
    payment = await request.app.state.mongodb.payments.find_one({
        "tx_ref": auth_request.tx_ref,
        "customer_id": current_user.id
    })
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment["status"] != ModelPaymentStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment is not in pending status"
        )
    
    try:
        # Authorize with Chapa
        chapa_response = await chapa_service.authorize_payment(
            auth_request.tx_ref,
            ModelPaymentMethod(payment["payment_method"]),
            auth_request.auth_data or {"otp": auth_request.otp}
        )
        
        # Update payment record
        update_data = {
            "chapa_response": chapa_response.get("chapa_response"),
            "updated_at": datetime.utcnow()
        }
        
        if chapa_response.get("authorization_completed"):
            update_data["status"] = ModelPaymentStatus.COMPLETED.value
            update_data["paid_at"] = datetime.utcnow()
            
            # Activate ticket
            await request.app.state.mongodb.tickets.update_one(
                {"payment_id": str(payment["_id"])},
                {"$set": {"status": ModelTicketStatus.ACTIVE.value}}
            )
        
        await request.app.state.mongodb.payments.update_one(
            {"_id": payment["_id"]},
            {"$set": update_data}
        )
        
        return AuthorizePaymentResponse(
            tx_ref=auth_request.tx_ref,
            status=chapa_response["status"],
            message=chapa_response["message"],
            authorization_completed=chapa_response.get("authorization_completed", False)
        )
        
    except Exception as e:
        logger.error(f"Payment authorization failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment authorization failed: {str(e)}"
        )


@router.post("/payments/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request: Request,
    verify_request: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Verify payment status with Chapa"""
    
    # Find payment record
    payment = await request.app.state.mongodb.payments.find_one({
        "tx_ref": verify_request.tx_ref,
        "customer_id": current_user.id
    })
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    try:
        # Verify with Chapa
        chapa_response = await chapa_service.verify_payment(verify_request.tx_ref)
        
        # Update payment record
        update_data = {
            "status": chapa_response["status"].value,
            "chapa_response": chapa_response.get("chapa_response"),
            "updated_at": datetime.utcnow()
        }
        
        if chapa_response["status"] == ModelPaymentStatus.COMPLETED:
            update_data["paid_at"] = chapa_response.get("paid_at") or datetime.utcnow()
            
            # Activate ticket and generate QR code
            ticket = await request.app.state.mongodb.tickets.find_one({"payment_id": str(payment["_id"])})
            if ticket:
                qr_code = chapa_service.generate_qr_code(ticket["ticket_number"])
                await request.app.state.mongodb.tickets.update_one(
                    {"_id": ticket["_id"]},
                    {"$set": {
                        "status": ModelTicketStatus.ACTIVE.value,
                        "qr_code": qr_code,
                        "updated_at": datetime.utcnow()
                    }}
                )
        elif chapa_response["status"] in [ModelPaymentStatus.FAILED, ModelPaymentStatus.CANCELLED]:
            # Cancel ticket
            await request.app.state.mongodb.tickets.update_one(
                {"payment_id": str(payment["_id"])},
                {"$set": {"status": ModelTicketStatus.CANCELLED.value}}
            )
        
        await request.app.state.mongodb.payments.update_one(
            {"_id": payment["_id"]},
            {"$set": update_data}
        )
        
        return VerifyPaymentResponse(
            tx_ref=verify_request.tx_ref,
            status=PaymentStatus(chapa_response["status"].value),
            amount=chapa_response.get("amount", payment["amount"]),
            currency=chapa_response.get("currency", "ETB"),
            paid_at=chapa_response.get("paid_at"),
            chapa_reference=chapa_response.get("chapa_reference")
        )
        
    except Exception as e:
        logger.error(f"Payment verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {str(e)}"
        )


@router.get("/payments", response_model=List[PaymentResponse])
async def get_user_payments(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get user's payment history"""
    
    payments = await request.app.state.mongodb.payments.find({
        "customer_id": current_user.id
    }).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(payment, PaymentResponse) for payment in payments]


# Ticket endpoints
@router.get("/tickets", response_model=List[TicketResponse])
async def get_user_tickets(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    ticket_status: Optional[TicketStatus] = None,
    current_user: User = Depends(get_current_user)
):
    """Get user's tickets"""
    
    query: Dict[str, Any] = {"customer_id": current_user.id}
    if ticket_status:
        query["status"] = ticket_status.value
        
    tickets = await request.app.state.mongodb.tickets.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(ticket, TicketResponse) for ticket in tickets]


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    request: Request,
    ticket_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific ticket details"""
    
    try:
        
        ticket_uuid = str(ticket_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ticket ID format"
        )
    
    ticket = await request.app.state.mongodb.tickets.find_one({
        "_id": str(ticket_uuid),
        "customer_id": current_user.id
    })
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return transform_mongo_doc(ticket, TicketResponse)


@router.get("/tickets/{ticket_id}/qr", response_model=TicketQRResponse)
async def get_ticket_qr(
    request: Request,
    ticket_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get ticket QR code"""
    
    try:
        
        ticket_uuid = str(ticket_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ticket ID format"
        )
    
    ticket = await request.app.state.mongodb.tickets.find_one({
        "_id": str(ticket_uuid),
        "customer_id": current_user.id,
        "status": ModelTicketStatus.ACTIVE.value
    })
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active ticket not found"
        )
    
    if not ticket.get("qr_code"):
        # Generate QR code if not exists
        qr_code = chapa_service.generate_qr_code(ticket["ticket_number"])
        await request.app.state.mongodb.tickets.update_one(
            {"_id": str(ticket_uuid)},
            {"$set": {"qr_code": qr_code}}
        )
        ticket["qr_code"] = qr_code
    
    return TicketQRResponse(
        ticket_number=ticket["ticket_number"],
        qr_code=ticket["qr_code"]
    )


@router.post("/tickets/validate", response_model=ValidateTicketResponse)
async def validate_ticket(
    request: Request,
    validate_request: ValidateTicketRequest,
    current_user: User = Depends(get_current_user)
):
    """Validate a ticket (for conductors/drivers)"""
    
    # Check if user has permission to validate tickets
    allowed_roles = ["BUS_DRIVER", "QUEUE_REGULATOR", "CONTROL_STAFF"]
    if current_user.role.value not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to validate tickets"
        )
    
    ticket = await request.app.state.mongodb.tickets.find_one({
        "ticket_number": validate_request.ticket_number
    })
    
    if not ticket:
        return ValidateTicketResponse(
            ticket_number=validate_request.ticket_number,
            is_valid=False,
            status=TicketStatus.CANCELLED,
            customer_name="Unknown",
            ticket_type=TicketType.SINGLE_TRIP,
            valid_until=datetime.utcnow(),
            message="Ticket not found"
        )
    
    # Get customer info
    customer = await request.app.state.mongodb.users.find_one({"_id": ticket["customer_id"]})
    customer_name = f"{customer['first_name']} {customer['last_name']}" if customer else "Unknown"
    
    # Check ticket validity
    is_valid = False
    message = ""
    
    if ticket["status"] == ModelTicketStatus.USED.value:
        message = "Ticket has already been used"
    elif ticket["status"] == ModelTicketStatus.CANCELLED.value:
        message = "Ticket has been cancelled"
    elif ticket["status"] == ModelTicketStatus.EXPIRED.value:
        message = "Ticket has expired"
    elif ticket["valid_until"] < datetime.utcnow():
        message = "Ticket has expired"
        # Update ticket status
        await request.app.state.mongodb.tickets.update_one(
            {"_id": ticket["_id"]},
            {"$set": {"status": ModelTicketStatus.EXPIRED.value}}
        )
    elif ticket["status"] == ModelTicketStatus.ACTIVE.value:
        is_valid = True
        message = "Ticket is valid"
        
        # Mark ticket as used
        update_data = {
            "status": ModelTicketStatus.USED.value,
            "used_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if validate_request.trip_id:
            update_data["used_trip_id"] = validate_request.trip_id
        
        await request.app.state.mongodb.tickets.update_one(
            {"_id": ticket["_id"]},
            {"$set": update_data}
        )
    
    return ValidateTicketResponse(
        ticket_number=validate_request.ticket_number,
        is_valid=is_valid,
        status=TicketStatus(ticket["status"]),
        customer_name=customer_name,
        ticket_type=TicketType(ticket["ticket_type"]),
        valid_until=ticket["valid_until"],
        message=message
    )


# Payment Methods Management
@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    request: Request,
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user)
):
    """Get available payment methods"""
    
    query = {}
    if active_only:
        query["is_active"] = True
    
    payment_methods = await request.app.state.mongodb.payment_method_configs.find(query).to_list(length=None)
    
    return [transform_mongo_doc(method, PaymentMethodResponse) for method in payment_methods]


@router.post("/payment-methods", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    request: Request,
    method_request: CreatePaymentMethodRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new payment method (admin only)"""
    
    if current_user.role.value not in ["CONTROL_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control admins can create payment methods"
        )
    
    # Check if method already exists
    existing = await request.app.state.mongodb.payment_method_configs.find_one({
        "method": method_request.method.value
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method already exists"
        )    # Create PaymentMethodConfig model instance
    payment_method_config = PaymentMethodConfig(
        method=ModelPaymentMethod(method_request.method.value),
        display_name=method_request.display_name,
        is_active=method_request.is_active,
        min_amount=method_request.min_amount,
        max_amount=method_request.max_amount,
        processing_fee=method_request.processing_fee,
        description=method_request.description,
        created_at=datetime.utcnow()
    )
    
    # Convert model to MongoDB document
    method_doc = model_to_mongo_doc(payment_method_config)
    # Add created_by separately since it's not part of the model
    method_doc["created_by"] = current_user.id
    result = await request.app.state.mongodb.payment_method_configs.insert_one(method_doc)
    created_method = await request.app.state.mongodb.payment_method_configs.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_method, PaymentMethodResponse)


@router.put("/payment-methods/{method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    request: Request,
    method_id: str,
    update_request: UpdatePaymentMethodRequest,
    current_user: User = Depends(get_current_user)
):
    """Update payment method (admin only)"""
    
    if current_user.role.value not in ["CONTROL_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,            detail="Only control admins can update payment methods"
        )
    
    try:
        
        method_uuid = str(method_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment method ID format"
        )
    
    update_data = {k: v for k, v in update_request.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await request.app.state.mongodb.payment_method_configs.update_one(
        {"_id": str(method_uuid)},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    updated_method = await request.app.state.mongodb.payment_method_configs.find_one({"_id": str(method_uuid)})
    return transform_mongo_doc(updated_method, PaymentMethodResponse)


# Webhook endpoint
@router.post("/payments/webhook/chapa")
async def chapa_webhook(
    request: Request,
    webhook_signature: Optional[str] = Header(None, alias="x-chapa-signature")
):
    """Handle Chapa webhook events"""
    
    try:
        body = await request.body()
        payload = body.decode()
        
        # Validate webhook signature
        if webhook_signature and not chapa_service.validate_webhook_signature(payload, webhook_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        webhook_data = json.loads(payload)
        event = ChapaWebhookEvent(**webhook_data)
        
        logger.info(f"Received Chapa webhook: {event.event}")
        
        # Process webhook event
        if event.event == "payment.success":
            await _handle_payment_success(request, event.data)
        elif event.event == "payment.failed":
            await _handle_payment_failed(request, event.data)
        elif event.event == "payment.cancelled":
            await _handle_payment_cancelled(request, event.data)
        
        return PaymentCallbackResponse(
            success=True,
            message="Webhook processed successfully"
        )
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


async def _handle_payment_success(request: Request, payment_data: Dict[str, Any]):
    """Handle successful payment webhook"""
    
    tx_ref = payment_data.get("tx_ref")
    if not tx_ref:
        return
    
    # Update payment status
    await request.app.state.mongodb.payments.update_one(
        {"tx_ref": tx_ref},
        {"$set": {
            "status": ModelPaymentStatus.COMPLETED.value,
            "paid_at": datetime.utcnow(),
            "chapa_response": payment_data,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Activate ticket
    payment = await request.app.state.mongodb.payments.find_one({"tx_ref": tx_ref})
    if payment:
        ticket = await request.app.state.mongodb.tickets.find_one({"payment_id": str(payment["_id"])})
        if ticket:
            qr_code = chapa_service.generate_qr_code(ticket["ticket_number"])
            await request.app.state.mongodb.tickets.update_one(
                {"_id": ticket["_id"]},
                {"$set": {
                    "status": ModelTicketStatus.ACTIVE.value,
                    "qr_code": qr_code,
                    "updated_at": datetime.utcnow()
                }}
            )


async def _handle_payment_failed(request: Request, payment_data: Dict[str, Any]):
    """Handle failed payment webhook"""
    
    tx_ref = payment_data.get("tx_ref")
    if not tx_ref:
        return
    
    # Update payment status
    await request.app.state.mongodb.payments.update_one(
        {"tx_ref": tx_ref},
        {"$set": {
            "status": ModelPaymentStatus.FAILED.value,
            "failed_reason": payment_data.get("message", "Payment failed"),
            "chapa_response": payment_data,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Cancel ticket
    payment = await request.app.state.mongodb.payments.find_one({"tx_ref": tx_ref})
    if payment:
        await request.app.state.mongodb.tickets.update_one(
            {"payment_id": str(payment["_id"])},
            {"$set": {
                "status": ModelTicketStatus.CANCELLED.value,
                "updated_at": datetime.utcnow()
            }}
        )


async def _handle_payment_cancelled(request: Request, payment_data: Dict[str, Any]):
    """Handle cancelled payment webhook"""
    
    tx_ref = payment_data.get("tx_ref")
    if not tx_ref:
        return
    
    # Update payment status
    await request.app.state.mongodb.payments.update_one(
        {"tx_ref": tx_ref},
        {"$set": {
            "status": ModelPaymentStatus.CANCELLED.value,
            "chapa_response": payment_data,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Cancel ticket
    payment = await request.app.state.mongodb.payments.find_one({"tx_ref": tx_ref})
    if payment:
        await request.app.state.mongodb.tickets.update_one(
            {"payment_id": str(payment["_id"])},
            {"$set": {
                "status": ModelTicketStatus.CANCELLED.value,
                "updated_at": datetime.utcnow()
            }}
        )
