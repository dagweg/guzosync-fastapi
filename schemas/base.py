from datetime import datetime
from typing import Optional, TypeVar, Generic
from pydantic import BaseModel, Field
from uuid import UUID

T = TypeVar('T')

class DateTimeModelMixin(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Location(BaseModel):
    latitude: float
    longitude: float

class RelatedEntity(BaseModel):
    entity_type: str
    entity_id: str