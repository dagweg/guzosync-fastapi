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
        jwt_secret = os.getenv("JWT_SECRET")
        if jwt_secret is None:
            raise ValueError("JWT_SECRET environment variable is not set")
        encoded_jwt = jwt.encode(to_encode, jwt_secret, algorithm="HS256")
        logger.info("Access token created successfully")
        return encoded_jwt
    except Exception as e:
        logger.error("Failed to create access token", exc_info=True)
        raise