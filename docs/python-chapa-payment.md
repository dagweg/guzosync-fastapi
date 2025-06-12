# Python Equivalent of JavaScript Chapa Payment Function

This document explains the Python equivalent of the JavaScript `initiatePayment` function for Chapa payment integration.

## Overview

The JavaScript function you provided has been converted to Python with identical functionality and API structure. The Python implementation maintains the same:

- Function signature and parameters
- API endpoint usage (`/transaction/initialize`)
- Request payload structure
- Response handling
- Error handling patterns

## JavaScript vs Python Comparison

### JavaScript (Original)
```javascript
exports.initiatePayment = async (amount, phone_number, bookingId, callback_url) => {
  try {
    const url = `${chapaBaseUrl}/transaction/initialize`;
    
    const payload = {
      amount: amount.toString(),
      currency: "ETB",
      phone_number,
      tx_ref: bookingId,
      callback_url,
      customization: {
        title: "Payment for Ride",
        description: "Ride payment",
      },
    };
    
    const headers = {
      Authorization: `Bearer ${chapaSecretKey}`,
      "Content-Type": "application/json",
    };
    
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    
    if (!response.ok) {
      const error = await response.text();
      logger.error(`Chapa API Error: ${response.status} : ${response.statusText} : ${error}`);
      throw new Error("Failed to initialize payment");
    }
    
    const data = await response.json();
    if (data && data.data && data.data.checkout_url) {
      logger.info(`Payment initialized with Chapa for driver ID ${bookingId}`);
      return { checkoutUrl: data.data.checkout_url, amount };
    } else {
      logger.error("Chapa API Error: Response does not have checkout_url");
      throw new Error("Failed to initialize payment");
    }
  } catch (error) {
    logger.error(`Failed to initialize payment for booking ID: ${bookingId}, Error: ${error}`);
    throw new Error("Failed to initialize payment");
  }
};
```

### Python (Equivalent)
```python
async def initiate_payment_simple(
    self,
    amount: float,
    phone_number: str,
    booking_id: str,
    callback_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Python equivalent of the JavaScript initiatePayment function.
    
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
                "title": "Payment for Ride",
                "description": "Ride payment",
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
```

## Usage Examples

### 1. Direct Service Call
```python
from core.chapa_service import chapa_service

async def example_payment():
    try:
        result = await chapa_service.initiate_payment_simple(
            amount=100.0,
            phone_number="0911234567",
            booking_id="booking-12345",
            callback_url="https://your-app.com/callback"
        )
        
        print(f"Checkout URL: {result['checkoutUrl']}")
        print(f"Amount: {result['amount']} ETB")
        
    except Exception as e:
        print(f"Payment failed: {str(e)}")
```

### 2. HTTP Endpoint Usage
```python
import httpx

async def example_http_payment():
    payload = {
        "amount": 100.0,
        "phone_number": "0911234567",
        "booking_id": "booking-12345",
        "callback_url": "https://your-app.com/callback"
    }
    
    headers = {
        "Authorization": "Bearer YOUR_JWT_TOKEN",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/payments/initiate-simple",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"Checkout URL: {result['checkoutUrl']}")
            print(f"Amount: {result['amount']} ETB")
```

## Configuration

### Environment Variables
```bash
# Required
CHAPA_SECRET_KEY=your-chapa-secret-key

# Optional
CHAPA_PUBLIC_KEY=your-chapa-public-key
CHAPA_BASE_URL=https://api.chapa.co/v1
CHAPA_WEBHOOK_SECRET=your-webhook-secret
```

### Test Mode Detection
The Python implementation includes automatic test mode detection:
```python
@property
def is_test_mode(self) -> bool:
    """Check if we're in test mode based on secret key"""
    return bool(self.secret_key and 'TEST' in self.secret_key.upper())
```

## Key Features

1. **Identical API**: Same function signature and behavior as JavaScript version
2. **Same Endpoint**: Uses `/transaction/initialize` endpoint like the JavaScript version
3. **Compatible Response**: Returns the same `{checkoutUrl, amount}` structure
4. **Error Handling**: Matches JavaScript error handling patterns
5. **Logging**: Comprehensive logging for debugging and monitoring
6. **Type Safety**: Full type hints for better development experience
7. **Async Support**: Native async/await support

## Integration with Existing Codebase

The Python function integrates seamlessly with the existing FastAPI application:

- Uses the same `ChapaPaymentService` class
- Leverages existing configuration and environment variables
- Maintains compatibility with existing logging and error handling
- Provides both direct service access and HTTP endpoint

## Testing

Run the example script to test the implementation:
```bash
# Set your Chapa secret key
export CHAPA_SECRET_KEY="your-chapa-secret-key"

# Run the example
python examples/simple_payment_example.py
```

## Differences from Existing Payment System

This simple payment function differs from the existing comprehensive payment system in that it:

- **Simpler**: Focuses only on payment initialization
- **Direct**: Uses Chapa's `/transaction/initialize` endpoint directly
- **Minimal**: Doesn't create database records or tickets
- **Compatible**: Matches the JavaScript function exactly

Use this for simple payment scenarios where you don't need the full ticket management system.
