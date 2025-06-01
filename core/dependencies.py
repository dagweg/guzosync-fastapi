from fastapi import Depends, HTTPException, status, Request
import os
import jwt   # or keep as just `import jwt` after uninstalling the wrong package
from uuid import UUID

# Import centralized logger
from core.logger import get_logger
from core.security import security

from models import User

logger = get_logger(__name__)

async def get_current_user(request: Request, token = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    tokenBytes = token.credentials.split(" ")[1].encode("utf-8")
    try:
        jwt_secret = os.getenv("JWT_SECRET")
        if jwt_secret is None:
            logger.error("JWT_SECRET environment variable is not set")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT secret not configured",
            )
        payload = jwt.decode(tokenBytes, jwt_secret.encode("utf-8"), algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning("Token payload missing user ID")
            raise credentials_exception
        logger.info("Token decoded successfully", extra={"user_id": user_id})
    except jwt.PyJWTError as e:
        logger.warning("JWT validation failed", exc_info=True)
        raise credentials_exception
    
    user = await request.app.state.mongodb.users.find_one({"id": UUID(user_id)})
    if user is None:
        logger.warning("User not found in database", extra={"user_id": user_id})
        raise credentials_exception
    return User(**user)