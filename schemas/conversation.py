from typing import List, Optional
from pydantic import BaseModel, Field

from datetime import datetime
from .base import DateTimeModelMixin


class MessageResponse(DateTimeModelMixin):
    id: str
    conversation_id: str
    sender_id: str
    content: str
    message_type: str = "TEXT"
    sent_at: datetime


class ConversationResponse(DateTimeModelMixin):
    id: str
    participants: List[str]
    title: str
    status: str = "ACTIVE"
    created_by: str
    last_message_at: Optional[datetime] = None


class CreateConversationRequest(BaseModel):
    # Option 1: For general user-to-user conversations
    participant_id: str = Field(..., description="ID of the user to start conversation with")
    initial_message: str = Field(..., min_length=1, max_length=1000, description="Initial message content")

    # Optional: conversation title (can be auto-generated if not provided)
    title: Optional[str] = Field(None, max_length=200, description="Optional conversation title")


class CreateSupportConversationRequest(BaseModel):
    # Option 2: For field staff to contact control center (current system)
    title: str = Field(..., min_length=1, max_length=200, description="Brief title for the support request")
    content: str = Field(..., min_length=1, max_length=1000, description="Initial message content")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Message content")
    message_type: str = "TEXT"