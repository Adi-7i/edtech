"""
Planner Router

API endpoints for study plan generation and management.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.user import UserModel
from app.core.database.mongo import get_database
from app.core.responses.base import SuccessResponse
from app.modules.auth.dependencies import get_current_active_user
from app.modules.planner.schemas import (
    DailyPlanResponse,
    PlanGenerateRequest,
    PlanPreviewResponse,
    PlanResponse,
)
from app.modules.planner.service import PlannerService


# -----------------------------------------------------------------------------
# Router Setup
# -----------------------------------------------------------------------------

router = APIRouter(tags=["Planner"])


# -----------------------------------------------------------------------------
# Plan Generation
# -----------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=SuccessResponse[PlanResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Study Plan",
    description="Generate a new study plan based on profile, subjects, and chapters."
)
async def generate_plan(
    request: PlanGenerateRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generate a new study plan.
    
    **Algorithm:**
    - Gathers profile, subjects, and chapters
    - Calculates days until exam
    - Prioritizes weak chapters first
    - Distributes chapters across available days
    - Respects daily study hour limits
    
    **Requirements:**
    - Must have active study profile
    - Must have added subjects
    - Must have added chapters
    
    **Options:**
    - `force_regenerate`: Delete existing plan and create new one
    - `prioritize_weak_only`: Only include weak chapters
    - `buffer_days`: Reserve N days before exam (for final revision)
    """
    service = PlannerService(db)
    
    plan = await service.generate_plan(
        user_id=str(current_user.id),
        force_regenerate=request.force_regenerate,
        prioritize_weak_only=request.prioritize_weak_only,
        buffer_days=request.buffer_days
    )
    
    return SuccessResponse(
        success=True,
        message="Study plan generated successfully",
        status_code=status.HTTP_201_CREATED,
        data=plan
    )


@router.get(
    "/preview",
    response_model=SuccessResponse[PlanPreviewResponse],
    summary="Preview Plan",
    description="Preview what would be generated without actually creating the plan."
)
async def preview_plan(
    buffer_days: int = Query(default=0, ge=0, le=7),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Preview study plan generation.
    
    Shows:
    - Timeline and available days
    - Chapter breakdown by strength
    - Time analysis (needed vs available)
    - Feasibility score
    - Warnings
    
    Useful for checking if plan is feasible before generating.
    """
    service = PlannerService(db)
    
    preview = await service.preview_plan(
        user_id=str(current_user.id),
        buffer_days=buffer_days
    )
    
    return SuccessResponse(
        success=True,
        message="Plan preview generated",
        status_code=status.HTTP_200_OK,
        data=preview
    )


# -----------------------------------------------------------------------------
# Plan Retrieval
# -----------------------------------------------------------------------------

@router.get(
    "",
    response_model=SuccessResponse[PlanResponse],
    summary="Get Active Plan",
    description="Get the current active study plan with upcoming days."
)
async def get_active_plan(
    days_ahead: int = Query(default=7, ge=1, le=30),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get active study plan.
    
    Returns:
    - Plan summary (timeline, progress, stats)
    - Upcoming daily plans (default: next 7 days)
    """
    service = PlannerService(db)
    
    plan = await service.get_plan_with_upcoming_days(
        user_id=str(current_user.id),
        days_ahead=days_ahead
    )
    
    return SuccessResponse(
        success=True,
        message="Active plan retrieved",
        status_code=status.HTTP_200_OK,
        data=plan
    )


@router.get(
    "/daily/{plan_date}",
    response_model=SuccessResponse[DailyPlanResponse],
    summary="Get Daily Plan",
    description="Get study plan for a specific date."
)
async def get_daily_plan(
    plan_date: date,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get daily plan for specific date.
    
    Returns:
    - Date and time allocation
    - List of study tasks for that day
    - Task details (subject, chapter, hours, priority)
    - Completion status
    """
    service = PlannerService(db)
    
    daily_plan = await service.get_daily_plan(
        user_id=str(current_user.id),
        plan_date=plan_date
    )
    
    return SuccessResponse(
        success=True,
        message=f"Daily plan for {plan_date} retrieved",
        status_code=status.HTTP_200_OK,
        data=daily_plan
    )


# -----------------------------------------------------------------------------
# Plan Management
# -----------------------------------------------------------------------------

@router.delete(
    "",
    response_model=SuccessResponse[dict],
    summary="Delete Active Plan",
    description="Delete the current active study plan and all associated data."
)
async def delete_plan(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete active plan.
    
    **WARNING:** This deletes:
    - The study plan
    - All daily plans
    - All study tasks
    
    This action cannot be undone.
    Use this if you want to regenerate with different parameters.
    """
    service = PlannerService(db)
    
    await service.delete_plan(user_id=str(current_user.id))
    
    return SuccessResponse(
        success=True,
        message="Study plan deleted successfully",
        status_code=status.HTTP_200_OK,
        data={"deleted": True}
    )
