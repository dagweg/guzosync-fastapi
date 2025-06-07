from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional
from datetime import datetime

from core.dependencies import get_current_user
from core.mongo_utils import transform_mongo_doc, model_to_mongo_doc
from core.email_service import send_welcome_email
from core import get_logger
from models import User, ApprovalRequest
from models.user import UserRole
from models.approval import ApprovalStatus
from schemas.approval import ApprovalRequestResponse, ApprovalActionRequest
from schemas.user import UserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])

@router.get("/requests", response_model=List[ApprovalRequestResponse])
async def get_approval_requests(
    request: Request,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all approval requests (CONTROL_ADMIN only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CONTROL_ADMIN can view approval requests"
        )
    
    try:
        # Build query filter
        query = {}
        if status_filter:
            if status_filter.upper() not in [s.value for s in ApprovalStatus]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status filter"
                )
            query["status"] = status_filter.upper()
        
        # Fetch approval requests
        requests_cursor = request.app.state.mongodb.approval_requests.find(query)
        requests = await requests_cursor.to_list(length=None)
        
        # Transform to response models
        response_requests = []
        for req in requests:
            response_requests.append(transform_mongo_doc(req, ApprovalRequestResponse))
        
        logger.info(f"Retrieved {len(response_requests)} approval requests", 
                   extra={"admin_user": current_user.email, "status_filter": status_filter})
        return response_requests
        
    except Exception as e:
        logger.error("Error retrieving approval requests", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving approval requests"
        )

@router.get("/requests/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(
    request_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get specific approval request (CONTROL_ADMIN only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CONTROL_ADMIN can view approval requests"
        )
    try:
        # Fetch the approval request using UUID string (not ObjectId)
        approval_request = await request.app.state.mongodb.approval_requests.find_one(
            {"_id": request_id}
        )
        
        if not approval_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found"
            )
        
        return transform_mongo_doc(approval_request, ApprovalRequestResponse)
        
    except Exception as e:
        logger.error("Error retrieving approval request", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving approval request"
        )

@router.post("/requests/{request_id}/action", response_model=UserResponse)
async def process_approval_request(
    request_id: str,
    action_data: ApprovalActionRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Approve or reject an approval request (CONTROL_ADMIN only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CONTROL_ADMIN can process approval requests"
        )
    
    if action_data.action not in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be either APPROVED or REJECTED"
        )
    try:
        # Fetch the approval request using UUID string (not ObjectId)
        approval_request = await request.app.state.mongodb.approval_requests.find_one(
            {"_id": request_id}
        )
        
        if not approval_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found"
            )
        
        if approval_request["status"] != ApprovalStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This request has already been processed"
            )
        
        # If approving, check if user already exists before updating approval status
        if action_data.action == ApprovalStatus.APPROVED:
            # Check if user already exists (safety check)
            existing_user = await request.app.state.mongodb.users.find_one( #type:ignore[unreachable]
                {"email": approval_request["email"]}
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User account already exists for this email"
                )
        
        # Update the approval request
        update_data = {
            "status": action_data.action.value,
            "reviewed_by": str(current_user.id),
            "reviewed_at": datetime.utcnow(),
            "review_notes": action_data.review_notes
        }
        
        await request.app.state.mongodb.approval_requests.update_one(
            {"_id": request_id},
            {"$set": update_data}
        )
        
        # If approved, create the user account
        if action_data.action == ApprovalStatus.APPROVED:
            
            # Create the user
            user = User( #type:ignore[unreachable]
                first_name=approval_request["first_name"],
                last_name=approval_request["last_name"],
                email=approval_request["email"],
                password="TempPassword123!",  # Generate a temporary password
                role=UserRole.CONTROL_STAFF,
                phone_number=approval_request["phone_number"],
                profile_image=approval_request.get("profile_image"),
                is_active=True,
                pending_approval=False
            )
            
            # Insert user into database
            user_doc = model_to_mongo_doc(user)
            result = await request.app.state.mongodb.users.insert_one(user_doc)
            
            # Retrieve the created user
            created_user = await request.app.state.mongodb.users.find_one({"_id": result.inserted_id})
              # Send welcome email with temporary password
            full_name = f"{approval_request['first_name']} {approval_request['last_name']}"
            email_sent = await send_welcome_email(approval_request["email"], full_name)
            if not email_sent:
                logger.warning("Failed to send welcome email", extra={"email": approval_request["email"]})
            
            logger.info(f"Approval request approved and user created", 
                       extra={"request_id": request_id, "admin": current_user.email, 
                             "user_email": approval_request["email"]})
            
            return transform_mongo_doc(created_user, UserResponse)
        else:
            # If rejected, just return success message
            logger.info(f"Approval request rejected", 
                       extra={"request_id": request_id, "admin": current_user.email, 
                             "reason": action_data.review_notes})
            
            return {
                "message": "Approval request has been rejected",
                "request_id": request_id,
                "status": "REJECTED"
            }
            
    except Exception as e:
        logger.error("Error processing approval request", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing approval request"
        )

@router.get("/requests/pending/count")
async def get_pending_requests_count(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get count of pending approval requests (CONTROL_ADMIN only)"""
    if current_user.role != UserRole.CONTROL_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CONTROL_ADMIN can view approval request statistics"
        )
    
    try:
        count = await request.app.state.mongodb.approval_requests.count_documents(
            {"status": ApprovalStatus.PENDING.value}
        )
        
        return {"pending_count": count}
        
    except Exception as e:
        logger.error("Error getting pending requests count", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting pending requests count"
        )
