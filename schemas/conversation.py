from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from .base import DateTimeModelMixin

class MessageResponse(DateTimeModelMixin):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    message_type: Optional[str] = "TEXT"
    sent_at: datetime

class ConversationResponse(BaseModel):
    id: UUID
    participants: List[UUID]
    last_message_at: Optional[datetime] = None

class SendMessageRequest(BaseModel):
    content: str
    message_type: Optional[str] = "TEXT"