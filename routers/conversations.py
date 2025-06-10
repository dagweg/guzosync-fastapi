from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List

from datetime import datetime

from core.dependencies import get_current_user
from models import User, Message, MessageType
from schemas.conversation import MessageResponse, ConversationResponse, SendMessageRequest
from core.realtime.chat import chat_service

from core import transform_mongo_doc
from core.mongo_utils import model_to_mongo_doc

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
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):    
    """Get messages from a conversation"""
    # Check if user is part of the conversation
    conversation = await request.app.state.mongodb.conversations.find_one({
        "_id": conversation_id,
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
    conversation_id: str,
    message_request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a message to a conversation"""
    # Check if user is part of the conversation
    conversation = await request.app.state.mongodb.conversations.find_one({
        "_id": conversation_id,
        "participants": current_user.id
    })
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
      # Create Message model instance
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=message_request.content,
        message_type=MessageType(message_request.message_type) if message_request.message_type else MessageType.TEXT,
        sent_at=datetime.utcnow()
    )
    
    # Convert model to MongoDB document
    message_doc = model_to_mongo_doc(message)
    result = await request.app.state.mongodb.messages.insert_one(message_doc)
    
    # Update conversation's last message timestamp
    await request.app.state.mongodb.conversations.update_one(
        {"_id": conversation_id},
        {"$set": {"last_message_at": datetime.utcnow()}}
    )
    
    created_message = await request.app.state.mongodb.messages.find_one({"_id": result.inserted_id})
    response_message = transform_mongo_doc(created_message, MessageResponse)
    
    # Send real-time message to conversation participants
    await chat_service.send_real_time_message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=message_request.content,
        message_type=message_request.message_type if message_request.message_type else "TEXT",
        message_id=str(result.inserted_id),
        app_state=request.app.state
    )
    
    return response_message

@router.post("/{conversation_id}/join")
async def join_conversation_websocket(
    request: Request,
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Join a conversation for real-time updates (WebSocket)"""
    success = await chat_service.join_conversation(
        user_id=str(current_user.id),
        conversation_id=conversation_id,
        app_state=request.app.state
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to join this conversation"
        )
    
    return {"message": f"Joined conversation {conversation_id} for real-time updates"}

@router.post("/{conversation_id}/leave")
async def leave_conversation_websocket(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Leave a conversation's real-time updates"""
    await chat_service.leave_conversation(str(current_user.id), conversation_id)
    return {"message": f"Left conversation {conversation_id} real-time updates"}

@router.post("/{conversation_id}/typing")
async def update_typing_status(
    conversation_id: str,
    is_typing: bool = Query(..., description="Whether user is currently typing"),
    current_user: User = Depends(get_current_user)
):
    """Update typing status in conversation"""
    await chat_service.notify_typing(
        conversation_id=conversation_id,
        user_id=str(current_user.id),
        is_typing=is_typing
    )
    
    return {"message": "Typing status updated"}
