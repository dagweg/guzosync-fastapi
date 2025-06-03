from typing import Optional, List
from pydantic import BaseModel

from datetime import datetime
from enum import Enum
from .base import DateTimeModelMixin, RelatedEntity


class NotificationType(str, Enum):
    ALERT = "ALERT"
    UPDATE = "UPDATE"
    PROMOTION = "PROMOTION"
    REMINDER = "REMINDER"

class BroadcastNotificationRequest(BaseModel):
    title: str
    message: str
    type: NotificationType
    target_user_ids: Optional[List[str]] = None
    target_roles: Optional[List[str]] = None
    related_entity: Optional[RelatedEntity] = None

    

class NotificationResponse(DateTimeModelMixin):
    id: str
    user_id: str
    title: str
    message: str
    type: NotificationType
    is_read: bool
    related_entity: Optional[RelatedEntity] = None

class UpdateNotificationSettingsRequest(BaseModel):
    email_enabled: bool

class NotificationSettingsResponse(BaseModel):
    id: str
    user_id: str
    email_enabled: bool

    