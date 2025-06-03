"""
Email configuration settings and validation
"""
import os
from typing import Dict, Any, Optional

def validate_email_config() -> Dict[str, Any]:
    """
    Validate email configuration and return status
    
    Returns:
        Dict containing validation results and configuration info
    """
    config = {
        "smtp_server": os.getenv("SMTP_SERVER", ""),
        "smtp_port": os.getenv("SMTP_PORT", ""),
        "smtp_username": os.getenv("SMTP_USERNAME", ""),
        "smtp_password": os.getenv("SMTP_PASSWORD", ""),
        "email_from": os.getenv("EMAIL_FROM", ""),
    }
    
    missing_vars = [key for key, value in config.items() if not value]
    
    return {
        "is_configured": len(missing_vars) == 0,
        "missing_variables": missing_vars,
        "config": {k: "***" if "password" in k.lower() and v else v for k, v in config.items()},
        "recommendations": get_email_setup_recommendations()
    }

def get_email_setup_recommendations() -> Dict[str, Any]:
    """Get email setup recommendations for popular providers"""
    return {
        "gmail": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": "587",
            "note": "Use App Password instead of regular password. Enable 2FA first.",
            "docs": "https://support.google.com/accounts/answer/185833"
        },
        "outlook": {
            "smtp_server": "smtp-mail.outlook.com", 
            "smtp_port": "587",
            "note": "Use your regular Outlook credentials",
            "docs": "https://support.microsoft.com/en-us/office"
        },
        "yahoo": {
            "smtp_server": "smtp.mail.yahoo.com",
            "smtp_port": "587", 
            "note": "Use App Password. Enable 2FA first.",
            "docs": "https://help.yahoo.com/kb/generate-third-party-passwords-sln15241.html"
        },
        "custom": {
            "note": "Contact your email provider for SMTP settings",
            "common_ports": "587 (TLS), 465 (SSL), 25 (unsecured)"
        }
    }

def print_email_setup_guide():
    """Print a helpful guide for setting up email configuration"""
    validation = validate_email_config()
    
    print("=" * 60)
    print("📧 EMAIL SERVICE CONFIGURATION")
    print("=" * 60)
    
    if validation["is_configured"]:
        print("✅ Email service is properly configured!")
        print(f"   SMTP Server: {validation['config']['smtp_server']}")
        print(f"   SMTP Port: {validation['config']['smtp_port']}")
        print(f"   From Email: {validation['config']['email_from']}")
    else:
        print("❌ Email service is not configured.")
        print(f"   Missing variables: {', '.join(validation['missing_variables'])}")
        print("\n📝 Add these to your .env file:")
        print()
        print("SMTP_SERVER=smtp.gmail.com")
        print("SMTP_PORT=587")
        print("SMTP_USERNAME=your-email@gmail.com") 
        print("SMTP_PASSWORD=your-app-password")
        print("EMAIL_FROM=noreply@yourapp.com")
        
    print("\n🔧 PROVIDER SPECIFIC SETTINGS:")
    recommendations = validation["recommendations"]
    
    for provider, settings in recommendations.items():
        if provider == "custom":
            continue
        print(f"\n{provider.upper()}:")
        print(f"   Server: {settings['smtp_server']}")
        print(f"   Port: {settings['smtp_port']}")
        print(f"   Note: {settings['note']}")
        print(f"   Docs: {settings['docs']}")
    
    print("\n" + "=" * 60)
    print("💡 IMPORTANT NOTES:")
    print("- Use App Passwords for Gmail/Yahoo (not your regular password)")
    print("- Enable 2-Factor Authentication first for Gmail/Yahoo")
    print("- Test your configuration by sending a test email")
    print("- Check spam folder if emails don't arrive")
    print("=" * 60)

if __name__ == "__main__":
    print_email_setup_guide()
