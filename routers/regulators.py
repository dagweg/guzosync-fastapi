from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List
from datetime import datetime

from core.dependencies import get_current_user, require_regulator
from models import User
from models.base import Location as ModelLocation
from models.regulators import ReallocationRequest, OvercrowdingReport, ReallocationReason, OvercrowdingSeverity
from schemas.transport import BusStopResponse
from schemas.regulators import (
    RequestReallocationRequest, ReallocationRequestResponse,
    ReportOvercrowdingRequest, OvercrowdingReportResponse
)

from core import transform_mongo_doc
from core.mongo_utils import model_to_mongo_doc

router = APIRouter(prefix="/api/regulators", tags=["regulators"])

@router.post("/request-reallocation", response_model=ReallocationRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_bus_reallocation(
    request: Request,
    reallocation_request: RequestReallocationRequest,
    current_user: User = Depends(require_regulator)
):
    """Request bus reallocation (regulator only)"""

    # Validate that the bus exists
    bus = await request.app.state.mongodb.buses.find_one({"id": reallocation_request.bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )    # Get the current route from the bus assignment
    current_route_id = bus.get("assigned_route_id")
    if not current_route_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bus is not currently assigned to any route"
        )

    # Create reallocation request - control center will decide route later
    # The regulator just reports the issue, control center handles the solution
    requested_route_id = None  # Control center will determine optimal route
    
    # Create ReallocationRequest model instance
    reallocation = ReallocationRequest(
        requested_by_user_id=current_user.id,
        bus_id=reallocation_request.bus_id,
        current_route_id=current_route_id,
        requested_route_id=requested_route_id,  # Control center will decide
        reason=ReallocationReason(reallocation_request.reason.value),
        description=reallocation_request.description,
        priority=reallocation_request.priority if reallocation_request.priority else "NORMAL"
    )

    # Convert model to MongoDB document (include None values for optional fields)
    reallocation_doc = model_to_mongo_doc(reallocation, exclude_none=False)
    result = await request.app.state.mongodb.reallocation_requests.insert_one(reallocation_doc)
    created_request = await request.app.state.mongodb.reallocation_requests.find_one({"id": reallocation.id})

    return transform_mongo_doc(created_request, ReallocationRequestResponse)


@router.post("/report-overcrowding", response_model=OvercrowdingReportResponse, status_code=status.HTTP_201_CREATED)
async def report_overcrowding(
    request: Request,
    overcrowding_request: ReportOvercrowdingRequest,
    current_user: User = Depends(require_regulator)
):
    """Report overcrowding at a bus stop (regulator only)"""

    # Validate that the bus stop exists
    bus_stop = await request.app.state.mongodb.bus_stops.find_one({"id": overcrowding_request.bus_stop_id})
    if not bus_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )

    # Validate bus if provided
    if overcrowding_request.bus_id:
        bus = await request.app.state.mongodb.buses.find_one({"id": overcrowding_request.bus_id})
        if not bus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus not found"
            )

    # Validate route if provided
    if overcrowding_request.route_id:
        route = await request.app.state.mongodb.routes.find_one({"id": overcrowding_request.route_id})
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found"
            )

    # Create OvercrowdingReport model instance
    overcrowding_report = OvercrowdingReport(
        reported_by_user_id=current_user.id,
        bus_stop_id=overcrowding_request.bus_stop_id,
        bus_id=overcrowding_request.bus_id,
        route_id=overcrowding_request.route_id,
        severity=OvercrowdingSeverity(overcrowding_request.severity.value),
        passenger_count=overcrowding_request.passenger_count,
        description=overcrowding_request.description,
        location=ModelLocation(
            latitude=overcrowding_request.location.latitude,
            longitude=overcrowding_request.location.longitude
        ) if overcrowding_request.location else None
    )

    # Convert model to MongoDB document
    overcrowding_doc = model_to_mongo_doc(overcrowding_report)
    result = await request.app.state.mongodb.overcrowding_reports.insert_one(overcrowding_doc)
    created_report = await request.app.state.mongodb.overcrowding_reports.find_one({"id": overcrowding_report.id})

    return transform_mongo_doc(created_report, OvercrowdingReportResponse)

