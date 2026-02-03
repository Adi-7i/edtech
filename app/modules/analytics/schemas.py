"""
Analytics Schemas

Request and response models for analytics API endpoints.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Component Models
# -----------------------------------------------------------------------------

class DailyTaskSummary(BaseModel):
    """Daily task execution summary."""
    
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    planned_tasks: int = Field(..., ge=0, description="Total tasks planned for the day")
    completed_tasks: int = Field(..., ge=0, description="Tasks completed fully")
    partial_tasks: int = Field(..., ge=0, description="Tasks partially completed")
    missed_tasks: int = Field(..., ge=0, description="Tasks missed or not attempted")
    planned_minutes: int = Field(..., ge=0, description="Total planned study minutes")
    actual_minutes: int = Field(..., ge=0, description="Actual study minutes logged")
    completion_percentage: float = Field(..., ge=0, le=100, description="Task completion %")


class ConsistencyMetrics(BaseModel):
    """Consistency tracking metrics."""
    
    score: int = Field(..., ge=0, le=100, description="Consistency score (0-100)")
    current_streak: int = Field(..., ge=0, description="Current consecutive study days")
    longest_streak: int = Field(..., ge=0, description="All-time longest streak")
    total_study_days: int = Field(..., ge=0, description="Total days with study activity")
    total_days: int = Field(..., ge=0, description="Days since profile creation")
    missed_days: int = Field(..., ge=0, description="Days with no study activity")
    partial_days: int = Field(..., ge=0, description="Days with partial completion")


class SubjectProgress(BaseModel):
    """Progress for a single subject."""
    
    subject_id: str
    subject_name: str
    total_chapters: int = Field(..., ge=0)
    completed_chapters: int = Field(..., ge=0)
    coverage_percentage: float = Field(..., ge=0, le=100)
    weak_chapters: int = Field(..., ge=0)
    medium_chapters: int = Field(..., ge=0)
    strong_chapters: int = Field(..., ge=0)
    revised_chapters: int = Field(..., ge=0, description="Chapters with at least one revision")
    revision_coverage: float = Field(..., ge=0, le=100, description="% of completed chapters revised")
    completion_status: str = Field(..., description="not_started, in_progress, or completed")


class ExamReadiness(BaseModel):
    """Exam readiness indicator with honest assessment."""
    
    score: int = Field(..., ge=0, le=100, description="Overall readiness score (0-100)")
    syllabus_coverage: float = Field(..., ge=0, le=100, description="% of syllabus covered")
    revision_completion: float = Field(..., ge=0, le=100, description="% of revisions completed")
    days_until_exam: int = Field(..., description="Days remaining (negative if past)")
    weak_chapter_count: int = Field(..., ge=0, description="Number of weak chapters")
    total_chapters: int = Field(..., ge=0, description="Total chapters across all subjects")
    is_ready: bool = Field(..., description="True if score >= 80")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------

class DailyAnalyticsResponse(BaseModel):
    """Response for GET /analytics/daily."""
    
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    task_summary: DailyTaskSummary
    study_minutes: int = Field(..., ge=0, description="Actual study time for the day")
    consistency_maintained: bool = Field(
        ...,
        description="True if >= 70% completion rate for the day"
    )
    has_plan: bool = Field(..., description="True if a study plan exists for this date")


class WeeklyAnalyticsResponse(BaseModel):
    """Response for GET /analytics/weekly."""
    
    week_start: str = Field(..., description="Week start date (YYYY-MM-DD)")
    week_end: str = Field(..., description="Week end date (YYYY-MM-DD)")
    daily_summaries: List[DailyTaskSummary] = Field(
        ...,
        description="Daily summaries for each day of the week"
    )
    total_study_minutes: int = Field(..., ge=0, description="Total study time for the week")
    average_completion_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="Average task completion % across the week"
    )
    consistency_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Consistency score for this week"
    )
    active_days: int = Field(
        ...,
        ge=0,
        le=7,
        description="Number of days with study activity"
    )


class OverviewAnalyticsResponse(BaseModel):
    """Response for GET /analytics/overview."""
    
    consistency: ConsistencyMetrics
    exam_readiness: ExamReadiness
    subjects: List[SubjectProgress]
    overall_progress: float = Field(
        ...,
        ge=0,
        le=100,
        description="Overall syllabus coverage across all subjects"
    )
    total_study_hours: float = Field(..., ge=0, description="Total hours studied (all time)")
    exam_date: str = Field(..., description="Target exam date (YYYY-MM-DD)")
    analytics_frozen: bool = Field(
        ...,
        description="True if exam date has passed (analytics frozen)"
    )
    profile_created_date: str = Field(..., description="Profile creation date")


# -----------------------------------------------------------------------------
# Internal DTOs (not exposed via API)
# -----------------------------------------------------------------------------

class StudyStreakData(BaseModel):
    """Internal model for study streak tracking."""
    
    current_streak: int
    longest_streak: int
    total_study_days: int
    partial_days: int


class SubjectStatistics(BaseModel):
    """Internal model for subject statistics."""
    
    total_chapters: int
    completed_chapters: int
    weak_count: int
    medium_count: int
    strong_count: int
    revised_count: int
