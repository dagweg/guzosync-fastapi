from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi_socketio import SocketManager
import googlemaps
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

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
    app.mongodb_client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    app.mongodb = app.mongodb_client[os.getenv("DATABASE_NAME")]

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

# Google Maps client
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

@app.get("/")
async def root():
    return {"message": "Hello World"}

# WebSocket event handlers
@socket_manager.on("connect")
async def handle_connect(sid, environ):
    print(f"Client connected: {sid}")

@socket_manager.on("disconnect")
async def handle_disconnect(sid):
    print(f"Client disconnected: {sid}")

@socket_manager.on("location_update")
async def handle_location_update(sid, data):
    # Store location update in MongoDB
    await app.mongodb.locations.insert_one({
        "user_id": data.get("user_id"),
        "location": {
            "type": "Point",
            "coordinates": [data.get("longitude"), data.get("latitude")]
        },
        "timestamp": data.get("timestamp")
    })
    # Broadcast location update to all connected clients
    await socket_manager.emit("location_broadcast", data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)