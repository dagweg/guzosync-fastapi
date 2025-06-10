from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from typing import List, Optional
from datetime import datetime

from core.dependencies import get_current_user
from models import User, Bus, BusStop
from models.user import UserRole
from models.transport import BusType as ModelBusType, BusStatus as ModelBusStatus, Location as ModelLocation
from schemas.transport import BusResponse, BusStopResponse, CreateBusRequest, UpdateBusRequest, CreateBusStopRequest, UpdateBusStopRequest, BusDetailedResponse, RouteInfo, CurrentTripInfo, DriverAssignmentResponse
from schemas.trip import SimplifiedTripResponse
from schemas.user import UserResponse
from core.realtime.bus_tracking import bus_tracking_service

from core import transform_mongo_doc, generate_uuid
from core.mongo_utils import model_to_mongo_doc

router = APIRouter(prefix="/api/buses", tags=["buses"])

# Helper functions for populating driver information
def build_bus_aggregation_pipeline(match_query: Optional[dict] = None) -> List[dict]:
    """Build aggregation pipeline to populate driver information"""
    pipeline = []
    
    # Match stage
    if match_query:
        pipeline.append({"$match": match_query})
    
    # Lookup stage for driver information
    pipeline.extend([
        {
            "$lookup": {
                "from": "users",
                "localField": "assigned_driver_id",
                "foreignField": "_id",
                "as": "assigned_driver_data"
            }
        },
        {
            "$addFields": {
                "assigned_driver": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$assigned_driver_data"}, 0]},
                        "then": {"$arrayElemAt": ["$assigned_driver_data", 0]},
                        "else": None
                    }
                }
            }
        },
        {
            "$project": {
                "assigned_driver_data": 0  # Remove the temporary field
            }
        }
    ])
    
    return pipeline

def transform_bus_with_driver(bus_doc: dict) -> BusResponse:
    """Transform bus document with populated driver into BusResponse format"""
    # Transform the main bus document
    bus_response = transform_mongo_doc(bus_doc, BusResponse)
    
    # Handle the populated driver
    if bus_doc.get("assigned_driver"):
        driver_doc = bus_doc["assigned_driver"]
        bus_response.assigned_driver = transform_mongo_doc(driver_doc, UserResponse)
    else:
        bus_response.assigned_driver = None
    
    return bus_response

# Bus CRUD Operations

@router.post("/", response_model=BusResponse, status_code=status.HTTP_201_CREATED)
async def create_bus(
    request: Request,
    bus_data: CreateBusRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new bus (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can create buses"
        )
    
    # Check if bus with same license plate already exists
    existing_bus = await request.app.state.mongodb.buses.find_one({"license_plate": bus_data.license_plate})
    if existing_bus:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bus with this license plate already exists"
        )
    
    # Create Bus model instance with UUID
    bus = Bus(
        license_plate=bus_data.license_plate,
        capacity=bus_data.capacity,
        bus_type=ModelBusType(bus_data.bus_type.value),
        bus_status=ModelBusStatus(bus_data.bus_status.value),
        manufacture_year=bus_data.manufacture_year,
        bus_model=bus_data.bus_model
    )
    
    # Convert to MongoDB document
    bus_doc = model_to_mongo_doc(bus)
    
    result = await request.app.state.mongodb.buses.insert_one(bus_doc)
    
    # Get created bus with populated driver information
    pipeline = build_bus_aggregation_pipeline({"_id": result.inserted_id})
    buses = await request.app.state.mongodb.buses.aggregate(pipeline).to_list(length=1)
    
    if not buses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found after creation"
        )
    
    return transform_bus_with_driver(buses[0])

# Bus Stop CRUD Operations - MOVED BEFORE parameterized bus routes to avoid conflicts

