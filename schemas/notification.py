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
    GENERAL = "GENERAL"
    TRIP_UPDATE = "TRIP_UPDATE"
    SERVICE_ALERT = "SERVICE_ALERT"
    ROUTE_REALLOCATION = "ROUTE_REALLOCATION"
    REALLOCATION_REQUEST_DISCARDED = "REALLOCATION_REQUEST_DISCARDED"
    INCIDENT_REPORTED = "INCIDENT_REPORTED"
    CHAT_MESSAGE = "CHAT_MESSAGE"

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

class SubscribeNotificationsRequest(BaseModel):
    notification_types: List[str]

class UnsubscribeNotificationsRequest(BaseModel):
    notification_types: List[str]

class NotificationSubscriptionResponse(BaseModel):
    success: bool
    message: str
    subscribed_types: Optional[List[str]] = None
    unsubscribed_types: Optional[List[str]] = None
    current_subscriptions: Optional[List[str]] = None
    available_types: Optional[List[str]] = None
    subscription_count: Optional[int] = None
    timestamp: str