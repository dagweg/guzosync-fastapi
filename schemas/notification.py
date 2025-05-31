from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID
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
    target_user_ids: Optional[List[UUID]] = None
    target_roles: Optional[List[str]] = None
    related_entity: Optional[RelatedEntity] = None

class NotificationResponse(DateTimeModelMixin):
    id: UUID
    user_id: UUID
    title: str
    message: str
    type: NotificationType
    is_read: bool
    related_entity: Optional[RelatedEntity] = None

class UpdateNotificationSettingsRequest(BaseModel):
    email_enabled: bool

class NotificationSettingsResponse(BaseModel):
    id: UUID
    user_id: UUID
    email_enabled: bool