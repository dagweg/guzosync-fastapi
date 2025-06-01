from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List
from uuid import UUID
from datetime import datetime

from models import User
from schemas.conversation import MessageResponse, ConversationResponse, SendMessageRequest
from core.dependencies import get_current_user
from core import transform_mongo_doc

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get conversations for current user"""
    conversations = await request.app.state.mongodb.conversations.find(
        {"participants": current_user.id}
    ).sort("last_message_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(conversation, ConversationResponse) for conversation in conversations]

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    request: Request,
    conversation_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get messages from a conversation"""
    # Check if user is part of the conversation
    conversation = await request.app.state.mongodb.conversations.find_one({
        "id": conversation_id,
        "participants": current_user.id
    })
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    messages = await request.app.state.mongodb.messages.find(
        {"conversation_id": conversation_id}
    ).sort("sent_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(message, MessageResponse) for message in messages]

@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    request: Request,
    conversation_id: UUID,
    message_request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a message to a conversation"""
    # Check if user is part of the conversation
    conversation = await request.app.state.mongodb.conversations.find_one({
        "id": conversation_id,
        "participants": current_user.id
    })
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    message_data = {
        "conversation_id": conversation_id,
        "sender_id": current_user.id,
        "content": message_request.content,
        "message_type": message_request.message_type,
        "sent_at": datetime.utcnow()
    }
    
    result = await request.app.state.mongodb.messages.insert_one(message_data)
    
    # Update conversation's last message timestamp
    await request.app.state.mongodb.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"last_message_at": datetime.utcnow()}}
    )
    
    created_message = await request.app.state.mongodb.messages.find_one({"_id": result.inserted_id})
    return transform_mongo_doc(created_message, MessageResponse)
