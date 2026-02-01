"""
Study Profile Module Models

User-specific models for study configuration:
- UserSubjectModel: User's subject configuration
- UserChapterModel: User's chapter status and strength
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from app.core.database.models.base import MongoBaseModel, PyObjectId
from app.core.database.models.study_profile import StrengthLevel


# -----------------------------------------------------------------------------
# User Subject Model
# -----------------------------------------------------------------------------

class UserSubjectModel(MongoBaseModel):
    """
    User's subject configuration.
    
    Collection: user_subjects
    
    Links a user's study profile to a master subject with
    personal settings like priority and enabled status.
    
    Indexes:
    - (profile_id, subject_id) unique compound
    - profile_id
    - is_enabled
    """
    
    # Parent references
    profile_id: PyObjectId = Field(
        ...,
        description="Reference to user's study profile"
    )
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user (denormalized for queries)"
    )
    subject_id: PyObjectId = Field(
        ...,
        description="Reference to master subject"
    )
    
    # Denormalized subject info for quick access
    subject_name: str = Field(
        ...,
        description="Subject name (from master)"
    )
    subject_code: Optional[str] = Field(
        default=None,
        description="Subject code (from master)"
    )
    exam_id: PyObjectId = Field(
        ...,
        description="Reference to exam (from master)"
    )
    
    # User configuration
    is_enabled: bool = Field(
        default=True,
        description="Whether subject is enabled for study"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Study priority (1=highest)"
    )
    strength: StrengthLevel = Field(
        default=StrengthLevel.MEDIUM,
        description="Overall subject strength"
    )
    
    # Progress tracking
    chapters_total: int = Field(
        default=0,
        ge=0,
        description="Total chapters in subject"
    )
    chapters_completed: int = Field(
        default=0,
        ge=0,
        description="Chapters marked as completed"
    )
    
    # Target
    target_completion_percentage: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Target completion percentage"
    )
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.chapters_total == 0:
            return 0.0
        return round((self.chapters_completed / self.chapters_total) * 100, 1)


# -----------------------------------------------------------------------------
# User Chapter Model
# -----------------------------------------------------------------------------

class UserChapterModel(MongoBaseModel):
    """
    User's chapter status and strength.
    
    Collection: user_chapters
    
    Links a user to a master chapter with personal
    strength assessment and progress tracking.
    
    Indexes:
    - (profile_id, chapter_id) unique compound
    - (profile_id, user_subject_id)
    - (profile_id, strength) for filtering weak chapters
    - profile_id
    """
    
    # Parent references
    profile_id: PyObjectId = Field(
        ...,
        description="Reference to user's study profile"
    )
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user (denormalized)"
    )
    user_subject_id: PyObjectId = Field(
        ...,
        description="Reference to user subject"
    )
    
    # Master references
    chapter_id: PyObjectId = Field(
        ...,
        description="Reference to master chapter"
    )
    subject_id: PyObjectId = Field(
        ...,
        description="Reference to master subject (denormalized)"
    )
    
    # Denormalized chapter info
    chapter_name: str = Field(
        ...,
        description="Chapter name (from master)"
    )
    chapter_code: Optional[str] = Field(
        default=None,
        description="Chapter code (from master)"
    )
    difficulty: str = Field(
        default="medium",
        description="Chapter difficulty (from master)"
    )
    importance_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Importance score (from master)"
    )
    
    # User assessment
    strength: StrengthLevel = Field(
        default=StrengthLevel.MEDIUM,
        description="User's strength in this chapter"
    )
    estimated_hours: float = Field(
        default=2.0,
        ge=0.5,
        le=50.0,
        description="Estimated hours to complete (user can override)"
    )
    
    # Progress
    is_completed: bool = Field(
        default=False,
        description="Whether chapter is marked complete"
    )
    completion_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Chapter completion percentage"
    )
    
    # Study tracking
    total_study_minutes: int = Field(
        default=0,
        ge=0,
        description="Total minutes spent on chapter"
    )
    last_studied_at: Optional[datetime] = Field(
        default=None,
        description="Last study session timestamp"
    )
    
    # Revision tracking
    revision_count: int = Field(
        default=0,
        ge=0,
        description="Number of revisions completed"
    )
    next_revision_date: Optional[datetime] = Field(
        default=None,
        description="Next scheduled revision date"
    )
    
    # Notes
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Personal notes for the chapter"
    )
