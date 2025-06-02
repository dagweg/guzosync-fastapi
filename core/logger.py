import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import json
import datetime
from typing import Dict, Any, Optional
import uuid

class HumanReadableFormatter(logging.Formatter):
    """A formatter that produces clean, readable console output with colors."""
    COLORS = {
        'DEBUG': '\033[37m',    # White
        'INFO': '\033[36m',     # Cyan
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m', # Red background
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        # Format timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Colorize levelname
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET if color else ''
        level_display = f"{color}{record.levelname[:4]}{reset}"
        
        # Format the main message
        log_line = f"{timestamp} | {level_display} | {record.name} | {record.getMessage()}"
        
        # Get relevant extra attributes (filter out internal ones)
        extra_attrs = {
            k: v for k, v in record.__dict__.items()
            if k not in [
                'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'exc_info', 'exc_text', 'stack_info', 'lineno',
                'funcName', 'created', 'msecs', 'relativeCreated', 'thread',
                'threadName', 'processName', 'process', 'taskName'
            ]
            and not k.startswith('_')
        }
        
        # Add extras if present
        if extra_attrs:
            extras = " ".join(f"{k}={v}" for k, v in extra_attrs.items())
            log_line += f" | {extras}"
        
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
        
        # Add all extra attributes (including context if present)
        extra_attrs = {k: v for k, v in record.__dict__.items() 
                    if k not in ('message', 'asctime', 'levelname', 'name', 
                                'exc_info', 'exc_text', 'stack_info') 
                    and not k.startswith('_')}
        
        # Convert non-JSON serializable objects to strings
        for key, value in extra_attrs.items():
            if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                extra_attrs[key] = str(value)
        
        log_data.update(extra_attrs)
                
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