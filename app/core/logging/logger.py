"""
Smart Study Planner - Structured Logging Configuration

Provides structured JSON logging for production environments
and human-readable logging for development.

Features:
- Environment-based log levels
- JSON formatting for production
- Request ID tracking
- Performance logging
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

from app.core.config.settings import get_settings


# -----------------------------------------------------------------------------
# Custom JSON Formatter
# -----------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """
    Custom JSON log formatter for structured logging.
    
    Outputs logs in JSON format for easy parsing by log aggregation tools.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        # Add file and line info for debugging
        if record.levelno >= logging.WARNING:
            log_data["file"] = record.pathname
            log_data["line"] = record.lineno
            log_data["function"] = record.funcName
        
        return json.dumps(log_data)


# -----------------------------------------------------------------------------
# Logger Setup
# -----------------------------------------------------------------------------

def setup_logging() -> None:
    """
    Configure application logging.
    
    Sets up logging based on environment configuration.
    Uses JSON format for production, text format for development.
    
    Call this during application startup.
    """
    settings = get_settings()
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    
    # Set formatter based on environment
    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Optional: Add file handler if LOG_FILE is specified
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(settings.LOG_LEVEL)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info(
        f"Logging configured: level={settings.LOG_LEVEL}, format={settings.LOG_FORMAT}"
    )


# -----------------------------------------------------------------------------
# Logger Helper Functions
# -----------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__ of the module)
    
    Returns:
        logging.Logger: Logger instance
    
    Example:
        ```python
        logger = get_logger(__name__)
        logger.info("User logged in", extra={"user_id": "123"})
        ```
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter for adding context to all log messages.
    
    Example:
        ```python
        logger = get_logger(__name__)
        request_logger = LoggerAdapter(logger, {"request_id": "abc-123"})
        request_logger.info("Processing request")
        # Output includes request_id in all logs
        ```
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add extra context to log messages."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs
