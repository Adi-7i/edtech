"""
MongoDB Schema Models for Smart Study Planner.

This package provides Pydantic models for MongoDB collections with:
- Type-safe ObjectId handling
- Automatic timestamps
- Embedded documents with bounded arrays
- Index recommendations in docstrings

Collections:
- users: User accounts (Student/Parent/Institute)
- study_profiles: Student study configuration
- exams: Master exam data
- subjects: Subjects under exams
- chapters: Chapters under subjects
- user_chapter_strengths: User's chapter-wise strength
- daily_plans: Date-based study plans
- task_executions: Task completion tracking
- revisions: Spaced repetition scheduling
- daily_analytics: Daily progress metrics
- user_progress_summaries: Aggregated user progress
- subscriptions: Subscription management
- plan_pricing: Pricing reference
- ai_usage_logs: AI feature usage tracking
- ai_usage_summaries: Monthly AI usage aggregates
- ethical_reviews: Flagged content review queue
- institutes: B2B institute accounts
- institute_memberships: Student-Institute mapping
- institute_invites: Join invite codes
"""

# Base utilities
from .base import (
    MongoBaseModel,
    PyObjectId,
    SoftDeleteMixin,
    TimestampMixin,
    validate_non_empty_string,
    validate_percentage,
    validate_positive_int,
)

# User models
from .user import (
    AccountStatus,
    AuthProvider,
    ParentLinkage,
    PlanType,
    UserCreateDTO,
    UserModel,
    UserPreferences,
    UserRole,
    UserUpdateDTO,
)

# Study profile models
from .study_profile import (
    DailyAvailability,
    ExamCategory,
    LearningStyle,
    PreferredTimeSlot,
    StrengthLevel,
    StudyMode,
    StudyPreferences,
    StudyProfileCreateDTO,
    StudyProfileModel,
    StudyProfileUpdateDTO,
    SubjectStrength,
)

# Exam models
from .exam import (
    ChapterModel,
    ContentType,
    DifficultyLevel,
    ExamMode,
    ExamModel,
    ExamStructure,
    SubjectModel,
    Topic,
    UserChapterStrengthModel,
)

# Daily plan models
from .daily_plan import (
    DailyPlanCreateDTO,
    DailyPlanModel,
    DailySummary,
    PlannedTask,
    PlanStatus,
    TaskPriority,
    TaskStatus,
    TaskType,
    TaskUpdateDTO,
    TimeSlotAllocation,
)

# Task execution models
from .task_execution import (
    CompletionQuality,
    DistractionLog,
    ExecutionSession,
    ExecutionStatus,
    SkipReason,
    TaskExecutionCreateDTO,
    TaskExecutionModel,
    TaskExecutionUpdateDTO,
)

# Revision models
from .revision import (
    RevisionCreateDTO,
    RevisionCycle,
    RevisionHistory,
    RevisionModel,
    RevisionQuality,
    RevisionScheduleSummary,
    RevisionStatus,
    RevisionUpdateDTO,
    TopicRevisionProgress,
)

# Analytics models
from .analytics import (
    DailyAnalyticsCreateDTO,
    DailyAnalyticsModel,
    ProgressQueryDTO,
    ReadinessLevel,
    StudySessionMetrics,
    SubjectProgress,
    TrendDirection,
    UserProgressSummaryModel,
    WeeklySnapshot,
)

# Subscription models
from .subscription import (
    BillingCycle,
    FeatureFlags,
    PaymentInfo,
    PaymentMethod,
    PlanPricingModel,
    SubscriptionCreateDTO,
    SubscriptionModel,
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionUpgradeDTO,
    get_default_features,
)

# AI usage models
from .ai_usage import (
    AIFeatureType,
    AIQuery,
    AIQueryCreateDTO,
    AIQueryResultDTO,
    AIUsageModel,
    AIUsageSummaryModel,
    EthicalFlag,
    EthicalReviewModel,
    QueryStatus,
    UsageByFeature,
)

# Institute models
from .institute import (
    InstituteBatch,
    InstituteContact,
    InstituteCreateDTO,
    InstituteInviteModel,
    InstituteMembershipModel,
    InstituteModel,
    InstitutePlanOverride,
    InstituteStats,
    InstituteStatus,
    InstituteType,
    MembershipCreateDTO,
    MembershipRole,
    MembershipStatus,
)


__all__ = [
    # Base
    "MongoBaseModel",
    "PyObjectId",
    "SoftDeleteMixin",
    "TimestampMixin",
    "validate_non_empty_string",
    "validate_percentage",
    "validate_positive_int",
    # User
    "UserModel",
    "UserRole",
    "PlanType",
    "AuthProvider",
    "AccountStatus",
    "UserPreferences",
    "ParentLinkage",
    "UserCreateDTO",
    "UserUpdateDTO",
    # Study Profile
    "StudyProfileModel",
    "ExamCategory",
    "StudyMode",
    "LearningStyle",
    "StrengthLevel",
    "DailyAvailability",
    "PreferredTimeSlot",
    "SubjectStrength",
    "StudyPreferences",
    "StudyProfileCreateDTO",
    "StudyProfileUpdateDTO",
    # Exam
    "ExamModel",
    "SubjectModel",
    "ChapterModel",
    "UserChapterStrengthModel",
    "DifficultyLevel",
    "ContentType",
    "ExamMode",
    "ExamStructure",
    "Topic",
    # Daily Plan
    "DailyPlanModel",
    "PlanStatus",
    "TaskType",
    "TaskPriority",
    "TaskStatus",
    "PlannedTask",
    "TimeSlotAllocation",
    "DailySummary",
    "DailyPlanCreateDTO",
    "TaskUpdateDTO",
    # Task Execution
    "TaskExecutionModel",
    "ExecutionStatus",
    "CompletionQuality",
    "SkipReason",
    "ExecutionSession",
    "DistractionLog",
    "TaskExecutionCreateDTO",
    "TaskExecutionUpdateDTO",
    # Revision
    "RevisionModel",
    "RevisionStatus",
    "RevisionCycle",
    "RevisionQuality",
    "RevisionHistory",
    "TopicRevisionProgress",
    "RevisionScheduleSummary",
    "RevisionCreateDTO",
    "RevisionUpdateDTO",
    # Analytics
    "DailyAnalyticsModel",
    "UserProgressSummaryModel",
    "ReadinessLevel",
    "TrendDirection",
    "SubjectProgress",
    "StudySessionMetrics",
    "WeeklySnapshot",
    "DailyAnalyticsCreateDTO",
    "ProgressQueryDTO",
    # Subscription
    "SubscriptionModel",
    "PlanPricingModel",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "BillingCycle",
    "PaymentMethod",
    "FeatureFlags",
    "PaymentInfo",
    "get_default_features",
    "SubscriptionCreateDTO",
    "SubscriptionUpgradeDTO",
    # AI Usage
    "AIUsageModel",
    "AIUsageSummaryModel",
    "EthicalReviewModel",
    "AIFeatureType",
    "QueryStatus",
    "EthicalFlag",
    "AIQuery",
    "UsageByFeature",
    "AIQueryCreateDTO",
    "AIQueryResultDTO",
    # Institute
    "InstituteModel",
    "InstituteMembershipModel",
    "InstituteInviteModel",
    "InstituteType",
    "InstituteStatus",
    "MembershipRole",
    "MembershipStatus",
    "InstitutePlanOverride",
    "InstituteContact",
    "InstituteBatch",
    "InstituteStats",
    "InstituteCreateDTO",
    "MembershipCreateDTO",
]
