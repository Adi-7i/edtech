"""
User & Role Model for Smart Study Planner.

Collection: users

Supports three user types:
- Student: Primary learners using the platform
- Parent: Guardians monitoring student progress
- Institute: Educational institutions (B2B)

Plan Types:
- Free: Basic features
- Pro: Advanced features
- Smart Pack: Full feature access

Indexes (to be created):
- email: unique, sparse
- phone: unique, sparse  
- role: regular index for filtering
- (role, plan_type): compound for user segmentation
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .base import MongoBaseModel, PyObjectId, SoftDeleteMixin


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class UserRole(str, Enum):
    """User roles in the system."""
    STUDENT = "student"
    PARENT = "parent"
    INSTITUTE = "institute"


class PlanType(str, Enum):
    """Subscription plan types."""
    FREE = "free"
    PRO = "pro"
    SMART_PACK = "smart_pack"


class AuthProvider(str, Enum):
    """Authentication providers."""
    EMAIL = "email"
    GOOGLE = "google"
    PHONE = "phone"


class AccountStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    DEACTIVATED = "deactivated"


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class UserPreferences(BaseModel):
    """User preference settings (embedded document)."""
    
    # Notification preferences
    email_notifications: bool = Field(
        default=True,
        description="Enable email notifications"
    )
    push_notifications: bool = Field(
        default=True,
        description="Enable push notifications"
    )
    sms_notifications: bool = Field(
        default=False,
        description="Enable SMS notifications"
    )
    
    # Study reminders
    daily_reminder_enabled: bool = Field(
        default=True,
        description="Enable daily study reminders"
    )
    daily_reminder_time: str = Field(
        default="09:00",
        description="Daily reminder time (HH:MM format, IST)"
    )
    
    # App preferences
    language: str = Field(
        default="en",
        description="Preferred language (en, hi, etc.)"
    )
    theme: str = Field(
        default="light",
        description="UI theme preference (light/dark)"
    )


class ParentLinkage(BaseModel):
    """Parent-Student linkage (embedded in parent user)."""
    
    student_id: PyObjectId = Field(
        ...,
        description="Linked student's user ID"
    )
    relationship: str = Field(
        default="parent",
        description="Relationship type (parent/guardian)"
    )
    linked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the linkage was created"
    )
    # Limited to max 5 students per parent
    

# -----------------------------------------------------------------------------
# Main User Model
# -----------------------------------------------------------------------------

class UserModel(MongoBaseModel, SoftDeleteMixin):
    """
    User document model.
    
    Collection: users
    
    Indexes:
    - email (unique, sparse)
    - phone (unique, sparse)
    - role (regular)
    - (role, plan_type) compound
    - created_at (for sorting/pagination)
    """
    
    # Authentication fields
    email: Optional[EmailStr] = Field(
        default=None,
        description="User email address (unique)"
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=15,
        description="Phone number with country code"
    )
    password_hash: Optional[str] = Field(
        default=None,
        description="Hashed password (bcrypt)"
    )
    auth_provider: AuthProvider = Field(
        default=AuthProvider.EMAIL,
        description="Primary authentication provider"
    )
    
    # Profile information
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="User's first name"
    )
    last_name: Optional[str] = Field(
        default=None,
        max_length=50,
        description="User's last name"
    )
    display_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Display name for UI"
    )
    profile_image_url: Optional[str] = Field(
        default=None,
        description="Profile image URL"
    )
    
    # Role and plan
    role: UserRole = Field(
        default=UserRole.STUDENT,
        description="User role in the system"
    )
    plan_type: PlanType = Field(
        default=PlanType.FREE,
        description="Current subscription plan"
    )
    
    # Account status
    status: AccountStatus = Field(
        default=AccountStatus.PENDING_VERIFICATION,
        description="Account status"
    )
    is_active: bool = Field(
        default=True,
        description="Whether user account is active"
    )
    email_verified: bool = Field(
        default=False,
        description="Email verification status"
    )
    phone_verified: bool = Field(
        default=False,
        description="Phone verification status"
    )
    
    # Preferences (embedded)
    preferences: UserPreferences = Field(
        default_factory=UserPreferences,
        description="User preferences"
    )
    
    # Parent-specific: linked students (max 5)
    linked_students: list[ParentLinkage] = Field(
        default_factory=list,
        max_length=5,
        description="Linked students (for parent users)"
    )
    
    # Institute reference (if user belongs to an institute)
    institute_id: Optional[PyObjectId] = Field(
        default=None,
        description="Associated institute ID"
    )
    
    # Login tracking
    last_login: Optional[datetime] = Field(
        default=None,
        description="Last login timestamp"
    )
    login_count: int = Field(
        default=0,
        ge=0,
        description="Total login count"
    )
    
    # Device tokens for push notifications (max 5 devices)
    device_tokens: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="FCM device tokens"
    )


# -----------------------------------------------------------------------------
# Create/Update DTOs (for type safety in services)
# -----------------------------------------------------------------------------

class UserCreateDTO(BaseModel):
    """DTO for creating a new user."""
    
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    role: UserRole = UserRole.STUDENT
    auth_provider: AuthProvider = AuthProvider.EMAIL


class UserUpdateDTO(BaseModel):
    """DTO for updating user profile."""
    
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    preferences: Optional[UserPreferences] = None
