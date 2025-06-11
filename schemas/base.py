from datetime import datetime
from typing import Optional, TypeVar, Generic
from pydantic import BaseModel, Field

T = TypeVar('T')

class DateTimeModelMixin(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

      # Allow arbitrary types like ObjectId

class RelatedEntity(BaseModel):
    entity_type: str
    entity_id: str  # This should be ObjectId if it refers to a DB ID, or str if it's a generic ID.
                    # For now, keeping as str as per previous structure. If conversion issues arise,
                    # this might need to be ObjectId and handled in routes/services.