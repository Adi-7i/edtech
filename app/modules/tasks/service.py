"""
Task Execution Service

Core business logic for daily task execution and tracking.
Enforces all execution rules and validation.
"""

from datetime import date, datetime
from typing import List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_plan import StudyTaskModel, TaskStatus
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.modules.tasks.repository import TaskExecutionRepository
from app.modules.tasks.schemas import (
    DailyTasksResponse,
    DayClosureResponse,
    TaskExecutionResponse,
    TaskUpdateResponse,
)


class TaskExecutionService:
    """Service for task execution operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.task_repo = TaskExecutionRepository(db)
    
    # -------------------------------------------------------------------------
    # Task Fetching
    # -------------------------------------------------------------------------
    
    async def get_tasks_for_today(self, user_id: str) -> DailyTasksResponse:
        """
        Get all tasks for today's date.
        
        Args:
            user_id: User ID
        
        Returns:
            DailyTasksResponse with today's tasks
        """
        today = date.today()
        return await self.get_tasks_for_date(user_id, today)
    
    async def get_tasks_for_date(
        self,
        user_id: str,
        task_date: date
    ) -> DailyTasksResponse:
        """
        Get all tasks for a specific date.
        
        Args:
            user_id: User ID
            task_date: Date to fetch tasks for
        
        Returns:
            DailyTasksResponse with tasks
        """
        # Fetch tasks from repository
        tasks = await self.task_repo.find_by_date_and_user(user_id, task_date)
        
        if not tasks:
            # Return empty response
            return DailyTasksResponse(
                date=task_date.isoformat(),
                tasks=[],
                total_tasks=0,
                completed_tasks=0,
                partial_tasks=0,
                missed_tasks=0,
                pending_tasks=0,
                total_allocated_hours=0.0,
                total_actual_hours=0.0,
                completion_percentage=0.0
            )
        
        # Convert to response models
        task_responses = [self._task_to_response(task) for task in tasks]
        
        # Calculate statistics
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        partial_tasks = sum(1 for t in tasks if t.status == TaskStatus.PARTIAL)
        missed_tasks = sum(1 for t in tasks if t.status == TaskStatus.MISSED)
        pending_tasks = sum(
            1 for t in tasks 
            if t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        )
        
        total_allocated = sum(t.allocated_hours for t in tasks)
        total_actual = sum(t.actual_hours or 0 for t in tasks)
        
        completion_pct = (
            (total_actual / total_allocated * 100) if total_allocated > 0 else 0
        )
        
        return DailyTasksResponse(
            date=task_date.isoformat(),
            tasks=task_responses,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            partial_tasks=partial_tasks,
            missed_tasks=missed_tasks,
            pending_tasks=pending_tasks,
            total_allocated_hours=total_allocated,
            total_actual_hours=total_actual,
            completion_percentage=completion_pct
        )
    
    # -------------------------------------------------------------------------
    # Task Status Updates
    # -------------------------------------------------------------------------
    
    async def update_task_status(
        self,
        task_id: str,
        user_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> TaskUpdateResponse:
        """
        Update task status with validation.
        
        Args:
            task_id: Task ID
            user_id: User ID (for ownership check)
            status: New status
            notes: Optional notes
        
        Returns:
            TaskUpdateResponse
        
        Raises:
            NotFoundException: Task not found
            ForbiddenException: Not task owner
            BadRequestException: Invalid status transition or date
        """
        # Get task
        task = await self.task_repo.find_by_id(task_id)
        if not task:
            raise NotFoundException(message="Task not found")
        
        # Verify ownership
        if str(task.user_id) != user_id:
            raise ForbiddenException(message="You do not own this task")
        
        # Check if task can be edited
        can_edit, reason = await self._can_edit_task(task)
        if not can_edit:
            raise BadRequestException(message=reason)
        
        # Validate status transition
        self._validate_status_transition(task, status)
        
        # For completed status, check if enough time was spent
        if status == TaskStatus.COMPLETED:
            if not self._can_mark_completed(task):
                raise BadRequestException(
                    message="Actual time is less than 80% of allocated time. "
                           "Mark as 'partial' instead or add more time."
                )
        
        # Update status
        updated_task = await self.task_repo.update_status(
            task_id,
            TaskStatus(status),
            notes
        )
        
        if not updated_task:
            raise NotFoundException(message="Task not found after update")
        
        return self._task_to_update_response(updated_task)
    
    # -------------------------------------------------------------------------
    # Time Tracking
    # -------------------------------------------------------------------------
    
    async def update_task_time(
        self,
        task_id: str,
        user_id: str,
        minutes: int,
        mode: str = "add"
    ) -> TaskUpdateResponse:
        """
        Update actual time spent on a task.
        
        Args:
            task_id: Task ID
            user_id: User ID
            minutes: Time in minutes
            mode: "add" or "set"
        
        Returns:
            TaskUpdateResponse
        
        Raises:
            NotFoundException: Task not found
            ForbiddenException: Not task owner
            BadRequestException: Invalid time or date
        """
        # Get task
        task = await self.task_repo.find_by_id(task_id)
        if not task:
            raise NotFoundException(message="Task not found")
        
        # Verify ownership
        if str(task.user_id) != user_id:
            raise ForbiddenException(message="You do not own this task")
        
        # Check if task can be edited (time updates only allowed for today)
        can_edit, reason = await self._can_edit_task(task, check_status=False)
        if not can_edit:
            raise BadRequestException(message=reason)
        
        # Calculate new actual hours
        hours = minutes / 60.0
        
        if mode == "set":
            new_actual_hours = hours
        else:  # add
            current_hours = task.actual_hours or 0
            new_actual_hours = current_hours + hours
        
        # Cap at 12 hours per task
        new_actual_hours = min(new_actual_hours, 12.0)
        
        # Update time
        updated_task = await self.task_repo.update_actual_time(task_id, new_actual_hours)
        
        if not updated_task:
            raise NotFoundException(message="Task not found after update")
        
        # Auto-update status to in_progress if pending
        if updated_task.status == TaskStatus.PENDING and new_actual_hours > 0:
            updated_task = await self.task_repo.update_status(
                task_id,
                TaskStatus.IN_PROGRESS
            )
        
        return self._task_to_update_response(updated_task)
    
    # -------------------------------------------------------------------------
    # Day Closure
    # -------------------------------------------------------------------------
    
    async def close_day(
        self,
        user_id: str,
        task_date: date
    ) -> DayClosureResponse:
        """
        Close a day and finalize task statuses.
        
        Logic:
        - pending/in_progress tasks with < 80% time → missed
        - pending/in_progress tasks with >= 50% time → partial
        - completed tasks remain completed
        
        Args:
            user_id: User ID
            task_date: Date to close
        
        Returns:
            DayClosureResponse
        
        Raises:
            BadRequestException: Cannot close future date
        """
        # Validate date (can only close today or past)
        today = date.today()
        if task_date > today:
            raise BadRequestException(message="Cannot close future dates")
        
        # Get all tasks for the date
        tasks = await self.task_repo.find_by_date_and_user(user_id, task_date)
        
        if not tasks:
            raise NotFoundException(message=f"No tasks found for {task_date}")
        
        # Categorize tasks for closure
        to_missed = []
        to_partial = []
        
        for task in tasks:
            # Skip already finalized tasks
            if task.status in [TaskStatus.COMPLETED, TaskStatus.PARTIAL, TaskStatus.MISSED]:
                continue
            
            # pending or in_progress tasks need closure
            if task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                actual = task.actual_hours or 0
                allocated = task.allocated_hours
                
                completion_pct = (actual / allocated) if allocated > 0 else 0
                
                if completion_pct >= 0.5:  # 50% or more
                    to_partial.append(str(task.id))
                else:  # Less than 50%
                    to_missed.append(str(task.id))
        
        # Bulk update
        missed_count = await self.task_repo.bulk_update_to_missed(to_missed)
        partial_count = await self.task_repo.bulk_update_to_partial(to_partial)
        
        # Count completed tasks
        completed_count = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        
        return DayClosureResponse(
            date=task_date.isoformat(),
            total_tasks=len(tasks),
            completed_tasks=completed_count,
            partial_tasks=partial_count,
            missed_tasks=missed_count,
            day_closed_at=datetime.utcnow().isoformat()
        )
    
    # -------------------------------------------------------------------------
    # Validation Helpers
    # -------------------------------------------------------------------------
    
    async def _can_edit_task(
        self,
        task: StudyTaskModel,
        check_status: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if task can be edited.
        
        Args:
            task: Task model
            check_status: Whether to check task status (False for time updates)
        
        Returns:
            (can_edit, reason)
        """
        # Get task date from daily plan
        daily_plan = await self.task_repo.daily_plan_repo.find_by_id(
            str(task.daily_plan_id)
        )
        
        if not daily_plan:
            return False, "Daily plan not found"
        
        task_date = daily_plan.plan_date
        today = date.today()
        
        # Check date constraints
        if task_date > today:
            return False, "Cannot update tasks for future dates"
        
        if task_date < today:
            return False, "Cannot edit tasks from past dates"
        
        # Check status constraints (only for status updates)
        if check_status:
            if task.status == TaskStatus.COMPLETED:
                return False, "Task is already completed"
            
            if task.status == TaskStatus.MISSED:
                return False, "Missed tasks cannot be updated"
        
        return True, ""
    
    def _validate_status_transition(
        self,
        task: StudyTaskModel,
        new_status: str
    ) -> None:
        """
        Validate status transition is allowed.
        
        Raises:
            BadRequestException: Invalid transition
        """
        current = task.status
        new = TaskStatus(new_status)
        
        # Valid transitions
        valid_transitions = {
            TaskStatus.PENDING: [
                TaskStatus.IN_PROGRESS,
                TaskStatus.COMPLETED,
                TaskStatus.PARTIAL,
                TaskStatus.MISSED
            ],
            TaskStatus.IN_PROGRESS: [
                TaskStatus.COMPLETED,
                TaskStatus.PARTIAL,
                TaskStatus.MISSED
            ],
            TaskStatus.PARTIAL: [
                TaskStatus.COMPLETED
            ],
            TaskStatus.COMPLETED: [],  # No transitions allowed
            TaskStatus.MISSED: []  # No transitions allowed
        }
        
        allowed = valid_transitions.get(current, [])
        
        if new not in allowed:
            raise BadRequestException(
                message=f"Invalid status transition from '{current}' to '{new}'"
            )
    
    def _can_mark_completed(self, task: StudyTaskModel) -> bool:
        """
        Check if task can be marked as completed.
        
        Requires actual time >= 80% of allocated time.
        """
        threshold = task.allocated_hours * 0.8
        actual = task.actual_hours or 0
        return actual >= threshold
    
    # -------------------------------------------------------------------------
    # Response Mapping
    # -------------------------------------------------------------------------
    
    def _task_to_response(self, task: StudyTaskModel) -> TaskExecutionResponse:
        """Convert task model to response."""
        actual = task.actual_hours or 0
        allocated = task.allocated_hours
        
        completion_pct = (actual / allocated * 100) if allocated > 0 else 0
        
        return TaskExecutionResponse(
            id=str(task.id),
            subject_name=task.subject_name,
            chapter_name=task.chapter_name,
            allocated_hours=allocated,
            actual_hours=actual,
            completion_percentage=completion_pct,
            status=task.status,
            is_completed=task.is_completed,
            priority_weight=task.priority_weight,
            chapter_strength=task.chapter_strength,
            order_in_day=task.order_in_day,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            notes=task.notes
        )
    
    def _task_to_update_response(self, task: StudyTaskModel) -> TaskUpdateResponse:
        """Convert task model to update response."""
        actual = task.actual_hours or 0
        allocated = task.allocated_hours
        
        completion_pct = (actual / allocated * 100) if allocated > 0 else 0
        
        return TaskUpdateResponse(
            id=str(task.id),
            status=task.status,
            actual_hours=actual,
            completion_percentage=completion_pct,
            is_completed=task.is_completed,
            completed_at=task.completed_at.isoformat() if task.completed_at else None
        )
