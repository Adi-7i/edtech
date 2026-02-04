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

# Study Profile routes
from app.modules.study_profile.router import router as profile_router

router.include_router(
    profile_router,
    prefix="/profile",
    tags=["Study Profile"]
)

# Planner routes
from app.modules.planner.router import router as planner_router

router.include_router(
    planner_router,
    prefix="/planner",
    tags=["Planner"]
)

# Task Execution routes
from app.modules.tasks.router import router as tasks_router

router.include_router(
    tasks_router,
    prefix="/tasks",
    tags=["Task Execution"]
)

# Revision routes
from app.modules.revision.router import router as revision_router

router.include_router(
    revision_router,
    prefix="/revision",
    tags=["Revision"]
)

# Analytics routes
from app.modules.analytics.router import router as analytics_router

router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["Analytics"]
)

# Notification routes
from app.modules.notifications.router import router as notifications_router

router.include_router(
    notifications_router,
    prefix="/notifications",
    tags=["Notifications"]
)

# Subscription routes
from app.modules.subscription.router import router as subscription_router

router.include_router(
    subscription_router,
    prefix="/subscription",
    tags=["Subscription"]
)

# AI Assistant routes
from app.modules.ai_assistant.router import router as ai_assistant_router

router.include_router(
    ai_assistant_router,
    prefix="/ai",
    tags=["AI Assistant"]
)

# Example of how to include feature module routes:
#
# from app.api.v1.endpoints import users, study_plans
#
# router.include_router(users.router, prefix="/users", tags=["Users"])
# router.include_router(study_plans.router, prefix="/study-plans", tags=["Study Plans"])
# )
