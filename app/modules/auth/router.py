"""
Authentication Router

API endpoints for authentication and authorization.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request, status

from app.core.database.models.user import UserModel
from app.core.database.mongo import get_database
from app.core.responses.base import success_response
from app.modules.auth.dependencies import get_current_active_user, get_device_info
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService
from app.shared.constants import ResponseMessage

# Create router
router = APIRouter()


# -----------------------------------------------------------------------------
# Public Endpoints (No Authentication Required)
# -----------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Create a new user account with email and password",
)
async def register(
    request: RegisterRequest,
    db=Depends(get_database)
):
    """
    Register a new user.
    
    Requirements:
    - Unique email address
    - Strong password (8+ chars, uppercase, lowercase, digit, special char)
    - First name required
    
    Default values:
    - Role: student (unless specified)
    - Plan: free
    - Active: true
    
    Returns:
        User data (without password)
    """
    auth_service = AuthService(db)
    user = await auth_service.register_user(request)
    
    return success_response(
        data=user.model_dump(),
        message="User registered successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.post(
    "/login",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user and receive access + refresh tokens",
)
async def login(
    request: LoginRequest,
    req: Request,
    device_info: dict = Depends(get_device_info),
    db=Depends(get_database)
):
    """
    Authenticate user and generate tokens.
    
    Returns:
    - User data
    - Access token (30 min expiry)
    - Refresh token (7 days expiry)
    
    The access token should be used for API requests.
    The refresh token is used to get a new access token when it expires.
    """
    auth_service = AuthService(db)
    response = await auth_service.login_user(request, device_info)
    
    return success_response(
        data=response.model_dump(),
        message="Login successful",
        status_code=status.HTTP_200_OK
    )


@router.post(
    "/refresh",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Get a new access token using refresh token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db=Depends(get_database)
):
    """
    Refresh access token.
    
    When the access token expires, use the refresh token to get a new one.
    The refresh token remains valid and can be reused until it expires.
    """
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_access_token(request)
    
    return success_response(
        data=tokens.model_dump(),
        message="Token refreshed successfully",
        status_code=status.HTTP_200_OK
    )


# -----------------------------------------------------------------------------
# Protected Endpoints (Authentication Required)
# -----------------------------------------------------------------------------

@router.post(
    "/logout",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Logout user by revoking refresh token",
)
async def logout(
    request: RefreshTokenRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db=Depends(get_database)
):
    """
    Logout user from current device.
    
    This revokes the refresh token, preventing it from being used again.
    Access tokens remain valid until they expire (can't be revoked server-side).
    
    For immediate logout effect, client should discard the access token.
    """
    auth_service = AuthService(db)
    await auth_service.logout_user(request.refresh_token)
    
    return success_response(
        data={"logout": True},
        message="Logout successful",
        status_code=status.HTTP_200_OK
    )


@router.post(
    "/logout/all",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Logout All Devices",
    description="Logout user from all devices",
)
async def logout_all_devices(
    current_user: UserModel = Depends(get_current_active_user),
    db=Depends(get_database)
):
    """
    Logout user from all devices.
    
    Revokes all refresh tokens for the current user.
    Useful for security when password is changed or account is compromised.
    """
    auth_service = AuthService(db)
    revoked_count = await auth_service.logout_all_devices(str(current_user.id))
    
    return success_response(
        data={"devices_logged_out": revoked_count},
        message=f"Logged out from {revoked_count} device(s)",
        status_code=status.HTTP_200_OK
    )


@router.get(
    "/me",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Get current authenticated user profile",
)
async def get_current_user_profile(
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get current user profile.
    
    Returns the authenticated user's data based on the JWT token.
    This endpoint is useful for:
    - Verifying token validity
    - Getting updated user information
    - Client-side user state management
    """
    user_response = UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        role=current_user.role.value,
        plan_type=current_user.plan_type.value,
        is_active=current_user.is_active,
        is_deleted=current_user.is_deleted,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
    )
    
    return success_response(
        data=user_response.model_dump(),
        message="User profile retrieved successfully",
        status_code=status.HTTP_200_OK
    )
