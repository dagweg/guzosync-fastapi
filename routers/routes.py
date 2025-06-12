from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Optional, Union
from datetime import datetime

from core.dependencies import get_current_user
from models import User, Route, Bus, BusStop
from models.user import UserRole
from models.base import Location
from schemas.route import (
    RouteResponse, CreateRouteRequest, UpdateRouteRequest,
    ETAResponse, RouteShapeResponse, BusETAResponse, RouteWithStopsResponse
)
from schemas.transport import BusStopResponse
from core.realtime.bus_tracking import bus_tracking_service

from core import transform_mongo_doc, generate_uuid
from core.mongo_utils import model_to_mongo_doc
from core.services.route_service import route_service
from core.services.mapbox_service import mapbox_service

router = APIRouter(prefix="/api/routes", tags=["routes"])

# Helper functions for populating bus stops in routes
def build_route_aggregation_pipeline(match_query: Optional[dict] = None) -> List[dict]:
    """Build aggregation pipeline to populate bus stops in routes"""
    pipeline = []

    # Match stage
    if match_query:
        pipeline.append({"$match": match_query})

    # Lookup stage for bus stops
    pipeline.extend([
        {
            "$lookup": {
                "from": "bus_stops",
                "localField": "stop_ids",
                "foreignField": "id",
                "as": "stops_data"
            }
        },
        {
            "$addFields": {
                "stops": {
                    "$map": {
                        "input": "$stop_ids",
                        "as": "stop_id",
                        "in": {
                            "$arrayElemAt": [
                                {
                                    "$filter": {
                                        "input": "$stops_data",
                                        "cond": {"$eq": ["$$this.id", "$$stop_id"]}
                                    }
                                },
                                0
                            ]
                        }
                    }
                }
            }
        },
        {
            "$project": {
                "stops_data": 0  # Remove the temporary field
            }
        }
    ])

    return pipeline

def transform_route_with_stops(route_doc: dict) -> RouteWithStopsResponse:
    """Transform route document with populated stops to RouteWithStopsResponse"""
    # Transform bus stops
    stops = []
    if route_doc.get("stops"):
        for stop_doc in route_doc["stops"]:
            if stop_doc:  # Check if stop exists (not None)
                stops.append(transform_mongo_doc(stop_doc, BusStopResponse))

    # Create route response
    route_response = RouteWithStopsResponse(
        id=route_doc["id"],
        name=route_doc["name"],
        description=route_doc.get("description"),
        stop_ids=route_doc["stop_ids"],
        stops=stops,
        total_distance=route_doc.get("total_distance"),
        estimated_duration=route_doc.get("estimated_duration"),
        is_active=route_doc.get("is_active", True),
        route_geometry=route_doc.get("route_geometry"),
        route_shape_data=route_doc.get("route_shape_data"),
        last_shape_update=route_doc.get("last_shape_update"),
        created_at=route_doc.get("created_at") or datetime.utcnow(),
        updated_at=route_doc.get("updated_at") or datetime.utcnow()
    )

    return route_response

