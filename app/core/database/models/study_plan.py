"""
Study Plan Database Models

Defines the database models for:
- StudyPlan: Overall plan metadata
- DailyPlan: Daily study schedule
- StudyTask: Individual study tasks within a day
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.database.models.base import MongoBaseModel, PyObjectId


class PlanStatus(str, Enum):
    """Status of a study plan."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    """Status of a study task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    MISSED = "missed"
    RESCHEDULED = "rescheduled"


class StudyTaskModel(MongoBaseModel):
    """
    Individual study task within a daily plan.
    
    Represents a single study session for a specific chapter.
    """
    # References
    daily_plan_id: PyObjectId = Field(..., description="Parent daily plan ID")
    plan_id: PyObjectId = Field(..., description="Overall study plan ID")
    user_id: PyObjectId = Field(..., description="Student user ID")
    profile_id: PyObjectId = Field(..., description="Study profile ID")
    
    subject_id: PyObjectId = Field(..., description="User subject ID")
    chapter_id: PyObjectId = Field(..., description="User chapter ID")
    
    # Task details
    subject_name: str = Field(..., description="Subject name (denormalized)")
    chapter_name: str = Field(..., description="Chapter name (denormalized)")
    
    # Time allocation
    allocated_hours: float = Field(..., ge=0.5, le=8.0, description="Allocated study hours")
    actual_hours: Optional[float] = Field(default=None, ge=0, description="Actual time spent")
    
    # Priority & strength
    priority_weight: float = Field(..., ge=1.0, le=3.0, description="Priority score (3=weak, 1=strong)")
    chapter_strength: str = Field(..., description="weak/medium/strong")
    
    # Status tracking
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    is_completed: bool = Field(default=False)
    completed_at: Optional[datetime] = None
    
    # Sequencing
    order_in_day: int = Field(..., ge=1, description="Order within the day (1=first)")
    
    # Notes
    notes: Optional[str] = Field(default=None, max_length=500)
    
    class Settings:
        name = "study_tasks"
        indexes = [
            "daily_plan_id",
            "plan_id",
            "user_id",
            "chapter_id",
            [("user_id", 1), ("status", 1)],
            [("daily_plan_id", 1), ("order_in_day", 1)],
        ]


class DailyPlanModel(MongoBaseModel):
    """
    Study plan for a specific date.
    
    Contains all study tasks scheduled for that day.
    """
    # References
    plan_id: PyObjectId = Field(..., description="Parent study plan ID")
    user_id: PyObjectId = Field(..., description="Student user ID")
    profile_id: PyObjectId = Field(..., description="Study profile ID")
    
    # Date
    plan_date: date = Field(..., description="Plan date (YYYY-MM-DD)")
    
    # Time allocation
    total_allocated_hours: float = Field(..., ge=0, description="Total hours allocated for this day")
    daily_limit_hours: float = Field(..., ge=0, description="Student's daily study hour limit")
    
    # Task references (for quick count)
    task_count: int = Field(default=0, ge=0, description="Number of tasks for this day")
    completed_task_count: int = Field(default=0, ge=0, description="Number of completed tasks")
    
    # Status
    is_fully_completed: bool = Field(default=False)
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Notes
    notes: Optional[str] = Field(default=None, max_length=500)
    
    class Settings:
        name = "daily_plans"
        indexes = [
            "plan_id",
            "user_id",
            "plan_date",
            [("user_id", 1), ("plan_date", 1)],
            [("plan_id", 1), ("plan_date", 1)],
        ]


class StudyPlanModel(MongoBaseModel):
    """
    Overall study plan metadata.
    
    Represents a complete study plan from generation to exam date.
    """
    # References
    user_id: PyObjectId = Field(..., description="Student user ID")
    profile_id: PyObjectId = Field(..., description="Study profile ID")
    
    # Exam information
    exam_type: str = Field(..., description="Target exam type")
    exam_date: date = Field(..., description="Exam date")
    
    # Plan timeline
    plan_start_date: date = Field(..., description="Plan start date")
    plan_end_date: date = Field(..., description="Plan end date (1 day before exam)")
    total_days: int = Field(..., ge=1, description="Total days in plan")
    
    # Subject/Chapter info
    total_subjects: int = Field(..., ge=1, description="Number of subjects in plan")
    total_chapters: int = Field(..., ge=1, description="Number of chapters in plan")
    
    # Time allocation
    daily_study_hours: float = Field(..., ge=0.5, description="Average daily study hours")
    total_allocated_hours: float = Field(..., ge=0, description="Total hours allocated across plan")
    
    # Status
    status: PlanStatus = Field(default=PlanStatus.ACTIVE)
    is_active: bool = Field(default=True, description="Only one active plan per user")
    
    # Progress tracking
    completed_tasks: int = Field(default=0, ge=0)
    total_tasks: int = Field(default=0, ge=0)
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Metadata
    generation_algorithm_version: str = Field(default="v1.0", description="Algorithm version used")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: Optional[datetime] = None
    
    class Settings:
        name = "study_plans"
        indexes = [
            "user_id",
            "profile_id",
            "status",
            [("user_id", 1), ("is_active", 1)],
            [("user_id", 1), ("status", 1)],
        ]
