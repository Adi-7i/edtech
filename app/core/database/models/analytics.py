"""
Progress & Analytics Model for Smart Study Planner.

Collection: daily_analytics

Tracks student progress and performance:
- Daily study metrics
- Consistency scoring
- Exam readiness indicators
- Subject-wise progress

Design decisions:
- One document per user per date
- Aggregated metrics for dashboard efficiency
- Historical data for trend analysis

Indexes (to be created):
- (user_id, date) unique compound
- user_id
- date
- consistency_score (for leaderboards)
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from .base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class ReadinessLevel(str, Enum):
    """Exam readiness levels."""
    NOT_STARTED = "not_started"
    BEGINNER = "beginner"  # 0-25%
    DEVELOPING = "developing"  # 25-50%
    PROFICIENT = "proficient"  # 50-75%
    ADVANCED = "advanced"  # 75-90%
    EXAM_READY = "exam_ready"  # 90%+


class TrendDirection(str, Enum):
    """Trend direction indicators."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class SubjectProgress(BaseModel):
    """
    Subject-wise progress (embedded).
    Max 15 subjects per analytics document.
    """
    
    subject_id: PyObjectId = Field(
        ...,
        description="Reference to subject"
    )
    subject_name: str = Field(
        ...,
        max_length=100,
        description="Subject name"
    )
    
    # Time metrics
    study_minutes: int = Field(
        default=0,
        ge=0,
        description="Minutes studied today"
    )
    
    # Progress metrics
    chapters_covered: int = Field(
        default=0,
        ge=0,
        description="Chapters addressed today"
    )
    tasks_completed: int = Field(
        default=0,
        ge=0,
        description="Tasks completed today"
    )
    
    # Performance
    accuracy_percentage: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Practice accuracy today"
    )


class StudySessionMetrics(BaseModel):
    """Study session aggregates for the day (embedded)."""
    
    total_sessions: int = Field(
        default=0,
        ge=0,
        description="Number of study sessions"
    )
    average_session_minutes: float = Field(
        default=0.0,
        ge=0,
        description="Average session duration"
    )
    longest_session_minutes: int = Field(
        default=0,
        ge=0,
        description="Longest session"
    )
    
    # Focus metrics
    total_focused_minutes: int = Field(
        default=0,
        ge=0,
        description="Minutes without distraction"
    )
    distraction_count: int = Field(
        default=0,
        ge=0,
        description="Total distractions"
    )


class WeeklySnapshot(BaseModel):
    """Weekly aggregated metrics (embedded in weekly analytics)."""
    
    week_start: date = Field(
        ...,
        description="Start of the week (Monday)"
    )
    total_study_minutes: int = Field(default=0, ge=0)
    total_tasks_completed: int = Field(default=0, ge=0)
    average_daily_minutes: float = Field(default=0.0, ge=0)
    active_days: int = Field(default=0, ge=0, le=7)
    
    consistency_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Weekly consistency score"
    )
    
    # Best day
    best_day: Optional[str] = Field(
        default=None,
        description="Most productive day of week"
    )
    best_day_minutes: int = Field(default=0, ge=0)


# -----------------------------------------------------------------------------
# Main Daily Analytics Model
# -----------------------------------------------------------------------------

