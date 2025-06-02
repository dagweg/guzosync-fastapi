from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from core.dependencies import get_current_user
from models import User
from schemas.transport import CreateAlertRequest, UpdateAlertRequest, AlertResponse

from core import transform_mongo_doc

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=List[AlertResponse])
async def get_alerts(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get all active alerts"""
    alerts = await request.app.state.mongodb.alerts.find(
        {"is_active": True}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(alert, AlertResponse) for alert in alerts]

@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    request: Request,
    alert_request: CreateAlertRequest, 
    current_user: User = Depends(get_current_user)
):
    """Create a new alert (admin only)"""
    if current_user.role not in ["CONTROL_CENTER_ADMIN", "REGULATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create alerts"
        )
    
    alert_data = {
        "title": alert_request.title,
        "message": alert_request.message,
        "alert_type": alert_request.alert_type,
        "severity": alert_request.severity,
        "affected_routes": alert_request.affected_routes,
        "affected_bus_stops": alert_request.affected_bus_stops,
        "is_active": True,
        "created_by": current_user.id,
        "created_at": datetime.utcnow()
    }
    
    result = await request.app.state.mongodb.alerts.insert_one(alert_data)
    created_alert = await request.app.state.mongodb.alerts.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_alert, AlertResponse)

@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    request: Request,
    alert_id: UUID,
    alert_request: UpdateAlertRequest, 
    current_user: User = Depends(get_current_user)
):
    """Update an existing alert (admin only)"""
    if current_user.role not in ["CONTROL_CENTER_ADMIN", "REGULATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update alerts"
        )
    
    # Check if alert exists
    alert = await request.app.state.mongodb.alerts.find_one({"id": alert_id})
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Update only provided fields
    update_data = {k: v for k, v in alert_request.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await request.app.state.mongodb.alerts.update_one(
        {"id": alert_id},
        {"$set": update_data}
    )
    
    updated_alert = await request.app.state.mongodb.alerts.find_one({"id": alert_id})
    return transform_mongo_doc(updated_alert, AlertResponse)

@router.delete("/{alert_id}")
async def delete_alert(
    request: Request,
    alert_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Delete an alert (admin only)"""
    if current_user.role not in ["CONTROL_CENTER_ADMIN", "REGULATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete alerts"
        )
    
    result = await request.app.state.mongodb.alerts.delete_one({"id": alert_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return {"message": "Alert deleted successfully"}
