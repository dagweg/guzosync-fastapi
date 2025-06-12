#!/usr/bin/env python3
"""
Simple Payment Example - Python equivalent of JavaScript initiatePayment function

This example demonstrates how to use the new initiate_payment_simple function
that matches the JavaScript implementation exactly.

Usage:
    python examples/simple_payment_example.py

Requirements:
    - Set CHAPA_SECRET_KEY environment variable
    - Ensure the FastAPI server is running (for the HTTP endpoint example)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.chapa_service import chapa_service


async def test_direct_service_call():
    """Test the direct service call (without HTTP endpoint)"""
    print("=" * 60)
    print("Testing Direct Service Call")
    print("=" * 60)
    
    try:
        # Test parameters - matching JavaScript function signature
        amount = 100.0
        phone_number = "0911234567"
        booking_id = "booking-12345-test"
        callback_url = "https://your-app.com/payment/callback"
        
        print(f"Initiating payment:")
        print(f"  Amount: {amount} ETB")
        print(f"  Phone: {phone_number}")
        print(f"  Booking ID: {booking_id}")
        print(f"  Callback URL: {callback_url}")
        print(f"  Test Mode: {chapa_service.is_test_mode}")
        print()
        
        # Call the Python equivalent of JavaScript initiatePayment
        result = await chapa_service.initiate_payment_simple(
            amount=amount,
            phone_number=phone_number,
            booking_id=booking_id,
            callback_url=callback_url
        )
        
        print("✅ Payment initiated successfully!")
        print(f"  Checkout URL: {result['checkoutUrl']}")
        print(f"  Amount: {result['amount']} ETB")
        print()
        
        return result
        
    except Exception as e:
        print(f"❌ Payment initiation failed: {str(e)}")
        return None


async def test_http_endpoint():
    """Test the HTTP endpoint (requires running FastAPI server)"""
    print("=" * 60)
    print("Testing HTTP Endpoint")
    print("=" * 60)
    
    try:
        import httpx
        
        # Test parameters
        payload = {
            "amount": 150.0,
            "phone_number": "0911234567",
            "booking_id": "booking-67890-test",
            "callback_url": "https://your-app.com/payment/callback"
        }
        
        print(f"Making HTTP request to: http://localhost:8000/api/payments/initiate-simple")
        print(f"Payload: {payload}")
        print()
        
        # Note: This requires authentication token in real usage
        headers = {
            "Content-Type": "application/json",
            # "Authorization": "Bearer YOUR_JWT_TOKEN"  # Add this for real usage
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/payments/initiate-simple",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 201:
                result = response.json()
                print("✅ HTTP request successful!")
                print(f"  Checkout URL: {result['checkoutUrl']}")
                print(f"  Amount: {result['amount']} ETB")
                print()
                return result
            else:
                print(f"❌ HTTP request failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return None
                
    except ImportError:
        print("⚠️  httpx not installed. Install with: pip install httpx")
        return None
    except Exception as e:
        print(f"❌ HTTP request failed: {str(e)}")
        print("   Make sure the FastAPI server is running on http://localhost:8000")
        return None


def compare_with_javascript():
    """Show comparison with the original JavaScript function"""
    print("=" * 60)
    print("Comparison with JavaScript Function")
    print("=" * 60)
    
    javascript_code = '''
// Original JavaScript function
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
      throw new Error("Failed to initialize payment");
    }
    
    const data = await response.json();
    if (data && data.data && data.data.checkout_url) {
      return { checkoutUrl: data.data.checkout_url, amount };
    } else {
      throw new Error("Failed to initialize payment");
    }
  } catch (error) {
    throw new Error("Failed to initialize payment");
  }
};
'''
    
    python_code = '''
# Python equivalent
async def initiate_payment_simple(
    self, amount: float, phone_number: str, booking_id: str, callback_url: Optional[str] = None
) -> Dict[str, Any]:
    try:
        url = f"{self.base_url}/transaction/initialize"
        
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
        
        if callback_url:
            payload["callback_url"] = callback_url
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if not response.ok:
            raise Exception("Failed to initialize payment")
        
        data = response.json()
        if data and data.get("data") and data["data"].get("checkout_url"):
            return {"checkoutUrl": data["data"]["checkout_url"], "amount": amount}
        else:
            raise Exception("Failed to initialize payment")
    except Exception:
        raise Exception("Failed to initialize payment")
'''
    
    print("JavaScript (Original):")
    print(javascript_code)
    print("\nPython (Equivalent):")
    print(python_code)
    print("\n✅ Both functions have identical behavior and API structure!")


async def main():
    """Main function to run all tests"""
    print("🚀 Simple Payment Example - Python equivalent of JavaScript initiatePayment")
    print()
    
    # Check if Chapa secret key is set
    if not os.getenv("CHAPA_SECRET_KEY"):
        print("❌ CHAPA_SECRET_KEY environment variable is not set!")
        print("   Please set it before running this example.")
        print("   Example: export CHAPA_SECRET_KEY='your-chapa-secret-key'")
        return
    
    # Test direct service call
    await test_direct_service_call()
    
    # Test HTTP endpoint (optional)
    print("Would you like to test the HTTP endpoint? (requires running FastAPI server)")
    print("Press Enter to skip, or 'y' to test:")
    user_input = input().strip().lower()
    
    if user_input == 'y':
        await test_http_endpoint()
    
    # Show comparison
    compare_with_javascript()
    
    print("=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
