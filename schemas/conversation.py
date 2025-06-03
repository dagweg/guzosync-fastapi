from typing import List, Optional
from pydantic import BaseModel

from datetime import datetime
from .base import DateTimeModelMixin


class MessageResponse(DateTimeModelMixin):
    id: str
    conversation_id: str
    sender_id: str
    content: str
    message_type: Optional[str] = "TEXT"
    sent_at: datetime

class ConversationResponse(BaseModel):
    id: str
    participants: List[str]
    last_message_at: Optional[datetime] = None

    

class SendMessageRequest(BaseModel):
    content: str
    message_type: Optional[str] = "TEXT"