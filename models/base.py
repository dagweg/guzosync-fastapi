from datetime import datetime

from pydantic import BaseModel, Field
from core.custom_types import  generate_uuid


class Location(BaseModel):
    latitude: float
    longitude: float


class BaseDBModel(BaseModel):
    id: str = Field(default_factory=generate_uuid)  # Remove _id alias, use id as primary key
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True