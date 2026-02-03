"""
Revision Router

API endpoints for spaced repetition revision scheduling.
"""

from fastapi import APIRouter, Depends, Path, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.user import UserModel
from app.core.database.mongo import get_database
from app.core.responses.base import SuccessResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.revision.schemas import (
    DailyRevisionsResponse,
    RevisionResponse,
    RevisionScheduleResponse,
    ScheduleRevisionRequest,
    UpdateRevisionStatusRequest,
)
from app.modules.revision.service import RevisionService

router = APIRouter()


@router.post(
    "/schedule",
    response_model=SuccessResponse[RevisionScheduleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Schedule Revisions",
    description="Create spaced repetition revision schedule for a completed chapter"
)
async def schedule_revisions(
    request: ScheduleRevisionRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Schedule revisions for a completed chapter.
    
    **Requirements:**
    - Chapter must be completed (is_completed=true)
    - No existing active revision schedule (unless force_reschedule=true)
    - Exam date must be in the future
    
    **Spaced Repetition Schedule:**
    - Day 1: First revision (tomorrow after completion)
    - Day 3: Second revision
    - Day 7: Third revision  
    - Day 21: Long-term retention revision
    
    **Args:**
    - chapter_id: User chapter ID
    - force_reschedule: Delete existing schedule and create new
    
    **Returns:**
    - Revision schedule details with first revision date
    """
    service = RevisionService(db)
    
    result = await service.schedule_revisions_for_chapter(
        user_id=str(current_user.id),
        chapter_id=request.chapter_id,
        force_reschedule=request.force_reschedule
    )
    
    return SuccessResponse(
        success=True,
        message="Revision schedule created successfully",
        status_code=status.HTTP_201_CREATED,
        data=result
    )


@router.get(
    "/today",
    response_model=SuccessResponse[DailyRevisionsResponse],
    summary="Get Today's Revisions",
    description="Fetch all revisions due today with intelligent priority ordering"
)
async def get_todays_revisions(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get today's revisions ordered by priority.
    
    **Priority Ordering:**
    1. Overdue revisions (highest priority)
    2. Weak chapters before strong chapters
    3. Chapters closer to exam date
    4. Earlier interval levels (newer revisions)
    
    **Auto-Rescheduling:**
    - Missed revisions from past dates are automatically rescheduled
    - Rescheduled to next valid date
    - Maintains spaced repetition integrity
    
    **Returns:**
    - List of revisions due today/overdue
    - Priority-ordered for optimal learning
    - Includes chapter details and progress metrics
    """
    service = RevisionService(db)
    
    result = await service.get_todays_revisions(user_id=str(current_user.id))
    
    return SuccessResponse(
        success=True,
        message="Today's revisions retrieved",
        status_code=status.HTTP_200_OK,
        data=result
    )


@router.put(
    "/{revision_id}/status",
    response_model=SuccessResponse[RevisionResponse],
    summary="Update Revision Status",
    description="Mark revision as completed/missed and schedule next revision"
)
async def update_revision_status(
    revision_id: str = Path(..., description="Revision ID"),
    request: UpdateRevisionStatusRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update revision status after completion or mark as missed.
    
    **For COMPLETED Status:**
    - Must provide quality rating (perfect/good/average/poor/failed)
    - Quality determines next interval:
      - PERFECT/GOOD → advance to next interval
      - AVERAGE → repeat current interval
      - POOR/FAILED → reset to Day 1
    - Automatically schedules next revision
    - Marks as mastered after completing all 4 cycles
    
    **For MISSED/SKIPPED Status:**
    - Marks revision as missed
    - Auto-reschedules to tomorrow
    - Increments miss counter
    
    **Args:**
    - revision_id: Revision schedule ID
    - status: New status (completed/missed/skipped)
    - quality: Recall quality (required for completed)
    - duration_minutes: Time spent on revision
    - notes: Optional revision notes
    
    **Returns:**
    - Updated revision details
    - Next scheduled revision date
    - Progress metrics
    """
    service = RevisionService(db)
    
    result = await service.update_revision_status(
        revision_id=revision_id,
        user_id=str(current_user.id),
        status=request.status,
        quality=request.quality,
        duration_minutes=request.duration_minutes,
        notes=request.notes
    )
    
    return SuccessResponse(
        success=True,
        message=f"Revision status updated to {request.status.value}",
        status_code=status.HTTP_200_OK,
        data=result
    )
