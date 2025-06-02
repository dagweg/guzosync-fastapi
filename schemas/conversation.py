from typing import List, Optional
from pydantic import BaseModel

from datetime import datetime
from .base import DateTimeModelMixin
from core.custom_types import UUID

class MessageResponse(DateTimeModelMixin):
    id: str
    conversation_id: UUID
    sender_id: UUID
    content: str
    message_type: Optional[str] = "TEXT"
    sent_at: datetime

class ConversationResponse(BaseModel):
    id: str
    participants: List[UUID]
    last_message_at: Optional[datetime] = None

    

class SendMessageRequest(BaseModel):
    content: str
    message_type: Optional[str] = "TEXT"