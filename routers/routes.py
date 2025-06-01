from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from uuid import UUID

from models import User, Route
from schemas.route import RouteResponse
from core.dependencies import get_current_user
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