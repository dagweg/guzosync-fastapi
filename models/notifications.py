from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from enum import Enum

from .base import BaseDBModel


class NotificationType(str, Enum):
    ALERT = "ALERT"
    UPDATE = "UPDATE"
    PROMOTION = "PROMOTION"
    REMINDER = "REMINDER"
    GENERAL = "GENERAL"
    TRIP_UPDATE = "TRIP_UPDATE"
    SERVICE_ALERT = "SERVICE_ALERT"

class RelatedEntity(BaseModel):
    entity_type: str
    entity_id: str

class Notification(BaseDBModel):
    user_id: str
    title: str
    message: str
    type: NotificationType
    is_read: bool = False
    related_entity: Optional[RelatedEntity] = None

class NotificationSettings(BaseDBModel):
    email_enabled: bool
    user_id: str