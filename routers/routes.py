from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Optional
from datetime import datetime

from core.dependencies import get_current_user
from models import User, Route
from models.user import UserRole
from schemas.route import RouteResponse, CreateRouteRequest, UpdateRouteRequest
from core.realtime.bus_tracking import bus_tracking_service

from core import transform_mongo_doc, generate_uuid
from core.mongo_utils import model_to_mongo_doc

router = APIRouter(prefix="/api/routes", tags=["routes"])

@router.post("/", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(
    request: Request,
    route_data: CreateRouteRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new route (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can create routes"
        )
    
    # Create Route model instance with UUID
    route = Route(
        name=route_data.name,
        description=route_data.description,
        stop_ids=route_data.stop_ids,
        total_distance=route_data.total_distance,
        estimated_duration=route_data.estimated_duration,
        is_active=route_data.is_active if route_data.is_active is not None else True
    )
    
    # Convert to MongoDB document
    route_doc = model_to_mongo_doc(route)
    
    result = await request.app.state.mongodb.routes.insert_one(route_doc)
    created_route = await request.app.state.mongodb.routes.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_route, RouteResponse)

@router.get("/", response_model=List[RouteResponse])
async def get_all_routes(
    request: Request,
    search: Optional[str] = Query(None, description="Search routes by name or description"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of routes per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user)
):
    """Get all routes with search, filtering, and pagination"""
    skip = (page - 1) * limit
    
    # Build search query
    query_filter: dict = {}
    
    # Add search functionality
    if search:
        query_filter["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    # Add active status filter
    if is_active is not None:
        query_filter["is_active"] = is_active
    
    # Get paginated routes with search
    routes_cursor = request.app.state.mongodb.routes.find(query_filter).skip(skip).limit(limit)
    routes = await routes_cursor.to_list(length=limit)
    
    # Transform routes
    return [transform_mongo_doc(route, RouteResponse) for route in routes]
    
    
@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(
    request: Request,
    route_id: str, 
    current_user: User = Depends(get_current_user)
):
    
    
    route = await request.app.state.mongodb.routes.find_one({"_id": route_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    return transform_mongo_doc(route, RouteResponse)

@router.put("/{route_id}", response_model=RouteResponse)
async def update_route(
    request: Request,
    route_id: str,
    update_data: UpdateRouteRequest,
    current_user: User = Depends(get_current_user)
):
    """Update an existing route (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update routes"
        )
    
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await request.app.state.mongodb.routes.update_one(
        {"_id": route_id},
        {"$set": update_dict}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    updated_route = await request.app.state.mongodb.routes.find_one({"_id": route_id})
    return transform_mongo_doc(updated_route, RouteResponse)

@router.delete("/{route_id}")
async def delete_route(
    request: Request,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a route (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can delete routes"
        )
    
    result = await request.app.state.mongodb.routes.delete_one({"_id": route_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    return {"message": "Route deleted successfully"}

@router.post("/{route_id}/track")
async def subscribe_to_route_tracking(
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Subscribe to real-time tracking of all buses on a route"""
    await bus_tracking_service.subscribe_to_route(str(current_user.id), route_id)
    return {"message": f"Subscribed to route {route_id} tracking"}

@router.delete("/{route_id}/track")
async def unsubscribe_from_route_tracking(
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Unsubscribe from real-time route tracking"""
    await bus_tracking_service.unsubscribe_from_route(str(current_user.id), route_id)
    return {"message": f"Unsubscribed from route {route_id} tracking"}