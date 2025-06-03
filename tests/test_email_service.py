#!/usr/bin/env python3
"""
Email Service Test Script

This script tests the email service configuration and sends test emails
to verify that the email functionality is working correctly.
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Add the parent directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.email_service import email_service
from core.email_config import validate_email_config, print_email_setup_guide

async def test_email_service():
    """Test the email service functionality"""
    print("🧪 TESTING EMAIL SERVICE")
    print("=" * 50)
    
    # Validate configuration
    config_validation = validate_email_config()
    
    if not config_validation["is_configured"]:
        print("❌ Email service is not properly configured!")
        print_email_setup_guide()
        return False
    
    print("✅ Email configuration validated")
    
    # Get test email address
    test_email = input("\nEnter your email address to receive test emails: ").strip()
    if not test_email:
        print("❌ No email address provided")
        return False
    
    print(f"\n📧 Sending test emails to: {test_email}")
    
    # Test 1: Welcome email
    print("\n1️⃣ Testing welcome email...")
    try:
        success = await email_service.send_welcome_email(test_email, "Test User")
        if success:
            print("   ✅ Welcome email sent successfully!")
        else:
            print("   ❌ Failed to send welcome email")
            return False
    except Exception as e:
        print(f"   ❌ Error sending welcome email: {e}")
        return False
    
    # Test 2: Password reset email
    print("\n2️⃣ Testing password reset email...")
    try:
        reset_link = "https://yourapp.com/reset-password?token=test123"
        success = await email_service.send_password_reset_email(test_email, reset_link)
        if success:
            print("   ✅ Password reset email sent successfully!")
        else:
            print("   ❌ Failed to send password reset email")
            return False
    except Exception as e:
        print(f"   ❌ Error sending password reset email: {e}")
        return False
    
    # Test 3: Personnel invitation email
    print("\n3️⃣ Testing personnel invitation email...")
    try:
        success = await email_service.send_personnel_invitation_email(
            test_email, "Test Personnel", "Control Staff", "temp123"
        )
        if success:
            print("   ✅ Personnel invitation email sent successfully!")
        else:
            print("   ❌ Failed to send personnel invitation email")
            return False
    except Exception as e:
        print(f"   ❌ Error sending personnel invitation email: {e}")
        return False
    
    # Test 4: Notification email
    print("\n4️⃣ Testing notification email...")
    try:
        success = await email_service.send_notification_email(
            test_email, 
            "Test Notification", 
            "This is a test notification email from GuzoSync.",
            "https://yourapp.com",
            "Visit App"
        )
        if success:
            print("   ✅ Notification email sent successfully!")
        else:
            print("   ❌ Failed to send notification email")
            return False
    except Exception as e:
        print(f"   ❌ Error sending notification email: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 ALL EMAIL TESTS PASSED!")
    print("Check your email inbox (and spam folder) for the test emails.")
    print("=" * 50)
    return True

async def main():
    """Main function"""
    # Load environment variables
    load_dotenv()
    
    print("GuzoSync Email Service Test")
    print("=" * 30)
    
    # Show configuration status
    config_validation = validate_email_config()
    if not config_validation["is_configured"]:
        print_email_setup_guide()
        print("\n❌ Please configure your email settings first!")
        return
    
    # Run tests
    try:
        success = await test_email_service()
        if success:
            print("\n✅ Email service is working correctly!")
        else:
            print("\n❌ Email service tests failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
