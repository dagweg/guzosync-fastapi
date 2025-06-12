from faker import Faker
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Any, List, Optional, Dict

from datetime import datetime

from core.dependencies import get_current_user
from core.mongo_utils import transform_mongo_doc, model_to_mongo_doc
from core.email_service import email_service
from core import get_logger
from core.security import generate_secure_password, get_password_hash
from models import User, BusStop, Route, Location
from models.approval import ApprovalRequest, ApprovalStatus
from schemas.user import RegisterUserRequest, UserResponse
from schemas.transport import (
    CreateBusStopRequest, UpdateBusStopRequest, BusStopResponse,
    CreateBusRequest, UpdateBusRequest, BusResponse
)
from schemas.route import CreateRouteRequest, UpdateRouteRequest, RouteResponse
from models.user import UserRole
from schemas.control_center import (RegisterPersonnelRequest, RegisterControlStaffRequest)
from schemas.regulators import ReallocationHistoryResponse, ReallocationAction, ReviewReallocationRequest
from uuid import uuid4
from core.ai_agent import route_optimization_agent
from core.realtime.notifications import notification_service


logger = get_logger(__name__)



router = APIRouter(prefix="/api/control-center", tags=["control-center"])

# Debug endpoint to check approval requests
@router.get("/debug/approval-requests")
async def debug_approval_requests(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to check approval requests (CONTROL_ADMIN only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CONTROL_ADMIN can access debug endpoints"
        )

    try:
        # Get all approval requests
        approval_requests = await request.app.state.mongodb.approval_requests.find({}).to_list(length=None)

        # Get collection stats
        collection_stats = await request.app.state.mongodb.approval_requests.count_documents({})

        return {
            "total_count": collection_stats,
            "requests": approval_requests,
            "collection_name": "approval_requests",
            "database_name": request.app.state.mongodb.name
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "total_count": 0,
            "requests": []
        }

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

# Personnel Management
@router.post("/personnel/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_personnel(
    request: Request,
    user_data: RegisterPersonnelRequest,
    current_user: User = Depends(get_current_user)
):    
    """Register new personnel (admin and staff only)"""    
    if current_user.role not in [UserRole.CONTROL_ADMIN, UserRole.CONTROL_STAFF]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center staffs and admins can register personnel"
        )
      # Check if user with email already exists
    existing_user = await request.app.state.mongodb.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )    # Store the temporary password for email (before hashing)
    temp_password = str(uuid4())
    
    # Create User model instance
    user = User(    
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password=get_password_hash(temp_password),  # Hash the temporary password
        role=UserRole(user_data.role.value),
        phone_number=user_data.phone_number,
        profile_image=user_data.profile_image,
        is_active=False
    )

    # Convert model to MongoDB document
    user_doc = model_to_mongo_doc(user)
    result = await request.app.state.mongodb.users.insert_one(user_doc)
    created_user = await request.app.state.mongodb.users.find_one({"id": user.id})

    # Add to approval request with proper error handling
    try:
        # Check if approval_requests collection exists and is accessible
        collection_exists = await request.app.state.mongodb.approval_requests.find_one({}, {"_id": 1})
        logger.info(f"Approval requests collection accessible: {collection_exists is not None or True}")

        approval_request = ApprovalRequest(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            phone_number=user_data.phone_number,
            profile_image=user_data.profile_image,
            role=user_data.role.value,
            status=ApprovalStatus.PENDING,
            requested_at=datetime.utcnow()
        )

        # Convert model to MongoDB document
        request_doc = model_to_mongo_doc(approval_request)
        logger.info(f"Approval request document prepared: {request_doc}")

        # Insert the approval request
        approval_result = await request.app.state.mongodb.approval_requests.insert_one(request_doc)

        # Verify the approval request was created
        if approval_result.inserted_id:
            # Double-check by retrieving the created document
            created_approval = await request.app.state.mongodb.approval_requests.find_one({"id": approval_request.id})
            if created_approval:
                logger.info(f"Approval request created and verified for {user_data.role.value}",
                           extra={"email": user_data.email, "approval_request_id": str(approval_result.inserted_id)})
                print(f"✅ DEBUG: Approval request created for {user_data.role.value} '{user_data.first_name} {user_data.last_name}' - ID: {approval_result.inserted_id}")
            else:
                logger.error("Approval request inserted but not found when retrieving",
                            extra={"email": user_data.email, "inserted_id": str(approval_result.inserted_id)})
                print(f"⚠️ DEBUG: Approval request inserted but not retrievable for {user_data.email}")
        else:
            logger.error("Failed to create approval request - no inserted_id returned",
                        extra={"email": user_data.email})
            print(f"❌ DEBUG: No inserted_id returned for approval request: {user_data.email}")

    except Exception as e:
        logger.error(f"Error creating approval request: {str(e)}",
                    extra={"email": user_data.email, "role": user_data.role.value}, exc_info=True)
        print(f"❌ DEBUG: Failed to create approval request for {user_data.email}: {str(e)}")
        # Don't raise the exception here as user creation was successful
        # Just log the error for debugging



    # Log temporary password for debugging purposes
    role_display = user_data.role.value.replace("_", " ").title()

    print(f"🔑 DEBUG: {role_display} '{user_data.first_name} {user_data.last_name}' ({user_data.email}) - Temp Password: {temp_password}")

    # Send invitation email with credentials
    full_name = f"{user_data.first_name} {user_data.last_name}"
    email_sent = await email_service.send_personnel_invitation_email(
        user_data.email,
        full_name,
        role_display,
        temp_password
    )
    if not email_sent:
        logger.warning("Failed to send personnel invitation email", extra={"email": user_data.email})
    
    return transform_mongo_doc(created_user, UserResponse)