@router.post("/stops", response_model=BusStopResponse, status_code=status.HTTP_201_CREATED)
async def create_bus_stop(
    request: Request,
    bus_stop_data: CreateBusStopRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new bus stop (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can create bus stops"
        )

    # Check if bus stop with same name already exists
    existing_stop = await request.app.state.mongodb.bus_stops.find_one({"name": bus_stop_data.name})
    if existing_stop:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bus stop with this name already exists"
        )

    # Create BusStop model instance with UUID
    bus_stop = BusStop(
        name=bus_stop_data.name,
        location=ModelLocation(
            latitude=bus_stop_data.location.latitude,
            longitude=bus_stop_data.location.longitude
        ),
        capacity=bus_stop_data.capacity,
        is_active=bus_stop_data.is_active
    )

    # Convert to MongoDB document
    bus_stop_doc = model_to_mongo_doc(bus_stop)

    result = await request.app.state.mongodb.bus_stops.insert_one(bus_stop_doc)
    created_bus_stop = await request.app.state.mongodb.bus_stops.find_one({"_id": result.inserted_id})

    return transform_mongo_doc(created_bus_stop, BusStopResponse)

@router.get("/stops", response_model=List[BusStopResponse])
async def get_bus_stops(
    request: Request,
    search: Optional[str] = None,
    filter_by: Optional[str] = None,
    page: int = Query(1, alias="pn", ge=1),
    page_size: int = Query(10, alias="ps", ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get all bus stops with optional search and filtering"""

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
    bus_stops = await request.app.state.mongodb.bus_stops.find(query).skip(skip).limit(page_size).to_list(length=page_size)

    return [transform_mongo_doc(stop, BusStopResponse) for stop in bus_stops]

@router.get("/stops/{bus_stop_id}", response_model=BusStopResponse)
async def get_bus_stop(
    request: Request,
    bus_stop_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific bus stop by ID"""

    bus_stop = await request.app.state.mongodb.bus_stops.find_one({"_id": bus_stop_id})
    if not bus_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )

    return transform_mongo_doc(bus_stop, BusStopResponse)

@router.put("/stops/{bus_stop_id}", response_model=BusStopResponse)
async def update_bus_stop(
    request: Request,
    bus_stop_id: str,
    update_data: UpdateBusStopRequest,
    current_user: User = Depends(get_current_user)
):
    """Update an existing bus stop (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update bus stops"
        )

    # Check if trying to update name to an existing one
    if update_data.name is not None:
        existing_stop = await request.app.state.mongodb.bus_stops.find_one({
            "name": update_data.name,
            "_id": {"$ne": bus_stop_id}
        })
        if existing_stop:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bus stop with this name already exists"
            )

    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()

    result = await request.app.state.mongodb.bus_stops.update_one(
        {"_id": bus_stop_id},
        {"$set": update_dict}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )

    updated_bus_stop = await request.app.state.mongodb.bus_stops.find_one({"_id": bus_stop_id})
    return transform_mongo_doc(updated_bus_stop, BusStopResponse)

@router.delete("/stops/{bus_stop_id}")
async def delete_bus_stop(
    request: Request,
    bus_stop_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a bus stop (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can delete bus stops"
        )

    result = await request.app.state.mongodb.bus_stops.delete_one({"_id": bus_stop_id})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )

    return {"message": "Bus stop deleted successfully"}

@router.get("/stops/{bus_stop_id}/incoming-buses", response_model=List[SimplifiedTripResponse])
async def get_incoming_buses(
    request: Request,
    bus_stop_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get incoming buses for a specific bus stop"""

    # First, verify bus stop exists
    bus_stop = await request.app.state.mongodb.bus_stops.find_one({"_id": bus_stop_id})
    if not bus_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )

    # Find routes that include this bus stop
    routes = await request.app.state.mongodb.routes.find(
        {"stop_ids": bus_stop_id}
    ).to_list(length=None)
    route_ids = [route["id"] for route in routes]

    # Find active trips on these routes
    trips = await request.app.state.mongodb.trips.find({
        "route_id": {"$in": route_ids},
        "status": {"$in": ["SCHEDULED", "IN_PROGRESS"]}
    }).to_list(length=None)

    return [transform_mongo_doc(trip, SimplifiedTripResponse) for trip in trips]

# Bus CRUD Operations - MOVED AFTER bus stops to avoid route conflicts

