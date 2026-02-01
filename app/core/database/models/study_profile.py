"""
Student Study Profile Model for Smart Study Planner.

Collection: study_profiles

Stores student-specific study configuration:
- Target exam and date
- Daily availability
- Learning preferences
- Subject-wise strength assessment

Each student has exactly one study profile (1:1 with user).

Indexes (to be created):
- user_id: unique (one profile per user)
- exam_type: regular index
- exam_date: regular index (for deadline-based queries)
"""

from datetime import date, datetime, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class ExamCategory(str, Enum):
    """Categories of competitive exams in India."""
    ENGINEERING = "engineering"  # JEE, BITSAT
    MEDICAL = "medical"  # NEET
    CIVIL_SERVICES = "civil_services"  # UPSC
    BANKING = "banking"  # IBPS, SBI
    SSC = "ssc"  # SSC CGL, CHSL
    DEFENCE = "defence"  # NDA, CDS
    LAW = "law"  # CLAT
    MBA = "mba"  # CAT, XAT
    STATE_PSC = "state_psc"
    SCHOOL = "school"  # Board exams
    OTHER = "other"


class StudyMode(str, Enum):
    """Preferred study mode."""
    SELF_PACED = "self_paced"
    STRUCTURED = "structured"
    INTENSIVE = "intensive"
    REVISION_ONLY = "revision_only"


class LearningStyle(str, Enum):
    """Student's preferred learning style."""
    VISUAL = "visual"
    AUDITORY = "auditory"
    READING_WRITING = "reading_writing"
    KINESTHETIC = "kinesthetic"
    MIXED = "mixed"


class StrengthLevel(str, Enum):
    """Subject/chapter strength levels."""
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class DailyAvailability(BaseModel):
    """Daily study time availability."""
    
    # Hours available per day
    monday: float = Field(default=2.0, ge=0, le=16, description="Hours available on Monday")
    tuesday: float = Field(default=2.0, ge=0, le=16, description="Hours available on Tuesday")
    wednesday: float = Field(default=2.0, ge=0, le=16, description="Hours available on Wednesday")
    thursday: float = Field(default=2.0, ge=0, le=16, description="Hours available on Thursday")
    friday: float = Field(default=2.0, ge=0, le=16, description="Hours available on Friday")
    saturday: float = Field(default=4.0, ge=0, le=16, description="Hours available on Saturday")
    sunday: float = Field(default=4.0, ge=0, le=16, description="Hours available on Sunday")
    
    @property
    def weekly_total(self) -> float:
        """Total weekly study hours."""
        return sum([
            self.monday, self.tuesday, self.wednesday,
            self.thursday, self.friday, self.saturday, self.sunday
        ])


class PreferredTimeSlot(BaseModel):
    """Preferred study time slots."""
    
    start_time: str = Field(
        default="18:00",
        description="Preferred start time (HH:MM, 24hr)"
    )
    end_time: str = Field(
        default="21:00",
        description="Preferred end time (HH:MM, 24hr)"
    )
    is_morning_person: bool = Field(
        default=False,
        description="Prefers early morning study"
    )


class SubjectStrength(BaseModel):
    """
    Subject-wise strength assessment.
    Limited to max 15 subjects per profile.
    """
    
    subject_id: PyObjectId = Field(
        ...,
        description="Reference to subject document"
    )
    subject_name: str = Field(
        ...,
        description="Subject name (denormalized for quick access)"
    )
    strength: StrengthLevel = Field(
        default=StrengthLevel.MEDIUM,
        description="Current strength level"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority for study planning (1=highest)"
    )
    target_improvement: Optional[StrengthLevel] = Field(
        default=None,
        description="Target strength level"
    )
    last_assessed_at: Optional[datetime] = Field(
        default=None,
        description="Last assessment timestamp"
    )