# Queue Regulators Management
@router.get("/personnel/queue-regulators", response_model=List[UserResponse])
async def get_queue_regulators(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get all queue regulators"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view personnel"
        )
    
    regulators = await request.app.state.mongodb.users.find(
        {"role": "QUEUE_REGULATOR"}
    ).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(regulator, UserResponse) for regulator in regulators]

@router.get("/personnel/queue-regulators/{regulator_id}", response_model=UserResponse)
async def get_queue_regulator(
    request: Request,
    regulator_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific queue regulator"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view personnel"
        )

    regulator = await request.app.state.mongodb.users.find_one({
        "id": regulator_id,
        "role": "QUEUE_REGULATOR"
    })
    
    if not regulator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulator not found"
        )
    
    return transform_mongo_doc(regulator, UserResponse)

@router.put("/personnel/queue-regulators/{regulator_id}", response_model=UserResponse)
async def update_queue_regulator(
    request: Request,
    regulator_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update queue regulator"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update personnel"
        )
    
    result = await request.app.state.mongodb.users.update_one(
        {"id": regulator_id, "role": "QUEUE_REGULATOR"},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulator not found"
        )

    updated_regulator = await request.app.state.mongodb.users.find_one({"id": regulator_id})
    return transform_mongo_doc(updated_regulator, UserResponse)

