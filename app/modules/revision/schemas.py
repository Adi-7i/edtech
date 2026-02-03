"""
Revision Schemas

Request and response models for revision API endpoints.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.database.models.revision import RevisionQuality, RevisionStatus


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------

class ScheduleRevisionRequest(BaseModel):
    """Request to schedule revisions for a completed chapter."""
    
    chapter_id: str = Field(..., description="User chapter ID")
    force_reschedule: bool = Field(
        default=False,
        description="Force rescheduling even if revisions exist"
    )


class UpdateRevisionStatusRequest(BaseModel):
    """Request to update revision status after attempt."""
    
    status: RevisionStatus = Field(..., description="New status")
    quality: Optional[RevisionQuality] = Field(
        default=None,
        description="Recall quality (required if status=completed)"
    )
    duration_minutes: int = Field(
        default=0,
        ge=0,
        le=480,
        description="Time spent on revision (0-480 minutes)"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional revision notes"
    )


# -----------------------------------------------------------------------------
# Response Schemas
# -----------------------------------------------------------------------------

class ChapterInfo(BaseModel):
    """Embedded chapter information in revision response."""
    
    id: str
    name: str
    subject_id: str
    subject_name: str
    strength: str


class RevisionResponse(BaseModel):
    """Single revision schedule response."""
    
    id: str
    chapter: ChapterInfo
    
    # Cycle info
    current_cycle_day: int
    next_revision_date: str
    status: str
    
    # Progress
    cycles_completed: int
    is_mastered: bool
    
    # Metrics
    missed_count: int
    consecutive_misses: int
    average_recall_quality: Optional[float] = None
    
    # Priority
    priority_score: int
    is_high_priority: bool
    is_overdue: bool
    days_until_due: int


class RevisionScheduleResponse(BaseModel):
    """Response after scheduling revisions for a chapter."""
    
    revision_id: str
    chapter_id: str
    chapter_name: str
    
    original_learning_date: str
    next_revision_date: str
    current_cycle_day: int
    
    message: str


class DailyRevisionsResponse(BaseModel):
    """Response for daily revisions fetch."""
    
    date: str
    revisions: List[RevisionResponse]
    
    # Counts
    total_revisions: int
    due_today: int
    overdue: int
    completed_today: int
    
    # Summary
    priority_order: str = "weak_chapters_first"
    auto_rescheduled_count: int = 0


class RevisionStatsResponse(BaseModel):
    """User's overall revision statistics."""
    
    total_chapters_with_revisions: int
    total_mastered: int
    total_in_progress: int
    
    due_today: int
    due_this_week: int
    overdue_count: int
    
    average_recall_quality: Optional[float] = None
    total_revision_time_minutes: int
