"""
Configuration settings for the application
"""
import os
from typing import Optional


class Settings:
    """Application settings"""

    def __init__(self):
        # Database Configuration
        self.MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.DATABASE_NAME: str = os.getenv("DATABASE_NAME", "guzosync")

        # Server Configuration
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.HOST: str = os.getenv("HOST", "0.0.0.0")

        # JWT Configuration
        self.JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-here")
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

        # Security Configuration
        self.BCRYPT_SALT_ROUNDS: int = int(os.getenv("BCRYPT_SALT_ROUNDS", "12"))

        # External APIs
        self.GOOGLE_MAPS_API_KEY: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY")
        self.MAPBOX_ACCESS_TOKEN: Optional[str] = os.getenv("MAPBOX_ACCESS_TOKEN")

        # Redis Configuration
        self.REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Email Configuration
        self.SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
        self.SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
        self.EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@guzosync.com")

        # Chapa Payment Configuration
        self.CHAPA_SECRET_KEY: Optional[str] = os.getenv("CHAPA_SECRET_KEY")
        self.CHAPA_PUBLIC_KEY: Optional[str] = os.getenv("CHAPA_PUBLIC_KEY")
        self.CHAPA_BASE_URL: str = os.getenv("CHAPA_BASE_URL", "https://api.chapa.co/v1")
        self.CHAPA_WEBHOOK_SECRET: Optional[str] = os.getenv("CHAPA_WEBHOOK_SECRET")

        # Application URLs
        self.APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
        self.CLIENT_URL: str = os.getenv("CLIENT_URL", "http://localhost:3000")

        # Logging Configuration
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE: str = os.getenv("LOG_FILE", "logs/guzosync.log")

        # Environment
        self.NODE_ENV: str = os.getenv("NODE_ENV", "development")


# Create a global settings instance
settings = Settings()
