"""
Authentication Dependencies

FastAPI dependencies for authentication and authorization.
Provides current user extraction, RBAC, and plan-based access control.
"""

from typing import Callable

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.database.models.user import PlanType, UserModel, UserRole
from app.core.database.mongo import get_database
from app.modules.auth.service import AuthService


# -----------------------------------------------------------------------------
# Token Extraction
# -----------------------------------------------------------------------------

async def get_token_from_header(
    authorization: str = Header(None, description="Bearer token")
) -> str:
    """
    Extract JWT token from Authorization header.
    
    Args:
        authorization: Authorization header value
    
    Returns:
        str: JWT token
    
    Raises:
        HTTPException: If authorization header is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return parts[1]


# -----------------------------------------------------------------------------
# Current User Dependencies
# -----------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(get_token_from_header),
    db=Depends(get_database)
) -> UserModel:
    """
    Get current authenticated user from JWT token.
    
    This is the main dependency for protected routes.
    
    Args:
        token: JWT access token
        db: Database instance
    
    Returns:
        UserModel: Current authenticated user
    
    Raises:
        HTTPException: If token is invalid or user not found
    
    Usage:
        ```python
        @router.get("/profile")
        async def get_profile(current_user: UserModel = Depends(get_current_user)):
            return current_user
        ```
    """
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.get_user_from_token(token)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    Get current active user (not deleted or inactive).
    
    Args:
        current_user: Current user from token
    
    Returns:
        UserModel: Active user
    
    Raises:
        HTTPException: If user is inactive or deleted
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    if current_user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deleted",
        )
    
    return current_user


# -----------------------------------------------------------------------------
# Role-Based Access Control (RBAC)
# -----------------------------------------------------------------------------

def require_role(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory for role-based access control.
    
    Args:
        *allowed_roles: Allowed user roles
    
    Returns:
        Dependency function
    
    Usage:
        ```python
        @router.post("/admin/settings")
        async def update_settings(
            current_user: UserModel = Depends(require_role(UserRole.INSTITUTE))
        ):
            # Only institute users can access
            pass
        ```
    """
    async def role_checker(
        current_user: UserModel = Depends(get_current_active_user)
    ) -> UserModel:
        """Check if user has required role."""
        if current_user.role not in allowed_roles:
            allowed_role_names = [role.value for role in allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_role_names)}",
            )
        return current_user
    
    return role_checker


# Convenience role dependencies
require_student = require_role(UserRole.STUDENT)
require_parent = require_role(UserRole.PARENT)
require_institute = require_role(UserRole.INSTITUTE)
require_student_or_parent = require_role(UserRole.STUDENT, UserRole.PARENT)


# -----------------------------------------------------------------------------
# Plan-Based Access Control
# -----------------------------------------------------------------------------

def require_plan(*allowed_plans: PlanType) -> Callable:
    """
    Dependency factory for plan-based access control.
    
    Args:
        *allowed_plans: Allowed subscription plans
    
    Returns:
        Dependency function
    
    Usage:
        ```python
        @router.get("/ai/suggestions")
        async def get_ai_suggestions(
            current_user: UserModel = Depends(
                require_plan(PlanType.PRO, PlanType.SMART_PACK)
            )
        ):
            # Only Pro and Smart Pack users can access
            pass
        ```
    """
    async def plan_checker(
        current_user: UserModel = Depends(get_current_active_user)
    ) -> UserModel:
        """Check if user has required plan."""
        if current_user.plan_type not in allowed_plans:
            allowed_plan_names = [plan.value for plan in allowed_plans]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required plan(s): {', '.join(allowed_plan_names)}. "
                       f"Please upgrade your subscription.",
            )
        return current_user
    
    return plan_checker


# Convenience plan dependencies
require_pro_plan = require_plan(PlanType.PRO, PlanType.SMART_PACK)
require_smart_pack = require_plan(PlanType.SMART_PACK)


# -----------------------------------------------------------------------------
# Device Information Extractor
# -----------------------------------------------------------------------------

async def get_device_info(request: Request) -> dict:
    """
    Extract device information from request.
    
    Args:
        request: FastAPI request object
    
    Returns:
        dict: Device information
    """
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "device_id": request.headers.get("x-device-id"),  # Optional custom header
    }