class DailyAnalyticsModel(MongoBaseModel):
    """
    Daily analytics document.
    
    Collection: daily_analytics
    
    Indexes:
    - (user_id, date) unique compound
    - user_id
    - date (for cleanup/archival)
    - consistency_score
    """
    
    # User reference
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    
    # Analytics date
    analytics_date: date = Field(
        ...,
        description="Date of analytics"
    )
    
    # Time metrics
    study_minutes: int = Field(
        default=0,
        ge=0,
        description="Total study minutes today"
    )
    planned_minutes: int = Field(
        default=0,
        ge=0,
        description="Originally planned minutes"
    )
    break_minutes: int = Field(
        default=0,
        ge=0,
        description="Break time taken"
    )
    
    # Task metrics
    tasks_planned: int = Field(default=0, ge=0)
    tasks_completed: int = Field(default=0, ge=0)
    tasks_partial: int = Field(default=0, ge=0)
    tasks_missed: int = Field(default=0, ge=0)
    
    # Revision metrics
    revisions_due: int = Field(default=0, ge=0)
    revisions_completed: int = Field(default=0, ge=0)
    
    # Session metrics (embedded)
    session_metrics: StudySessionMetrics = Field(
        default_factory=StudySessionMetrics,
        description="Study session aggregates"
    )
    
    # Subject progress (bounded, max 15)
    subject_progress: list[SubjectProgress] = Field(
        default_factory=list,
        max_length=15,
        description="Subject-wise progress"
    )
    
    # Scores
    consistency_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Daily consistency score (0-100)"
    )
    productivity_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Daily productivity score"
    )
    
    # Exam readiness
    exam_readiness_percentage: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Overall exam readiness percentage"
    )
    readiness_level: ReadinessLevel = Field(
        default=ReadinessLevel.NOT_STARTED,
        description="Readiness level category"
    )
    
    # Trends (compared to 7-day average)
    study_time_trend: TrendDirection = Field(
        default=TrendDirection.STABLE,
        description="Study time trend"
    )
    productivity_trend: TrendDirection = Field(
        default=TrendDirection.STABLE,
        description="Productivity trend"
    )
    
    # Streak tracking
    current_streak_days: int = Field(
        default=0,
        ge=0,
        description="Current study streak"
    )
    longest_streak_days: int = Field(
        default=0,
        ge=0,
        description="Longest streak ever"
    )
    
    # Goal achievement
    daily_goal_met: bool = Field(
        default=False,
        description="Whether daily goal was met"
    )
    goal_completion_percentage: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Percentage of daily goal completed"
    )
    
    # AI insights (max 5)
    ai_insights: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="AI-generated insights for the day"
    )
    
    @computed_field
    @property
    def task_completion_rate(self) -> float:
        """Calculate task completion rate."""
        if self.tasks_planned == 0:
            return 0.0
        return round((self.tasks_completed / self.tasks_planned) * 100, 1)
    
    @computed_field
    @property
    def time_efficiency(self) -> float:
        """Calculate time efficiency (actual vs planned)."""
        if self.planned_minutes == 0:
            return 0.0
        return round((self.study_minutes / self.planned_minutes) * 100, 1)


# -----------------------------------------------------------------------------
# User Progress Summary Model (aggregated view)
# -----------------------------------------------------------------------------

class UserProgressSummaryModel(MongoBaseModel):
    """
    Aggregated user progress summary.
    Updated periodically (e.g., daily at midnight).
    
    Collection: user_progress_summaries
    
    Indexes:
    - user_id (unique)
    - exam_readiness_percentage (for rankings)
    """
    
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    
    # Overall metrics
    total_study_hours: float = Field(
        default=0.0,
        ge=0,
        description="Total lifetime study hours"
    )
    total_tasks_completed: int = Field(default=0, ge=0)
    total_chapters_covered: int = Field(default=0, ge=0)
    
    # Current metrics
    current_streak_days: int = Field(default=0, ge=0)
    longest_streak_days: int = Field(default=0, ge=0)
    
    # Averages (last 30 days)
    avg_daily_study_minutes: float = Field(default=0.0, ge=0)
    avg_consistency_score: float = Field(default=0.0, ge=0, le=100)
    avg_task_completion_rate: float = Field(default=0.0, ge=0, le=100)
    
    # Exam readiness
    exam_readiness_percentage: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Current exam readiness"
    )
    readiness_level: ReadinessLevel = Field(
        default=ReadinessLevel.NOT_STARTED
    )
    
    # Weekly snapshots (last 4 weeks)
    weekly_snapshots: list[WeeklySnapshot] = Field(
        default_factory=list,
        max_length=4,
        description="Last 4 weeks summary"
    )
    
    # Achievements/milestones (max 20)
    achievements: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Earned achievement codes"
    )
    
    # Last activity
    last_study_date: Optional[date] = Field(
        default=None,
        description="Last active study date"
    )
    
    # Rankings (if enabled)
    percentile_rank: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentile among peers"
    )


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------

class DailyAnalyticsCreateDTO(BaseModel):
    """DTO for creating daily analytics."""
    
    analytics_date: date
    study_minutes: int = 0
    planned_minutes: int = 0


class ProgressQueryDTO(BaseModel):
    """DTO for querying progress data."""
    
    start: date
    end: date
    include_subjects: bool = True
