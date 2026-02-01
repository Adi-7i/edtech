"""
Study Profile Schemas

Pydantic request/response models for:
- Study profile management
- Subject management
- Chapter management
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.database.models.study_profile import (
    DailyAvailability,
    ExamCategory,
    PreferredTimeSlot,
    StrengthLevel,
    StudyPreferences,
)


# -----------------------------------------------------------------------------
# Profile Schemas
# -----------------------------------------------------------------------------

class StudyProfileCreateRequest(BaseModel):
    """Request schema for creating a study profile."""
    
    # Exam information
    exam_type: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Target exam name (e.g., 'JEE Main', 'NEET')",
        examples=["JEE Main", "NEET", "CBSE Class 12", "SSC CGL"]
    )
    exam_category: ExamCategory = Field(
        default=ExamCategory.OTHER,
        description="Category of the target exam"
    )
    exam_date: date = Field(
        ...,
        description="Target exam date (must be in future)"
    )
    
    # Daily study hours (simple format for initial setup)
    daily_study_hours: float = Field(
        default=4.0,
        ge=0.5,
        le=16.0,
        description="Average daily study hours available"
    )
    
    # Detailed availability (optional, for advanced setup)
    daily_availability: Optional[DailyAvailability] = Field(
        default=None,
        description="Detailed weekly availability (optional)"
    )
    
    # Preferred time slot (optional)
    preferred_time_slot: Optional[PreferredTimeSlot] = Field(
        default=None,
        description="Preferred study time slot"
    )
    
    # Study preferences (optional)
    preferences: Optional[StudyPreferences] = Field(
        default=None,
        description="Detailed study preferences"
    )
    
    @field_validator("exam_date")
    @classmethod
    def validate_exam_date_future(cls, v: date) -> date:
        """Validate that exam date is in the future."""
        if v <= date.today():
            raise ValueError("Exam date must be in the future")
        return v
    
    @field_validator("daily_study_hours")
    @classmethod
    def validate_study_hours(cls, v: float) -> float:
        """Validate study hours are realistic."""
        if v < 0.5:
            raise ValueError("Daily study hours must be at least 0.5")
        if v > 16:
            raise ValueError("Daily study hours cannot exceed 16")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "exam_type": "NEET",
                "exam_category": "medical",
                "exam_date": "2026-05-15",
                "daily_study_hours": 6.0
            }
        }


class StudyProfileUpdateRequest(BaseModel):
    """Request schema for updating a study profile."""
    
    exam_type: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=50,
        description="Target exam name"
    )
    exam_category: Optional[ExamCategory] = Field(
        default=None,
        description="Category of the target exam"
    )
    exam_date: Optional[date] = Field(
        default=None,
        description="Target exam date"
    )
    daily_study_hours: Optional[float] = Field(
        default=None,
        ge=0.5,
        le=16.0,
        description="Average daily study hours"
    )
    daily_availability: Optional[DailyAvailability] = Field(
        default=None,
        description="Detailed weekly availability"
    )
    preferred_time_slot: Optional[PreferredTimeSlot] = Field(
        default=None,
        description="Preferred study time slot"
    )
    preferences: Optional[StudyPreferences] = Field(
        default=None,
        description="Detailed study preferences"
    )
    
    @field_validator("exam_date")
    @classmethod
    def validate_exam_date_future(cls, v: Optional[date]) -> Optional[date]:
        """Validate that exam date is in the future if provided."""
        if v is not None and v <= date.today():
            raise ValueError("Exam date must be in the future")
        return v


class StudyProfileResponse(BaseModel):
    """Response schema for study profile."""
    
    id: str = Field(..., description="Profile ID")
    user_id: str = Field(..., description="Owner user ID")
    
    # Exam info
    exam_type: str
    exam_category: str
    exam_date: str
    days_until_exam: int
    
    # Study hours
    daily_study_hours: float
    weekly_study_hours: float
    
    # Availability
    daily_availability: Optional[DailyAvailability] = None
    preferred_time_slot: Optional[PreferredTimeSlot] = None
    
    # Preferences
    preferences: Optional[StudyPreferences] = None
    
    # Status
    is_complete: bool
    current_phase: str
    
    # Timestamps
    created_at: str
    updated_at: Optional[str] = None


# -----------------------------------------------------------------------------
# Subject Schemas
# -----------------------------------------------------------------------------

class SubjectAddRequest(BaseModel):
    """Request schema for adding subjects to profile."""
    
    subject_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=15,
        description="List of subject IDs to add"
    )


class SubjectUpdateRequest(BaseModel):
    """Request schema for updating a user subject."""
    
    is_enabled: Optional[bool] = Field(
        default=None,
        description="Enable/disable subject"
    )
    priority: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Subject priority (1=highest)"
    )
    strength: Optional[StrengthLevel] = Field(
        default=None,
        description="Overall subject strength"
    )
    target_completion_percentage: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Target completion percentage"
    )


class SubjectResponse(BaseModel):
    """Response schema for user subject."""
    
    id: str = Field(..., description="User subject ID")
    subject_id: str = Field(..., description="Master subject ID")
    subject_name: str
    subject_code: Optional[str] = None
    
    is_enabled: bool
    priority: int
    strength: str
    
    # Progress
    chapters_total: int = 0
    chapters_completed: int = 0
    completion_percentage: float = 0.0
    
    created_at: str


# -----------------------------------------------------------------------------
# Chapter Schemas
# -----------------------------------------------------------------------------

class ChapterAddRequest(BaseModel):
    """Request schema for adding chapters to a subject."""
    
    chapter_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of chapter IDs to add"
    )


class ChapterUpdateRequest(BaseModel):
    """Request schema for updating a user chapter."""
    
    strength: Optional[StrengthLevel] = Field(
        default=None,
        description="Chapter strength (weak/medium/strong)"
    )
    estimated_hours: Optional[float] = Field(
        default=None,
        ge=0.5,
        le=50.0,
        description="Estimated hours to complete"
    )
    is_completed: Optional[bool] = Field(
        default=None,
        description="Mark chapter as completed"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Personal notes for the chapter"
    )


class ChapterResponse(BaseModel):
    """Response schema for user chapter."""
    
    id: str = Field(..., description="User chapter ID")
    chapter_id: str = Field(..., description="Master chapter ID")
    subject_id: str = Field(..., description="Parent subject ID")
    
    chapter_name: str
    chapter_code: Optional[str] = None
    
    strength: str
    estimated_hours: float
    is_completed: bool
    
    # From master chapter
    difficulty: str
    importance_score: int
    
    notes: Optional[str] = None
    
    created_at: str
    last_studied_at: Optional[str] = None


# -----------------------------------------------------------------------------
# List Response Schemas
# -----------------------------------------------------------------------------

class SubjectListResponse(BaseModel):
    """Response schema for list of subjects."""
    
    subjects: List[SubjectResponse]
    total: int
    enabled_count: int


class ChapterListResponse(BaseModel):
    """Response schema for list of chapters."""
    
    chapters: List[ChapterResponse]
    total: int
    completed_count: int
    weak_count: int
