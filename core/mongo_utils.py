from typing import Dict, Any, TypeVar, Type
from pydantic import BaseModel
from bson import ObjectId

__all__ = ['transform_mongo_doc', 'model_to_mongo_doc']

ModelType = TypeVar("ModelType", bound=BaseModel)

def transform_mongo_doc(doc: Dict[str, Any], model_class: Type[ModelType], **defaults) -> ModelType:
    """
    Transform a MongoDB document into a Pydantic model, handling common field conversions
    and applying default values. Uses UUID strings as primary keys.

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

    # Handle legacy documents that might have _id instead of id
    if "_id" in transformed and "id" not in transformed:
        _id_value = transformed.pop("_id")
        # Convert ObjectId to string if necessary (for legacy compatibility)
        if isinstance(_id_value, ObjectId):
            transformed["id"] = str(_id_value)
        else:
            transformed["id"] = _id_value
    elif "_id" in transformed and "id" in transformed:
        # Remove _id if both exist, prefer id
        transformed.pop("_id")

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
    Convert a Pydantic model to a MongoDB document format. Uses UUID strings as primary keys.
    No longer uses MongoDB's _id field - uses 'id' field with UUID strings instead.

    Args:
        model: The Pydantic model instance
        exclude_none: Whether to exclude None values from the document

    Returns:
        A dictionary suitable for MongoDB storage with UUID string as 'id'
    """
    # Get the model data as dict using JSON mode to properly serialize dates, enums, etc.
    doc = model.model_dump(exclude_none=exclude_none, mode='json')

    # Ensure id is a string (convert UUID objects to strings if needed)
    if "id" in doc and doc["id"] is not None:
        doc["id"] = str(doc["id"])

    # Add _id field set to the same value as id for MongoDB indexing compatibility
    # This allows MongoDB to use id as the primary key while maintaining compatibility
    if "id" in doc:
        doc["_id"] = doc["id"]

    return doc