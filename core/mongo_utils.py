from typing import Dict, Any, TypeVar, Type
from pydantic import BaseModel
from uuid import UUID

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
        transformed["id"] = str(transformed.pop("_id"))
    
    # Set is_active to True by default if not present
    if "is_active" not in transformed and "is_active" in model_class.__annotations__:
        transformed["is_active"] = True
        
    # Apply any additional default values
    for key, value in defaults.items():
        if key not in transformed:
            transformed[key] = value
            
    return model_class(**transformed)
