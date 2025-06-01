from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List
from uuid import UUID

from models import User
from schemas.transport import BusStopResponse
from core.dependencies import get_current_user
from core import transform_mongo_doc

router = APIRouter(prefix="/api/regulators", tags=["regulators"])

@router.get("/bus-stops/{bus_stop_id}", response_model=BusStopResponse)
async def get_regulator_bus_stop(
    request: Request,
    bus_stop_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get bus stop information for regulators"""
    if current_user.role != "REGULATOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only regulators can access this endpoint"
        )
    
    # Check if regulator is assigned to this bus stop
    assignment = await request.app.state.mongodb.regulator_assignments.find_one({
        "regulator_id": current_user.id,
        "bus_stop_id": bus_stop_id
    })
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this bus stop"
        )
    
    bus_stop = await request.app.state.mongodb.bus_stops.find_one({"id": bus_stop_id})
    if not bus_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )
    
    return transform_mongo_doc(bus_stop, BusStopResponse)