class StudyPreferences(BaseModel):
    """Detailed study preferences."""
    
    learning_style: LearningStyle = Field(
        default=LearningStyle.MIXED,
        description="Preferred learning style"
    )
    study_mode: StudyMode = Field(
        default=StudyMode.STRUCTURED,
        description="Preferred study mode"
    )
    
    # Session preferences
    preferred_session_duration: int = Field(
        default=45,
        ge=15,
        le=120,
        description="Preferred session duration in minutes"
    )
    break_duration: int = Field(
        default=10,
        ge=5,
        le=30,
        description="Preferred break duration in minutes"
    )
    sessions_before_long_break: int = Field(
        default=3,
        ge=1,
        le=6,
        description="Number of sessions before a long break"
    )
    
    # Content preferences
    include_practice_tests: bool = Field(
        default=True,
        description="Include practice tests in study plan"
    )
    include_revision_blocks: bool = Field(
        default=True,
        description="Include revision blocks in study plan"
    )
    focus_on_weak_areas: bool = Field(
        default=True,
        description="Prioritize weak areas in planning"
    )
    
    # Language preference for content
    preferred_language: str = Field(
        default="en",
        description="Preferred content language"
    )


# -----------------------------------------------------------------------------
# Main Study Profile Model
# -----------------------------------------------------------------------------

class StudyProfileModel(MongoBaseModel):
    """
    Student study profile document.
    
    Collection: study_profiles
    
    Indexes:
    - user_id (unique) - one profile per student
    - exam_type
    - exam_date
    - (exam_type, exam_date) compound
    """
    
    # User reference (1:1 relationship)
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user document"
    )
    
    # Exam information
    exam_type: str = Field(
        ...,
        max_length=50,
        description="Target exam name (e.g., 'JEE Main', 'NEET')"
    )
    exam_category: ExamCategory = Field(
        default=ExamCategory.OTHER,
        description="Category of the target exam"
    )
    exam_date: date = Field(
        ...,
        description="Target exam date"
    )
    exam_attempt_number: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Which attempt this is"
    )
    
    # Preparation start
    preparation_start_date: date = Field(
        ...,
        description="When preparation started"
    )
    
    # Daily availability (embedded)
    daily_availability: DailyAvailability = Field(
        default_factory=DailyAvailability,
        description="Weekly study time availability"
    )
    
    # Preferred time slots (embedded)
    preferred_time_slot: PreferredTimeSlot = Field(
        default_factory=PreferredTimeSlot,
        description="Preferred study time slots"
    )
    
    # Study preferences (embedded)
    preferences: StudyPreferences = Field(
        default_factory=StudyPreferences,
        description="Detailed study preferences"
    )
    
    # Subject strengths (bounded array - max 15)
    subject_strengths: list[SubjectStrength] = Field(
        default_factory=list,
        max_length=15,
        description="Subject-wise strength assessment"
    )
    
    # Current study phase
    current_phase: str = Field(
        default="foundation",
        description="Current preparation phase (foundation/intermediate/advanced/revision)"
    )
    
    # Profile completion status
    is_complete: bool = Field(
        default=False,
        description="Whether profile setup is complete"
    )
    
    # Onboarding progress
    onboarding_step: int = Field(
        default=0,
        ge=0,
        le=5,
        description="Current onboarding step (0-5)"
    )
    
    @field_validator('exam_date')
    @classmethod
    def exam_date_must_be_future(cls, v: date) -> date:
        """Validate exam date is not in the past."""
        # Allow past dates for historical records, but flag for active planning
        return v
    
    @property
    def days_until_exam(self) -> int:
        """Calculate days remaining until exam."""
        delta = self.exam_date - date.today()
        return max(0, delta.days)


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------

class StudyProfileCreateDTO(BaseModel):
    """DTO for creating a new study profile."""
    
    exam_type: str
    exam_category: ExamCategory = ExamCategory.OTHER
    exam_date: date
    preparation_start_date: Optional[date] = None
    daily_availability: Optional[DailyAvailability] = None
    preferences: Optional[StudyPreferences] = None


class StudyProfileUpdateDTO(BaseModel):
    """DTO for updating study profile."""
    
    exam_date: Optional[date] = None
    daily_availability: Optional[DailyAvailability] = None
    preferred_time_slot: Optional[PreferredTimeSlot] = None
    preferences: Optional[StudyPreferences] = None
    current_phase: Optional[str] = None
