from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from uuid import UUID

from models import User, Feedback
from schemas.feedback import SubmitFeedbackRequest, FeedbackResponse
from routers.accounts import get_current_user

router = APIRouter(prefix="/api/trip", tags=["feedback"])

@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(request: SubmitFeedbackRequest, current_user: User = Depends(get_current_user)):
    from fastapi import Request
    request_obj = Request
    
    feedback = Feedback(
        submitted_by_user_id=current_user.id,
        content=request.content,
        rating=request.rating,
        related_trip_id=request.related_trip_id,
        related_bus_id=request.related_bus_id
    )
    
    result = await request_obj.app.mongodb.feedback.insert_one(feedback.dict())
    created_feedback = await request_obj.app.mongodb.feedback.find_one({"_id": result.inserted_id})
    
    return FeedbackResponse(**created_feedback)

@router.get("/feedback", response_model=List[FeedbackResponse])
async def get_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    from fastapi import Request
    request = Request
    
    # For regular users, only show their own feedback
    query = {"submitted_by_user_id": current_user.id}
    
    # For admins, show all feedback
    if current_user.role in ["CONTROL_CENTER_ADMIN", "REGULATOR"]:
        query = {}
    
    feedback_list = await request.app.mongodb.feedback.find(query).skip(skip).limit(limit).to_list(length=limit)
    
    return [FeedbackResponse(**feedback) for feedback in feedback_list]