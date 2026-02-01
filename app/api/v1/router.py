"""
Smart Study Planner - API v1 Router

Aggregates all v1 API routes and provides health check endpoint.
"""

from fastapi import APIRouter, Depends

from app.core.database.mongo import check_database_health
from app.core.responses.base import success_response
from app.shared.constants import ResponseMessage, StatusCode

# Create v1 router
router = APIRouter()


# -----------------------------------------------------------------------------
# Health Check Endpoint
# -----------------------------------------------------------------------------

@router.get(
    "/health",
    summary="Health Check",
    description="Check API and database health status",
    tags=["Health"],
)
async def health_check():
    """
    Health check endpoint.
    
    Returns API status and database connectivity status.
    Useful for monitoring and load balancers.
    
    Returns:
        dict: Health status information
    """
    # Check database health
    db_healthy = await check_database_health()
    
    health_data = {
        "api": "healthy",
        "database": "healthy" if db_healthy else "unhealthy",
        "version": "1.0.0",
    }
    
    # Return degraded status if database is down
    status_code = StatusCode.OK if db_healthy else StatusCode.SERVICE_UNAVAILABLE
    
    return success_response(
        data=health_data,
        message="Health check completed",
        status_code=status_code,
    )


# -----------------------------------------------------------------------------
# Future Module Routes (to be added)
# -----------------------------------------------------------------------------

# Auth routes
from app.modules.auth.router import router as auth_router

router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

# Example of how to include feature module routes:
#
# from app.api.v1.endpoints import users, study_plans
#
# router.include_router(
#     users.router,
#     prefix="/users",
#     tags=["Users"]
# )
#
# router.include_router(
#     study_plans.router,
#     prefix="/study-plans",
#     tags=["Study Plans"]
# )
