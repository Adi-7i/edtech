"""
Task Execution Router

API endpoints for daily task execution and tracking.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Path, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.user import UserModel
from app.core.database.mongo import get_database
from app.core.responses.base import SuccessResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.tasks.schemas import (
    CloseDayRequest,
    DailyTasksResponse,
    DayClosureResponse,
    TaskUpdateResponse,
    UpdateTaskStatusRequest,
    UpdateTaskTimeRequest,
)
from app.modules.tasks.service import TaskExecutionService

router = APIRouter()


@router.get(
    "/today",
    response_model=SuccessResponse[DailyTasksResponse],
    summary="Get today's tasks",
    description="Fetch all tasks scheduled for today"
)
async def get_todays_tasks(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all tasks for today's date.
    
    Returns tasks ordered by priority and sequence.
    """
    service = TaskExecutionService(db)
    result = await service.get_tasks_for_today(str(current_user.id))
    
    return SuccessResponse(
        success=True,
        message="Today's tasks retrieved",
        status_code=status.HTTP_200_OK,
        data=result
    )


@router.get(
    "/date/{task_date}",
    response_model=SuccessResponse[DailyTasksResponse],
    summary="Get tasks for specific date",
    description="Fetch all tasks for a given date (YYYY-MM-DD)"
)
async def get_tasks_by_date(
    task_date: str = Path(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Date in YYYY-MM-DD format"
    ),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all tasks for a specific date.
    
    Args:
        task_date: Date in YYYY-MM-DD format
    
    Returns:
        DailyTasksResponse with tasks
    """
    # Parse date
    try:
        parsed_date = datetime.strptime(task_date, "%Y-%m-%d").date()
    except ValueError:
        return SuccessResponse(
            success=False,
            message="Invalid date format. Use YYYY-MM-DD",
            status_code=status.HTTP_400_BAD_REQUEST,
            data=None
        )
    
    service = TaskExecutionService(db)
    result = await service.get_tasks_for_date(str(current_user.id), parsed_date)
    
    return SuccessResponse(
        success=True,
        message=f"Tasks for {task_date} retrieved",
        status_code=status.HTTP_200_OK,
        data=result
    )


@router.put(
    "/{task_id}/status",
    response_model=SuccessResponse[TaskUpdateResponse],
    summary="Update task status",
    description="Update task execution status (pending, in_progress, completed, partial, missed)"
)
async def update_task_status(
    task_id: str = Path(..., description="Task ID"),
    request: UpdateTaskStatusRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update task status.
    
    Validation rules:
    - Task must belong to current user
    - Task date must be today (cannot update past or future)
    - Status transition must be valid
    - For 'completed': actual time must be >= 80% of allocated time
    
    Args:
        task_id: Task ID
        request: Status update request
    
    Returns:
        TaskUpdateResponse
    """
    service = TaskExecutionService(db)
    
    result = await service.update_task_status(
        task_id=task_id,
        user_id=str(current_user.id),
        status=request.status,
        notes=request.notes
    )
    
    return SuccessResponse(
        success=True,
        message=f"Task status updated to {request.status}",
        status_code=status.HTTP_200_OK,
        data=result
    )


@router.put(
    "/{task_id}/time",
    response_model=SuccessResponse[TaskUpdateResponse],
    summary="Update task time",
    description="Track actual time spent on a task"
)
async def update_task_time(
    task_id: str = Path(..., description="Task ID"),
    request: UpdateTaskTimeRequest = ...,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Update actual time spent on a task.
    
    Validation rules:
    - Task must belong to current user
    - Task date must be today
    - Minutes must be 1-480 (max 8 hours per update)
    - Total actual time capped at 12 hours
    
    Args:
        task_id: Task ID
        request: Time update request
    
    Returns:
        TaskUpdateResponse
    """
    service = TaskExecutionService(db)
    
    result = await service.update_task_time(
        task_id=task_id,
        user_id=str(current_user.id),
        minutes=request.minutes,
        mode=request.mode
    )
    
    return SuccessResponse(
        success=True,
        message=f"Task time updated ({request.mode}: {request.minutes} minutes)",
        status_code=status.HTTP_200_OK,
        data=result
    )


@router.post(
    "/day/close",
    response_model=SuccessResponse[DayClosureResponse],
    summary="Close a day",
    description="Finalize task statuses for a day (mark pending as missed/partial)"
)
async def close_day(
    request: CloseDayRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Close a day and finalize task statuses.
    
    Logic:
    - Tasks with < 50% completion → missed
    - Tasks with 50-79% completion → partial
    - Tasks with 80%+ completion → (already completed)
    
    Args:
        request: Day closure request with date
    
    Returns:
        DayClosureResponse with summary
    """
    # Parse date
    try:
        parsed_date = datetime.strptime(request.date, "%Y-%m-%d").date()
    except ValueError:
        return SuccessResponse(
            success=False,
            message="Invalid date format. Use YYYY-MM-DD",
            status_code=status.HTTP_400_BAD_REQUEST,
            data=None
        )
    
    service = TaskExecutionService(db)
    
    result = await service.close_day(
        user_id=str(current_user.id),
        task_date=parsed_date
    )
    
    return SuccessResponse(
        success=True,
        message=f"Day {request.date} closed successfully",
        status_code=status.HTTP_200_OK,
        data=result
    )
