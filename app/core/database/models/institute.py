"""
Institute / B2B Mapping Model for Smart Study Planner.

Collections:
- institutes: Institute/organization details
- institute_memberships: Student-Institute mapping

Supports B2B features:
- Student enrollment under institutes
- Plan override for sponsored access
- Admin hierarchy
- Batch/class organization

Design decisions:
- Separate membership collection for scalability
- Plan overrides for institute-sponsored features
- Role-based access within institute

Indexes (to be created):
institutes:
- code (unique)
- name
- is_active

institute_memberships:
- (institute_id, student_id) unique compound
- institute_id
- student_id
- status
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class InstituteType(str, Enum):
    """Types of educational institutes."""
    COACHING = "coaching"  # Coaching centers
    SCHOOL = "school"
    COLLEGE = "college"
    ONLINE_PLATFORM = "online_platform"
    TUITION_CENTER = "tuition_center"
    OTHER = "other"


class InstituteStatus(str, Enum):
    """Institute account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"


class MembershipRole(str, Enum):
    """Roles within an institute."""
    ADMIN = "admin"  # Full access
    TEACHER = "teacher"  # Can view student progress
    STUDENT = "student"  # Regular student access
    PARENT = "parent"  # Parent view access


class MembershipStatus(str, Enum):
    """Membership status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"  # Awaiting approval
    EXPIRED = "expired"
    REMOVED = "removed"


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class InstitutePlanOverride(BaseModel):
    """
    Plan override settings for institute-sponsored access.
    Allows institutes to provide features to their students.
    """
    
    # Plan override
    override_plan: Optional[str] = Field(
        default=None,
        description="Plan to give students (pro/smart_pack)"
    )
    
    # Feature-level overrides
    enable_ai_features: bool = Field(
        default=False,
        description="Enable AI features"
    )
    enable_advanced_analytics: bool = Field(
        default=False,
        description="Enable advanced analytics"
    )
    enable_practice_tests: bool = Field(
        default=False,
        description="Enable unlimited practice tests"
    )
    
    # Limits
    daily_ai_queries_override: Optional[int] = Field(
        default=None,
        ge=0,
        description="Override daily AI query limit"
    )
    max_subjects_override: Optional[int] = Field(
        default=None,
        ge=1,
        description="Override max subjects limit"
    )
    
    # Validity
    valid_from: Optional[date] = Field(
        default=None,
        description="Override valid from"
    )
    valid_until: Optional[date] = Field(
        default=None,
        description="Override valid until"
    )


class InstituteContact(BaseModel):
    """Contact person details (embedded)."""
    
    name: str = Field(
        ...,
        max_length=100,
        description="Contact person name"
    )
    email: EmailStr = Field(
        ...,
        description="Contact email"
    )
    phone: str = Field(
        ...,
        max_length=15,
        description="Contact phone"
    )
    role: str = Field(
        default="admin",
        max_length=50,
        description="Role in institute"
    )


class InstituteBatch(BaseModel):
    """
    Batch/class within institute (embedded).
    Max 50 batches per institute.
    """
    
    batch_id: str = Field(
        ...,
        description="Unique batch ID"
    )
    name: str = Field(
        ...,
        max_length=100,
        description="Batch name (e.g., 'JEE 2025 Batch A')"
    )
    exam_type: str = Field(
        ...,
        max_length=50,
        description="Target exam"
    )
    year: int = Field(
        ...,
        ge=2024,
        description="Target year"
    )
    student_count: int = Field(
        default=0,
        ge=0,
        description="Number of students"
    )
    is_active: bool = Field(
        default=True,
        description="Whether batch is active"
    )


class InstituteStats(BaseModel):
    """Institute statistics (embedded, updated periodically)."""
    
    total_students: int = Field(default=0, ge=0)
    active_students: int = Field(default=0, ge=0)
    total_teachers: int = Field(default=0, ge=0)
    total_batches: int = Field(default=0, ge=0)
    
    # Engagement metrics
    avg_daily_active_students: float = Field(default=0.0, ge=0)
    avg_study_hours_per_student: float = Field(default=0.0, ge=0)
    
    # Performance metrics
    avg_consistency_score: float = Field(default=0.0, ge=0, le=100)
    avg_exam_readiness: float = Field(default=0.0, ge=0, le=100)
    
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Stats last updated"
    )


# -----------------------------------------------------------------------------
# Main Institute Model
# -----------------------------------------------------------------------------

class InstituteModel(MongoBaseModel):
    """
    Institute document.
    
    Collection: institutes
    
    Indexes:
    - code (unique)
    - name
    - is_active
    - (type, is_active) compound
    """
    
    # Basic info
    name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Institute name"
    )
    code: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="Unique institute code"
    )
    type: InstituteType = Field(
        default=InstituteType.COACHING,
        description="Institute type"
    )
    
    # Description
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Institute description"
    )
    logo_url: Optional[str] = Field(
        default=None,
        description="Institute logo URL"
    )
    website: Optional[str] = Field(
        default=None,
        description="Institute website"
    )
    
    # Location
    city: Optional[str] = Field(
        default=None,
        max_length=100,
        description="City"
    )
    state: Optional[str] = Field(
        default=None,
        max_length=100,
        description="State"
    )
    address: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Full address"
    )
    
    # Status
    status: InstituteStatus = Field(
        default=InstituteStatus.PENDING_VERIFICATION,
        description="Account status"
    )
    is_active: bool = Field(
        default=True,
        description="Whether institute is active"
    )
    verified_at: Optional[datetime] = Field(
        default=None,
        description="Verification timestamp"
    )
    
    # Primary contact (embedded)
    primary_contact: InstituteContact = Field(
        ...,
        description="Primary contact person"
    )
    
    # Plan overrides (embedded)
    plan_override: InstitutePlanOverride = Field(
        default_factory=InstitutePlanOverride,
        description="Plan override settings for students"
    )
    
    # Batches (bounded, max 50)
    batches: list[InstituteBatch] = Field(
        default_factory=list,
        max_length=50,
        description="Batches/classes"
    )
    
    # Statistics (embedded)
    stats: InstituteStats = Field(
        default_factory=InstituteStats,
        description="Institute statistics"
    )
    
    # Exam types offered (max 10)
    exam_types_offered: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Exam types the institute prepares for"
    )
    
    # Subscription/billing
    subscription_id: Optional[PyObjectId] = Field(
        default=None,
        description="Institute subscription reference"
    )
    max_students_allowed: int = Field(
        default=100,
        ge=10,
        description="Maximum students allowed in plan"
    )
    
    # Admin users (user IDs, max 10)
    admin_user_ids: list[PyObjectId] = Field(
        default_factory=list,
        max_length=10,
        description="Admin user IDs"
    )


# -----------------------------------------------------------------------------
# Institute Membership Model
# -----------------------------------------------------------------------------

class InstituteMembershipModel(MongoBaseModel):
    """
    Institute-Student membership document.
    
    Collection: institute_memberships
    
    Indexes:
    - (institute_id, student_id) unique compound
    - institute_id
    - student_id
    - status
    - (institute_id, batch_id) for batch queries
    - (institute_id, role, status) compound
    """
    
    # References
    institute_id: PyObjectId = Field(
        ...,
        description="Reference to institute"
    )
    student_id: PyObjectId = Field(
        ...,
        description="Reference to user (student)"
    )
    
    # Role
    role: MembershipRole = Field(
        default=MembershipRole.STUDENT,
        description="Role in institute"
    )
    
    # Status
    status: MembershipStatus = Field(
        default=MembershipStatus.PENDING,
        description="Membership status"
    )
    
    # Batch assignment
    batch_id: Optional[str] = Field(
        default=None,
        description="Assigned batch ID"
    )
    batch_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Batch name (denormalized)"
    )
    
    # Dates
    joined_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Joining timestamp"
    )
    expires_at: Optional[date] = Field(
        default=None,
        description="Membership expiry date"
    )
    
    # Plan override flag
    apply_plan_override: bool = Field(
        default=True,
        description="Whether to apply institute plan override"
    )
    
    # Inviter info
    invited_by: Optional[PyObjectId] = Field(
        default=None,
        description="User who invited (admin/teacher)"
    )
    invite_code: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Invite code used"
    )
    
    # Roll number / enrollment
    roll_number: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Roll number in institute"
    )
    enrollment_id: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Enrollment/admission ID"
    )
    
    # Activity tracking
    last_active_at: Optional[datetime] = Field(
        default=None,
        description="Last activity timestamp"
    )
    is_visible_to_institute: bool = Field(
        default=True,
        description="Whether profile visible to institute"
    )


# -----------------------------------------------------------------------------
# Institute Invite Model
# -----------------------------------------------------------------------------

class InstituteInviteModel(MongoBaseModel):
    """
    Invite codes/links for joining institute.
    
    Collection: institute_invites
    
    Indexes:
    - code (unique)
    - institute_id
    - expires_at
    """
    
    institute_id: PyObjectId = Field(
        ...,
        description="Reference to institute"
    )
    
    code: str = Field(
        ...,
        min_length=6,
        max_length=20,
        description="Unique invite code"
    )
    
    # Targeting
    batch_id: Optional[str] = Field(
        default=None,
        description="Target batch for invite"
    )
    role: MembershipRole = Field(
        default=MembershipRole.STUDENT,
        description="Role assigned on join"
    )
    
    # Limits
    max_uses: int = Field(
        default=100,
        ge=1,
        description="Maximum uses allowed"
    )
    current_uses: int = Field(
        default=0,
        ge=0,
        description="Current use count"
    )
    
    # Validity
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Invite expiry"
    )
    is_active: bool = Field(
        default=True,
        description="Whether invite is active"
    )
    
    # Creator
    created_by: PyObjectId = Field(
        ...,
        description="User who created invite"
    )


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------

class InstituteCreateDTO(BaseModel):
    """DTO for creating an institute."""
    
    name: str
    code: str
    type: InstituteType = InstituteType.COACHING
    primary_contact: InstituteContact
    exam_types_offered: list[str] = Field(default_factory=list, max_length=10)


class MembershipCreateDTO(BaseModel):
    """DTO for creating a membership."""
    
    student_id: PyObjectId
    batch_id: Optional[str] = None
    role: MembershipRole = MembershipRole.STUDENT
    roll_number: Optional[str] = None
