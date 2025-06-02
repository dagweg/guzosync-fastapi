from typing import Dict, Any, TypeVar, Type, Union
from pydantic import BaseModel
from bson import ObjectId
import uuid
from .custom_types import UUID

__all__ = ['transform_mongo_doc', 'model_to_mongo_doc']

ModelType = TypeVar("ModelType", bound=BaseModel)

def transform_mongo_doc(doc: Dict[str, Any], model_class: Type[ModelType], **defaults) -> ModelType:
    """
    Transform a MongoDB document into a Pydantic model, handling common field conversions
    and applying default values.
    
    Args:
        doc: The MongoDB document
        model_class: The Pydantic model class to convert to
        **defaults: Additional default values to set if not present in doc
        
    Returns:
        An instance of the specified Pydantic model
    """
    if not doc:
        raise ValueError("Cannot transform empty document")
          # Copy the document to avoid modifying the original
    transformed = doc.copy()
      # Convert _id to id if present
    if "_id" in transformed:
        mongo_id = transformed.pop("_id")
        # Handle different types of _id values
        if isinstance(mongo_id, str):
            try:
                # Try to parse as UUID first
                transformed["id"] = uuid.UUID(mongo_id)
            except ValueError:
                # If not a valid UUID string, try to convert ObjectId string to UUID
                if len(mongo_id) == 24:  # ObjectId string length
                    # For ObjectId, create a deterministic UUID by padding
                    padded = mongo_id + '0' * 8
                    try:
                        transformed["id"] = uuid.UUID(padded)
                    except ValueError:
                        # If padding fails, generate new UUID
                        transformed["id"] = uuid.uuid4()
                else:
                    # For other string formats, generate new UUID
                    transformed["id"] = uuid.uuid4()
        elif isinstance(mongo_id, ObjectId):
            # Convert ObjectId to UUID by padding the hex string
            hex_string = str(mongo_id) + '0' * 8  # Pad to 32 chars
            try:
                transformed["id"] = uuid.UUID(hex_string)
            except ValueError:
                transformed["id"] = uuid.uuid4()
        elif isinstance(mongo_id, uuid.UUID):
            # Already a UUID
            transformed["id"] = mongo_id
        else:
            # Unknown type, generate new UUID
            transformed["id"] = uuid.uuid4()
    
    # Convert any string UUID fields back to UUID objects
    for field_name, field_type in model_class.__annotations__.items():
        if field_name in transformed and transformed[field_name] is not None:
            # Check if this field should be a UUID
            if hasattr(field_type, '__origin__') and field_type.__origin__ is Union:
                # Handle Optional[UUID] fields
                args = getattr(field_type, '__args__', ())
                if uuid.UUID in args and isinstance(transformed[field_name], str):
                    try:
                        transformed[field_name] = uuid.UUID(transformed[field_name])
                    except ValueError:
                        pass  # Keep as string if invalid
            elif field_type is uuid.UUID and isinstance(transformed[field_name], str):
                try:
                    transformed[field_name] = uuid.UUID(transformed[field_name])
                except ValueError:
                    pass  # Keep as string if invalid
            # Handle List[UUID] fields
            elif hasattr(field_type, '__origin__'):
                origin = getattr(field_type, '__origin__', None)
                if origin is list:
                    args = getattr(field_type, '__args__', ())
                    if args and args[0] is uuid.UUID and isinstance(transformed[field_name], list):
                        # Convert list of UUID strings to UUID objects
                        try:
                            transformed[field_name] = [
                                uuid.UUID(item) if isinstance(item, str) else item 
                                for item in transformed[field_name]
                            ]
                        except ValueError:
                            pass  # Keep as is if conversion fails
    
    # Set is_active to True by default if not present
    if "is_active" not in transformed and "is_active" in model_class.__annotations__:
        transformed["is_active"] = True
        
    # Apply any additional default values
    for key, value in defaults.items():
        if key not in transformed:
            transformed[key] = value
            
    return model_class(**transformed)

def model_to_mongo_doc(model: BaseModel, exclude_none: bool = True) -> Dict[str, Any]:
    """
    Convert a Pydantic model to a MongoDB document format.
    
    Args:
        model: The Pydantic model instance
        exclude_none: Whether to exclude None values from the document
        
    Returns:
        A dictionary suitable for MongoDB storage
    """
    # Get the model data as dict, using aliases (so id becomes _id)
    doc = model.model_dump(by_alias=True, exclude_none=exclude_none)
    
    # Ensure _id is properly formatted as string for MongoDB storage
    if "_id" in doc:
        # Convert UUID to string for MongoDB storage
        if isinstance(doc["_id"], uuid.UUID):
            doc["_id"] = str(doc["_id"])
    
    # Also ensure other UUID fields are converted to strings
    for key, value in doc.items():
        if isinstance(value, uuid.UUID):
            doc[key] = str(value)
        elif isinstance(value, list):
            # Handle lists that might contain UUIDs
            doc[key] = [str(item) if isinstance(item, uuid.UUID) else item for item in value]
        elif isinstance(value, dict):
            # Handle nested dictionaries
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, uuid.UUID):
                    value[nested_key] = str(nested_value)
    
    return doc
