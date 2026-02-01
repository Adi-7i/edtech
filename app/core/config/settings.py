"""
Smart Study Planner - Application Settings

Centralized configuration management using Pydantic BaseSettings.
Supports environment-based configuration for dev/staging/production.

Environment variables are loaded from .env file or system environment.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.constants import Environment, ALLOWED_ORIGINS_DEV


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings have sensible defaults for development.
    Production deployments should override via environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # -----------------------------------------------------------------------------
    # Application Settings
    # -----------------------------------------------------------------------------
    
    APP_NAME: str = Field(
        default="Smart Study Planner API",
        description="Application name"
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version"
    )
    ENVIRONMENT: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment (development/staging/production)"
    )
    DEBUG: bool = Field(
        default=True,
        description="Enable debug mode"
    )
    
    # -----------------------------------------------------------------------------
    # Server Configuration
    # -----------------------------------------------------------------------------
    
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="Server port"
    )
    RELOAD: bool = Field(
        default=True,
        description="Enable auto-reload (dev only)"
    )
    
    # -----------------------------------------------------------------------------
    # MongoDB Configuration
    # -----------------------------------------------------------------------------
    
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URL"
    )
    MONGODB_DB_NAME: str = Field(
        default="smart_study_planner",
        description="MongoDB database name"
    )
    MONGODB_MIN_POOL_SIZE: int = Field(
        default=10,
        ge=1,
        description="Minimum connection pool size"
    )
    MONGODB_MAX_POOL_SIZE: int = Field(
        default=100,
        ge=10,
        description="Maximum connection pool size"
    )
    MONGODB_TIMEOUT_MS: int = Field(
        default=5000,
        ge=1000,
        description="MongoDB connection timeout in milliseconds"
    )
    
    # -----------------------------------------------------------------------------
    # CORS Configuration
    # -----------------------------------------------------------------------------
    
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True,
        description="Allow credentials in CORS"
    )
    CORS_ALLOW_METHODS: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP methods"
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP headers"
    )
    
    # -----------------------------------------------------------------------------
    # Security Configuration (Placeholders for Future)
    # -----------------------------------------------------------------------------
    
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT and other security features"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=1,
        description="Access token expiration in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        description="Refresh token expiration in days"
    )
    
    # -----------------------------------------------------------------------------
    # Logging Configuration
    # -----------------------------------------------------------------------------
    
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format (json/text)"
    )
    LOG_FILE: Optional[str] = Field(
        default=None,
        description="Log file path (None for stdout only)"
    )
    
    # -----------------------------------------------------------------------------
    # API Configuration
    # -----------------------------------------------------------------------------
    
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="API v1 route prefix"
    )
    DOCS_URL: str = Field(
        default="/docs",
        description="Swagger UI docs URL"
    )
    REDOC_URL: str = Field(
        default="/redoc",
        description="ReDoc URL"
    )
    OPENAPI_URL: str = Field(
        default="/openapi.json",
        description="OpenAPI schema URL"
    )
    
    # -----------------------------------------------------------------------------
    # Rate Limiting (Future Use)
    # -----------------------------------------------------------------------------
    
    RATE_LIMIT_ENABLED: bool = Field(
        default=False,
        description="Enable rate limiting"
    )
    
    # -----------------------------------------------------------------------------
    # Redis Configuration (Future Use)
    # -----------------------------------------------------------------------------
    
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL (for caching/sessions)"
    )
    
    # -----------------------------------------------------------------------------
    # Validators
    # -----------------------------------------------------------------------------
    
    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def validate_environment(cls, v: str) -> Environment:
        """Validate and convert environment string to enum."""
        if isinstance(v, Environment):
            return v
        return Environment(v.lower())
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()
    
    # -----------------------------------------------------------------------------
    # Helper Properties
    # -----------------------------------------------------------------------------
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == Environment.TESTING
    
    @property
    def mongodb_connection_params(self) -> dict:
        """Get MongoDB connection parameters."""
        return {
            "minPoolSize": self.MONGODB_MIN_POOL_SIZE,
            "maxPoolSize": self.MONGODB_MAX_POOL_SIZE,
            "serverSelectionTimeoutMS": self.MONGODB_TIMEOUT_MS,
        }


# -----------------------------------------------------------------------------
# Settings Singleton
# -----------------------------------------------------------------------------

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings singleton.
    
    Uses lru_cache to ensure only one Settings instance is created.
    This instance is shared across the application.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Convenience export
settings = get_settings()