@router.delete("/personnel/queue-regulators/{regulator_id}")
async def delete_queue_regulator(
    request: Request,
    regulator_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete queue regulator"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can delete personnel"
        )
    
    result = await request.app.state.mongodb.users.delete_one({
        "id": regulator_id,
        "role": "QUEUE_REGULATOR"
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulator not found"
        )
    
    return {"message": "Regulator deleted successfully"}

@router.put("/personnel/queue-regulators/{regulator_id}/assign/bus-stop/{bus_stop_id}")
async def assign_regulator_to_bus_stop(
    request: Request,
    regulator_id: str,
    bus_stop_id: str,
    current_user: User = Depends(get_current_user)
):
    """Assign regulator to a bus stop"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can assign regulators"
        )
    
    # Check if regulator exists
    regulator = await request.app.state.mongodb.users.find_one({
        "id": regulator_id,
        "role": "QUEUE_REGULATOR"
    })
    if not regulator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulator not found"
        )
    
    # Check if bus stop exists
    bus_stop = await request.app.state.mongodb.bus_stops.find_one({"id": bus_stop_id})
    if not bus_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )
    
    # Create or update assignment
    assignment_data = {
        "regulator_id": regulator_id,
        "bus_stop_id": bus_stop_id,
        "assigned_at": datetime.utcnow(),
        "assigned_by": current_user.id
    }
    
    await request.app.state.mongodb.regulator_assignments.replace_one(
        {"regulator_id": regulator_id},
        assignment_data,
        upsert=True
    )
    
    return {"message": "Regulator assigned to bus stop successfully"}

# Bus Drivers Management
@router.get("/personnel/bus-drivers", response_model=List[UserResponse])
async def get_bus_drivers(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get all bus drivers"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view personnel"
        )
    
    drivers = await request.app.state.mongodb.users.find(
        {"role": "BUS_DRIVER"}
    ).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(driver, UserResponse) for driver in drivers]

@router.get("/personnel/bus-drivers/{driver_id}", response_model=UserResponse)
async def get_bus_driver(
    request: Request,
    driver_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific bus driver"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view personnel"
        )
    
    driver = await request.app.state.mongodb.users.find_one({
        "id": driver_id,
        "role": "BUS_DRIVER"
    })
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    return transform_mongo_doc(driver, UserResponse)

@router.put("/personnel/bus-drivers/{driver_id}", response_model=UserResponse)
async def update_bus_driver(
    request: Request,
    driver_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update bus driver"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update personnel"
        )
    
    result = await request.app.state.mongodb.users.update_one(
        {"id": driver_id, "role": "BUS_DRIVER"},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )

    updated_driver = await request.app.state.mongodb.users.find_one({"id": driver_id})
    return transform_mongo_doc(updated_driver, UserResponse)

@router.delete("/personnel/bus-drivers/{driver_id}")
async def delete_bus_driver(
    request: Request,
    driver_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete bus driver"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can delete personnel"
        )
    
    result = await request.app.state.mongodb.users.delete_one({
        "id": driver_id,
        "role": "BUS_DRIVER"
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    return {"message": "Driver deleted successfully"}

@router.put("/personnel/bus-drivers/{driver_id}/assign-bus/{bus_id}")
async def assign_driver_to_bus(
    request: Request,
    driver_id: str,
    bus_id: str,
    current_user: User = Depends(get_current_user)
):
    """Assign driver to a bus"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can assign drivers"
        )
    
    # Check if driver exists
    driver = await request.app.state.mongodb.users.find_one({
        "id": driver_id,
        "role": "BUS_DRIVER"
    })
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Check if bus exists
    bus = await request.app.state.mongodb.buses.find_one({"id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
      # Update bus with assigned driver
    await request.app.state.mongodb.buses.update_one(
        {"id": bus_id},
        {"$set": {"assigned_driver_id": driver_id}}
    )
    
    return {"message": "Driver assigned to bus successfully"}

# Get All Personnel - for both CONTROL_ADMIN and CONTROL_STAFF
@router.get("/personnel", response_model=List[UserResponse])
async def get_all_personnel(
    request: Request,
    role_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all personnel (CONTROL_ADMIN and CONTROL_STAFF can access)"""
    if current_user.role not in [UserRole.CONTROL_ADMIN, UserRole.CONTROL_STAFF]:   
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CONTROL_ADMIN and CONTROL_STAFF can view personnel"
        )
    
    try:
        # Build query filter for personnel roles based on user role (RBAC)
        if current_user.role == UserRole.CONTROL_ADMIN:
            # CONTROL_ADMIN can see all personnel including other admins
            personnel_roles = ["CONTROL_ADMIN", "CONTROL_STAFF", "BUS_DRIVER", "QUEUE_REGULATOR", "PASSENGER"]
        else:  # CONTROL_STAFF
            # CONTROL_STAFF can see all personnel EXCEPT CONTROL_ADMIN users
            personnel_roles = ["CONTROL_STAFF", "BUS_DRIVER", "QUEUE_REGULATOR", "PASSENGER"]
        
        query: dict[str, Any] = {"role": {"$in": personnel_roles}}
          # Apply role filter if specified
        if role_filter:
            if role_filter.upper() not in personnel_roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role filter. Must be one of: {', '.join(personnel_roles)}"
                )
            query = {"role": role_filter.upper()}
        
        # Fetch personnel
        personnel_cursor = request.app.state.mongodb.users.find(query)
        personnel = await personnel_cursor.to_list(length=None)
        
        logger.info(f"Retrieved {len(personnel)} personnel records", 
                   extra={"requestor": current_user.email, "role_filter": role_filter})
        
        return [transform_mongo_doc(person, UserResponse) for person in personnel]
        
    except Exception as e:
        logger.error("Error retrieving personnel", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving personnel"
        )

# Passengers Management
@router.get("/passengers", response_model=List[UserResponse])
async def get_all_passengers(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get all passengers (CONTROL_ADMIN and CONTROL_STAFF can access)"""
    if current_user.role not in [UserRole.CONTROL_ADMIN, UserRole.CONTROL_STAFF]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CONTROL_ADMIN and CONTROL_STAFF can view passengers"
        )
    
    try:
        passengers = await request.app.state.mongodb.users.find(
            {"role": "PASSENGER"}
        ).skip(skip).limit(limit).to_list(length=limit)
        
        logger.info(f"Retrieved {len(passengers)} passenger records", 
                   extra={"requestor": current_user.email, "skip": skip, "limit": limit})
        
        return [transform_mongo_doc(passenger, UserResponse) for passenger in passengers]
        
    except Exception as e:
        logger.error("Error retrieving passengers", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving passengers"
        )

# Bus Stops Management
@router.post("/bus-stops", response_model=BusStopResponse, status_code=status.HTTP_201_CREATED)
async def create_bus_stop(
    request: Request,
    bus_stop_data: CreateBusStopRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new bus stop"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can create bus stops"
        )    # Create BusStop model instance
    bus_stop = BusStop(
        name=bus_stop_data.name,
        location=Location(
            latitude=bus_stop_data.location.latitude,
            longitude=bus_stop_data.location.longitude
        ),
        capacity=bus_stop_data.capacity,
        is_active=bus_stop_data.is_active if bus_stop_data.is_active is not None else True
    )
    
    # Convert model to MongoDB document
    bus_stop_doc = model_to_mongo_doc(bus_stop)
    result = await request.app.state.mongodb.bus_stops.insert_one(bus_stop_doc)
    created_bus_stop = await request.app.state.mongodb.bus_stops.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_bus_stop, BusStopResponse)

@router.get("/bus-stops", response_model=List[BusStopResponse])
async def get_control_center_bus_stops(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get all bus stops for management"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view all bus stops"
        )
    
    bus_stops = await request.app.state.mongodb.bus_stops.find({}).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(stop, BusStopResponse) for stop in bus_stops]

