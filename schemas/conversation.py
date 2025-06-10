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
    title: str = Field(..., min_length=1, max_length=200, description="Brief title for the conversation")
    content: str = Field(..., min_length=1, max_length=1000, description="Initial message content")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Message content")
    message_type: str = "TEXT"