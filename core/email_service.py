"""
Email service module for sending emails
"""
import logging
import os
import ssl
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import aiosmtplib
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailConfig:
    """Email configuration class"""
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.email_from = os.getenv("EMAIL_FROM", "noreply@guzosync.com")
        self.app_name = "GuzoSync"
        self.app_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
        self.client_url = os.getenv("CLIENT_URL", "http://localhost:3000")
        
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.smtp_username and self.smtp_password)


class EmailService:
    """Email service for sending various types of emails"""
    
    def __init__(self):
        self.config = EmailConfig()
        # Get the templates directory path
        current_dir = Path(__file__).parent
        templates_dir = current_dir.parent / "templates" / "email"
        self.template_env = Environment(loader=FileSystemLoader(str(templates_dir)))
    
    async def _send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str, 
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email using SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.config.is_configured():
            logger.warning("Email service not configured. Skipping email send.")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.email_from
            msg['To'] = to_email
            
            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                start_tls=True,
                username=self.config.smtp_username,
                password=self.config.smtp_password,
                tls_context=context
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
        
    async def send_password_reset_email(self, email: str, reset_link: str) -> bool:
        """
        Send password reset email to user
        
        Args:
            email: User's email address
            reset_link: Password reset link
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            template = self.template_env.get_template('password_reset.html')
            html_content = template.render(
                app_name=self.config.app_name,
                reset_link=reset_link,
                app_url=self.config.app_url
            )
            
            subject = f"Password Reset - {self.config.app_name}"
            
            return await self._send_email(email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False    
    
    async def send_welcome_email(self, email: str, name: str) -> bool:
        """
        Send welcome email to new user
        
        Args:
            email: User's email address
            name: User's name
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            template = self.template_env.get_template('welcome.html')
            html_content = template.render(
                app_name=self.config.app_name,
                name=name,
                app_url=self.config.client_url
            )
            
            subject = f"Welcome to {self.config.app_name}!"
            
            return await self._send_email(email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return False

    async def send_personnel_invitation_email(
        self, 
        email: str, 
        name: str, 
        role: str, 
        temp_password: str
    ) -> bool:
        """
        Send personnel invitation email with login credentials
        
        Args:
            email: Personnel email address
            name: Personnel name
            role: Personnel role
            temp_password: Temporary password
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            template = self.template_env.get_template('personnel_invitation.html')
            html_content = template.render(
                app_name=self.config.app_name,
                name=name,
                role=role,
                email=email,
                temp_password=temp_password,
                login_url=f"{self.config.client_url}/login"
            )
            
            subject = f"Your {self.config.app_name} Personnel Account"
            
            return await self._send_email(email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send personnel invitation email to {email}: {str(e)}")
            return False

    async def send_notification_email(
        self, 
        email: str, 
        subject: str, 
        message: str, 
        action_url: Optional[str] = None,
        action_text: Optional[str] = None
    ) -> bool:
        """
        Send a generic notification email
        
        Args:
            email: Recipient email address
            subject: Email subject
            message: Email message content
            action_url: Optional action URL
            action_text: Optional action button text
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """        
        
        try:
            template = self.template_env.get_template('notification.html')
            html_content = template.render(
                app_name=self.config.app_name,
                subject=subject,
                message=message,
                action_url=action_url,
                action_text=action_text
            )
            
            return await self._send_email(email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send notification email to {email}: {str(e)}")
            return False


# Global email service instance
email_service = EmailService()


# Convenience functions for backward compatibility
async def send_password_reset_email(email: str, reset_link: str) -> bool:
    """Send password reset email to user"""
    return await email_service.send_password_reset_email(email, reset_link)


async def send_welcome_email(email: str, name: str) -> bool:
    """Send welcome email to new user"""
    return await email_service.send_welcome_email(email, name)
