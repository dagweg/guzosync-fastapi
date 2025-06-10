from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import socketio
import googlemaps
from dotenv import load_dotenv
import os
import asyncio
from contextlib import asynccontextmanager
from bson import UuidRepresentation  # Added import for UuidRepresentation

# Import centralized logger
from core.logger import setup_logging, get_logger
from core.action_logging_middleware import ActionLoggingMiddleware
# EmailConfig is imported inside the lifespan function when needed
from core.realtime_analytics import RealTimeAnalyticsService
from core.scheduled_analytics import ScheduledAnalyticsService

# Import routers
from routers import (
    accounts, account, notifications, config, buses, routes, feedback, issues, attendance,
    alerts, conversations, drivers, regulators, control_center, approvals, trip, payments, websocket, socketio as socketio_router, realtime_demo, analytics
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

        # Modified: Added connection timeout and SSL configuration for Atlas
        app.state.mongodb_client = AsyncIOMotorClient(
            mongodb_url,
            uuidRepresentation="unspecified",
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,          # 5 second connection timeout
            socketTimeoutMS=5000,           # 5 second socket timeout
            maxPoolSize=10,                 # Limit connection pool
            retryWrites=True
        )
        app.state.mongodb = app.state.mongodb_client[database_name]
        
        # Test connection with timeout
        try:
            await asyncio.wait_for(app.state.mongodb.command('ping'), timeout=10.0)
            logger.info("Successfully connected to MongoDB")
        except asyncio.TimeoutError:
            logger.error("MongoDB ping timeout - continuing without database verification")
        except Exception as e:
            logger.error(f"MongoDB ping failed: {e} - continuing without database verification")
          # Seed database if empty
        logger.info("Checking database seeding...")
        try:
            bus_count = await app.state.mongodb.buses.count_documents({})
            bus_stop_count = await app.state.mongodb.bus_stops.count_documents({})
            route_count = await app.state.mongodb.routes.count_documents({})

            if bus_count == 0 or bus_stop_count == 0 or route_count == 0:
                logger.info(f"Database appears empty (buses: {bus_count}, stops: {bus_stop_count}, routes: {route_count})")
                logger.info("Consider running: python seed_db_startup.py --minimal")
            else:
                logger.info(f"Database has data (buses: {bus_count}, stops: {bus_stop_count}, routes: {route_count})")
        except Exception as e:
            logger.warning(f"Could not check database content: {e}")

        # Initialize analytics services
        logger.info("Initializing analytics services...")
        from core.realtime_analytics import RealTimeAnalyticsService
        from core.scheduled_analytics import ScheduledAnalyticsService
        from core.websocket_manager import websocket_manager
        
        # Initialize Socket.IO manager
        from core.socketio_manager import socketio_manager

        # Store app state in Socket.IO manager for authentication
        socketio_manager.set_app_state(app.state)

        # Initialize background tasks for Mapbox integration
        logger.info("Starting background tasks...")
        from core.services.background_tasks import background_task_service
        background_task_service.set_app_state(app.state)
        await background_task_service.start_background_tasks()
        logger.info("Background tasks started successfully")

        # Initialize real-time analytics service with Socket.IO
        try:
            app.state.realtime_analytics = RealTimeAnalyticsService(
                mongodb_client=app.state.mongodb,
                websocket_manager=socketio_manager  # Use Socket.IO manager instead
            )
            await app.state.realtime_analytics.start()
            logger.info("Real-time analytics service started")
        except Exception as e:
            logger.error(f"Failed to start real-time analytics service: {e}")
        
        # Initialize scheduled analytics service
        try:
            app.state.scheduled_analytics = ScheduledAnalyticsService(
                mongodb_client=app.state.mongodb
            )
            await app.state.scheduled_analytics.start()
            logger.info("Scheduled analytics service started")
        except Exception as e:
            logger.error(f"Failed to start scheduled analytics service: {e}")        # Check email configuration
        from core.email_service import EmailConfig
        email_config = EmailConfig()
        if email_config.is_configured():
            logger.info("✅ Email service is configured and ready")
        else:
            logger.warning("⚠️  Email service is not configured - emails will be logged only")
            logger.warning("   Add SMTP settings to .env file to enable email sending")

    except Exception as e:
        logger.error("Error during startup", exc_info=True)
        logger.warning("⚠️  Starting server in degraded mode without full database functionality")
        # Set minimal app state for Socket.IO manager
        try:
            from core.socketio_manager import socketio_manager
            socketio_manager.set_app_state(app.state)
            logger.info("Socket.IO manager initialized in degraded mode")
        except Exception as socket_error:
            logger.error(f"Failed to initialize Socket.IO in degraded mode: {socket_error}")
        # Don't raise - continue with degraded functionality
        # Set minimal app state for Socket.IO manager
        try:
            from core.socketio_manager import socketio_manager
            socketio_manager.set_app_state(app.state)
            logger.info("Socket.IO manager initialized in degraded mode")
        except Exception as socket_error:
            logger.error(f"Failed to initialize Socket.IO in degraded mode: {socket_error}")
        # Don't raise - continue with degraded functionality

    yield

    # Shutdown
    try:
        # Stop background tasks
        logger.info("Stopping background tasks...")
        from core.services.background_tasks import background_task_service
        await background_task_service.stop_background_tasks()
        logger.info("Background tasks stopped")

        # Stop analytics services
        if hasattr(app.state, 'realtime_analytics'):
            await app.state.realtime_analytics.stop()
            logger.info("Real-time analytics service stopped")

        if hasattr(app.state, 'scheduled_analytics'):
            await app.state.scheduled_analytics.stop()
            logger.info("Scheduled analytics service stopped")

        logger.info("Closing MongoDB connection...")
        app.state.mongodb_client.close()
        logger.info("MongoDB connection closed successfully")
    except Exception as e:
        logger.error("Error during shutdown", exc_info=True)

app = FastAPI(
    title="GuzoSync API",
    description="Backend API for GuzoSync transportation system",
    version="1.0.0",
    lifespan=lifespan
)

# Add action logging middleware
app.add_middleware(ActionLoggingMiddleware)

# socket_manager = SocketManager(app=app)  # Commented out - conflicts with native WebSocket

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
app.include_router(approvals.router)
app.include_router(payments.router)
app.include_router(analytics.router)
app.include_router(websocket.router)
app.include_router(socketio_router.router)
app.include_router(realtime_demo.router)

# Mount Socket.IO server
from core.socketio_manager import socketio_manager

# Create a custom ASGI app that handles both FastAPI and Socket.IO
async def custom_asgi_app(scope, receive, send):
    """Custom ASGI app that routes between FastAPI and Socket.IO"""
    if scope["type"] == "http" and scope["path"].startswith("/socket.io/"):
        # Handle Socket.IO requests
        return await socketio_manager.sio.handle_request(scope, receive, send)
    else:
        # Handle regular FastAPI requests
        return await app(scope, receive, send)

socket_app = custom_asgi_app

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to GuzoSync API"}

# Email configuration is now handled in the lifespan function above

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server with Socket.IO support...")
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)