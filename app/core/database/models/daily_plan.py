"""
Daily Study Plan Model for Smart Study Planner.

Collection: daily_plans

Stores date-based study plans for students:
- Planned tasks for the day
- Time allocation per task
- Overall status tracking

Design decisions:
- Tasks embedded as bounded array (max 20 per day)
- One document per user per date
- Task details kept minimal; execution tracked separately

Indexes (to be created):
- (user_id, plan_date) unique compound
- user_id
- plan_date
- status
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class PlanStatus(str, Enum):
    """Daily plan overall status."""
    DRAFT = "draft"  # Plan being created
    SCHEDULED = "scheduled"  # Ready for execution
    IN_PROGRESS = "in_progress"  # Currently being worked on
    COMPLETED = "completed"  # All tasks done
    PARTIAL = "partial"  # Some tasks completed
    MISSED = "missed"  # Day passed without completion


class TaskType(str, Enum):
    """Types of study tasks."""
    LEARNING = "learning"  # New content
    REVISION = "revision"  # Review of learned content
    PRACTICE = "practice"  # Problem solving
    TEST = "test"  # Mock test/quiz
    READING = "reading"  # Reading material
    VIDEO = "video"  # Video lectures
    BREAK = "break"  # Scheduled breaks


class TaskPriority(str, Enum):
    """Task priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Individual task status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Partially completed
    SKIPPED = "skipped"  # Intentionally skipped
    MISSED = "missed"  # Not done


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class PlannedTask(BaseModel):
    """
    Individual task in a daily plan (embedded).
    Max 20 tasks per daily plan to keep document size bounded.
    """
    
    # Task identification
    task_id: str = Field(
        ...,
        description="Unique task ID within the plan (UUID)"
    )
    
    # Content reference
    chapter_id: Optional[PyObjectId] = Field(
        default=None,
        description="Reference to chapter (if applicable)"
    )
    topic_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Topic name within chapter"
    )
    
    # Task details
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Task title"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Task description"
    )
    task_type: TaskType = Field(
        default=TaskType.LEARNING,
        description="Type of task"
    )
    
    # Time allocation
    scheduled_start_time: Optional[str] = Field(
        default=None,
        description="Scheduled start time (HH:MM)"
    )
    planned_duration_minutes: int = Field(
        default=30,
        ge=5,
        le=180,
        description="Planned duration in minutes"
    )
    
    # Priority and ordering
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task priority"
    )
    sequence_order: int = Field(
        default=0,
        ge=0,
        description="Order in the daily plan"
    )
    
    # Status (updated during execution)
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current task status"
    )
    
    # AI-generated flag
    is_ai_generated: bool = Field(
        default=False,
        description="Whether task was AI-generated"
    )
    
    # Revision-specific
    is_revision_task: bool = Field(
        default=False,
        description="Part of spaced repetition"
    )
    revision_cycle: Optional[int] = Field(
        default=None,
        description="Revision cycle day (1, 3, 7, 21)"
    )


class TimeSlotAllocation(BaseModel):
    """Time slot allocation for the day (embedded)."""
    
    morning_minutes: int = Field(
        default=0,
        ge=0,
        description="Minutes allocated for morning (6AM-12PM)"
    )
    afternoon_minutes: int = Field(
        default=0,
        ge=0,
        description="Minutes allocated for afternoon (12PM-5PM)"
    )
    evening_minutes: int = Field(
        default=0,
        ge=0,
        description="Minutes allocated for evening (5PM-9PM)"
    )
    night_minutes: int = Field(
        default=0,
        ge=0,
        description="Minutes allocated for night (9PM-12AM)"
    )
    
    @property
    def total_minutes(self) -> int:
        """Total planned minutes for the day."""
        return (
            self.morning_minutes + 
            self.afternoon_minutes + 
            self.evening_minutes + 
            self.night_minutes
        )


class DailySummary(BaseModel):
    """End-of-day summary (embedded, updated after day ends)."""
    
    tasks_completed: int = Field(default=0, ge=0)
    tasks_partial: int = Field(default=0, ge=0)
    tasks_missed: int = Field(default=0, ge=0)
    
    actual_study_minutes: int = Field(default=0, ge=0)
    planned_study_minutes: int = Field(default=0, ge=0)
    
    completion_percentage: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Overall completion percentage"
    )
    
    # Subject-wise breakdown (max 10)
    subjects_covered: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Subjects studied today"
    )


# -----------------------------------------------------------------------------
# Main Daily Plan Model
# -----------------------------------------------------------------------------

class DailyPlanModel(MongoBaseModel):
    """
    Daily study plan document.
    
    Collection: daily_plans
    
    Indexes:
    - (user_id, plan_date) unique compound
    - user_id
    - plan_date
    - status
    - (user_id, status) compound for filtering
    """
    
    # User reference
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    
    # Plan date (one plan per user per day)
    plan_date: date = Field(
        ...,
        description="Date of the study plan"
    )
    
    # Tasks (bounded array - max 20)
    tasks: list[PlannedTask] = Field(
        default_factory=list,
        max_length=20,
        description="Planned tasks for the day"
    )
    
    # Time allocation
    time_allocation: TimeSlotAllocation = Field(
        default_factory=TimeSlotAllocation,
        description="Time slot allocations"
    )
    total_planned_minutes: int = Field(
        default=0,
        ge=0,
        description="Total planned study minutes"
    )
    
    # Status
    status: PlanStatus = Field(
        default=PlanStatus.DRAFT,
        description="Overall plan status"
    )
    
    # Generation info
    is_auto_generated: bool = Field(
        default=False,
        description="Whether plan was AI-generated"
    )
    generation_strategy: Optional[str] = Field(
        default=None,
        max_length=50,
        description="AI strategy used (balanced/intensive/revision)"
    )
    
    # User modifications
    user_modified: bool = Field(
        default=False,
        description="Whether user modified AI plan"
    )
    modification_count: int = Field(
        default=0,
        ge=0,
        description="Number of user modifications"
    )
    
    # Daily summary (populated at end of day)
    summary: Optional[DailySummary] = Field(
        default=None,
        description="End-of-day summary"
    )
    
    # Notes
    user_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User notes for the day"
    )
    
    @property
    def task_count(self) -> int:
        """Number of tasks in the plan."""
        return len(self.tasks)
    
    @property
    def pending_tasks(self) -> int:
        """Count of pending tasks."""
        return sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------

class DailyPlanCreateDTO(BaseModel):
    """DTO for creating a daily plan."""
    
    plan_date: date
    tasks: list[PlannedTask] = Field(default_factory=list, max_length=20)
    time_allocation: Optional[TimeSlotAllocation] = None
    is_auto_generated: bool = False


class TaskUpdateDTO(BaseModel):
    """DTO for updating a task status."""
    
    task_id: str
    status: TaskStatus
    actual_duration_minutes: Optional[int] = None
