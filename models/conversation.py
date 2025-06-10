from datetime import datetime
from typing import Optional, List
from enum import Enum

from .base import BaseDBModel


class MessageType(str, Enum):
    TEXT = "TEXT"
    SYSTEM = "SYSTEM"


class ConversationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class Message(BaseDBModel):
    conversation_id: str
    sender_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    sent_at: datetime


class Conversation(BaseDBModel):
    participants: List[str]  # List of user IDs
    title: str  # Brief description of the conversation
    status: ConversationStatus = ConversationStatus.ACTIVE
    created_by: str  # User ID who initiated the conversation
    last_message_at: Optional[datetime] = None
