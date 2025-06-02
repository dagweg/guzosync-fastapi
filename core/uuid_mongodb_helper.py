"""
UUID-MongoDB Helper Module

This module provides utilities to standardize UUID handling when working with MongoDB.
It ensures consistent storage and retrieval of UUID fields across the application.
"""

from typing import Dict, Any, List, Union
from uuid import UUID, uuid4
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

def prepare_uuid_query(query: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Prepare MongoDB query to handle both UUID and ObjectId formats.
    Returns a list of queries to try in order.
    
    Args:
        query: The original query dict
        
    Returns:
        List of query variations to try
    """
    queries = []
    
    # If querying by id, create multiple variations
    if "id" in query:
        uuid_val = query["id"]
        
        # Query 1: Use id field with UUID as string
        queries.append({**query, "id": str(uuid_val)})
        
        # Query 2: Use _id field with UUID as string
        query_with_id = query.copy()
        query_with_id.pop("id")
        queries.append({**query_with_id, "_id": str(uuid_val)})
        
        # Query 3: Use id field with UUID object (if supported)
        if isinstance(uuid_val, str):
            try:
                uuid_obj = UUID(uuid_val)
                queries.append({**query, "id": uuid_obj})
            except ValueError:
                pass
    else:
        # For other queries, just return as-is
        queries.append(query)
    
    return queries

async def find_one_by_uuid(collection, query: Dict[str, Any], **kwargs):
    """
    Find a single document by trying multiple UUID query formats.
    
    Args:
        collection: MongoDB collection
        query: Query dict
        **kwargs: Additional arguments for find_one
        
    Returns:
        Document if found, None otherwise
    """
    queries = prepare_uuid_query(query)
    
    for q in queries:
        try:
            result = await collection.find_one(q, **kwargs)
            if result:
                logger.debug(f"Found document with query: {q}")
                return result
        except Exception as e:
            logger.debug(f"Query failed: {q}, error: {str(e)}")
            continue
    
    logger.debug(f"No document found for any query variation of: {query}")
    return None

async def find_by_uuid(collection, query: Dict[str, Any], **kwargs):
    """
    Find documents by trying multiple UUID query formats.
    
    Args:
        collection: MongoDB collection
        query: Query dict
        **kwargs: Additional arguments for find
        
    Returns:
        Cursor or list of documents
    """
    queries = prepare_uuid_query(query)
    
    for q in queries:
        try:
            cursor = collection.find(q, **kwargs)
            # Check if any results exist
            first_doc = await cursor.to_list(length=1)
            if first_doc:
                logger.debug(f"Found documents with query: {q}")
                # Return a new cursor for the successful query
                return collection.find(q, **kwargs)
        except Exception as e:
            logger.debug(f"Query failed: {q}, error: {str(e)}")
            continue
    
    logger.debug(f"No documents found for any query variation of: {query}")
    # Return empty cursor
    return collection.find({"_id": ObjectId("000000000000000000000000")})  # Non-existent ID

async def update_one_by_uuid(collection, query: Dict[str, Any], update: Dict[str, Any], **kwargs):
    """
    Update a single document by trying multiple UUID query formats.
    
    Args:
        collection: MongoDB collection
        query: Query dict for finding the document
        update: Update operations
        **kwargs: Additional arguments for update_one
        
    Returns:
        UpdateResult
    """
    queries = prepare_uuid_query(query)
    
    for q in queries:
        try:
            result = await collection.update_one(q, update, **kwargs)
            if result.matched_count > 0:
                logger.debug(f"Updated document with query: {q}")
                return result
        except Exception as e:
            logger.debug(f"Update failed: {q}, error: {str(e)}")
            continue
    
    logger.debug(f"No document updated for any query variation of: {query}")
    # Return a result with no matches
    from pymongo.results import UpdateResult
    return UpdateResult(raw_result={"n": 0, "nModified": 0, "ok": 1}, acknowledged=True)

async def delete_one_by_uuid(collection, query: Dict[str, Any], **kwargs):
    """
    Delete a single document by trying multiple UUID query formats.
    
    Args:
        collection: MongoDB collection
        query: Query dict for finding the document
        **kwargs: Additional arguments for delete_one
        
    Returns:
        DeleteResult
    """
    queries = prepare_uuid_query(query)
    
    for q in queries:
        try:
            result = await collection.delete_one(q, **kwargs)
            if result.deleted_count > 0:
                logger.debug(f"Deleted document with query: {q}")
                return result
        except Exception as e:
            logger.debug(f"Delete failed: {q}, error: {str(e)}")
            continue
    
    logger.debug(f"No document deleted for any query variation of: {query}")
    # Return a result with no deletions
    from pymongo.results import DeleteResult
    return DeleteResult(raw_result={"n": 0, "ok": 1}, acknowledged=True)

def standardize_uuid_fields(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardize UUID fields in a document for consistent storage.
    Converts all UUID objects to strings.
    
    Args:
        doc: Document to standardize
        
    Returns:
        Standardized document
    """
    if not doc:
        return doc
    
    result = {}
    
    for key, value in doc.items():
        if isinstance(value, UUID):
            result[key] = str(value)
        elif isinstance(value, list):
            result[key] = [str(item) if isinstance(item, UUID) else item for item in value]
        elif isinstance(value, dict):
            result[key] = standardize_uuid_fields(value)
        else:
            result[key] = value
    
    return result

__all__ = [
    'prepare_uuid_query',
    'find_one_by_uuid',
    'find_by_uuid', 
    'update_one_by_uuid',
    'delete_one_by_uuid',
    'standardize_uuid_fields'
]
