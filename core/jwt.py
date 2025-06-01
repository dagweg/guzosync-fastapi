from datetime import datetime, timedelta
import os
import jwt  

# Import centralized logger
from core.logger import get_logger

logger = get_logger(__name__)

# Helper functions for JWT
def create_access_token(data: dict):
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=30)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, os.getenv("JWT_SECRET"), algorithm="HS256")
        logger.info("Access token created successfully")
        return encoded_jwt
    except Exception as e:
        logger.error("Failed to create access token", exc_info=True)
        raise