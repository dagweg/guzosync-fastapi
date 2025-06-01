from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from uuid import UUID

from models import User, Bus, BusStop
from schemas.transport import BusResponse, BusStopResponse
from schemas.trip import SimplifiedTripResponse
from routers.accounts import get_current_user

router = APIRouter(prefix="/api/buses", tags=["buses"])

@router.get("/{bus_id}", response_model=BusResponse)
async def get_bus(bus_id: UUID, current_user: User = Depends(get_current_user)):
    
    
    bus = await request.app.mongodb.buses.find_one({"id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    return BusResponse(**bus)

@router.get("/stops", response_model=List[BusStopResponse])
async def get_bus_stops(
    search: Optional[str] = None,
    filter_by: Optional[str] = None,
    page: int = Query(1, alias="pn", ge=1),
    page_size: int = Query(10, alias="ps", ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    
    
    # Build query
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if filter_by:
        # Add filter logic based on filter_by parameter
        pass
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    # Get bus stops
    bus_stops = await request.app.mongodb.bus_stops.find(query).skip(skip).limit(page_size).to_list(length=page_size)
    
    return [BusStopResponse(**stop) for stop in bus_stops]

@router.get("/stops/{bus_stop_id}", response_model=BusStopResponse)
async def get_bus_stop(bus_stop_id: UUID, current_user: User = Depends(get_current_user)):
    
    
    bus_stop = await request.app.mongodb.bus_stops.find_one({"id": bus_stop_id})
    if not bus_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )
    
    return BusStopResponse(**bus_stop)

@router.get("/stops/{bus_stop_id}/incoming-buses", response_model=List[SimplifiedTripResponse])
async def get_incoming_buses(bus_stop_id: UUID, current_user: User = Depends(get_current_user)):
    
    
    # First, verify bus stop exists
    bus_stop = await request.app.mongodb.bus_stops.find_one({"id": bus_stop_id})
    if not bus_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )
    
    # Find routes that include this bus stop
    routes = await request.app.mongodb.routes.find(
        {"stop_ids": bus_stop_id}
    ).to_list(length=None)
    route_ids = [route["id"] for route in routes]
    
    # Find active trips on these routes
    trips = await request.app.mongodb.trips.find({
        "route_id": {"$in": route_ids},
        "status": {"$in": ["SCHEDULED", "IN_PROGRESS"]}
    }).to_list(length=None)
    
    return [SimplifiedTripResponse(**trip) for trip in trips]

@router.post("/reallocate")
async def request_bus_reallocation(current_user: User = Depends(get_current_user)):
    # Implementation for bus reallocation request
    pass

@router.get("/reallocation/requests")
async def get_reallocation_requests(current_user: User = Depends(get_current_user)):
    # Implementation for getting reallocation requests
    pass