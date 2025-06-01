import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import json
import datetime
from typing import Dict, Any, Optional
import uuid

class HumanReadableFormatter(logging.Formatter):
    """A formatter that produces more readable console output while keeping JSON for files."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Format the basic message
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        levelname = record.levelname
        name = record.name
        message = record.getMessage()
        
        # Base format
        log_line = f"{timestamp} | {levelname:8} | {name} | {message}"
        
        # Add context if present
        context = getattr(record, "context", None)
        if context:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            log_line += f" | {context_str}"
        
        # Add exception if present
        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"
            
        return log_line

class JSONFormatter(logging.Formatter):
    """Formatter for structured JSON logging (used in files)"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        context = getattr(record, "context", None)
        if context:
            log_data.update(context)
            
        return json.dumps(log_data)

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure centralized logging for the application."""
    
    # Create logs directory if it doesn't exist
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with human-readable format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(HumanReadableFormatter())
    logger.addHandler(console_handler)
    
    # File handler with JSON format if log file is specified
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    # Configure uvicorn logging to use our format
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)

def log_context(**kwargs):
    """Add context to a log record."""
    return {"context": kwargs}