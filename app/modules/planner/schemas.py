"""
Planner Schemas

Request and response models for the Study Planner API.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Task Schemas
# -----------------------------------------------------------------------------

class StudyTaskResponse(BaseModel):
    """Response schema for a study task."""
    
    id: str = Field(..., description="Task ID")
    
    # Subject and chapter
    subject_id: str
    chapter_id: str
    subject_name: str
    chapter_name: str
    
    # Time
    allocated_hours: float
    actual_hours: Optional[float] = None
    
    # Priority
    priority_weight: float
    chapter_strength: str
    order_in_day: int
    
    # Status
    status: str
    is_completed: bool
    completed_at: Optional[str] = None
    
    # Notes
    notes: Optional[str] = None


# -----------------------------------------------------------------------------
# Daily Plan Schemas
# -----------------------------------------------------------------------------

class DailyPlanResponse(BaseModel):
    """Response schema for a daily study plan."""
    
    id: str = Field(..., description="Daily plan ID")
    date: str = Field(..., description="Plan date (YYYY-MM-DD)")
    
    # Time allocation
    total_allocated_hours: float
    daily_limit_hours: float
    utilization_percentage: float = Field(
        ..., 
        description="Percentage of daily limit used"
    )
    
    # Tasks
    tasks: List[StudyTaskResponse] = Field(default_factory=list)
    task_count: int
    completed_task_count: int
    
    # Status
    is_fully_completed: bool
    completion_percentage: float
    
    notes: Optional[str] = None


# -----------------------------------------------------------------------------
# Plan Schemas
# -----------------------------------------------------------------------------

class PlanGenerateRequest(BaseModel):
    """Request to generate a new study plan."""
    
    # Optional: allow regeneration parameters
    force_regenerate: bool = Field(
        default=False,
        description="Force regenerate even if active plan exists"
    )
    
    # Optional: custom preferences
    prioritize_weak_only: bool = Field(
        default=False,
        description="Only focus on weak chapters"
    )
    
    buffer_days: int = Field(
        default=0,
        ge=0,
        le=7,
        description="Stop planning N days before exam (for final revision)"
    )


class PlanSummaryResponse(BaseModel):
    """Summary information about a study plan."""
    
    id: str = Field(..., description="Plan ID")
    
    # Timeline
    exam_date: str
    plan_start_date: str
    plan_end_date: str
    total_days: int
    days_completed: int
    days_remaining: int
    
    # Content
    total_subjects: int
    total_chapters: int
    total_tasks: int
    completed_tasks: int
    
    # Progress
    completion_percentage: float
    
    # Time
    daily_study_hours: float
    total_allocated_hours: float
    
    # Status
    status: str
    is_active: bool
    
    # Metadata
    generated_at: str


class PlanResponse(BaseModel):
    """Full plan response with summary and upcoming days."""
    
    plan: PlanSummaryResponse
    upcoming_days: List[DailyPlanResponse] = Field(
        default_factory=list,
        description="Next 7 days of daily plans"
    )


# -----------------------------------------------------------------------------
# Preview Schema
# -----------------------------------------------------------------------------

class PlanPreviewResponse(BaseModel):
    """Preview of what would be generated without saving."""
    
    # Timeline
    exam_date: str
    plan_start_date: str
    plan_end_date: str
    total_days: int
    
    # Content
    total_subjects: int
    total_chapters: int
    estimated_total_tasks: int
    
    # Breakdown by strength
    weak_chapters: int
    medium_chapters: int
    strong_chapters: int
    
    # Time analysis
    daily_study_hours: float
    total_hours_needed: float
    total_hours_available: float
    time_buffer_percentage: float = Field(
        ...,
        description="Percentage of buffer time (positive = comfortable, negative = tight)"
    )
    
    # Warnings
    warnings: List[str] = Field(
        default_factory=list,
        description="Potential issues (e.g., insufficient time)"
    )
    
    feasibility_score: str = Field(
        ...,
        description="COMFORTABLE / TIGHT / CHALLENGING / UNFEASIBLE"
    )


# -----------------------------------------------------------------------------
# Update Schemas
# -----------------------------------------------------------------------------

class TaskUpdateRequest(BaseModel):
    """Request to update a task's status."""
    
    status: Optional[str] = Field(
        default=None,
        description="pending / in_progress / completed / missed"
    )
    actual_hours: Optional[float] = Field(default=None, ge=0, le=24)
    notes: Optional[str] = Field(default=None, max_length=500)


class TaskCompleteRequest(BaseModel):
    """Request to mark a task as completed."""
    
    actual_hours: float = Field(..., ge=0.1, le=24.0)
    notes: Optional[str] = Field(default=None, max_length=500)
