"""
Task Execution Schemas

Request and response models for daily task execution and tracking.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# -------------------------------------------------------------------------
# Request Schemas
# -------------------------------------------------------------------------

class UpdateTaskStatusRequest(BaseModel):
    """Request to update task status."""
    
    status: Literal["pending", "in_progress", "completed", "partial", "missed"] = Field(
        ...,
        description="New task status"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional notes about the status change"
    )


class UpdateTaskTimeRequest(BaseModel):
    """Request to update actual time spent on a task."""
    
    minutes: int = Field(
        ...,
        ge=1,
        le=480,
        description="Time in minutes (1-480, max 8 hours per update)"
    )
    mode: Literal["add", "set"] = Field(
        default="add",
        description="'add' to increment, 'set' to replace"
    )


class CloseDayRequest(BaseModel):
    """Request to close a day and finalize task statuses."""
    
    date: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Date to close (YYYY-MM-DD format)"
    )


# -------------------------------------------------------------------------
# Response Schemas
# -------------------------------------------------------------------------

class TaskExecutionResponse(BaseModel):
    """Response schema for a single task."""
    
    id: str = Field(..., description="Task ID")
    subject_name: str = Field(..., description="Subject name")
    chapter_name: str = Field(..., description="Chapter name")
    
    # Time tracking
    allocated_hours: float = Field(..., description="Planned study hours")
    actual_hours: float = Field(..., description="Actual time spent")
    completion_percentage: float = Field(
        ...,
        description="Completion percentage (actual/allocated * 100)"
    )
    
    # Status
    status: str = Field(..., description="Current task status")
    is_completed: bool = Field(..., description="Whether task is completed")
    
    # Metadata
    priority_weight: float = Field(..., description="Priority score")
    chapter_strength: str = Field(..., description="Chapter difficulty")
    order_in_day: int = Field(..., description="Order within the day")
    
    # Optional fields
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    notes: Optional[str] = Field(None, description="Task notes")


class DailyTasksResponse(BaseModel):
    """Response schema for daily tasks list."""
    
    date: str = Field(..., description="Task date (YYYY-MM-DD)")
    
    # Tasks
    tasks: List[TaskExecutionResponse] = Field(
        default_factory=list,
        description="List of tasks for the day"
    )
    
    # Summary statistics
    total_tasks: int = Field(..., description="Total number of tasks")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    partial_tasks: int = Field(..., description="Number of partially completed tasks")
    missed_tasks: int = Field(..., description="Number of missed tasks")
    pending_tasks: int = Field(..., description="Number of pending tasks")
    
    # Time statistics
    total_allocated_hours: float = Field(..., description="Total planned hours")
    total_actual_hours: float = Field(..., description="Total actual hours spent")
    completion_percentage: float = Field(
        ...,
        description="Overall completion percentage"
    )


class TaskUpdateResponse(BaseModel):
    """Response for task update operations."""
    
    id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Updated status")
    actual_hours: float = Field(..., description="Updated actual hours")
    completion_percentage: float = Field(..., description="Completion percentage")
    is_completed: bool = Field(..., description="Whether task is completed")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")


class DayClosureResponse(BaseModel):
    """Response for day closure operation."""
    
    date: str = Field(..., description="Closed date")
    total_tasks: int = Field(..., description="Total tasks for the day")
    completed_tasks: int = Field(..., description="Tasks marked as completed")
    partial_tasks: int = Field(..., description="Tasks marked as partial")
    missed_tasks: int = Field(..., description="Tasks marked as missed")
    day_closed_at: str = Field(..., description="Closure timestamp")
