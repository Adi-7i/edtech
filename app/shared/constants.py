"""
Smart Study Planner - Application-Wide Constants

This module contains all shared constants used across the application.
Keeps configuration values centralized and maintainable.
"""

from enum import Enum


# -----------------------------------------------------------------------------
# Application Metadata
# -----------------------------------------------------------------------------

APP_NAME = "Smart Study Planner"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "AI-powered study planning and revision system for competitive exam preparation"


# -----------------------------------------------------------------------------
# Environment Types
# -----------------------------------------------------------------------------

class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# -----------------------------------------------------------------------------
# API Configuration
# -----------------------------------------------------------------------------

API_V1_PREFIX = "/api/v1"
API_TITLE = f"{APP_NAME} API"
API_DOCS_URL = "/docs"
API_REDOC_URL = "/redoc"
API_OPENAPI_URL = "/openapi.json"


# -----------------------------------------------------------------------------
# HTTP Status Codes (Commonly Used)
# -----------------------------------------------------------------------------

class StatusCode:
    """HTTP status codes used in the application."""
    
    # Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    
    # Server Errors
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# -----------------------------------------------------------------------------
# Response Messages
# -----------------------------------------------------------------------------

class ResponseMessage:
    """Standard response messages."""
    
    # Success
    SUCCESS = "Operation completed successfully"
    CREATED = "Resource created successfully"
    UPDATED = "Resource updated successfully"
    DELETED = "Resource deleted successfully"
    
    # Errors
    NOT_FOUND = "Resource not found"
    UNAUTHORIZED = "Authentication required"
    FORBIDDEN = "Access denied"
    BAD_REQUEST = "Invalid request"
    INTERNAL_ERROR = "Internal server error"
    SERVICE_UNAVAILABLE = "Service temporarily unavailable"
    
    # Validation
    VALIDATION_ERROR = "Validation failed"
    INVALID_INPUT = "Invalid input provided"


# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------

# Collection Names (match those defined in models)
class Collections:
    """MongoDB collection names."""
    
    # User & Auth
    USERS = "users"
    STUDY_PROFILES = "study_profiles"
    
    # Academic
    EXAMS = "exams"
    SUBJECTS = "subjects"
    CHAPTERS = "chapters"
    USER_CHAPTER_STRENGTHS = "user_chapter_strengths"
    
    # Study Planning
    DAILY_PLANS = "daily_plans"
    TASK_EXECUTIONS = "task_executions"
    
    # Learning
    REVISIONS = "revisions"
    
    # Analytics
    DAILY_ANALYTICS = "daily_analytics"
    USER_PROGRESS_SUMMARIES = "user_progress_summaries"
    
    # Business
    SUBSCRIPTIONS = "subscriptions"
    PLAN_PRICING = "plan_pricing"
    
    # AI
    AI_USAGE_LOGS = "ai_usage_logs"
    AI_USAGE_SUMMARIES = "ai_usage_summaries"
    ETHICAL_REVIEWS = "ethical_reviews"
    
    # B2B
    INSTITUTES = "institutes"
    INSTITUTE_MEMBERSHIPS = "institute_memberships"
    INSTITUTE_INVITES = "institute_invites"


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------

class LogLevel:
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Default log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# -----------------------------------------------------------------------------
# Pagination
# -----------------------------------------------------------------------------

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1


# -----------------------------------------------------------------------------
# Rate Limiting (Future Use)
# -----------------------------------------------------------------------------

DEFAULT_RATE_LIMIT = "100/minute"
AUTH_RATE_LIMIT = "5/minute"


# -----------------------------------------------------------------------------
# CORS Configuration
# -----------------------------------------------------------------------------

ALLOWED_ORIGINS_DEV = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]


# -----------------------------------------------------------------------------
# Timezone
# -----------------------------------------------------------------------------

DEFAULT_TIMEZONE = "Asia/Kolkata"  # IST for India-focused app
