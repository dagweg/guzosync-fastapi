from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List

from datetime import datetime

from core.dependencies import get_current_user
from models import User, Message, MessageType, Conversation, UserRole
from models.conversation import ConversationStatus
from schemas.conversation import MessageResponse, ConversationResponse, SendMessageRequest, CreateConversationRequest
from core.realtime.chat import chat_service

from core import transform_mongo_doc
from core.mongo_utils import model_to_mongo_doc

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def can_use_chat(user_role: UserRole) -> bool:
    """Check if user role is allowed to use chat system"""
    allowed_roles = {
        UserRole.BUS_DRIVER,
        UserRole.QUEUE_REGULATOR,
        UserRole.CONTROL_STAFF,
        UserRole.CONTROL_ADMIN
    }
    return user_role in allowed_roles


def can_communicate_with(sender_role: UserRole, target_role: UserRole) -> bool:
    """Check if two user roles can communicate with each other"""
    # Field roles (drivers/regulators) can communicate with control center
    field_roles = {UserRole.BUS_DRIVER, UserRole.QUEUE_REGULATOR}
    control_roles = {UserRole.CONTROL_STAFF, UserRole.CONTROL_ADMIN}
    
    # Field roles can communicate with control roles and vice versa
    if sender_role in field_roles and target_role in control_roles:
        return True
    if sender_role in control_roles and target_role in field_roles:
        return True
    
    # Control roles can communicate among themselves
    if sender_role in control_roles and target_role in control_roles:
        return True
    
    return False


async def get_control_center_users(mongodb) -> List[dict]:
    """Get all control center users (staff and admin)"""
    return await mongodb.users.find({
        "role": {"$in": ["CONTROL_STAFF", "CONTROL_ADMIN"]},
        "is_active": True
    }).to_list(length=None)

@router.post("/create", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: Request,
    conversation_request: CreateConversationRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation (only for field staff to contact control center)"""
    # Check if user can use chat
    if not can_use_chat(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role is not authorized to use the chat system"
        )
    
    # Field staff (drivers/regulators) can only create conversations with control center
    if current_user.role in [UserRole.BUS_DRIVER, UserRole.QUEUE_REGULATOR]:
        # Get all control center users and add them to conversation
        control_users = await get_control_center_users(request.app.state.mongodb)
        if not control_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No control center staff available"
            )
        
        participants = [current_user.id] + [user.get("id", str(user["_id"])) for user in control_users]
    else:
        # Control staff cannot create new conversations, only respond to existing ones
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Control center staff can only respond to existing conversations"
        )
    
    # Create conversation
    conversation = Conversation(
        participants=participants,
        title=conversation_request.title,
        status=ConversationStatus.ACTIVE,
        created_by=current_user.id,
        last_message_at=datetime.utcnow()
    )
    
    conversation_doc = model_to_mongo_doc(conversation)
    result = await request.app.state.mongodb.conversations.insert_one(conversation_doc)
    
    # Get the conversation ID from the created document
    conversation_id = conversation_doc["id"]  # Use UUID string, not ObjectId

    # Create initial message
    initial_message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=conversation_request.content,
        message_type=MessageType.TEXT,
        sent_at=datetime.utcnow()
    )

    message_doc = model_to_mongo_doc(initial_message)
    await request.app.state.mongodb.messages.insert_one(message_doc)

    # Get created conversation using UUID string
    created_conversation = await request.app.state.mongodb.conversations.find_one({"id": conversation_id})
    
    # Send real-time notification to control center
    await chat_service.send_real_time_message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=conversation_request.content,
        message_id=message_doc["id"],  # Use UUID string
        message_type="TEXT",
        app_state=request.app.state
    )
    
    return transform_mongo_doc(created_conversation, ConversationResponse)


@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Get conversations for current user"""
    # Check if user can use chat
    if not can_use_chat(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role is not authorized to use the chat system"
        )
    
    conversations = await request.app.state.mongodb.conversations.find(
        {"participants": current_user.id}
    ).sort("last_message_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    return [transform_mongo_doc(conversation, ConversationResponse) for conversation in conversations]

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    request: Request,
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    current_user: User = Depends(get_current_user)
):    
    """Get messages from a conversation"""
    # Check if user can use chat
    if not can_use_chat(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role is not authorized to use the chat system"
        )
    
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
    conversation_id: str,
    message_request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a message to a conversation"""
    # Check if user can use chat
    if not can_use_chat(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role is not authorized to use the chat system"
        )
    
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
    
    # Only allow TEXT message type for simplicity
    if message_request.message_type != "TEXT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only text messages are allowed"
        )
    
    # Create Message model instance
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=message_request.content,
        message_type=MessageType.TEXT,
        sent_at=datetime.utcnow()
    )
    
    # Convert model to MongoDB document
    message_doc = model_to_mongo_doc(message)
    result = await request.app.state.mongodb.messages.insert_one(message_doc)
    
    # Update conversation's last message timestamp
    await request.app.state.mongodb.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"last_message_at": datetime.utcnow()}}
    )

    created_message = await request.app.state.mongodb.messages.find_one({"id": message_doc["id"]})
    response_message = transform_mongo_doc(created_message, MessageResponse)
    
    # Send real-time message to conversation participants
    await chat_service.send_real_time_message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=message_request.content,
        message_type="TEXT",
        message_id=message_doc["id"],  # Use UUID string
        app_state=request.app.state
    )
    
    return response_message

@router.post("/{conversation_id}/close")
async def close_conversation(
    request: Request,
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Close a conversation (only for control center staff)"""
    # Only control center staff can close conversations
    if current_user.role not in [UserRole.CONTROL_STAFF, UserRole.CONTROL_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center staff can close conversations"
        )
    
    # Check if conversation exists and user is participant
    conversation = await request.app.state.mongodb.conversations.find_one({
        "id": conversation_id,
        "participants": current_user.id
    })
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    # Update conversation status
    await request.app.state.mongodb.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"status": "CLOSED", "updated_at": datetime.utcnow()}}
    )
    
    # Send system message about closure
    system_message = Message(
        conversation_id=conversation_id,
        sender_id="system",
        content=f"Conversation closed by {current_user.first_name} {current_user.last_name}",
        message_type=MessageType.SYSTEM,
        sent_at=datetime.utcnow()
    )
    
    message_doc = model_to_mongo_doc(system_message)
    await request.app.state.mongodb.messages.insert_one(message_doc)
    
    return {"message": "Conversation closed successfully"}


@router.get("/stats")
async def get_chat_stats(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get chat statistics (only for control center)"""
    if current_user.role not in [UserRole.CONTROL_STAFF, UserRole.CONTROL_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only control center staff can view chat statistics"
        )
    
    # Get conversation counts
    total_conversations = await request.app.state.mongodb.conversations.count_documents({})
    active_conversations = await request.app.state.mongodb.conversations.count_documents({"status": "ACTIVE"})
    closed_conversations = await request.app.state.mongodb.conversations.count_documents({"status": "CLOSED"})
    
    # Get recent conversations
    recent_conversations = await request.app.state.mongodb.conversations.find(
        {}
    ).sort("created_at", -1).limit(5).to_list(length=5)
    
    return {
        "total_conversations": total_conversations,
        "active_conversations": active_conversations,
        "closed_conversations": closed_conversations,
        "recent_conversations": [
            {
                "id": str(conv["_id"]),
                "title": conv.get("title", ""),
                "status": conv.get("status", "ACTIVE"),
                "created_at": conv.get("created_at"),
                "last_message_at": conv.get("last_message_at")
            }
            for conv in recent_conversations
        ]
    }
