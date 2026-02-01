"""
Task Execution Model for Smart Study Planner.

Collection: task_executions

Tracks actual execution of planned tasks:
- Completion status (completed/partial/missed)
- Actual time spent
- User feedback and notes

Design decisions:
- Separate from daily_plan for detailed tracking
- One document per task execution
- Supports partial completion with percentage

Indexes (to be created):
- (user_id, plan_id) compound
- (user_id, task_id) unique compound
- user_id
- status
- executed_at
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class ExecutionStatus(str, Enum):
    """Task execution status."""
    COMPLETED = "completed"
    PARTIAL = "partial"
    MISSED = "missed"
    SKIPPED = "skipped"  # User intentionally skipped


class CompletionQuality(str, Enum):
    """Self-assessed quality of completion."""
    EXCELLENT = "excellent"  # Fully understood
    GOOD = "good"  # Understood well
    AVERAGE = "average"  # Basic understanding
    POOR = "poor"  # Struggled
    NOT_RATED = "not_rated"


class SkipReason(str, Enum):
    """Reasons for skipping a task."""
    TOO_DIFFICULT = "too_difficult"
    ALREADY_KNOWN = "already_known"
    TIME_CONSTRAINT = "time_constraint"
    NOT_RELEVANT = "not_relevant"
    HEALTH_ISSUE = "health_issue"
    EMERGENCY = "emergency"
    OTHER = "other"


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class ExecutionSession(BaseModel):
    """
    Individual study session for a task (embedded).
    Max 5 sessions per task (for tasks done in multiple sittings).
    """
    
    started_at: datetime = Field(
        ...,
        description="Session start time"
    )
    ended_at: Optional[datetime] = Field(
        default=None,
        description="Session end time"
    )
    duration_minutes: int = Field(
        default=0,
        ge=0,
        description="Session duration in minutes"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Session notes"
    )


class DistractionLog(BaseModel):
    """Distraction tracking (embedded)."""
    
    distraction_count: int = Field(
        default=0,
        ge=0,
        description="Number of distractions"
    )
    total_distraction_minutes: int = Field(
        default=0,
        ge=0,
        description="Total distraction time"
    )
    main_distraction_type: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Primary distraction type"
    )


# -----------------------------------------------------------------------------
# Main Task Execution Model
# -----------------------------------------------------------------------------

class TaskExecutionModel(MongoBaseModel):
    """
    Task execution document.
    
    Collection: task_executions
    
    Indexes:
    - (user_id, plan_id) compound
    - (user_id, task_id) unique compound
    - user_id
    - status
    - executed_at
    - (user_id, status, executed_at) for analytics
    """
    
    # References
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    plan_id: PyObjectId = Field(
        ...,
        description="Reference to daily plan"
    )
    task_id: str = Field(
        ...,
        description="Task ID within the plan"
    )
    
    # Content reference (denormalized for quick access)
    chapter_id: Optional[PyObjectId] = Field(
        default=None,
        description="Reference to chapter"
    )
    task_title: str = Field(
        ...,
        max_length=200,
        description="Task title (denormalized)"
    )
    task_type: str = Field(
        default="learning",
        description="Task type (denormalized)"
    )
    
    # Execution status
    status: ExecutionStatus = Field(
        default=ExecutionStatus.MISSED,
        description="Execution status"
    )
    
    # Completion details
    completion_percentage: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Completion percentage (0-100)"
    )
    quality: CompletionQuality = Field(
        default=CompletionQuality.NOT_RATED,
        description="Self-assessed quality"
    )
    
    # Time tracking
    planned_duration_minutes: int = Field(
        default=0,
        ge=0,
        description="Originally planned duration"
    )
    actual_duration_minutes: int = Field(
        default=0,
        ge=0,
        description="Actual time spent"
    )
    
    # Execution timestamps
    started_at: Optional[datetime] = Field(
        default=None,
        description="When task was started"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When task was completed"
    )
    executed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date of execution"
    )
    
    # Sessions (for multi-sitting tasks, max 5)
    sessions: list[ExecutionSession] = Field(
        default_factory=list,
        max_length=5,
        description="Individual study sessions"
    )
    
    # Skip handling
    was_skipped: bool = Field(
        default=False,
        description="Whether task was skipped"
    )
    skip_reason: Optional[SkipReason] = Field(
        default=None,
        description="Reason for skipping"
    )
    
    # Distraction tracking
    distraction_log: Optional[DistractionLog] = Field(
        default=None,
        description="Distraction information"
    )
    
    # User feedback
    difficulty_rating: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Difficulty rating (1-5)"
    )
    user_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User notes after completion"
    )
    
    # Follow-up flags
    needs_revision: bool = Field(
        default=False,
        description="User flagged for revision"
    )
    needs_more_practice: bool = Field(
        default=False,
        description="User wants more practice"
    )
    
    @property
    def efficiency_ratio(self) -> float:
        """Calculate time efficiency (planned vs actual)."""
        if self.planned_duration_minutes == 0:
            return 0.0
        return min(
            self.planned_duration_minutes / max(self.actual_duration_minutes, 1),
            2.0  # Cap at 200%
        )


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------

class TaskExecutionCreateDTO(BaseModel):
    """DTO for creating task execution record."""
    
    plan_id: PyObjectId
    task_id: str
    chapter_id: Optional[PyObjectId] = None
    task_title: str
    task_type: str = "learning"
    planned_duration_minutes: int


class TaskExecutionUpdateDTO(BaseModel):
    """DTO for updating execution status."""
    
    status: ExecutionStatus
    completion_percentage: int = 100
    actual_duration_minutes: Optional[int] = None
    quality: Optional[CompletionQuality] = None
    user_notes: Optional[str] = None
