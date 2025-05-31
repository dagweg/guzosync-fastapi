from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class BaseDBModel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)