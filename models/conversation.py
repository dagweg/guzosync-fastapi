from datetime import datetime
from typing import Optional, List
from enum import Enum

from .base import BaseDBModel


class MessageType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    FILE = "FILE"
    SYSTEM = "SYSTEM"


class Message(BaseDBModel):
    conversation_id: str
    sender_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    sent_at: datetime


class Conversation(BaseDBModel):
    participants: List[str]
    last_message_at: Optional[datetime] = None
