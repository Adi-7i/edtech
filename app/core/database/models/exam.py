"""
Exam, Subject & Chapter Models for Smart Study Planner.

Collections:
- exams: Master list of competitive exams
- subjects: Subjects under each exam
- chapters: Chapters/topics under each subject

This forms the academic hierarchy:
Exam → Subject → Chapter → Topics

Indexes (to be created):
- exams: name (unique), category, is_active
- subjects: exam_id, (exam_id, name) unique compound
- chapters: subject_id, (subject_id, name) unique compound
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class DifficultyLevel(str, Enum):
    """Difficulty levels for chapters/topics."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ContentType(str, Enum):
    """Types of content within a chapter."""
    THEORY = "theory"
    NUMERICAL = "numerical"
    CONCEPTUAL = "conceptual"
    PRACTICAL = "practical"
    MIXED = "mixed"


class ExamMode(str, Enum):
    """Exam mode types."""
    ONLINE = "online"
    OFFLINE = "offline"
    HYBRID = "hybrid"


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class ExamStructure(BaseModel):
    """Exam structure details (embedded)."""
    
    total_marks: int = Field(
        default=0,
        ge=0,
        description="Total marks in the exam"
    )
    duration_minutes: int = Field(
        default=180,
        ge=30,
        le=600,
        description="Exam duration in minutes"
    )
    total_questions: int = Field(
        default=0,
        ge=0,
        description="Total number of questions"
    )
    negative_marking: bool = Field(
        default=False,
        description="Whether negative marking applies"
    )
    negative_marks_value: float = Field(
        default=0.0,
        ge=0,
        le=5,
        description="Negative marks per wrong answer"
    )
    sections_count: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of sections in the exam"
    )


class Topic(BaseModel):
    """
    Topic within a chapter (embedded).
    Max 20 topics per chapter to keep document size bounded.
    """
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Topic name"
    )
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.MEDIUM,
        description="Topic difficulty"
    )
    estimated_hours: float = Field(
        default=1.0,
        ge=0.5,
        le=20,
        description="Estimated hours to complete"
    )
    weightage_percentage: float = Field(
        default=0,
        ge=0,
        le=100,
        description="Weightage in exams"
    )
    is_important: bool = Field(
        default=False,
        description="Marked as important for exam"
    )


# -----------------------------------------------------------------------------
# Exam Model
# -----------------------------------------------------------------------------

class ExamModel(MongoBaseModel):
    """
    Exam master document.
    
    Collection: exams
    
    Indexes:
    - name (unique)
    - category
    - is_active
    - (category, is_active) compound
    """
    
    # Basic info
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Exam name (e.g., 'JEE Main', 'NEET UG')"
    )
    full_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Full official name"
    )
    code: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Short code (e.g., 'JEE', 'NEET')"
    )
    category: str = Field(
        ...,
        description="Exam category (engineering/medical/etc.)"
    )
    
    # Description
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Brief description of the exam"
    )
    
    # Exam details
    exam_mode: ExamMode = Field(
        default=ExamMode.ONLINE,
        description="Mode of examination"
    )
    conducting_body: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Organization conducting the exam"
    )
    
    # Structure (embedded)
    structure: ExamStructure = Field(
        default_factory=ExamStructure,
        description="Exam structure details"
    )
    
    # Typical exam months
    typical_exam_months: list[int] = Field(
        default_factory=list,
        max_length=12,
        description="Months when exam is typically held (1-12)"
    )
    
    # Eligibility
    min_age: Optional[int] = Field(
        default=None,
        ge=10,
        le=60,
        description="Minimum age requirement"
    )
    max_age: Optional[int] = Field(
        default=None,
        ge=15,
        le=65,
        description="Maximum age requirement"
    )
    required_qualification: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Required educational qualification"
    )
    
    # Status
    is_active: bool = Field(
        default=True,
        description="Whether exam is currently active"
    )
    
    # Popularity/usage metrics
    total_aspirants: int = Field(
        default=0,
        ge=0,
        description="Number of students preparing on platform"
    )


# -----------------------------------------------------------------------------
# Subject Model
# -----------------------------------------------------------------------------