@router.get("/bus-stops/{bus_stop_id}", response_model=BusStopResponse)
async def get_control_center_bus_stop(
    request: Request,
    bus_stop_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific bus stop for management"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view bus stop details"
        )
    
    bus_stop = await request.app.state.mongodb.bus_stops.find_one({"id": bus_stop_id})
    if not bus_stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )

    return transform_mongo_doc(bus_stop, BusStopResponse)

@router.put("/bus-stops/{bus_stop_id}", response_model=BusStopResponse)
async def update_control_center_bus_stop(
    request: Request,
    bus_stop_id: str,
    update_data: UpdateBusStopRequest,
    current_user: User = Depends(get_current_user)
):
    """Update bus stop"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update bus stops"
        )
    
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await request.app.state.mongodb.bus_stops.update_one(
        {"id": bus_stop_id},
        {"$set": update_dict}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )

    updated_bus_stop = await request.app.state.mongodb.bus_stops.find_one({"id": bus_stop_id})
    return transform_mongo_doc(updated_bus_stop, BusStopResponse)

@router.delete("/bus-stops/{bus_stop_id}")
async def delete_control_center_bus_stop(
    request: Request,
    bus_stop_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete bus stop"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can delete bus stops"
        )
    
    result = await request.app.state.mongodb.bus_stops.delete_one({"id": bus_stop_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus stop not found"
        )
    
    return {"message": "Bus stop deleted successfully"}

# Buses Management
@router.get("/buses", response_model=List[BusResponse])
async def get_control_center_buses(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get all buses for management"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view all buses"
        )
    
    # Build aggregation pipeline with populated driver information
    pipeline = build_bus_aggregation_pipeline()
    
    # Add pagination stages
    pipeline.extend([
        {"$skip": skip},
        {"$limit": limit}
    ])
    
    # Execute aggregation
    buses = await request.app.state.mongodb.buses.aggregate(pipeline).to_list(length=None)
    
    return [transform_bus_with_driver(bus) for bus in buses]

@router.get("/buses/{bus_id}", response_model=BusResponse)
async def get_control_center_bus(
    request: Request,
    bus_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific bus for management"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view bus details"
        )
    
    # Build aggregation pipeline for single bus
    pipeline = build_bus_aggregation_pipeline({"id": bus_id})

    # Execute aggregation
    buses = await request.app.state.mongodb.buses.aggregate(pipeline).to_list(length=1)
    
    if not buses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    return transform_bus_with_driver(buses[0])

@router.put("/buses/{bus_id}", response_model=BusResponse)
async def update_control_center_bus(
    request: Request,
    bus_id: str,
    update_data: UpdateBusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update bus"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update buses"
        )
    
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await request.app.state.mongodb.buses.update_one(
        {"id": bus_id},
        {"$set": update_dict}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )

    # Get updated bus with populated driver information
    pipeline = build_bus_aggregation_pipeline({"id": bus_id})
    buses = await request.app.state.mongodb.buses.aggregate(pipeline).to_list(length=1)
    
    if not buses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    return transform_bus_with_driver(buses[0])

@router.put("/buses/{bus_id}/assign-route/{route_id}")
async def assign_bus_to_route(
    request: Request,
    bus_id: str,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Assign bus to a route"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can assign buses to routes"
        )
    
    # Check if bus exists
    bus = await request.app.state.mongodb.buses.find_one({"id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )

    # Check if route exists
    route = await request.app.state.mongodb.routes.find_one({"id": route_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )

    # Update bus with assigned route
    await request.app.state.mongodb.buses.update_one(
        {"id": bus_id},
        {"$set": {"assigned_route_id": route_id}}
    )
    
    return {"message": "Bus assigned to route successfully"}

@router.put("/buses/{bus_id}/reallocate-route/{route_id}")
async def reallocate_bus_route(
    request: Request,
    bus_id: str,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Reallocate bus to a different route"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can reallocate buses"
        )
    
    # Check if bus exists
    bus = await request.app.state.mongodb.buses.find_one({"id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )

    # Check if route exists
    route = await request.app.state.mongodb.routes.find_one({"id": route_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )

    # Create reallocation record
    reallocation_data = {
        "bus_id": bus_id,
        "old_route_id": bus.get("assigned_route_id"),
        "new_route_id": route_id,
        "reallocated_by": current_user.id,
        "reallocated_at": datetime.utcnow(),
        "status": "COMPLETED"
    }

    await request.app.state.mongodb.reallocation_requests.insert_one(reallocation_data)

    # Update bus with new route
    await request.app.state.mongodb.buses.update_one(
        {"id": bus_id},
        {"$set": {"assigned_route_id": route_id}}
    )

    # Send route reallocation notifications
    await notification_service.send_route_reallocation_notification(
        bus_id=bus_id,
        old_route_id=bus.get("assigned_route_id"),
        new_route_id=route_id,
        reallocated_by_user_id=current_user.id,
        app_state=request.app.state,
        requesting_regulator_id=None  # Direct reallocation, no requesting regulator
    )

    return {"message": "Bus reallocated to new route successfully"}

@router.post("/buses/deploy-stationary")
async def deploy_stationary_bus(
    request: Request,
    deployment_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Deploy a stationary bus"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can deploy buses"
        )
    
    # Implementation for deploying stationary bus
    deployment_record = {
        **deployment_data,
        "deployed_by": current_user.id,
        "deployed_at": datetime.utcnow(),
        "status": "DEPLOYED"
    }
    
    result = await request.app.state.mongodb.bus_deployments.insert_one(deployment_record)
    
    return {"message": "Stationary bus deployed successfully", "deployment_id": str(result.inserted_id)}

# Routes Management
@router.post("/routes", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def create_control_center_route(
    request: Request,
    route_data: CreateRouteRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new route"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can create routes"
        )
      # Create Route model instance
    route = Route(
        name=route_data.name,
        description=route_data.description,
        stop_ids=route_data.stop_ids,
        total_distance=route_data.total_distance,
        estimated_duration=route_data.estimated_duration,
        is_active=route_data.is_active if route_data.is_active is not None else True
    )
    
    # Convert model to MongoDB document
    route_doc = model_to_mongo_doc(route)
    result = await request.app.state.mongodb.routes.insert_one(route_doc)
    created_route = await request.app.state.mongodb.routes.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_route, RouteResponse)

@router.get("/routes", response_model=List[RouteResponse])
async def get_control_center_routes(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get all routes for management"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view all routes"
        )
    
    routes = await request.app.state.mongodb.routes.find({}).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(route, RouteResponse) for route in routes]

@router.get("/routes/{route_id}", response_model=RouteResponse)
async def get_control_center_route(
    request: Request,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific route for management"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view route details"
        )
    
    route = await request.app.state.mongodb.routes.find_one({"id": route_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )

    return transform_mongo_doc(route, RouteResponse)

@router.put("/routes/{route_id}", response_model=RouteResponse)
async def update_control_center_route(
    request: Request,
    route_id: str,
    update_data: UpdateRouteRequest,
    current_user: User = Depends(get_current_user)
):
    """Update route"""
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

@router.delete("/routes/{route_id}")
async def delete_control_center_route(
    request: Request,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete route"""
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

