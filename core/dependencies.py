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

    
    try:
        user = await request.app.state.mongodb.users.find_one({"id": user_id})
        logger.debug("Found user by id field")
    except Exception as e:
        logger.debug(f"Query by id field failed: {e}")
    
    if user is None:
        logger.warning("User not found in database", extra={"user_id": user_id})
        raise credentials_exception
    
    # Use transform_mongo_doc to properly convert the document
    from core.mongo_utils import transform_mongo_doc
    return transform_mongo_doc(user, User)

async def get_current_user_websocket(token: str, app_state):
    """Get current user for WebSocket connections using token"""
    try:
        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            logger.error("JWT_SECRET not configured")
            return None
        
        # Decode the JWT token
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if not user_id:
            logger.error("Token payload missing user ID")
            return None
        
        # Convert string to ObjectId for MongoDB query
        try:
            user_object_id = ObjectId(user_id)
        except Exception:
            logger.error(f"Invalid user ID format: {user_id}")
            return None
        
        # Get user from database
        user_data = await app_state.mongodb.users.find_one({"_id": user_object_id})
        if not user_data:
            logger.error(f"User not found: {user_id}")
            return None
        
        # Convert to User model
        user = User(**{k: v for k, v in user_data.items() if k != "_id"})
        logger.debug(f"WebSocket authentication successful for user: {user.email}")
        return user
        
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None