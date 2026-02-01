"""
Smart Study Planner - Dependency Injection & Security

Provides common dependencies for FastAPI routes.
Includes database access, authentication (placeholder), and other shared dependencies.
"""

from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.mongo import get_database


# -----------------------------------------------------------------------------
# Database Dependency
# -----------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    Database dependency for FastAPI routes.
    
    Provides async MongoDB database instance to route handlers.
    
    Usage:
        ```python
        @router.get("/users")
        async def get_users(db: AsyncIOMotorDatabase = Depends(get_db)):
            users = await db.users.find().to_list(100)
            return users
        ```
    
    Yields:
        AsyncIOMotorDatabase: MongoDB database instance
    """
    db = await get_database()
    try:
        yield db
    finally:
        # Cleanup if needed (connection pooling handles this)
        pass


# -----------------------------------------------------------------------------
# Authentication Dependencies (Placeholders for Future Implementation)
# -----------------------------------------------------------------------------

async def get_current_user(
    authorization: str = Header(None, description="Bearer token")
):
    """
    Get current authenticated user from JWT token.
    
    PLACEHOLDER: Implement actual JWT validation in future.
    
    Args:
        authorization: Authorization header with Bearer token
    
    Returns:
        dict: Current user data
    
    Raises:
        HTTPException: If token is invalid or missing
    """
    # TODO: Implement JWT token validation
    # For now, this is a placeholder that can be implemented later
    # when authentication module is built
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Placeholder: Extract and validate token
    # token = authorization.replace("Bearer ", "")
    # user = await verify_token(token)
    # return user
    
    # For now, return a mock user
    return {"id": "placeholder", "role": "student"}


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current active user (non-deleted, active subscription).
    
    PLACEHOLDER: Implement actual user status checks in future.
    
    Args:
        current_user: Current user from get_current_user
    
    Returns:
        dict: Current active user data
    
    Raises:
        HTTPException: If user is inactive or deleted
    """
    # TODO: Check if user is active, not deleted, etc.
    # For now, just pass through
    return current_user


async def require_role(required_role: str):
    """
    Dependency factory for role-based access control.
    
    PLACEHOLDER: Implement actual role checking in future.
    
    Usage:
        ```python
        @router.post("/admin/settings")
        async def update_settings(
            user: dict = Depends(require_role("admin"))
        ):
            # Only admins can access this
            pass
        ```
    
    Args:
        required_role: Required role for access
    
    Returns:
        Dependency function
    """
    async def role_checker(current_user: dict = Depends(get_current_active_user)):
        # TODO: Implement actual role checking
        # For now, just pass through
        user_role = current_user.get("role")
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}",
            )
        return current_user
    
    return role_checker


# -----------------------------------------------------------------------------
# Pagination Dependencies
# -----------------------------------------------------------------------------

async def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Common pagination parameters.
    
    Args:
        page: Page number (1-indexed)
        page_size: Items per page (default 20, max 100)
    
    Returns:
        dict: Pagination parameters with skip and limit
    
    Raises:
        HTTPException: If parameters are invalid
    """
    from app.shared.constants import MAX_PAGE_SIZE, MIN_PAGE_SIZE
    
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1",
        )
    
    if page_size < MIN_PAGE_SIZE or page_size > MAX_PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page size must be between {MIN_PAGE_SIZE} and {MAX_PAGE_SIZE}",
        )
    
    skip = (page - 1) * page_size
    
    return {
        "page": page,
        "page_size": page_size,
        "skip": skip,
        "limit": page_size,
    }


# -----------------------------------------------------------------------------
# Request ID Dependency (for logging/tracing)
# -----------------------------------------------------------------------------

def get_request_id(x_request_id: str = Header(None)) -> str:
    """
    Get or generate request ID for tracing.
    
    Args:
        x_request_id: Optional request ID from header
    
    Returns:
        str: Request ID
    """
    if x_request_id:
        return x_request_id
    
    # Generate new request ID if not provided
    import uuid
    return str(uuid.uuid4())