@router.get("/reallocation-requests")
async def get_reallocation_requests(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get all reallocation requests"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view reallocation requests"
        )
    
    requests = await request.app.state.mongodb.reallocation_requests.find({}).sort("reallocated_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return requests

# @router.post("/reallocation-requests/{request_id}/process")
# async def process_reallocation_request(
#     request: Request,
#     request_id: str,
#     current_user: User = Depends(get_current_user)
# ):
#     """Process a reallocation request using AI agent to determine optimal route"""
#     if current_user.role != UserRole.CONTROL_ADMIN:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only control center admins can process reallocation requests"
#         )
    
#     # Get the reallocation request
#     reallocation_request = await request.app.state.mongodb.reallocation_requests.find_one({"_id": request_id})
#     if not reallocation_request:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Reallocation request not found"
#         )
    
#     if reallocation_request.get("status") != "PENDING":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Request has already been processed"
#         )
    
#     # Use AI agent to determine optimal route if not already set
#     optimal_route_id = reallocation_request.get("requested_route_id")
#     if not optimal_route_id:
#         optimal_route_id = await route_optimization_agent.determine_optimal_route(
#             bus_id=reallocation_request["bus_id"],
#             current_route_id=reallocation_request["current_route_id"],
#             reason=reallocation_request["reason"],
#             priority=reallocation_request.get("priority", "NORMAL"),
#             description=reallocation_request.get("description", ""),
#             mongodb_client=request.app.state.mongodb
#         )
    
#     if not optimal_route_id:
#         # Update request as rejected if no suitable route found
#         await request.app.state.mongodb.reallocation_requests.update_one(
#             {"_id": request_id},
#             {
#                 "$set": {
#                     "status": "REJECTED",
#                     "reviewed_by": current_user.id,
#                     "reviewed_at": datetime.utcnow().isoformat(),
#                     "review_notes": "AI agent could not find suitable alternative route"
#                 }
#             }
#         )

#         # Send reallocation request discarded notification
#         await notification_service.send_reallocation_request_discarded_notification(
#             request_id=request_id,
#             requesting_regulator_id=reallocation_request["requested_by_user_id"],
#             reason="AI agent could not find suitable alternative route",
#             app_state=request.app.state
#         )

#         return {"message": "No suitable route found for reallocation", "status": "REJECTED"}
    
#     # Verify the optimal route exists and is active
#     optimal_route = await request.app.state.mongodb.routes.find_one({"_id": optimal_route_id})
#     if not optimal_route or not optimal_route.get("is_active", True):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Selected route is not available"
#         )
    
#     # Update the bus assignment
#     bus_update_result = await request.app.state.mongodb.buses.update_one(
#         {"_id": reallocation_request["bus_id"]},
#         {"$set": {"assigned_route_id": optimal_route_id}}
#     )
    
#     if bus_update_result.modified_count == 0:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Bus not found or could not be updated"
#         )
    
#     # Update reallocation request as approved and completed
#     await request.app.state.mongodb.reallocation_requests.update_one(
#         {"_id": request_id},
#         {
#             "$set": {
#                 "requested_route_id": optimal_route_id,
#                 "status": "COMPLETED",
#                 "reviewed_by": current_user.id,
#                 "reviewed_at": datetime.utcnow().isoformat(),
#                 "review_notes": f"AI agent selected optimal route: {optimal_route['name']}"
#             }
#         }
#     )

#     # Send route reallocation notifications
#     await notification_service.send_route_reallocation_notification(
#         bus_id=reallocation_request["bus_id"],
#         old_route_id=reallocation_request["current_route_id"],
#         new_route_id=optimal_route_id,
#         reallocated_by_user_id=current_user.id,
#         app_state=request.app.state
#     )

#     return {
#         "message": "Reallocation request processed successfully",
#         "status": "COMPLETED",
#         "bus_id": reallocation_request["bus_id"],
#         "old_route_id": reallocation_request["current_route_id"],
#         "new_route_id": optimal_route_id,
#         "route_name": optimal_route["name"]
#     }

@router.post("/reallocation-requests/{request_id}/review")
async def review_reallocation_request(
    request: Request,
    request_id: str,
    review_data: ReviewReallocationRequest,
    current_user: User = Depends(get_current_user)
):
    """Manually review a reallocation request (approve, reject, or keep pending)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can review reallocation requests"
        )

    # Get the reallocation request
    reallocation_request = await request.app.state.mongodb.reallocation_requests.find_one({"id": request_id})
    if not reallocation_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reallocation request not found"
        )

    # Allow re-review of requests in any status
    # This enables admins to change decisions or re-process requests as needed

    # Handle different actions
    if review_data.action == ReallocationAction.APPROVE:
        # Approval requires a route_id
        if not review_data.route_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Route ID is required for approval"
            )

        # Verify the route exists and is active
        route = await request.app.state.mongodb.routes.find_one({"id": review_data.route_id})
        if not route or not route.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected route is not available"
            )

        # Update the bus assignment
        bus_update_result = await request.app.state.mongodb.buses.update_one(
            {"id": reallocation_request["bus_id"]},
            {"$set": {"assigned_route_id": review_data.route_id}}
        )

        if bus_update_result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus not found or could not be updated"
            )

        # Update reallocation request as approved and completed
        await request.app.state.mongodb.reallocation_requests.update_one(
            {"id": request_id},
            {
                "$set": {
                    "requested_route_id": review_data.route_id,
                    "status": "COMPLETED",
                    "reviewed_by": current_user.id,
                    "reviewed_at": datetime.utcnow().isoformat(),
                    "review_notes": review_data.reason or f"Manually approved - assigned to route: {route['name']}"
                }
            }
        )

        # Send route reallocation notifications - Include requesting regulator ID
        await notification_service.send_route_reallocation_notification(
            bus_id=reallocation_request["bus_id"],
            old_route_id=reallocation_request["current_route_id"],
            new_route_id=review_data.route_id,
            reallocated_by_user_id=current_user.id,
            app_state=request.app.state,
            requesting_regulator_id=reallocation_request["requested_by_user_id"]  # Add this!
        )

        return {
            "message": "Reallocation request approved successfully",
            "status": "COMPLETED",
            "bus_id": reallocation_request["bus_id"],
            "old_route_id": reallocation_request["current_route_id"],
            "new_route_id": review_data.route_id,
            "route_name": route["name"]
        }

    elif review_data.action == ReallocationAction.REJECT:
        # Update request as rejected
        await request.app.state.mongodb.reallocation_requests.update_one(
            {"id": request_id},
            {
                "$set": {
                    "status": "REJECTED",
                    "reviewed_by": current_user.id,
                    "reviewed_at": datetime.utcnow().isoformat(),
                    "review_notes": review_data.reason or "Manually rejected by admin"
                }
            }
        )

        # Send reallocation request discarded notification
        await notification_service.send_reallocation_request_discarded_notification(
            request_id=request_id,
            requesting_regulator_id=reallocation_request["requested_by_user_id"],
            reason=review_data.reason or "Request rejected by admin",
            app_state=request.app.state
        )

        return {
            "message": "Reallocation request rejected successfully",
            "status": "REJECTED",
            "reason": review_data.reason or "Manually rejected by admin"
        }

    elif review_data.action == ReallocationAction.PENDING:
        # Keep as pending but update review info
        await request.app.state.mongodb.reallocation_requests.update_one(
            {"id": request_id},
            {
                "$set": {
                    "reviewed_by": current_user.id,
                    "reviewed_at": datetime.utcnow().isoformat(),
                    "review_notes": review_data.reason or "Under review - kept pending"
                }
            }
        )

        return {
            "message": "Reallocation request kept pending for further review",
            "status": "PENDING",
            "notes": review_data.reason or "Under review - kept pending"
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be APPROVE, REJECT, or PENDING"
        )

@router.get("/reallocation-requests/pending")
async def get_pending_reallocation_requests(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get pending reallocation requests that need AI processing"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view reallocation requests"
        )
    
    # Get pending requests (those without requested_route_id or with PENDING status)
    requests = await request.app.state.mongodb.reallocation_requests.find({
        "$or": [
            {"status": "PENDING"},
            {"requested_route_id": {"$in": [None, ""]}},
            {"requested_route_id": {"$exists": False}}
        ]
    }).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return requests

@router.post("/reallocation-requests/{request_id}/discard")
async def discard_reallocation_request(
    request: Request,
    request_id: str,
    discard_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Manually discard a reallocation request"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can discard reallocation requests"
        )

    # Get the reallocation request
    reallocation_request = await request.app.state.mongodb.reallocation_requests.find_one({"id": request_id})
    if not reallocation_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reallocation request not found"
        )

    if reallocation_request.get("status") != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request has already been processed"
        )

    reason = discard_data.get("reason", "Request discarded by admin")

    # Update request as discarded
    await request.app.state.mongodb.reallocation_requests.update_one(
        {"id": request_id},
        {
            "$set": {
                "status": "REJECTED",
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.utcnow().isoformat(),
                "review_notes": f"Manually discarded: {reason}"
            }
        }
    )

    # Send reallocation request discarded notification
    await notification_service.send_reallocation_request_discarded_notification(
        request_id=request_id,
        requesting_regulator_id=reallocation_request["requested_by_user_id"],
        reason=reason,
        app_state=request.app.state
    )

    return {
        "message": "Reallocation request discarded successfully",
        "status": "REJECTED",
        "reason": reason
    }

@router.get("/reallocation-history", response_model=List[ReallocationHistoryResponse])
async def get_reallocation_history(
    request: Request,
    bus_id: Optional[str] = Query(None, description="Filter by bus ID"),
    route_id: Optional[str] = Query(None, description="Filter by route ID (old or new)"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive reallocation history with filtering options"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view reallocation history"
        )

    # Build match query for filtering
    match_query: Dict[str, Any] = {}

    if bus_id:
        match_query["bus_id"] = bus_id

    if route_id:
        match_query["$or"] = [
            {"current_route_id": route_id},
            {"requested_route_id": route_id},
            {"old_route_id": route_id},
            {"new_route_id": route_id}
        ]

    if status_filter:
        match_query["status"] = status_filter.upper()

    # Date filtering
    date_filter: Dict[str, Any] = {}
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date)
            date_filter["$gte"] = start_datetime
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )

    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date + "T23:59:59")
            date_filter["$lte"] = end_datetime
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )

    if date_filter:
        match_query["$or"] = [
            {"created_at": date_filter},
            {"reallocated_at": date_filter}
        ]

    # Build aggregation pipeline to enrich data
    pipeline: List[Dict[str, Any]] = []

    if match_query:
        pipeline.append({"$match": match_query})

    # Add lookups for related data
    pipeline.extend([
        # Lookup bus information
        {
            "$lookup": {
                "from": "buses",
                "localField": "bus_id",
                "foreignField": "_id",
                "as": "bus_data"
            }
        },
        # Lookup old/current route information
        {
            "$lookup": {
                "from": "routes",
                "localField": "current_route_id",
                "foreignField": "_id",
                "as": "old_route_data"
            }
        },
        {
            "$lookup": {
                "from": "routes",
                "localField": "old_route_id",
                "foreignField": "_id",
                "as": "old_route_data_direct"
            }
        },
        # Lookup new/requested route information
        {
            "$lookup": {
                "from": "routes",
                "localField": "requested_route_id",
                "foreignField": "_id",
                "as": "new_route_data"
            }
        },
        {
            "$lookup": {
                "from": "routes",
                "localField": "new_route_id",
                "foreignField": "_id",
                "as": "new_route_data_direct"
            }
        },
        # Lookup user information for requested_by
        {
            "$lookup": {
                "from": "users",
                "localField": "requested_by_user_id",
                "foreignField": "_id",
                "as": "requested_by_data"
            }
        },
        # Lookup user information for reallocated_by
        {
            "$lookup": {
                "from": "users",
                "localField": "reallocated_by",
                "foreignField": "_id",
                "as": "reallocated_by_data"
            }
        },
        # Lookup user information for reviewed_by
        {
            "$lookup": {
                "from": "users",
                "localField": "reviewed_by",
                "foreignField": "_id",
                "as": "reviewed_by_data"
            }
        },
        # Add computed fields
        {
            "$addFields": {
                "bus_number": {"$arrayElemAt": ["$bus_data.license_plate", 0]},
                "old_route_name": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$old_route_data"}, 0]},
                        "then": {"$arrayElemAt": ["$old_route_data.name", 0]},
                        "else": {"$arrayElemAt": ["$old_route_data_direct.name", 0]}
                    }
                },
                "new_route_name": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$new_route_data"}, 0]},
                        "then": {"$arrayElemAt": ["$new_route_data.name", 0]},
                        "else": {"$arrayElemAt": ["$new_route_data_direct.name", 0]}
                    }
                },
                "requested_by_name": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$requested_by_data"}, 0]},
                        "then": {
                            "$concat": [
                                {"$arrayElemAt": ["$requested_by_data.first_name", 0]},
                                " ",
                                {"$arrayElemAt": ["$requested_by_data.last_name", 0]}
                            ]
                        },
                        "else": None
                    }
                },
                "reallocated_by_name": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$reallocated_by_data"}, 0]},
                        "then": {
                            "$concat": [
                                {"$arrayElemAt": ["$reallocated_by_data.first_name", 0]},
                                " ",
                                {"$arrayElemAt": ["$reallocated_by_data.last_name", 0]}
                            ]
                        },
                        "else": None
                    }
                },
                "reviewed_by_name": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$reviewed_by_data"}, 0]},
                        "then": {
                            "$concat": [
                                {"$arrayElemAt": ["$reviewed_by_data.first_name", 0]},
                                " ",
                                {"$arrayElemAt": ["$reviewed_by_data.last_name", 0]}
                            ]
                        },
                        "else": None
                    }
                },
                "reallocation_type": {
                    "$cond": {
                        "if": {"$ifNull": ["$requested_by_user_id", False]},
                        "then": "FORMAL_REQUEST",
                        "else": "DIRECT_REALLOCATION"
                    }
                },
                # Normalize route IDs for consistent response
                "old_route_id": {
                    "$cond": {
                        "if": {"$ifNull": ["$old_route_id", False]},
                        "then": "$old_route_id",
                        "else": "$current_route_id"
                    }
                },
                "new_route_id": {
                    "$cond": {
                        "if": {"$ifNull": ["$new_route_id", False]},
                        "then": "$new_route_id",
                        "else": "$requested_route_id"
                    }
                }
            }
        },
        # Remove lookup arrays to clean up response
        {
            "$project": {
                "bus_data": 0,
                "old_route_data": 0,
                "old_route_data_direct": 0,
                "new_route_data": 0,
                "new_route_data_direct": 0,
                "requested_by_data": 0,
                "reallocated_by_data": 0,
                "reviewed_by_data": 0
            }
        },
        # Sort by most recent first
        {"$sort": {"created_at": -1}},
        # Pagination
        {"$skip": skip},
        {"$limit": limit}
    ])

    # Execute aggregation
    history_cursor = request.app.state.mongodb.reallocation_requests.aggregate(pipeline)
    history_records = await history_cursor.to_list(length=limit)

    # Transform to response format
    history_responses = []
    for record in history_records:
        # Convert MongoDB document to ReallocationHistoryResponse
        history_response = ReallocationHistoryResponse(
            id=str(record["_id"]),
            bus_id=record["bus_id"],
            bus_number=record.get("bus_number"),
            old_route_id=record.get("old_route_id"),
            old_route_name=record.get("old_route_name"),
            new_route_id=record.get("new_route_id"),
            new_route_name=record.get("new_route_name"),
            reason=record.get("reason"),
            description=record.get("description"),
            priority=record.get("priority"),
            status=record.get("status", "PENDING"),
            requested_by_user_id=record.get("requested_by_user_id"),
            requested_by_name=record.get("requested_by_name"),
            reallocated_by=record.get("reallocated_by"),
            reallocated_by_name=record.get("reallocated_by_name"),
            reviewed_by=record.get("reviewed_by"),
            reviewed_by_name=record.get("reviewed_by_name"),
            reviewed_at=record.get("reviewed_at"),
            reallocated_at=record.get("reallocated_at").isoformat() if record.get("reallocated_at") else None,
            review_notes=record.get("review_notes"),
            reallocation_type=record.get("reallocation_type", "UNKNOWN"),
            created_at=record.get("created_at", datetime.utcnow()),
            updated_at=record.get("updated_at", datetime.utcnow())
        )
        history_responses.append(history_response)

    return history_responses
