from faker import Faker
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Any, List, Optional

from datetime import datetime

from core.dependencies import get_current_user
from core.mongo_utils import transform_mongo_doc, model_to_mongo_doc
from core.email_service import email_service
from core import get_logger
from core.security import generate_secure_password, get_password_hash
from models import User, BusStop, Route, Location
from schemas.user import RegisterUserRequest, UserResponse
from schemas.transport import (
    CreateBusStopRequest, UpdateBusStopRequest, BusStopResponse,
    CreateBusRequest, UpdateBusRequest, BusResponse
)
from schemas.route import CreateRouteRequest, UpdateRouteRequest, RouteResponse
from models.user import UserRole
from schemas.control_center import (RegisterPersonnelRequest, RegisterControlStaffRequest)
from uuid import uuid4
from core.ai_agent import route_optimization_agent


logger = get_logger(__name__)



router = APIRouter(prefix="/api/control-center", tags=["control-center"])

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
        is_active=True
    )

    # Convert model to MongoDB document
    user_doc = model_to_mongo_doc(user)
    result = await request.app.state.mongodb.users.insert_one(user_doc)
    created_user = await request.app.state.mongodb.users.find_one({"_id": result.inserted_id})

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
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get all queue regulators"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view personnel"
        )
    
    regulators = await request.app.state.mongodb.users.find(
        {"role": "REGULATOR"}
    ).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(regulator, UserResponse) for regulator in regulators]

@router.get("/personnel/queue-regulators/{regulator_id}", response_model=UserResponse)
async def get_queue_regulator(
    request: Request,
    regulator_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific queue regulator"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view personnel"
        )

    regulator = await request.app.state.mongodb.users.find_one({
        "_id": regulator_id,
        "role": "REGULATOR"
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update personnel"
        )
    
    result = await request.app.state.mongodb.users.update_one(
        {"_id": regulator_id, "role": "REGULATOR"},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulator not found"
        )
    
    updated_regulator = await request.app.state.mongodb.users.find_one({"_id": regulator_id})
    return transform_mongo_doc(updated_regulator, UserResponse)

@router.delete("/personnel/queue-regulators/{regulator_id}")
async def delete_queue_regulator(
    request: Request,
    regulator_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete queue regulator"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can delete personnel"
        )
    
    result = await request.app.state.mongodb.users.delete_one({
        "_id": regulator_id,
        "role": "REGULATOR"
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can assign regulators"
        )
    
    # Check if regulator exists
    regulator = await request.app.state.mongodb.users.find_one({
        "_id": regulator_id,
        "role": "REGULATOR"
    })
    if not regulator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulator not found"
        )
    
    # Check if bus stop exists
    bus_stop = await request.app.state.mongodb.bus_stops.find_one({"_id": bus_stop_id})
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
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get all bus drivers"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view personnel"
        )
    
    drivers = await request.app.state.mongodb.users.find(
        {"role": "DRIVER"}
    ).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(driver, UserResponse) for driver in drivers]

