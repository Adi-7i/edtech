"""
Smart Revision Model for Smart Study Planner.

Collection: revisions

Implements spaced repetition scheduling:
- Day 1: First revision (after learning)
- Day 3: Second revision
- Day 7: Third revision
- Day 21: Long-term retention

Design decisions:
- One document per user-chapter revision cycle
- Tracks missed revisions for rescheduling
- Supports custom intervals for flexibility

Indexes (to be created):
- user_id
- (user_id, chapter_id) unique compound
- next_revision_date (for daily scheduling)
- (user_id, next_revision_date) compound
- status
"""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from .base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Standard spaced repetition intervals (in days)
SPACED_REPETITION_DAYS = [1, 3, 7, 21]


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class RevisionStatus(str, Enum):
    """Revision item status."""
    SCHEDULED = "scheduled"  # Waiting for revision date
    DUE = "due"  # Ready for revision
    COMPLETED = "completed"  # Revision done
    MISSED = "missed"  # Missed the scheduled date
    RESCHEDULED = "rescheduled"  # Rescheduled after miss


class RevisionCycle(int, Enum):
    """Spaced repetition cycle days."""
    DAY_1 = 1
    DAY_3 = 3
    DAY_7 = 7
    DAY_21 = 21


class RevisionQuality(str, Enum):
    """Quality of recall during revision."""
    PERFECT = "perfect"  # Recalled everything
    GOOD = "good"  # Minor gaps
    AVERAGE = "average"  # Some effort needed
    POOR = "poor"  # Significant difficulty
    FAILED = "failed"  # Could not recall


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class RevisionHistory(BaseModel):
    """
    Individual revision attempt (embedded).
    Max 10 history entries per revision item.
    """
    
    revision_date: date = Field(
        ...,
        description="Date of revision"
    )
    cycle_day: int = Field(
        ...,
        description="Which cycle day (1, 3, 7, 21)"
    )
    status: RevisionStatus = Field(
        ...,
        description="Status of this revision"
    )
    quality: Optional[RevisionQuality] = Field(
        default=None,
        description="Recall quality"
    )
    duration_minutes: int = Field(
        default=0,
        ge=0,
        description="Time spent on revision"
    )
    was_rescheduled: bool = Field(
        default=False,
        description="Whether this was a rescheduled revision"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Revision notes"
    )


class TopicRevisionProgress(BaseModel):
    """
    Topic-level revision progress (embedded).
    Max 20 topics per revision item.
    """
    
    topic_name: str = Field(
        ...,
        max_length=200,
        description="Topic name"
    )
    is_revised: bool = Field(
        default=False,
        description="Whether topic was revised"
    )
    confidence_level: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Confidence percentage"
    )


# -----------------------------------------------------------------------------
# Main Revision Model
# -----------------------------------------------------------------------------

class RevisionModel(MongoBaseModel):
    """
    Revision schedule document.
    
    Collection: revisions
    
    Indexes:
    - user_id
    - (user_id, chapter_id) unique compound
    - next_revision_date
    - (user_id, next_revision_date) compound
    - (user_id, status) compound
    - status
    """
    
    # References
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    chapter_id: PyObjectId = Field(
        ...,
        description="Reference to chapter"
    )
    subject_id: PyObjectId = Field(
        ...,
        description="Reference to subject (denormalized)"
    )
    
    # Denormalized info for quick access
    chapter_name: str = Field(
        ...,
        max_length=200,
        description="Chapter name"
    )
    subject_name: str = Field(
        ...,
        max_length=100,
        description="Subject name"
    )
    
    # Learning reference
    original_learning_date: date = Field(
        ...,
        description="When chapter was first learned"
    )
    learning_task_id: Optional[str] = Field(
        default=None,
        description="Reference to original learning task"
    )
    
    # Current cycle status
    current_cycle_day: int = Field(
        default=1,
        description="Current revision cycle (1, 3, 7, 21)"
    )
    next_revision_date: date = Field(
        ...,
        description="Next scheduled revision date"
    )
    status: RevisionStatus = Field(
        default=RevisionStatus.SCHEDULED,
        description="Current status"
    )
    
    # Completion tracking
    cycles_completed: int = Field(
        default=0,
        ge=0,
        le=4,
        description="Number of cycles completed (max 4)"
    )
    is_mastered: bool = Field(
        default=False,
        description="Completed all 4 cycles"
    )
    
    # Missed tracking
    missed_count: int = Field(
        default=0,
        ge=0,
        description="Number of missed revisions"
    )
    consecutive_misses: int = Field(
        default=0,
        ge=0,
        description="Consecutive missed revisions"
    )
    last_missed_date: Optional[date] = Field(
        default=None,
        description="Last missed revision date"
    )
    
    # Revision history (bounded, max 10)
    history: list[RevisionHistory] = Field(
        default_factory=list,
        max_length=10,
        description="Revision attempt history"
    )
    
    # Topic-level progress (bounded, max 20)
    topic_progress: list[TopicRevisionProgress] = Field(
        default_factory=list,
        max_length=20,
        description="Topic-wise revision progress"
    )
    
    # Metrics
    average_recall_quality: Optional[float] = Field(
        default=None,
        ge=0,
        le=5,
        description="Average recall quality score (1-5)"
    )
    total_revision_minutes: int = Field(
        default=0,
        ge=0,
        description="Total time spent on revisions"
    )
    
    # Priority
    priority_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority for scheduling (1=highest)"
    )
    is_high_priority: bool = Field(
        default=False,
        description="Flagged as high priority"
    )
    
    # AI recommendations
    ai_confidence_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="AI-predicted mastery confidence"
    )
    recommended_extra_revision: bool = Field(
        default=False,
        description="AI recommends additional revision"
    )
    
    def calculate_next_revision_date(self, from_date: date = None) -> date:
        """Calculate next revision date based on current cycle."""
        base_date = from_date or date.today()
        
        # Get next cycle day
        cycle_days = SPACED_REPETITION_DAYS
        current_idx = cycle_days.index(self.current_cycle_day) if self.current_cycle_day in cycle_days else 0
        
        if current_idx < len(cycle_days) - 1:
            next_cycle = cycle_days[current_idx + 1]
            days_until = next_cycle - self.current_cycle_day
        else:
            # All cycles complete
            days_until = 30  # Monthly review
        
        return base_date + timedelta(days=days_until)
    
    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Check if revision is overdue."""
        return self.next_revision_date < date.today() and self.status != RevisionStatus.COMPLETED


# -----------------------------------------------------------------------------
# Revision Schedule Summary (for dashboard)
# -----------------------------------------------------------------------------

class RevisionScheduleSummary(BaseModel):
    """Summary of pending revisions for a user."""
    
    user_id: PyObjectId
    date: date
    
    due_today: int = Field(default=0, ge=0)
    overdue_count: int = Field(default=0, ge=0)
    upcoming_week: int = Field(default=0, ge=0)
    
    high_priority_count: int = Field(default=0, ge=0)
    
    # Subject-wise breakdown (max 10)
    by_subject: dict[str, int] = Field(
        default_factory=dict,
        description="Count by subject name"
    )


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------

class RevisionCreateDTO(BaseModel):
    """DTO for creating a revision schedule."""
    
    chapter_id: PyObjectId
    subject_id: PyObjectId
    chapter_name: str
    subject_name: str
    original_learning_date: date
    learning_task_id: Optional[str] = None


class RevisionUpdateDTO(BaseModel):
    """DTO for updating revision after completion."""
    
    status: RevisionStatus
    quality: RevisionQuality
    duration_minutes: int = 0
    notes: Optional[str] = None
