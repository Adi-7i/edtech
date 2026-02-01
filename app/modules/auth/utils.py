"""
Authentication Security Utilities

Provides:
- Password hashing and verification (bcrypt)
- JWT token creation and validation
- Token payload handling
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config.settings import get_settings

settings = get_settings()


# -----------------------------------------------------------------------------
# Password Hashing
# -----------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Pre-hashes password with SHA256 to avoid bcrypt's 72-byte limit.
    This is a security best practice for long passwords.
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
    """
    # Pre-hash with SHA256 to avoid bcrypt's 72-byte limit
    password_bytes = password.encode('utf-8')
    sha_hash = hashlib.sha256(password_bytes).hexdigest()
    
    # Hash with bcrypt (12 rounds)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(sha_hash.encode('utf-8'), salt)
    
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
    
    Returns:
        bool: True if password matches, False otherwise
    """
    # Pre-hash with SHA256 (same as during hashing)
    password_bytes = plain_password.encode('utf-8')
    sha_hash = hashlib.sha256(password_bytes).hexdigest()
    
    return bcrypt.checkpw(sha_hash.encode('utf-8'), hashed_password.encode('utf-8'))


# -----------------------------------------------------------------------------
# JWT Token Creation
# -----------------------------------------------------------------------------

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Payload data to encode in token
        expires_delta: Optional custom expiration time
    
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    # Set expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token.
    
    Args:
        data: Payload data to encode in token
        expires_delta: Optional custom expiration time
    
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    # Set expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


# -----------------------------------------------------------------------------
# JWT Token Validation
# -----------------------------------------------------------------------------

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token to decode
    
    Returns:
        Dict: Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
        
    except JWTError:
        return None


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
    """
    Verify token type matches expected type.
    
    Args:
        payload: Decoded token payload
        expected_type: Expected token type ('access' or 'refresh')
    
    Returns:
        bool: True if type matches, False otherwise
    """
    return payload.get("type") == expected_type


# -----------------------------------------------------------------------------
# Token Payload Helpers
# -----------------------------------------------------------------------------

def create_token_payload(user_id: str, email: str, role: str) -> Dict[str, Any]:
    """
    Create minimal token payload.
    
    Security: Keep payload minimal to reduce token size and exposure.
    
    Args:
        user_id: User ID
        email: User email
        role: User role
    
    Returns:
        Dict: Token payload
    """
    return {
        "sub": user_id,  # Subject (user ID)
        "email": email,
        "role": role,
    }


def extract_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from token without full validation.
    
    Use this only for non-security-critical operations.
    
    Args:
        token: JWT token
    
    Returns:
        str: User ID if present, None otherwise
    """
    payload = decode_token(token)
    if payload:
        return payload.get("sub")
    return None
