# GuzoSync Backend API

The backend API for the GuzoSync transportation system, built with FastAPI and MongoDB.

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` file with required environment variables (see `.env.example`)
6. **Configure Email Service** (see Email Configuration section below)
7. Initialize the database with mock data: `python -m init_db --drop` (see [Database Initialization](docs/database-initialization.md))
8. Run the application: `uvicorn main:app --reload`

## Email Configuration

The application includes a comprehensive email service for sending:

- Welcome emails to new users
- Password reset emails
- Personnel invitation emails with credentials
- General notification emails

### Setup Email Service

1. **Add email settings to your `.env` file:**

   ```env
   # Email Configuration
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   EMAIL_FROM=noreply@guzosync.com
   ```

2. **For Gmail users:**

   - Enable 2-Factor Authentication
   - Generate an App Password (not your regular password)
   - Use the App Password in `SMTP_PASSWORD`

3. **Test your email configuration:**

   ```bash
   python test_email_service.py
   ```

4. **Check configuration status:**
   ```bash
   python -c "from core.email_config import print_email_setup_guide; print_email_setup_guide()"
   ```

### Email Templates

The service includes responsive HTML email templates with:

- Professional styling with your app branding
- Mobile-friendly responsive design
- Security warnings for sensitive emails
- Call-to-action buttons
- Footer with company information

### Email Service Features

- **Async SMTP with TLS encryption**
- **Automatic fallback** when email is not configured
- **Comprehensive logging** for debugging
- **Multiple provider support** (Gmail, Outlook, Yahoo, custom SMTP)
- **Template system** using Jinja2
- **Error handling** with detailed logging

## Documentation

- [Database Initialization](docs/database-initialization.md)
- [API Documentation](docs/apis.doc)
- [Payment Integration](docs/apis-payment.doc)
- [UUID Migration Guide](UUID_MIGRATION_GUIDE.md)