@router.get("/", response_model=List[BusResponse])
async def get_all_buses(
    request: Request,
    search: Optional[str] = None,
    filter_by: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, alias="pn", ge=1),
    page_size: int = Query(10, alias="ps", ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get all buses with optional search, filtering, and pagination"""

    # Build query
    query: dict = {}

    # Add status filter
    if status:
        query["bus_status"] = status.upper()

    # Add search conditions
    if search:
        query["$or"] = [
            {"license_plate": {"$regex": search, "$options": "i"}},
            {"bus_model": {"$regex": search, "$options": "i"}}
        ]

    if filter_by:
        # Additional filtering based on filter_by parameter
        # Could be used for bus_type, capacity range, etc.
        pass

    # Build aggregation pipeline with populated driver information
    pipeline = build_bus_aggregation_pipeline(query)

    # Add pagination stages
    pipeline.extend([
        {"$skip": (page - 1) * page_size},
        {"$limit": page_size}
    ])

    # Execute aggregation
    buses = await request.app.state.mongodb.buses.aggregate(pipeline).to_list(length=None)

    return [transform_bus_with_driver(bus) for bus in buses]

@router.get("/{bus_id}", response_model=BusResponse)
async def get_bus(
    request: Request,
    bus_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific bus with populated driver information"""

    # Build aggregation pipeline for single bus
    pipeline = build_bus_aggregation_pipeline({"_id": bus_id})

    # Execute aggregation
    buses = await request.app.state.mongodb.buses.aggregate(pipeline).to_list(length=1)

    if not buses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )

    return transform_bus_with_driver(buses[0])

