from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List
from uuid import UUID
from datetime import datetime

from core.dependencies import get_current_user
from models import User, Feedback
from models.user import UserRole
from schemas.feedback import SubmitFeedbackRequest, FeedbackResponse

from core import transform_mongo_doc
from core.mongo_utils import model_to_mongo_doc

router = APIRouter(prefix="/api/trip", tags=["trip"])

@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_trip_feedback(
    request: Request,
    feedback_request: SubmitFeedbackRequest, 
    current_user: User = Depends(get_current_user)
):
    """Submit feedback for a trip"""
    # Create Feedback model instance
    feedback = Feedback(
        submitted_by_user_id=current_user.id,
        content=feedback_request.content,
        rating=feedback_request.rating,
        related_trip_id=feedback_request.related_trip_id,
        related_bus_id=feedback_request.related_bus_id
    )
    
    # Convert model to MongoDB document
    feedback_doc = model_to_mongo_doc(feedback)
    result = await request.app.state.mongodb.feedback.insert_one(feedback_doc)
    created_feedback = await request.app.state.mongodb.feedback.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_feedback, FeedbackResponse)

@router.get("/feedback", response_model=List[FeedbackResponse])
async def get_trip_feedback(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get trip feedback"""
    # For regular users, only show their own feedback
    query = {
        "submitted_by_user_id": current_user.id,
        "feedback_type": "TRIP"
    }
    
    # For admins, show all trip feedback
    if current_user.role in [UserRole.CONTROL_ADMIN, UserRole.QUEUE_REGULATOR]:
        query = {"feedback_type": "TRIP"}
    
    feedback_list = await request.app.state.mongodb.feedback.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(feedback, FeedbackResponse) for feedback in feedback_list]