@router.get("/personnel/bus-drivers/{driver_id}", response_model=UserResponse)
async def get_bus_driver(
    request: Request,
    driver_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific bus driver"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view personnel"
        )
    
    driver = await request.app.state.mongodb.users.find_one({
        "_id": driver_id,
        "role": "DRIVER"
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update personnel"
        )
    
    result = await request.app.state.mongodb.users.update_one(
        {"_id": driver_id, "role": "DRIVER"},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    updated_driver = await request.app.state.mongodb.users.find_one({"_id": driver_id})
    return transform_mongo_doc(updated_driver, UserResponse)

@router.delete("/personnel/bus-drivers/{driver_id}")
async def delete_bus_driver(
    request: Request,
    driver_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete bus driver"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can delete personnel"
        )
    
    result = await request.app.state.mongodb.users.delete_one({
        "_id": driver_id,
        "role": "DRIVER"
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can assign drivers"
        )
    
    # Check if driver exists
    driver = await request.app.state.mongodb.users.find_one({
        "_id": driver_id,
        "role": "DRIVER"
    })
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Check if bus exists
    bus = await request.app.state.mongodb.buses.find_one({"_id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
      # Update bus with assigned driver
    await request.app.state.mongodb.buses.update_one(
        {"_id": bus_id},
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
    limit: int = Query(10, ge=1, le=100),
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
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
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get all bus stops for management"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view bus stop details"
        )
    
    bus_stop = await request.app.state.mongodb.bus_stops.find_one({"_id": bus_stop_id})
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update bus stops"
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

@router.delete("/bus-stops/{bus_stop_id}")
async def delete_control_center_bus_stop(
    request: Request,
    bus_stop_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete bus stop"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
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

# Buses Management
@router.get("/buses", response_model=List[BusResponse])
async def get_control_center_buses(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get all buses for management"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view all buses"
        )
    
    buses = await request.app.state.mongodb.buses.find({}).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(bus, BusResponse) for bus in buses]

@router.get("/buses/{bus_id}", response_model=BusResponse)
async def get_control_center_bus(
    request: Request,
    bus_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific bus for management"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view bus details"
        )
    
    bus = await request.app.state.mongodb.buses.find_one({"_id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    return transform_mongo_doc(bus, BusResponse)

@router.put("/buses/{bus_id}", response_model=BusResponse)
async def update_control_center_bus(
    request: Request,
    bus_id: str,
    update_data: UpdateBusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update bus"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can update buses"
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
    
    updated_bus = await request.app.state.mongodb.buses.find_one({"_id": bus_id})
    return transform_mongo_doc(updated_bus, BusResponse)

@router.put("/buses/{bus_id}/assign-route/{route_id}")
async def assign_bus_to_route(
    request: Request,
    bus_id: str,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Assign bus to a route"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can assign buses to routes"
        )
    
    # Check if bus exists
    bus = await request.app.state.mongodb.buses.find_one({"_id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    # Check if route exists
    route = await request.app.state.mongodb.routes.find_one({"_id": route_id})
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    # Update bus with assigned route
    await request.app.state.mongodb.buses.update_one(
        {"_id": bus_id},
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can reallocate buses"
        )
    
    # Check if bus exists
    bus = await request.app.state.mongodb.buses.find_one({"_id": bus_id})
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found"
        )
    
    # Check if route exists
    route = await request.app.state.mongodb.routes.find_one({"_id": route_id})
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
        {"_id": bus_id},
        {"$set": {"assigned_route_id": route_id}}
    )
    
    return {"message": "Bus reallocated to new route successfully"}

@router.post("/buses/deploy-stationary")
async def deploy_stationary_bus(
    request: Request,
    deployment_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Deploy a stationary bus"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
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
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get all routes for management"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view route details"
        )
    
    route = await request.app.state.mongodb.routes.find_one({"_id": route_id})
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
    if current_user.role != "CONTROL_CENTER_ADMIN":
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

@router.delete("/routes/{route_id}")
async def delete_control_center_route(
    request: Request,
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete route"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
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

@router.get("/reallocation-requests")
async def get_reallocation_requests(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get all reallocation requests"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can view reallocation requests"
        )
    
    requests = await request.app.state.mongodb.reallocation_requests.find({}).sort("reallocated_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return requests

@router.post("/reallocation-requests/{request_id}/process")
async def process_reallocation_request(
    request: Request,
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Process a reallocation request using AI agent to determine optimal route"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center admins can process reallocation requests"
        )
    
    # Get the reallocation request
    reallocation_request = await request.app.state.mongodb.reallocation_requests.find_one({"_id": request_id})
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
    
    # Use AI agent to determine optimal route if not already set
    optimal_route_id = reallocation_request.get("requested_route_id")
    if not optimal_route_id:
        optimal_route_id = await route_optimization_agent.determine_optimal_route(
            bus_id=reallocation_request["bus_id"],
            current_route_id=reallocation_request["current_route_id"],
            reason=reallocation_request["reason"],
            priority=reallocation_request.get("priority", "NORMAL"),
            description=reallocation_request.get("description", ""),
            mongodb_client=request.app.state.mongodb
        )
    
    if not optimal_route_id:
        # Update request as rejected if no suitable route found
        await request.app.state.mongodb.reallocation_requests.update_one(
            {"_id": request_id},
            {
                "$set": {
                    "status": "REJECTED",
                    "reviewed_by": current_user.id,
                    "reviewed_at": datetime.utcnow().isoformat(),
                    "review_notes": "AI agent could not find suitable alternative route"
                }
            }
        )
        
        return {"message": "No suitable route found for reallocation", "status": "REJECTED"}
    
    # Verify the optimal route exists and is active
    optimal_route = await request.app.state.mongodb.routes.find_one({"_id": optimal_route_id})
    if not optimal_route or not optimal_route.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected route is not available"
        )
    
    # Update the bus assignment
    bus_update_result = await request.app.state.mongodb.buses.update_one(
        {"_id": reallocation_request["bus_id"]},
        {"$set": {"assigned_route_id": optimal_route_id}}
    )
    
    if bus_update_result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found or could not be updated"
        )
    
    # Update reallocation request as approved and completed
    await request.app.state.mongodb.reallocation_requests.update_one(
        {"_id": request_id},
        {
            "$set": {
                "requested_route_id": optimal_route_id,
                "status": "COMPLETED",
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.utcnow().isoformat(),
                "review_notes": f"AI agent selected optimal route: {optimal_route['name']}"
            }
        }
    )
    
    return {
        "message": "Reallocation request processed successfully",
        "status": "COMPLETED",
        "bus_id": reallocation_request["bus_id"],
        "old_route_id": reallocation_request["current_route_id"],
        "new_route_id": optimal_route_id,
        "route_name": optimal_route["name"]
    }

@router.get("/reallocation-requests/pending")
async def get_pending_reallocation_requests(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get pending reallocation requests that need AI processing"""
    if current_user.role != "CONTROL_CENTER_ADMIN":
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
