from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum
from uuid import UUID
from .base import BaseDBModel

class NotificationType(str, Enum):
    ALERT = "ALERT"
    UPDATE = "UPDATE"
    PROMOTION = "PROMOTION"
    REMINDER = "REMINDER"

class RelatedEntity(BaseModel):
    entity_type: str
    entity_id: str

class Notification(BaseDBModel):
    user_id: UUID
    title: str
    message: str
    type: NotificationType
    is_read: bool = False
    related_entity: Optional[RelatedEntity] = None

class NotificationSettings(BaseDBModel):
    email_enabled: bool
    user_id: UUID