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

class ConversationResponse(BaseModel):
    id: UUID
    participants: List[UUID]
    last_message_at: Optional[datetime] = None