from typing import Dict, Any, TypeVar, Type
from pydantic import BaseModel

__all__ = ['transform_mongo_doc', 'model_to_mongo_doc']

ModelType = TypeVar("ModelType", bound=BaseModel)

def transform_mongo_doc(doc: Dict[str, Any], model_class: Type[ModelType], **defaults) -> ModelType:
    """
    Transform a MongoDB document into a Pydantic model, handling common field conversions
    and applying default values. Assumes _id is stored as a string in MongoDB.

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
        transformed["id"] = transformed.pop("_id")  # Keep as string, no UUID conversion

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
    Convert a Pydantic model to a MongoDB document format. Ensures all UUIDs are strings.

    Args:
        model: The Pydantic model instance
        exclude_none: Whether to exclude None values from the document

    Returns:
        A dictionary suitable for MongoDB storage
    """
    # Get the model data as dict, using aliases (so id becomes _id)
    doc = model.model_dump(by_alias=True, exclude_none=exclude_none)

    # Ensure _id is set from id and is a string
    if "id" in doc:
        doc["_id"] = doc["id"]  # Copy id to _id
        # Remove id to avoid duplication unless explicitly needed
        if "id" not in model.__fields__ or model.__fields__["id"].alias != "id":
            doc.pop("id", None)

    return doc