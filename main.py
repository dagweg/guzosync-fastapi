from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi_socketio import SocketManager
import googlemaps
from dotenv import load_dotenv
import os

# Import centralized logger
# from core.logger import setup_logging, get_logger
from core.logger import setup_logging, get_logger

# Import routers
from routers import accounts, account, notifications, config, buses, routes, feedback, issues, attendance

# Load environment variables
load_dotenv()

# Setup logging before anything else
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE")
)

logger = get_logger(__name__)

app = FastAPI(
    title="GuzoSync API",
    description="Backend API for GuzoSync transportation system",
    version="1.0.0"
)

socket_manager = SocketManager(app=app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
@app.on_event("startup")
async def startup_db_client():
    try:
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("DATABASE_NAME")
        
        if not mongodb_url or not database_name:
            logger.error("MongoDB configuration not found")
            raise RuntimeError("Database configuration missing")
            
        logger.info("Connecting to MongoDB...")
        
        # Configure UUID representation
        app.mongodb_client = AsyncIOMotorClient(
            mongodb_url,
            uuidRepresentation='standard'  # This is the key change
        )
        app.mongodb = app.mongodb_client[database_name]
        
        await app.mongodb.command('ping')
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error("Error connecting to MongoDB", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_db_client():
    try:
        logger.info("Closing MongoDB connection...")
        app.mongodb_client.close()
        logger.info("MongoDB connection closed successfully")
    except Exception as e:
        logger.error("Error closing MongoDB connection", exc_info=True)

# Include routers
app.include_router(accounts.router)
app.include_router(account.router)
app.include_router(notifications.router)
app.include_router(config.router)
app.include_router(buses.router)
app.include_router(routes.router)
app.include_router(feedback.router)
app.include_router(issues.router)
app.include_router(attendance.router)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to GuzoSync API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
