"""
Subscription Models

Plan definitions, feature flags, and subscription models.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Set

from pydantic import Field

from app.core.database.models.base import MongoBaseModel
from bson import ObjectId


class PlanType(str, Enum):
    """Subscription plan types."""
    
    FREE = "free"
    PRO = "pro"
    SMART_PACK = "smart_pack"


class FeatureFlag(str, Enum):
    """Feature flags for access control."""
    
    # Core Features (Free Plan)
    STUDY_PROFILE = "study_profile"
    DAILY_PLANNER = "daily_planner"
    TASK_EXECUTION = "task_execution"
    BASIC_ANALYTICS = "basic_analytics"
    
    # Pro Features
    SMART_REVISION = "smart_revision"
    ADVANCED_ANALYTICS = "advanced_analytics"
    NOTIFICATIONS = "notifications"
    DATA_EXPORT = "data_export"
    
    # Smart Pack Features
    AI_PLANNER = "ai_planner"
    AI_PRIORITIZATION = "ai_prioritization"
    PRIORITY_SUPPORT = "priority_support"
    EARLY_ACCESS = "early_access"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    GRACE_PERIOD = "grace_period"


# -----------------------------------------------------------------------------
# Plan Configuration (Single Source of Truth)
# -----------------------------------------------------------------------------

PLAN_FEATURES: Dict[PlanType, Set[FeatureFlag]] = {
    PlanType.FREE: {
        FeatureFlag.STUDY_PROFILE,
        FeatureFlag.DAILY_PLANNER,
        FeatureFlag.TASK_EXECUTION,
        FeatureFlag.BASIC_ANALYTICS,
    },
    PlanType.PRO: {
        # All Free features
        FeatureFlag.STUDY_PROFILE,
        FeatureFlag.DAILY_PLANNER,
        FeatureFlag.TASK_EXECUTION,
        FeatureFlag.BASIC_ANALYTICS,
        # Pro features
        FeatureFlag.SMART_REVISION,
        FeatureFlag.ADVANCED_ANALYTICS,
        FeatureFlag.NOTIFICATIONS,
        FeatureFlag.DATA_EXPORT,
    },
    PlanType.SMART_PACK: {
        # All Pro features
        FeatureFlag.STUDY_PROFILE,
        FeatureFlag.DAILY_PLANNER,
        FeatureFlag.TASK_EXECUTION,
        FeatureFlag.BASIC_ANALYTICS,
        FeatureFlag.SMART_REVISION,
        FeatureFlag.ADVANCED_ANALYTICS,
        FeatureFlag.NOTIFICATIONS,
        FeatureFlag.DATA_EXPORT,
        # Smart Pack features
        FeatureFlag.AI_PLANNER,
        FeatureFlag.AI_PRIORITIZATION,
        FeatureFlag.PRIORITY_SUPPORT,
        FeatureFlag.EARLY_ACCESS,
    }
}

PLAN_LIMITS: Dict[PlanType, Dict[str, int]] = {
    PlanType.FREE: {
        "subjects": 5,
        "tasks_per_day": 5,
        "chapters": 50,
        "analytics_days": 7,
    },
    PlanType.PRO: {
        "subjects": 15,
        "tasks_per_day": -1,  # -1 = Unlimited
        "chapters": 200,
        "analytics_days": 90,
    },
    PlanType.SMART_PACK: {
        "subjects": -1,  # Unlimited
        "tasks_per_day": -1,
        "chapters": -1,
        "analytics_days": -1,  # Full history
    }
}

# Plan hierarchy for comparison
PLAN_HIERARCHY = {
    PlanType.FREE: 0,
    PlanType.PRO: 1,
    PlanType.SMART_PACK: 2,
}


# -----------------------------------------------------------------------------
# Database Models
# -----------------------------------------------------------------------------

class SubscriptionModel(MongoBaseModel):
    """
    User's subscription record.
    
    Each user has one subscription document.
    Free plan never expires (end_date = None).
    """
    
    user_id: ObjectId = Field(..., description="User ID (unique index)")
    plan_type: PlanType = Field(default=PlanType.FREE, description="Current plan")
    status: SubscriptionStatus = Field(
        default=SubscriptionStatus.ACTIVE,
        description="Subscription status"
    )
    start_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this plan started"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="When this plan expires (None for Free plan)"
    )
    auto_renew: bool = Field(True, description="Auto-renewal enabled")
    grace_period_until: Optional[datetime] = Field(
        None,
        description="Grace period end for downgrades"
    )
    previous_plan: Optional[PlanType] = Field(
        None,
        description="Previous plan before downgrade/cancellation"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        collection_name = "subscriptions"


class UsageTrackingModel(MongoBaseModel):
    """
    Track feature usage for limit enforcement.
    
    Separate documents for daily and monthly tracking.
    """
    
    user_id: ObjectId = Field(..., description="User ID")
    feature: str = Field(
        ...,
        description="Feature being tracked (subjects, tasks_per_day, chapters)"
    )
    period: str = Field(
        ...,
        description="Tracking period: 'daily' or 'monthly'"
    )
    count: int = Field(default=0, ge=0, description="Usage count")
    date: Optional[datetime] = Field(
        None,
        description="Date for daily tracking (YYYY-MM-DD)"
    )
    month: Optional[str] = Field(
        None,
        description="Month for monthly tracking (YYYY-MM)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        collection_name = "usage_tracking"


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def has_feature_access(plan_type: PlanType, feature: FeatureFlag) -> bool:
    """
    Check if a plan has access to a feature.
    
    Args:
        plan_type: User's plan type
        feature: Feature to check
    
    Returns:
        True if plan includes this feature
    """
    return feature in PLAN_FEATURES.get(plan_type, set())


def get_plan_limit(plan_type: PlanType, limit_type: str) -> int:
    """
    Get limit value for a plan.
    
    Args:
        plan_type: User's plan type
        limit_type: Limit to get (subjects, tasks_per_day, etc.)
    
    Returns:
        Limit value (-1 for unlimited, 0+ for specific limit)
    """
    return PLAN_LIMITS.get(plan_type, {}).get(limit_type, 0)


def meets_plan_requirement(current_plan: PlanType, required_plan: PlanType) -> bool:
    """
    Check if current plan meets minimum requirement.
    
    Args:
        current_plan: User's current plan
        required_plan: Minimum required plan
    
    Returns:
        True if current plan >= required plan
    """
    return PLAN_HIERARCHY.get(current_plan, 0) >= PLAN_HIERARCHY.get(required_plan, 0)


def get_required_plan_for_feature(feature: FeatureFlag) -> PlanType:
    """
    Get minimum plan required for a feature.
    
    Args:
        feature: Feature to check
    
    Returns:
        Minimum plan type that includes this feature
    """
    for plan_type in [PlanType.FREE, PlanType.PRO, PlanType.SMART_PACK]:
        if feature in PLAN_FEATURES[plan_type]:
            return plan_type
    
    return PlanType.SMART_PACK  # Default to highest
