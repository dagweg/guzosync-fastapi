from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from core.logger import get_logger
import time

logger = get_logger("action-logger")

class ActionLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        user = None
        try:
            # Try to get user info from request.state if set by dependencies
            user = getattr(request.state, 'user', None)
        except Exception:
            user = None
        try:
            response: Response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            log_data = {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time_ms": round(process_time, 2),
            }
            if user:
                log_data["user_id"] = getattr(user, 'id', None)
                log_data["user_email"] = getattr(user, 'email', None)
            logger.info(f"{request.method} {request.url.path} - {response.status_code} ({log_data['process_time_ms']}ms)", extra={"context": log_data})
            return response
        except Exception as exc:
            process_time = (time.time() - start_time) * 1000
            log_data = {
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "process_time_ms": round(process_time, 2),
                "exception": str(exc),
            }
            if user:
                log_data["user_id"] = getattr(user, 'id', None)
                log_data["user_email"] = getattr(user, 'email', None)
            logger.error(f"Exception in {request.method} {request.url.path}: {exc}", extra={"context": log_data}, exc_info=True)
            raise
