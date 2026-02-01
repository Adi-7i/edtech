"""
Authentication Service Layer

Business logic for authentication operations.
Coordinates between repository and utilities layers.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.user import PlanType, UserModel, UserRole
from app.core.exceptions.handlers import (
    BadRequestException,
    ConflictException,
    UnauthorizedException,
)
from app.modules.auth.models import RefreshTokenModel
from app.modules.auth.repository import RefreshTokenRepository, UserRepository
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.utils import (
    create_access_token,
    create_refresh_token,
    create_token_payload,
    decode_token,
    hash_password,
    verify_password,
    verify_token_type,
)


# -----------------------------------------------------------------------------
# Service Class
# -----------------------------------------------------------------------------

class AuthService:
    """Authentication service with business logic."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize auth service.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)
    
    # -------------------------------------------------------------------------
    # User Registration
    # -------------------------------------------------------------------------
    
    async def register_user(self, request: RegisterRequest) -> UserResponse:
        """
        Register a new user.
        
        Args:
            request: Registration request data
        
        Returns:
            UserResponse: Created user data
        
        Raises:
            ConflictException: If email already exists
        """
        # Check if email exists
        if await self.user_repo.email_exists(request.email):
            raise ConflictException(
                message=f"Email {request.email} is already registered"
            )
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create user model
        user = UserModel(
            email=request.email.lower(),
            password_hash=password_hash,
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            role=request.role,
            plan_type=PlanType.FREE,  # Default to free plan
            is_active=True,
            is_deleted=False,
        )
        
        # Save to database
        created_user = await self.user_repo.create_user(user)
        
        # Return public user data
        return self._user_to_response(created_user)
    
    # -------------------------------------------------------------------------
    # User Login
    # -------------------------------------------------------------------------
    
    async def login_user(
        self,
        request: LoginRequest,
        device_info: Optional[dict] = None
    ) -> LoginResponse:
        """
        Authenticate user and generate tokens.
        
        Args:
            request: Login request data
            device_info: Optional device information
        
        Returns:
            LoginResponse: User data and tokens
        
        Raises:
            UnauthorizedException: If credentials are invalid
        """
        # Find user by email
        user = await self.user_repo.find_by_email(request.email)
        if not user:
            raise UnauthorizedException(message="Invalid email or password")
        
        # Verify password
        if not verify_password(request.password, user.password_hash):
            raise UnauthorizedException(message="Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise UnauthorizedException(message="Account is inactive")
        
        if user.is_deleted:
            raise UnauthorizedException(message="Account has been deleted")
        
        # Update last login
        await self.user_repo.update_last_login(str(user.id))
        
        # Generate tokens
        tokens = await self._generate_tokens(user, request.device_name, device_info)
        
        # Return user data and tokens
        return LoginResponse(
            user=self._user_to_response(user),
            tokens=tokens
        )
    
    # -------------------------------------------------------------------------
    # Token Refresh
    # -------------------------------------------------------------------------
    
    async def refresh_access_token(
        self,
        request: RefreshTokenRequest
    ) -> TokenResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            request: Refresh token request
        
        Returns:
            TokenResponse: New access token
        
        Raises:
            UnauthorizedException: If refresh token is invalid
        """
        # Decode refresh token
        payload = decode_token(request.refresh_token)
        if not payload:
            raise UnauthorizedException(message="Invalid refresh token")
        
        # Verify token type
        if not verify_token_type(payload, "refresh"):
            raise UnauthorizedException(message="Invalid token type")
        
        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException(message="Invalid token payload")
        
        # Hash token for lookup (security: don't store raw tokens)
        token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
        
        # Find refresh token in database
        stored_token = await self.token_repo.find_by_token(token_hash)
        if not stored_token:
            raise UnauthorizedException(message="Refresh token not found")
        
        # Check if token is revoked
        if stored_token.is_revoked:
            raise UnauthorizedException(message="Refresh token has been revoked")
        
        # Check if token is expired
        # Ensure timezone awareness for comparison
        token_expires = stored_token.expires_at
        if token_expires.tzinfo is None:
            # Make timezone aware if it isnt
            token_expires = token_expires.replace(tzinfo=timezone.utc)
        
        if token_expires < datetime.now(timezone.utc):
            raise UnauthorizedException(message="Refresh token has expired")
        
        # Get user
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise UnauthorizedException(message="User not found")
        
        # Check user status
        if not user.is_active or user.is_deleted:
            raise UnauthorizedException(message="User account is not active")
        
        # Update last used timestamp
        await self.token_repo.update_last_used(str(stored_token.id))
        
        # Generate new access token (keep same refresh token)
        from app.core.config.settings import get_settings
        settings = get_settings()
        
        token_payload = create_token_payload(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value
        )
        
        access_token = create_access_token(token_payload)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,  # Return same refresh token
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    # -------------------------------------------------------------------------
    # User Logout
    # -------------------------------------------------------------------------
    
    async def logout_user(self, refresh_token: str) -> bool:
        """
        Logout user by revoking refresh token.
        
        Args:
            refresh_token: Refresh token to revoke
        
        Returns:
            bool: True if logout successful
        """
        # Hash token for lookup
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        # Find and revoke token
        stored_token = await self.token_repo.find_by_token(token_hash)
        if stored_token:
            return await self.token_repo.revoke_token(str(stored_token.id))
        
        return False
    
    async def logout_all_devices(self, user_id: str) -> int:
        """
        Logout user from all devices.
        
        Args:
            user_id: User ID
        
        Returns:
            int: Number of tokens revoked
        """
        return await self.token_repo.revoke_all_user_tokens(user_id)
    
    # -------------------------------------------------------------------------
    # Get Current User
    # -------------------------------------------------------------------------
    
    async def get_user_from_token(self, token: str) -> UserModel:
        """
        Get user from access token.
        
        Args:
            token: JWT access token
        
        Returns:
            UserModel: User object
        
        Raises:
            UnauthorizedException: If token is invalid
        """
        # Decode token
        payload = decode_token(token)
        if not payload:
            raise UnauthorizedException(message="Invalid token")
        
        # Verify token type
        if not verify_token_type(payload, "access"):
            raise UnauthorizedException(message="Invalid token type")
        
        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException(message="Invalid token payload")
        
        # Get user from database
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise UnauthorizedException(message="User not found")
        
        # Check user status
        if not user.is_active:
            raise UnauthorizedException(message="User account is inactive")
        
        if user.is_deleted:
            raise UnauthorizedException(message="User account has been deleted")
        
        return user
    
    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------
    
    async def _generate_tokens(
        self,
        user: UserModel,
        device_name: Optional[str] = None,
        device_info: Optional[dict] = None
    ) -> TokenResponse:
        """
        Generate access and refresh tokens for user.
        
        Args:
            user: User model
            device_name: Optional device name
            device_info: Optional device information
        
        Returns:
            TokenResponse: Generated tokens
        """
        from app.core.config.settings import get_settings
        settings = get_settings()
        
        # Create token payload
        token_payload = create_token_payload(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value
        )
        
        # Generate access token
        access_token = create_access_token(token_payload)
        
        # Generate refresh token
        refresh_token = create_refresh_token(token_payload)
        
        # Store refresh token in database
        # Hash token for security (don't store raw tokens)
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        refresh_token_model = RefreshTokenModel(
            user_id=user.id,
            token=token_hash,
            device_name=device_name,
            device_id=device_info.get("device_id") if device_info else None,
            ip_address=device_info.get("ip_address") if device_info else None,
            user_agent=device_info.get("user_agent") if device_info else None,
            expires_at=datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            ),
        )
        
        await self.token_repo.create_token(refresh_token_model)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def _user_to_response(self, user: UserModel) -> UserResponse:
        """
        Convert UserModel to UserResponse.
        
        Args:
            user: User model
        
        Returns:
            UserResponse: Public user data
        """
        return UserResponse(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            role=user.role.value,
            plan_type=user.plan_type.value,
            is_active=user.is_active,
            is_deleted=user.is_deleted,
            created_at=user.created_at.isoformat() if user.created_at else "",
        )
