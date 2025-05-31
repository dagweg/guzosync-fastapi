from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from models import User, Route
from schemas.route import RouteResponse
from routers.accounts import get_current_user

router = APIRouter(prefix="/api/routes", tags=["routes"])

@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(route_id: UUID, current_user: User = Depends(get_current_user)):
    from fastapi import Request
    request = Request
    
    route = await request.app.mongodb.routes.find_one({"id": route_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    return RouteResponse(**route)