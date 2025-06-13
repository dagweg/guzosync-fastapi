import os
import secrets
import hashlib
import base64
import qrcode
import requests
import json
from io import BytesIO
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4
import logging

from models.payment import Payment, PaymentStatus, PaymentMethod
from schemas.payment import InitiatePaymentRequest

# Setup logger
logger = logging.getLogger(__name__)


class ChapaPaymentService:
    def __init__(self):
        self.base_url = "https://api.chapa.co/v1"
        self.secret_key = os.getenv("CHAPA_SECRET_KEY")
        self.public_key = os.getenv("CHAPA_PUBLIC_KEY")
        self.encryption_key = os.getenv("CHAPA_ENCRYPTION_KEY")
        self.webhook_url = os.getenv("CHAPA_WEBHOOK_URL")

        if not self.secret_key:
            raise ValueError("CHAPA_SECRET_KEY environment variable is required")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Chapa API requests"""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

    def _get_form_headers(self) -> Dict[str, str]:
        """Get headers for form-data requests"""
        return {
            "Authorization": f"Bearer {self.secret_key}"
        }

    def generate_tx_ref(self) -> str:
        """Generate unique transaction reference"""
        return f"guzosync-{uuid4().hex[:12]}-{int(datetime.utcnow().timestamp())}"

    @property
    def is_test_mode(self) -> bool:
        """Check if we're in test mode based on secret key"""
        return bool(self.secret_key and 'TEST' in self.secret_key.upper())

    async def initiate_payment_simple(
        self,
        amount: float,
        phone_number: str,
        booking_id: str,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Python equivalent of the JavaScript initiatePayment function.

        This function matches the JavaScript implementation exactly:
        - Uses the /transaction/initialize endpoint
        - Takes amount, phone_number, booking_id, and callback_url
        - Returns checkoutUrl and amount on success

        Args:
            amount: Payment amount in ETB
            phone_number: Customer's phone number
            booking_id: Unique booking/transaction reference
            callback_url: Optional callback URL for payment completion

        Returns:
            Dict containing checkoutUrl and amount on success

        Raises:
            Exception: If payment initialization fails
        """
        try:
            # Chapa API endpoint - matches JavaScript implementation
            url = f"{self.base_url}/transaction/initialize"

            # Prepare payload - matches JavaScript structure exactly
            payload = {
                "amount": str(amount),
                "currency": "ETB",
                "phone_number": phone_number,
                "tx_ref": booking_id,
                "customization": {
                    "title": "Ride Payment",
                    "description": "Bus Ride payment",
                }
            }

            # Add callback_url if provided
            if callback_url:
                payload["callback_url"] = callback_url

            # Prepare headers - matches JavaScript implementation
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }

            # Make the API request
            response = requests.post(url, json=payload, headers=headers)

            # Handle non-200 responses
            if not response.ok:
                error_text = response.text
                logger.error(
                    f"Chapa API Error: {response.status_code} : {response.reason} : {error_text}"
                )
                raise Exception("Failed to initialize payment")

            # Parse response
            data = response.json()

            # Validate response structure - matches JavaScript validation
            if data and data.get("data") and data["data"].get("checkout_url"):
                logger.info(f"Payment initialized with Chapa for booking ID {booking_id}")
                return {
                    "checkoutUrl": data["data"]["checkout_url"],
                    "amount": amount
                }
            else:
                logger.error("Chapa API Error: Response does not have checkout_url")
                raise Exception("Failed to initialize payment")

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to initialize payment for booking ID: {booking_id}, Error: {str(e)}"
            )
            raise Exception("Failed to initialize payment")
        except Exception as e:
            logger.error(
                f"Failed to initialize payment for booking ID: {booking_id}, Error: {str(e)}"
            )
            raise Exception("Failed to initialize payment")

    async def initiate_payment(
        self,
        payment_request: InitiatePaymentRequest,
        customer_email: str,
        customer_first_name: str,
        customer_last_name: str
    ) -> Dict[str, Any]:
        """Initiate payment with Chapa"""

        tx_ref = self.generate_tx_ref()

        if payment_request.payment_method in [PaymentMethod.TELEBIRR, PaymentMethod.MPESA,
                                             PaymentMethod.CBEBIRR, PaymentMethod.EBIRR]:
            return await self._initiate_ussd_payment(
                payment_request, tx_ref, customer_email,
                customer_first_name, customer_last_name
            )

        raise ValueError(f"Unsupported payment method: {payment_request.payment_method}")

    async def _initiate_ussd_payment(
        self,
        payment_request: InitiatePaymentRequest,
        tx_ref: str,
        customer_email: str,
        customer_first_name: str,
        customer_last_name: str
    ) -> Dict[str, Any]:
        """Initiate USSD-based payment (Telebirr, M-Pesa, etc.)"""

        url = f"{self.base_url}/charges?type={payment_request.payment_method.value}"

        # Prepare form data
        data = {
            "amount": str(payment_request.amount),
            "currency": "ETB",
            "tx_ref": tx_ref,
            "mobile": payment_request.mobile_number,
            "email": customer_email,
            "first_name": customer_first_name,
            "last_name": customer_last_name,
            "description": payment_request.description or f"Bus ticket payment - {payment_request.ticket_type.value}",
        }

        if self.webhook_url:
            data["webhook_url"] = self.webhook_url

        if payment_request.return_url:
            data["return_url"] = payment_request.return_url

        try:
            response = requests.post(url, data=data, headers=self._get_form_headers())
            response.raise_for_status()

            result = response.json()
            logger.info(f"Chapa payment initiated: {tx_ref}", extra={"chapa_response": result})

            return {
                "tx_ref": tx_ref,
                "status": result.get("status", "pending"),
                "message": result.get("message", "Payment initiated successfully"),
                "requires_authorization": True,
                "auth_type": "ussd",
                "chapa_response": result
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Chapa payment initiation failed: {str(e)}")
            raise Exception(f"Payment initiation failed: {str(e)}")

    async def _initiate_portal_payment(
        self,
        payment_request: InitiatePaymentRequest,
        tx_ref: str,
        customer_email: str,
        customer_first_name: str,
        customer_last_name: str
    ) -> Dict[str, Any]:
        """Initiate portal-based payment (Enat Bank)"""

        url = f"{self.base_url}/charges?type={payment_request.payment_method.value}"

        data = {
            "amount": str(payment_request.amount),
            "currency": "ETB",
            "tx_ref": tx_ref,
            "email": customer_email,
            "first_name": customer_first_name,
            "last_name": customer_last_name,
            "description": payment_request.description or f"Bus ticket payment - {payment_request.ticket_type.value}",
        }

        if self.webhook_url:
            data["webhook_url"] = self.webhook_url

        if payment_request.return_url:
            data["return_url"] = payment_request.return_url

        try:
            response = requests.post(url, data=data, headers=self._get_form_headers())
            response.raise_for_status()

            result = response.json()
            logger.info(f"Chapa portal payment initiated: {tx_ref}", extra={"chapa_response": result})

            return {
                "tx_ref": tx_ref,
                "status": result.get("status", "pending"),
                "message": result.get("message", "Payment initiated successfully"),
                "auth_url": result.get("checkout_url"),
                "requires_authorization": True,
                "auth_type": "portal",
                "chapa_response": result
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Chapa portal payment initiation failed: {str(e)}")
            raise Exception(f"Payment initiation failed: {str(e)}")

    async def authorize_payment(
        self,
        tx_ref: str,
        payment_method: PaymentMethod,
        auth_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Authorize payment with OTP or other auth method"""

        url = f"{self.base_url}/validate?type={payment_method.value}"

        # Prepare authorization data
        if payment_method in [PaymentMethod.TELEBIRR, PaymentMethod.MPESA]:
            # For OTP-based authorization
            otp = auth_data.get("otp")
            if not otp:
                raise ValueError("OTP is required for this payment method")

            # Encrypt OTP if needed (3DES encryption)
            encrypted_otp = self._encrypt_otp(otp) if self.encryption_key else otp

            payload = {
                "tx_ref": tx_ref,
                "otp": encrypted_otp
            }
        else:
            # For other methods
            payload = {
                "tx_ref": tx_ref,
                **auth_data
            }

        try:
            response = requests.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()

            result = response.json()
            logger.info(f"Chapa payment authorized: {tx_ref}", extra={"chapa_response": result})

            return {
                "tx_ref": tx_ref,
                "status": result.get("status", "pending"),
                "message": result.get("message", "Payment authorized successfully"),
                "authorization_completed": result.get("status") == "success",
                "chapa_response": result
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Chapa payment authorization failed: {str(e)}")
            raise Exception(f"Payment authorization failed: {str(e)}")

    async def verify_payment(self, tx_ref: str) -> Dict[str, Any]:
        """Verify payment status with Chapa"""

        url = f"{self.base_url}/verify/{tx_ref}"

        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()

            result = response.json()
            logger.info(f"Chapa payment verified: {tx_ref}", extra={"chapa_response": result})

            # Parse Chapa response
            status = result.get("status", "pending").lower()
            payment_status = PaymentStatus.PENDING

            if status == "success":
                payment_status = PaymentStatus.COMPLETED
            elif status == "failed":
                payment_status = PaymentStatus.FAILED
            elif status == "cancelled":
                payment_status = PaymentStatus.CANCELLED

            return {
                "tx_ref": tx_ref,
                "status": payment_status,
                "amount": result.get("amount"),
                "currency": result.get("currency", "ETB"),
                "paid_at": result.get("created_at"),
                "chapa_reference": result.get("reference"),
                "chapa_response": result
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Chapa payment verification failed: {str(e)}")
            raise Exception(f"Payment verification failed: {str(e)}")

    def _encrypt_otp(self, otp: str) -> str:
        """Encrypt OTP using 3DES algorithm"""
        if not self.encryption_key:
            logger.warning("CHAPA_ENCRYPTION_KEY is not set. OTP encryption skipped.")
            return otp

        # This is a simplified encryption example
        # In production, implement proper 3DES encryption with your key
        try:
            from Crypto.Cipher import DES3
            from Crypto.Util.Padding import pad

            key = self.encryption_key.encode()[:24]  # 3DES key should be 24 bytes
            cipher = DES3.new(key, DES3.MODE_ECB)

            padded_otp = pad(otp.encode(), DES3.block_size)
            encrypted = cipher.encrypt(padded_otp)

            return base64.b64encode(encrypted).decode()
        except ImportError:
            logger.warning("PyCrypto not available, OTP encryption skipped")
            return otp
        except Exception as e:
            logger.error(f"OTP encryption failed: {str(e)}")
            return otp

    def generate_qr_code(self, ticket_number: str) -> str:
        """Generate QR code for ticket"""

        # Create QR code data
        qr_data = f"GUZOSYNC-TICKET:{ticket_number}:{int(datetime.utcnow().timestamp())}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        # Generate QR code image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64 string
        buffer = BytesIO()
        img.save(buffer, kind='PNG')
        qr_image_base64 = base64.b64encode(buffer.getvalue()).decode()

        return qr_image_base64

    def validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """Validate Chapa webhook signature"""
        if not self.secret_key:
            return False

        expected_signature = hashlib.sha256(
            (payload + self.secret_key).encode()
        ).hexdigest()

        return secrets.compare_digest(signature, expected_signature)


# Create singleton instance
chapa_service = ChapaPaymentService()