class SubjectModel(MongoBaseModel):
    """
    Subject document under an exam.
    
    Collection: subjects
    
    Indexes:
    - exam_id
    - (exam_id, name) unique compound
    - is_active
    """
    
    # Parent exam reference
    exam_id: PyObjectId = Field(
        ...,
        description="Reference to parent exam"
    )
    
    # Basic info
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Subject name (e.g., 'Physics', 'Chemistry')"
    )
    code: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Short code for the subject"
    )
    
    # Weightage in exam
    weightage_percentage: float = Field(
        default=0,
        ge=0,
        le=100,
        description="Percentage weightage in exam"
    )
    total_marks: int = Field(
        default=0,
        ge=0,
        description="Total marks for this subject"
    )
    
    # Study metrics
    estimated_total_hours: float = Field(
        default=0,
        ge=0,
        description="Total estimated hours to complete"
    )
    total_chapters: int = Field(
        default=0,
        ge=0,
        description="Total number of chapters"
    )
    
    # Content type
    predominant_content_type: ContentType = Field(
        default=ContentType.MIXED,
        description="Primary type of content"
    )
    
    # Ordering
    display_order: int = Field(
        default=0,
        ge=0,
        description="Order for display purposes"
    )
    
    # Status
    is_active: bool = Field(
        default=True,
        description="Whether subject is active"
    )
    is_optional: bool = Field(
        default=False,
        description="Whether subject is optional in exam"
    )


# -----------------------------------------------------------------------------
# Chapter Model
# -----------------------------------------------------------------------------

class ChapterModel(MongoBaseModel):
    """
    Chapter document under a subject.
    
    Collection: chapters
    
    Indexes:
    - subject_id
    - (subject_id, name) unique compound
    - (subject_id, display_order) for ordered retrieval
    - is_active
    """
    
    # Parent references
    subject_id: PyObjectId = Field(
        ...,
        description="Reference to parent subject"
    )
    exam_id: PyObjectId = Field(
        ...,
        description="Reference to parent exam (denormalized)"
    )
    
    # Basic info
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Chapter name"
    )
    code: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Short code for the chapter"
    )
    
    # Description
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Brief description"
    )
    
    # Difficulty and importance
    difficulty: DifficultyLevel = Field(
        default=DifficultyLevel.MEDIUM,
        description="Overall chapter difficulty"
    )
    importance_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Importance for exam (1-10)"
    )
    
    # Weightage
    weightage_percentage: float = Field(
        default=0,
        ge=0,
        le=100,
        description="Weightage in subject"
    )
    expected_questions: int = Field(
        default=0,
        ge=0,
        description="Expected number of questions in exam"
    )
    
    # Study metrics
    estimated_hours: float = Field(
        default=2.0,
        ge=0.5,
        le=50,
        description="Estimated hours to complete"
    )
    content_type: ContentType = Field(
        default=ContentType.MIXED,
        description="Type of content in chapter"
    )
    
    # Topics (embedded, max 20)
    topics: list[Topic] = Field(
        default_factory=list,
        max_length=20,
        description="Topics within the chapter"
    )
    
    # Prerequisites (references to other chapters, max 5)
    prerequisite_chapter_ids: list[PyObjectId] = Field(
        default_factory=list,
        max_length=5,
        description="Prerequisite chapter IDs"
    )
    
    # Ordering
    display_order: int = Field(
        default=0,
        ge=0,
        description="Order for display/study sequence"
    )
    
    # Status
    is_active: bool = Field(
        default=True,
        description="Whether chapter is active"
    )
    
    # Tags for filtering
    tags: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Tags for categorization"
    )


# -----------------------------------------------------------------------------
# User-Chapter Strength Model (separate collection for growth-safe design)
# -----------------------------------------------------------------------------

class UserChapterStrengthModel(MongoBaseModel):
    """
    User's strength level for a specific chapter.
    Separate collection to avoid unbounded arrays in user profile.
    
    Collection: user_chapter_strengths
    
    Indexes:
    - (user_id, chapter_id) unique compound
    - user_id
    - (user_id, strength) for filtering weak chapters
    """
    
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
    
    # Strength assessment
    strength: str = Field(
        default="medium",
        description="Strength level (weak/medium/strong)"
    )
    confidence_score: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Confidence percentage (0-100)"
    )
    
    # Practice metrics
    questions_attempted: int = Field(
        default=0,
        ge=0,
        description="Total questions attempted"
    )
    questions_correct: int = Field(
        default=0,
        ge=0,
        description="Total correct answers"
    )
    
    # Time spent
    total_study_minutes: int = Field(
        default=0,
        ge=0,
        description="Total minutes spent on chapter"
    )
    
    # Last activity
    last_studied_at: Optional[datetime] = Field(
        default=None,
        description="Last study session timestamp"
    )
    last_assessed_at: Optional[datetime] = Field(
        default=None,
        description="Last assessment timestamp"
    )
    
    # Revision tracking
    revision_count: int = Field(
        default=0,
        ge=0,
        description="Number of revisions completed"
    )
    needs_revision: bool = Field(
        default=False,
        description="Flagged for revision"
    )
