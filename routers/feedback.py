from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List
from uuid import UUID
from datetime import datetime

from models import User, Feedback
from schemas.feedback import SubmitFeedbackRequest, FeedbackResponse
from core.dependencies import get_current_user
from core import transform_mongo_doc

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    request: Request,
    feedback_request: SubmitFeedbackRequest, 
    current_user: User = Depends(get_current_user)
):
    feedback_data = {
        "submitted_by_user_id": current_user.id,
        "content": feedback_request.content,
        "rating": feedback_request.rating,
        "related_trip_id": feedback_request.related_trip_id,
        "related_bus_id": feedback_request.related_bus_id
    }
    
    result = await request.app.state.mongodb.feedback.insert_one(feedback_data)
    created_feedback = await request.app.state.mongodb.feedback.find_one({"_id": result.inserted_id})
    
    return transform_mongo_doc(created_feedback, FeedbackResponse)

@router.get("", response_model=List[FeedbackResponse])
async def get_feedback(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    # For regular users, only show their own feedback
    query = {"submitted_by_user_id": current_user.id}
    
    # For admins, show all feedback
    if current_user.role in ["CONTROL_CENTER_ADMIN", "REGULATOR"]:
        query = {}
    
    feedback_list = await request.app.state.mongodb.feedback.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(feedback, FeedbackResponse) for feedback in feedback_list]