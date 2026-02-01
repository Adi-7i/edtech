"""
Authentication Models

MongoDB models for authentication-related data:
- Refresh tokens with device tracking
- Session management
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from app.core.database.models.base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Refresh Token Model
# -----------------------------------------------------------------------------

class RefreshTokenModel(MongoBaseModel):
    """
    Refresh token storage for session management.
    
    Collection: refresh_tokens
    
    Supports:
    - Multiple device login
    - Token revocation
    - Device tracking
    
    Indexes:
    - user_id
    - token (unique)
    - (user_id, device_id) compound
    - expires_at (TTL index for auto-deletion)
    """
    
    # User reference
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    
    # Token data
    token: str = Field(
        ...,
        min_length=32,
        max_length=512,
        description="Hashed refresh token"
    )
    
    # Device information
    device_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Unique device identifier"
    )
    device_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Device name (e.g., 'Chrome on Windows')"
    )
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="IP address when token was created"
    )
    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Browser user agent string"
    )
    
    # Token lifecycle
    expires_at: datetime = Field(
        ...,
        description="Token expiration timestamp"
    )
    is_revoked: bool = Field(
        default=False,
        description="Whether token has been revoked"
    )
    revoked_at: Optional[datetime] = Field(
        default=None,
        description="When token was revoked"
    )
    
    # Activity tracking
    last_used_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last time token was used"
    )
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "token": "<hashed_token>",
                "device_name": "Chrome on Windows",
                "ip_address": "192.168.1.1",
                "expires_at": "2024-01-15T00:00:00Z",
                "is_revoked": False,
            }
        }
