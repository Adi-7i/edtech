"""
Authentication Schemas

Pydantic models for request/response validation in auth endpoints.
"""

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.database.models.user import PlanType, UserRole


# -----------------------------------------------------------------------------
# Password Validators
# -----------------------------------------------------------------------------

def validate_password_strength(password: str) -> str:
    """
    Validate password meets security requirements.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password: Password to validate
    
    Returns:
        str: Validated password
    
    Raises:
        ValueError: If password doesn't meet requirements
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least one special character")
    
    return password


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """User registration request."""
    
    email: EmailStr = Field(
        ...,
        description="User email address"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (will be hashed)"
    )
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="User first name"
    )
    last_name: Optional[str] = Field(
        default=None,
        max_length=50,
        description="User last name"
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=15,
        description="Phone number with country code"
    )
    role: UserRole = Field(
        default=UserRole.STUDENT,
        description="User role (student/parent/institute)"
    )
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate name fields."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "student@example.com",
                "password": "SecurePass123!",
                "first_name": "Rahul",
                "last_name": "Sharma",
                "phone": "+919876543210",
                "role": "student"
            }
        }


class LoginRequest(BaseModel):
    """User login request."""
    
    email: EmailStr = Field(
        ...,
        description="User email address"
    )
    password: str = Field(
        ...,
        description="User password"
    )
    device_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Device name for session tracking"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "student@example.com",
                "password": "SecurePass123!",
                "device_name": "Chrome on Windows"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""
    
    refresh_token: str = Field(
        ...,
        description="Refresh token"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
            }
        }


# -----------------------------------------------------------------------------
# Response Schemas
# -----------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """Authentication token response."""
    
    access_token: str = Field(
        ...,
        description="JWT access token (short-lived)"
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token (long-lived)"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiry in seconds"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class UserResponse(BaseModel):
    """Public user data response."""
    
    id: str = Field(
        ...,
        description="User ID"
    )
    email: str = Field(
        ...,
        description="User email"
    )
    first_name: str = Field(
        ...,
        description="User first name"
    )
    last_name: Optional[str] = Field(
        default=None,
        description="User last name"
    )
    phone: Optional[str] = Field(
        default=None,
        description="Phone number"
    )
    role: str = Field(
        ...,
        description="User role"
    )
    plan_type: str = Field(
        ...,
        description="Subscription plan"
    )
    is_active: bool = Field(
        ...,
        description="Whether user is active"
    )
    is_deleted: bool = Field(
        ...,
        description="Whether user is deleted"
    )
    created_at: str = Field(
        ...,
        description="Account creation timestamp"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "student@example.com",
                "first_name": "Rahul",
                "last_name": "Sharma",
                "phone": "+919876543210",
                "role": "student",
                "plan_type": "free",
                "is_active": True,
                "is_deleted": False,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }


class LoginResponse(BaseModel):
    """Login response with user data and tokens."""
    
    user: UserResponse = Field(
        ...,
        description="User data"
    )
    tokens: TokenResponse = Field(
        ...,
        description="Authentication tokens"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "507f1f77bcf86cd799439011",
                    "email": "student@example.com",
                    "first_name": "Rahul",
                    "role": "student",
                    "plan_type": "free"
                },
                "tokens": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
                    "token_type": "bearer",
                    "expires_in": 1800
                }
            }
        }
