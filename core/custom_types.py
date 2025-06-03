"""
Custom types for the application.
"""
import uuid
from typing import Annotated
from pydantic import Field, BeforeValidator


def validate_uuid(v: str | uuid.UUID) -> uuid.UUID:
    """Validate and convert string to UUID."""
    if isinstance(v, str):
        return uuid.UUID(v)
    return v


# Custom UUID type that can be used in Pydantic models
UUID = Annotated[uuid.UUID, BeforeValidator(validate_uuid)]

# Function to generate new UUIDs
def generate_uuid() -> str:
    """Generate a new UUID4."""
    return str(uuid.uuid4())


__all__ = ['UUID', 'generate_uuid']