@router.get("/{bus_id}/details", response_model=BusDetailedResponse)
async def get_bus_details(
    request: Request,
    bus_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive bus details including route, trip, and real-time information"""

    # Build aggregation pipeline for detailed bus information
    pipeline = [
        {"$match": {"_id": bus_id}},

        # Lookup driver information
        {
            "$lookup": {
                "from": "users",
                "localField": "assigned_driver_id",
                "foreignField": "_id",
                "as": "assigned_driver_data"
            }
        },
        {
            "$addFields": {
                "assigned_driver": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$assigned_driver_data"}, 0]},
                        "then": {"$arrayElemAt": ["$assigned_driver_data", 0]},
                        "else": None
                    }
                }
            }
        },

        # Lookup route information
        {
            "$lookup": {
                "from": "routes",
                "localField": "assigned_route_id",
                "foreignField": "_id",
                "as": "route_data"
            }
        },
        {
            "$addFields": {
                "route": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$route_data"}, 0]},
                        "then": {"$arrayElemAt": ["$route_data", 0]},
                        "else": None
                    }
                }
            }
        },

        # Lookup current trip
        {
            "$lookup": {
                "from": "trips",
                "let": {"bus_id": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {"$eq": ["$bus_id", "$$bus_id"]},
                            "status": {"$in": ["SCHEDULED", "IN_PROGRESS"]}
                        }
                    },
                    {"$sort": {"created_at": -1}},
                    {"$limit": 1}
                ],
                "as": "current_trip_data"
            }
        },
        {
            "$addFields": {
                "current_trip": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$current_trip_data"}, 0]},
                        "then": {"$arrayElemAt": ["$current_trip_data", 0]},
                        "else": None
                    }
                }
            }
        },

        # Clean up temporary fields
        {
            "$project": {
                "assigned_driver_data": 0,
                "route_data": 0,
                "current_trip_data": 0
            }
        }
    ]

    # Execute aggregation
    buses = await request.app.state.mongodb.buses.aggregate(pipeline).to_list(length=1)

    if not buses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )

    bus_doc = buses[0]

    # Transform basic bus data
    bus_response = BusDetailedResponse(
        id=str(bus_doc["_id"]),
        license_plate=bus_doc["license_plate"],
        bus_type=bus_doc["bus_type"],
        capacity=bus_doc["capacity"],
        bus_status=bus_doc["bus_status"],
        manufacture_year=bus_doc.get("manufacture_year"),
        bus_model=bus_doc.get("bus_model"),
        current_location=bus_doc.get("current_location"),
        last_location_update=bus_doc.get("last_location_update"),
        heading=bus_doc.get("heading"),
        speed=bus_doc.get("speed"),
        location_accuracy=bus_doc.get("location_accuracy"),
        current_address=bus_doc.get("current_address"),
        created_at=bus_doc.get("created_at"),
        updated_at=bus_doc.get("updated_at"),
        is_tracking_active=bus_doc.get("last_location_update") is not None,
        last_ping=bus_doc.get("last_location_update")
    )

    # Transform driver information
    if bus_doc.get("assigned_driver"):
        driver_doc = bus_doc["assigned_driver"]
        bus_response.assigned_driver = transform_mongo_doc(driver_doc, UserResponse)

    # Transform route information with start/end destinations
    if bus_doc.get("route"):
        route_doc = bus_doc["route"]
        route_info = RouteInfo(
            id=str(route_doc["_id"]),
            name=route_doc["name"],
            description=route_doc.get("description"),
            total_distance=route_doc.get("total_distance"),
            estimated_duration=route_doc.get("estimated_duration"),
            total_stops=len(route_doc.get("stop_ids", []))
        )

        # Get start and end destinations (first and last bus stops)
        stop_ids = route_doc.get("stop_ids", [])
        if stop_ids:
            # Get first and last stops
            start_stop = await request.app.state.mongodb.bus_stops.find_one({"_id": stop_ids[0]})
            end_stop = await request.app.state.mongodb.bus_stops.find_one({"_id": stop_ids[-1]}) if len(stop_ids) > 1 else start_stop

            if start_stop:
                route_info.start_destination = transform_mongo_doc(start_stop, BusStopResponse)
            if end_stop and end_stop != start_stop:
                route_info.end_destination = transform_mongo_doc(end_stop, BusStopResponse)

        bus_response.current_route = route_info

    # Transform current trip information
    if bus_doc.get("current_trip"):
        trip_doc = bus_doc["current_trip"]
        bus_response.current_trip = CurrentTripInfo(
            id=str(trip_doc["_id"]),
            status=trip_doc["status"],
            actual_departure_time=trip_doc.get("actual_departure_time"),
            estimated_arrival_time=trip_doc.get("estimated_arrival_time"),
            passenger_count=len(trip_doc.get("passenger_ids", []))
        )

    # Calculate daily metrics (simplified - you might want to implement more sophisticated logic)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Count today's trips
    today_trips = await request.app.state.mongodb.trips.count_documents({
        "bus_id": bus_id,
        "created_at": {"$gte": today_start}
    })
    bus_response.total_trips_today = today_trips

    # You could add more sophisticated metrics here like:
    # - Average speed calculation from location updates
    # - Distance covered calculation
    # - Real-time passenger count from tickets/check-ins

    return bus_response

@router.put("/{bus_id}/assign-driver/{driver_id}", response_model=DriverAssignmentResponse)
async def assign_driver_to_bus(
    request: Request,
    bus_id: str,
    driver_id: str,
    current_user: User = Depends(get_current_user)
):
    """Assign a bus driver to a specific bus"""

    # Check permissions - only control admins can assign drivers
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can assign drivers to buses"
        )

    # Verify bus exists
    bus = await request.app.state.mongodb.buses.find_one({"_id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )

    # Verify driver exists and has correct role
    driver = await request.app.state.mongodb.users.find_one({
        "_id": driver_id,
        "role": UserRole.BUS_DRIVER
    })
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus driver not found"
        )

    # Check if driver is already assigned to another bus
    existing_assignment = await request.app.state.mongodb.buses.find_one({
        "assigned_driver_id": driver_id,
        "_id": {"$ne": bus_id}
    })
    if existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Driver is already assigned to bus {existing_assignment['license_plate']}"
        )

    # Store previous driver info for response
    previous_driver_id = bus.get("assigned_driver_id")

    # Update bus with new driver assignment
    assignment_timestamp = datetime.utcnow()
    result = await request.app.state.mongodb.buses.update_one(
        {"_id": bus_id},
        {
            "$set": {
                "assigned_driver_id": driver_id,
                "updated_at": assignment_timestamp
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign driver to bus"
        )

    # Return assignment confirmation
    return DriverAssignmentResponse(
        message=f"Driver {driver['first_name']} {driver['last_name']} successfully assigned to bus {bus['license_plate']}",
        bus_id=bus_id,
        driver_id=driver_id,
        driver_name=f"{driver['first_name']} {driver['last_name']}",
        assignment_timestamp=assignment_timestamp,
        previous_driver_id=previous_driver_id
    )

@router.put("/{bus_id}/unassign-driver", response_model=DriverAssignmentResponse)
async def unassign_driver_from_bus(
    request: Request,
    bus_id: str,
    current_user: User = Depends(get_current_user)
):
    """Unassign the current driver from a specific bus"""

    # Check permissions - only control admins can unassign drivers
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can unassign drivers from buses"
        )

    # Verify bus exists and has an assigned driver
    bus = await request.app.state.mongodb.buses.find_one({"_id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )

    current_driver_id = bus.get("assigned_driver_id")
    if not current_driver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No driver is currently assigned to this bus"
        )

    # Get driver info for response
    driver = await request.app.state.mongodb.users.find_one({"_id": current_driver_id})
    driver_name = f"{driver['first_name']} {driver['last_name']}" if driver else "Unknown Driver"

    # Remove driver assignment from bus
    assignment_timestamp = datetime.utcnow()
    result = await request.app.state.mongodb.buses.update_one(
        {"_id": bus_id},
        {
            "$unset": {"assigned_driver_id": ""},
            "$set": {"updated_at": assignment_timestamp}
        }
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unassign driver from bus"
        )

    # Return unassignment confirmation
    return DriverAssignmentResponse(
        message=f"Driver {driver_name} successfully unassigned from bus {bus['license_plate']}",
        bus_id=bus_id,
        driver_id=None,
        driver_name=None,
        assignment_timestamp=assignment_timestamp,
        previous_driver_id=current_driver_id
    )

@router.put("/{bus_id}", response_model=BusResponse)
async def update_bus(
    request: Request,
    bus_id: str,
    update_data: UpdateBusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update an existing bus (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update buses"
        )
    
    # Check if trying to update license plate to an existing one
    if update_data.license_plate is not None:
        existing_bus = await request.app.state.mongodb.buses.find_one({
            "license_plate": update_data.license_plate,
            "_id": {"$ne": bus_id}
        })
        if existing_bus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bus with this license plate already exists"
            )

    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await request.app.state.mongodb.buses.update_one(
        {"_id": bus_id},
        {"$set": update_dict}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    # Get updated bus with populated driver information
    pipeline = build_bus_aggregation_pipeline({"_id": bus_id})
    buses = await request.app.state.mongodb.buses.aggregate(pipeline).to_list(length=1)
    
    if not buses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    return transform_bus_with_driver(buses[0])

@router.delete("/{bus_id}")
async def delete_bus(
    request: Request,
    bus_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a bus (admin only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can delete buses"
        )
    
    result = await request.app.state.mongodb.buses.delete_one({"_id": bus_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    return {"message": "Bus deleted successfully"}



@router.post("/reallocate")
async def request_bus_reallocation(current_user: User = Depends(get_current_user)):
    # Implementation for bus reallocation request
    pass

@router.get("/reallocation/requests")
async def get_reallocation_requests(current_user: User = Depends(get_current_user)):
    # Implementation for getting reallocation requests
    pass

@router.post("/{bus_id}/location")
async def update_bus_location(
    request: Request,
    bus_id: str,
    location_data: dict = Body(...),
    current_user: User = Depends(get_current_user)
):
    """Update bus location (for drivers and control center)"""
    if current_user.role not in ["BUS_DRIVER", UserRole.CONTROL_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers and control center admins can update bus location"
        )
    
    # Verify bus exists
    bus = await request.app.state.mongodb.buses.find_one({"_id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    # Extract location data
    latitude = location_data.get("latitude")
    longitude = location_data.get("longitude")
    heading = location_data.get("heading")
    speed = location_data.get("speed")
    
    if not latitude or not longitude:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude and longitude are required"
        )
    
    # Update location with real-time broadcast
    await bus_tracking_service.update_bus_location(
        bus_id=bus_id,
        latitude=latitude,
        longitude=longitude,
        heading=heading,
        speed=speed,
        app_state=request.app.state
    )
    
    return {"message": "Bus location updated successfully"}

@router.post("/{bus_id}/track")
async def subscribe_to_bus_tracking(
    bus_id: str,
    current_user: User = Depends(get_current_user)
):
    """Subscribe to real-time bus tracking updates"""
    await bus_tracking_service.subscribe_to_bus(str(current_user.id), bus_id)
    return {"message": f"Subscribed to bus {bus_id} tracking"}

@router.delete("/{bus_id}/track")
async def unsubscribe_from_bus_tracking(
    bus_id: str,
    current_user: User = Depends(get_current_user)
):
    """Unsubscribe from real-time bus tracking updates"""
    await bus_tracking_service.unsubscribe_from_bus(str(current_user.id), bus_id)
    return {"message": f"Unsubscribed from bus {bus_id} tracking"}

