"""
Bus Simulation API Router

Provides endpoints for monitoring and controlling the bus simulation service.
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends
from typing import Dict, Any
from pydantic import BaseModel

from core.dependencies import get_current_user
from models.user import User, UserRole


class BaseResponse(BaseModel):
    """Basic response model for API endpoints."""
    status: str
    message: str

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/status", response_model=Dict[str, Any])
async def get_simulation_status(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get the current status of the bus simulation service.
    
    Requires: Control staff or admin access
    """
    # Check permissions
    if current_user.role not in [UserRole.CONTROL_STAFF, UserRole.CONTROL_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center staff can access simulation status"
        )
    
    try:
        # Get simulation service status
        if hasattr(request.app.state, 'bus_simulation'):
            simulation_status = request.app.state.bus_simulation.get_status()
        else:
            simulation_status = {
                "enabled": False,
                "is_running": False,
                "error": "Bus simulation service not initialized"
            }
        
        return {
            "status": "success",
            "simulation": simulation_status,
            "message": "Simulation status retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get simulation status: {str(e)}"
        )


@router.post("/restart", response_model=BaseResponse)
async def restart_simulation(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Restart the bus simulation service.
    
    Requires: Control admin access
    """
    # Check permissions - only admins can restart simulation
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can restart simulation"
        )
    
    try:
        if not hasattr(request.app.state, 'bus_simulation'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Bus simulation service not available"
            )
        
        simulation_service = request.app.state.bus_simulation
        
        # Stop and restart simulation
        await simulation_service.stop()
        await simulation_service.start()
        
        return BaseResponse(
            status="success",
            message="Bus simulation service restarted successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart simulation: {str(e)}"
        )


@router.post("/stop", response_model=BaseResponse)
async def stop_simulation(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Stop the bus simulation service.
    
    Requires: Control admin access
    """
    # Check permissions - only admins can stop simulation
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can stop simulation"
        )
    
    try:
        if not hasattr(request.app.state, 'bus_simulation'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Bus simulation service not available"
            )
        
        simulation_service = request.app.state.bus_simulation
        await simulation_service.stop()
        
        return BaseResponse(
            status="success",
            message="Bus simulation service stopped successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop simulation: {str(e)}"
        )


@router.post("/start", response_model=BaseResponse)
async def start_simulation(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Start the bus simulation service.
    
    Requires: Control admin access
    """
    # Check permissions - only admins can start simulation
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can start simulation"
        )
    
    try:
        if not hasattr(request.app.state, 'bus_simulation'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Bus simulation service not available"
            )
        
        simulation_service = request.app.state.bus_simulation
        await simulation_service.start()
        
        return BaseResponse(
            status="success",
            message="Bus simulation service started successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start simulation: {str(e)}"
        )


@router.get("/health")
async def simulation_health_check(request: Request):
    """
    Public health check for simulation service.
    Returns basic status without requiring authentication.
    """
    try:
        if hasattr(request.app.state, 'bus_simulation'):
            simulation_service = request.app.state.bus_simulation
            status = simulation_service.get_status()
            
            return {
                "simulation_enabled": status.get("enabled", False),
                "simulation_running": status.get("is_running", False),
                "active_buses": status.get("active_buses", 0),
                "total_buses": status.get("total_buses", 0)
            }
        else:
            return {
                "simulation_enabled": False,
                "simulation_running": False,
                "active_buses": 0,
                "total_buses": 0,
                "error": "Simulation service not initialized"
            }
            
    except Exception as e:
        return {
            "simulation_enabled": False,
            "simulation_running": False,
            "active_buses": 0,
            "total_buses": 0,
            "error": str(e)
        }
