from fastapi import Depends, HTTPException, status, Request
import os
import jwt   # or keep as just `import jwt` after uninstalling the wrong package
from uuid import UUID

# Import centralized logger
from core.logger import get_logger
from core.security import security
from bson import ObjectId

from models import User

logger = get_logger(__name__)

async def get_current_user(request: Request, token = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        jwt_secret = os.getenv("JWT_SECRET")
        if jwt_secret is None:
            logger.error("JWT_SECRET environment variable is not set")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT secret not configured",
            )
        payload = jwt.decode(token.credentials, jwt_secret, algorithms=["HS256"])
        user_id = payload.get("sub")
        logger.info('User ID extracted from token', extra={"user_id": user_id})
        if user_id is None:
            logger.warning("Token payload missing user ID")
            raise credentials_exception
        logger.info("Token decoded successfully", extra={"payload": payload})
    except jwt.PyJWTError as e:
        logger.warning("JWT validation failed", exc_info=True)
        raise credentials_exception    # Try to find user by different ID formats
    user = None
    logger.info("Fetching user from database", extra={"user_id": user_id})

    # First try to find by id field (UUID as string)
    try:
        user = await request.app.state.mongodb.users.find_one({"id": user_id})
        logger.debug("Found user by id field")
    except Exception as e:
        logger.debug(f"Query by id field failed: {e}")
    
    # If not found, try by _id field with UUID string
    if user is None:
        try:
            user = await request.app.state.mongodb.users.find_one({"_id": user_id})
            logger.debug("Found user by _id field")
        except Exception as e:
            logger.debug(f"Query by _id field failed: {e}")
    
    # If still not found, try by _id field as ObjectId (for backwards compatibility)
    if user is None:
        try:
            user = await request.app.state.mongodb.users.find_one({"_id": ObjectId(user_id)})
            logger.debug("Found user by _id field as ObjectId")
        except Exception as e:
            logger.debug(f"Query by _id ObjectId failed: {e}")
    
    if user is None:
        logger.warning("User not found in database", extra={"user_id": user_id})
        raise credentials_exception
    
    # Use transform_mongo_doc to properly convert the document
    from core.mongo_utils import transform_mongo_doc
    return transform_mongo_doc(user, User)