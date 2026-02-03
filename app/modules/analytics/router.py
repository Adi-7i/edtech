"""
Analytics Router

API endpoints for analytics and progress tracking.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.database.mongo import get_database
from app.core.exceptions import BadRequestException
from app.core.responses.base import SuccessResponse
from app.modules.analytics.schemas import (
    DailyAnalyticsResponse,
    OverviewAnalyticsResponse,
    WeeklyAnalyticsResponse,
)
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.dependencies import get_current_user
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_analytics_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> AnalyticsService:
    """Dependency injection for analytics service."""
    return AnalyticsService(db)


@router.get(
    "/daily",
    response_model=SuccessResponse[DailyAnalyticsResponse],
    summary="Get Daily Analytics",
    description="""
    Get analytics for a specific day.
    
    Returns:
    - Task summary (planned vs completed)
    - Study time metrics
    - Consistency status
    
    If no date is provided, returns analytics for today.
    """
)
async def get_daily_analytics(
    date_param: Optional[str] = Query(
        None,
        alias="date",
        description="Date in YYYY-MM-DD format (defaults to today)",
        example="2026-02-03"
    ),
    current_user: dict = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get daily analytics for the user.
    
    Query Parameters:
    - date: Optional date in YYYY-MM-DD format
    
    Returns:
    - DailyAnalyticsResponse with day's metrics
    """
    user_id = current_user["id"]
    
    # Parse date if provided
    if date_param:
        try:
            target_date = date.fromisoformat(date_param)
        except ValueError:
            raise BadRequestException(message="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = None  # Service will default to today
    
    analytics = await service.get_daily_analytics(user_id, target_date)
    
    return SuccessResponse(
        message="Daily analytics retrieved successfully",
        status_code=200,
        data=analytics
    )


@router.get(
    "/weekly",
    response_model=SuccessResponse[WeeklyAnalyticsResponse],
    summary="Get Weekly Analytics",
    description="""
    Get analytics for a 7-day week.
    
    Returns:
    - Daily summaries for each day
    - Weekly totals and averages
    - Consistency score for the week
    - Active study days count
    
    If no week_start is provided, returns current week (Monday-Sunday).
    """
)
async def get_weekly_analytics(
    week_start: Optional[str] = Query(
        None,
        description="Week start date in YYYY-MM-DD format (defaults to current week's Monday)",
        example="2026-02-03"
    ),
    current_user: dict = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get weekly analytics for the user.
    
    Query Parameters:
    - week_start: Optional week start date in YYYY-MM-DD format
    
    Returns:
    - WeeklyAnalyticsResponse with week's metrics
    """
    user_id = current_user["id"]
    
    # Parse week_start if provided
    if week_start:
        try:
            start_date = date.fromisoformat(week_start)
        except ValueError:
            raise BadRequestException(message="Invalid date format. Use YYYY-MM-DD")
    else:
        start_date = None  # Service will default to current week
    
    analytics = await service.get_weekly_analytics(user_id, start_date)
    
    return SuccessResponse(
        message="Weekly analytics retrieved successfully",
        status_code=200,
        data=analytics
    )


@router.get(
    "/overview",
    response_model=SuccessResponse[OverviewAnalyticsResponse],
    summary="Get Complete Analytics Overview",
    description="""
    Get comprehensive analytics overview including:
    
    - **Consistency Metrics**: Score (0-100), streaks, study days
    - **Exam Readiness**: Score (0-100) with breakdown and recommendations
    - **Subject Progress**: Coverage, strength distribution, revisions per subject
    - **Overall Progress**: Total syllabus coverage percentage
    - **Study Time**: Total hours studied (all-time)
    
    **Note**: Analytics are frozen (read-only) after exam date passes.
    
    **Honest Metrics Philosophy**:
    - No score inflation
    - Consistency heavily penalizes missed days
    - Exam readiness reflects realistic preparation
    - Partial completion weighted lower than full
    """
)
async def get_overview_analytics(
    current_user: dict = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get complete analytics overview for the user.
    
    Returns:
    - OverviewAnalyticsResponse with all metrics
    """
    user_id = current_user["id"]
    
    analytics = await service.get_overview_analytics(user_id)
    
    # Add context message if frozen
    message = "Analytics overview retrieved successfully"
    if analytics.analytics_frozen:
        message += " (Analytics frozen - exam date has passed)"
    
    return SuccessResponse(
        message=message,
        status_code=200,
        data=analytics
    )