# Debug endpoint to check database content
@router.get("/debug/count")
async def debug_route_count(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to check route counts"""
    try:
        route_count = await request.app.state.mongodb.routes.count_documents({})

        # Get sample documents
        sample_route = await request.app.state.mongodb.routes.find_one({})

        return {
            "route_count": route_count,
            "sample_route": sample_route,
            "database_name": request.app.state.mongodb.name
        }
    except Exception as e:
        return {
            "error": str(e),
            "route_count": 0
        }

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

@router.get("/", response_model=List[Union[RouteResponse, RouteWithStopsResponse]])
async def get_all_routes(
    request: Request,
    search: Optional[str] = Query(None, description="Search routes by name or description"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, description="Number of routes per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    populate: bool = Query(False, description="Populate bus stops data"),
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

    if populate:
        # Use aggregation pipeline to populate bus stops
        pipeline = build_route_aggregation_pipeline(query_filter)
        pipeline.extend([
            {"$skip": skip},
            {"$limit": limit}
        ])

        routes = await request.app.state.mongodb.routes.aggregate(pipeline).to_list(length=None)
        return [transform_route_with_stops(route) for route in routes]
    else:
        # Get paginated routes with search (without population)
        routes_cursor = request.app.state.mongodb.routes.find(query_filter).skip(skip).limit(limit)
        routes = await routes_cursor.to_list(length=limit)

        # Transform routes
        return [transform_mongo_doc(route, RouteResponse) for route in routes]
    
    
@router.get("/{route_id}", response_model=Union[RouteResponse, RouteWithStopsResponse])
async def get_route(
    request: Request,
    route_id: str,
    populate: bool = Query(False, description="Populate bus stops data"),
    current_user: User = Depends(get_current_user)
):
    """Get a specific route by ID with optional population"""

    if populate:
        # Use aggregation pipeline to populate bus stops
        pipeline = build_route_aggregation_pipeline({"id": route_id})
        routes = await request.app.state.mongodb.routes.aggregate(pipeline).to_list(length=1)

        if not routes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found"
            )

        return transform_route_with_stops(routes[0])
    else:
        # Get route without population
        route = await request.app.state.mongodb.routes.find_one({"id": route_id})
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
        {"id": route_id},
        {"$set": update_dict}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    updated_route = await request.app.state.mongodb.routes.find_one({"id": route_id})
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
    
    result = await request.app.state.mongodb.routes.delete_one({"id": route_id})
    
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

@router.get("/{route_id}/shape", response_model=RouteShapeResponse)
async def get_route_shape(
    request: Request,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get route shape (GeoJSON LineString) for map visualization"""
    try:
        # Get route shape from service (cached or generated)
        shape_data = await route_service.get_route_shape_cached(route_id, request.app.state)

        if not shape_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route shape not available"
            )

        return RouteShapeResponse(
            route_id=route_id,
            geometry=shape_data["geometry"],
            distance_meters=shape_data["distance"],
            duration_seconds=shape_data["duration"],
            profile=shape_data.get("profile", "driving"),
            created_at=shape_data.get("created_at", datetime.utcnow().isoformat())
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting route shape: {str(e)}"
        )

@router.post("/{route_id}/generate-shape")
async def generate_route_shape(
    request: Request,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Generate/regenerate route shape from bus stops (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can generate route shapes"
        )

    try:
        # Get route from database
        route_doc = await request.app.state.mongodb.routes.find_one({"id": route_id})
        if not route_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found"
            )

        # Get bus stops for this route
        stop_ids = route_doc.get("stop_ids", [])
        if len(stop_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Route must have at least 2 stops for shape generation"
            )

        # Fetch bus stops from database
        bus_stops_cursor = request.app.state.mongodb.bus_stops.find({"id": {"$in": stop_ids}})
        bus_stops_docs = await bus_stops_cursor.to_list(length=None)

        # Convert to BusStop objects and maintain order
        bus_stops = []
        for stop_id in stop_ids:
            for stop_doc in bus_stops_docs:
                if stop_doc["id"] == stop_id:
                    bus_stop = BusStop(
                        id=stop_doc["id"],
                        name=stop_doc["name"],
                        location=Location(
                            latitude=stop_doc["location"]["latitude"],
                            longitude=stop_doc["location"]["longitude"]
                        ),
                        capacity=stop_doc.get("capacity"),
                        is_active=stop_doc.get("is_active", True)
                    )
                    bus_stops.append(bus_stop)
                    break

        if len(bus_stops) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not find enough bus stops for route shape generation"
            )

        # Generate route shape
        shape_data = await route_service.generate_route_shape(route_id, bus_stops, request.app.state)

        if not shape_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate route shape"
            )

        return {
            "message": "Route shape generated successfully",
            "route_id": route_id,
            "distance_km": round(shape_data["distance"] / 1000, 2),
            "duration_minutes": round(shape_data["duration"] / 60, 2),
            "generated_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating route shape: {str(e)}"
        )