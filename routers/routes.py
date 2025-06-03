from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from uuid import UUID

from core.dependencies import get_current_user
from models import User, Route
from schemas.route import RouteResponse
from core.realtime.bus_tracking import bus_tracking_service

from core import transform_mongo_doc

router = APIRouter(prefix="/api/routes", tags=["routes"])

@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(
    request: Request,
    route_id: UUID, 
    current_user: User = Depends(get_current_user)
):
    
    
    route = await request.app.state.mongodb.routes.find_one({"id": route_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    return transform_mongo_doc(route, RouteResponse)

@router.post("/{route_id}/track")
async def subscribe_to_route_tracking(
    route_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Subscribe to real-time tracking of all buses on a route"""
    await bus_tracking_service.subscribe_to_route(str(current_user.id), route_id)
    return {"message": f"Subscribed to route {route_id} tracking"}

@router.delete("/{route_id}/track")
async def unsubscribe_from_route_tracking(
    route_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Unsubscribe from real-time route tracking"""
    bus_tracking_service.unsubscribe_from_route(str(current_user.id), route_id)
    return {"message": f"Unsubscribed from route {route_id} tracking"}