from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi_socketio import SocketManager
import googlemaps
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
from bson import UuidRepresentation  # Added import for UuidRepresentation

# Import centralized logger
from core.logger import setup_logging, get_logger
from core.action_logging_middleware import ActionLoggingMiddleware
from core.email_service import EmailConfig

# Import routers
from routers import (
    accounts, account, notifications, config, buses, routes, feedback, issues, attendance,
    alerts, conversations, drivers, regulators, control_center, trip, payments, websocket
)

# Load environment variables
load_dotenv()

# Setup logging before anything else
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "logs/guzosync.log"),
)

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME")

        if not mongodb_url or not database_name:
            logger.error("MongoDB configuration not found")
            raise RuntimeError("Database configuration missing")

        logger.info("Connecting to MongoDB...")

        # Modified: Added uuidRepresentation to AsyncIOMotorClient
        app.state.mongodb_client = AsyncIOMotorClient(
            mongodb_url,
            uuidRepresentation="unspecified"
        )
        app.state.mongodb = app.state.mongodb_client[database_name]

        await app.state.mongodb.command('ping')
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error("Error connecting to MongoDB", exc_info=True)
        raise

    yield

    # Shutdown
    try:
        logger.info("Closing MongoDB connection...")
        app.state.mongodb_client.close()
        logger.info("MongoDB connection closed successfully")
    except Exception as e:
        logger.error("Error closing MongoDB connection", exc_info=True)

app = FastAPI(
    title="GuzoSync API",
    description="Backend API for GuzoSync transportation system",
    version="1.0.0",
    lifespan=lifespan
)

# Add action logging middleware
app.add_middleware(ActionLoggingMiddleware)

socket_manager = SocketManager(app=app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(accounts.router)
app.include_router(account.router)
app.include_router(notifications.router)
app.include_router(config.router)
app.include_router(buses.router)
app.include_router(routes.router)
app.include_router(feedback.router)
app.include_router(trip.router)
app.include_router(issues.router)
app.include_router(attendance.router)
app.include_router(alerts.router)
app.include_router(conversations.router)
app.include_router(drivers.router)
app.include_router(regulators.router)
app.include_router(control_center.router)
# app.include_router(control_center_admin.router)
app.include_router(payments.router)
app.include_router(websocket.router)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to GuzoSync API"}

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    # Check email configuration
    email_config = EmailConfig()
    if email_config.is_configured():
        logger.info("✅ Email service is configured and ready")
    else:
        logger.warning("⚠️  Email service is not configured - emails will be logged only")
        logger.warning("   Add SMTP settings to .env file to enable email sending")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)