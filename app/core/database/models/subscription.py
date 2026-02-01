"""
Subscription & Feature Control Model for Smart Study Planner.

Collection: subscriptions

Manages user subscription lifecycle:
- Plan type (Free/Pro/Smart Pack)
- Billing and expiry
- Feature flags for access control
- Payment references

Design decisions:
- One active subscription per user
- Historical subscriptions preserved
- Feature flags for granular control

Indexes (to be created):
- user_id
- (user_id, is_active) compound
- expiry_date (for expiry notifications)
- status
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class SubscriptionPlan(str, Enum):
    """Available subscription plans."""
    FREE = "free"
    PRO = "pro"
    SMART_PACK = "smart_pack"
    INSTITUTE = "institute"  # B2B plan
    TRIAL = "trial"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    PENDING = "pending"  # Payment pending
    TRIAL = "trial"


class BillingCycle(str, Enum):
    """Billing cycle options."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class PaymentMethod(str, Enum):
    """Payment methods."""
    UPI = "upi"
    CARD = "card"
    NET_BANKING = "net_banking"
    WALLET = "wallet"
    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    FREE = "free"
    INSTITUTE = "institute"  # Paid by institute


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class FeatureFlags(BaseModel):
    """
    Feature access flags (embedded).
    Granular control over feature access.
    """
    
    # AI Features
    ai_study_plan_generation: bool = Field(
        default=False,
        description="AI-generated study plans"
    )
    ai_doubt_solving: bool = Field(
        default=False,
        description="AI doubt resolution"
    )
    ai_personalized_tips: bool = Field(
        default=False,
        description="AI personalized study tips"
    )
    
    # Content Features
    unlimited_revisions: bool = Field(
        default=False,
        description="Unlimited revision scheduling"
    )
    advanced_analytics: bool = Field(
        default=False,
        description="Detailed analytics dashboard"
    )
    progress_reports: bool = Field(
        default=False,
        description="Weekly/monthly progress reports"
    )
    
    # Practice Features
    unlimited_practice_tests: bool = Field(
        default=False,
        description="Unlimited practice tests"
    )
    detailed_solutions: bool = Field(
        default=False,
        description="Detailed solution explanations"
    )
    
    # Study Tools
    pomodoro_timer: bool = Field(
        default=True,
        description="Pomodoro timer (free feature)"
    )
    focus_mode: bool = Field(
        default=False,
        description="Distraction-free focus mode"
    )
    offline_access: bool = Field(
        default=False,
        description="Offline content access"
    )
    
    # Social Features
    peer_comparison: bool = Field(
        default=False,
        description="Compare with peers"
    )
    study_groups: bool = Field(
        default=False,
        description="Join study groups"
    )
    
    # Support
    priority_support: bool = Field(
        default=False,
        description="Priority customer support"
    )
    
    # Limits
    daily_ai_queries: int = Field(
        default=5,
        ge=0,
        description="Daily AI query limit"
    )
    max_subjects: int = Field(
        default=3,
        ge=1,
        description="Maximum subjects allowed"
    )
    max_daily_tasks: int = Field(
        default=10,
        ge=5,
        description="Maximum tasks per day"
    )


class PaymentInfo(BaseModel):
    """Payment transaction info (embedded)."""
    
    payment_id: Optional[str] = Field(
        default=None,
        description="Payment gateway transaction ID"
    )
    order_id: Optional[str] = Field(
        default=None,
        description="Order ID"
    )
    payment_method: PaymentMethod = Field(
        default=PaymentMethod.FREE,
        description="Payment method used"
    )
    amount_paid: float = Field(
        default=0.0,
        ge=0,
        description="Amount paid in INR"
    )
    currency: str = Field(
        default="INR",
        max_length=3,
        description="Currency code"
    )
    payment_date: Optional[datetime] = Field(
        default=None,
        description="Payment timestamp"
    )
    invoice_url: Optional[str] = Field(
        default=None,
        description="Invoice download URL"
    )


# -----------------------------------------------------------------------------
# Default Feature Flags by Plan
# -----------------------------------------------------------------------------

def get_default_features(plan: SubscriptionPlan) -> FeatureFlags:
    """Get default feature flags for a plan."""
    if plan == SubscriptionPlan.FREE:
        return FeatureFlags(
            daily_ai_queries=5,
            max_subjects=3,
            max_daily_tasks=10,
            pomodoro_timer=True
        )
    elif plan == SubscriptionPlan.PRO:
        return FeatureFlags(
            ai_study_plan_generation=True,
            ai_doubt_solving=True,
            unlimited_revisions=True,
            advanced_analytics=True,
            unlimited_practice_tests=True,
            detailed_solutions=True,
            focus_mode=True,
            daily_ai_queries=50,
            max_subjects=10,
            max_daily_tasks=25,
            pomodoro_timer=True
        )
    elif plan == SubscriptionPlan.SMART_PACK:
        return FeatureFlags(
            ai_study_plan_generation=True,
            ai_doubt_solving=True,
            ai_personalized_tips=True,
            unlimited_revisions=True,
            advanced_analytics=True,
            progress_reports=True,
            unlimited_practice_tests=True,
            detailed_solutions=True,
            focus_mode=True,
            offline_access=True,
            peer_comparison=True,
            study_groups=True,
            priority_support=True,
            daily_ai_queries=200,
            max_subjects=15,
            max_daily_tasks=50,
            pomodoro_timer=True
        )
    else:
        return FeatureFlags()


# -----------------------------------------------------------------------------
# Main Subscription Model
# -----------------------------------------------------------------------------

class SubscriptionModel(MongoBaseModel):
    """
    Subscription document.
    
    Collection: subscriptions
    
    Indexes:
    - user_id
    - (user_id, is_active) compound
    - expiry_date
    - status
    - plan
    """
    
    # User reference
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    
    # Plan details
    plan: SubscriptionPlan = Field(
        default=SubscriptionPlan.FREE,
        description="Subscription plan"
    )
    billing_cycle: BillingCycle = Field(
        default=BillingCycle.MONTHLY,
        description="Billing cycle"
    )
    
    # Status and dates
    status: SubscriptionStatus = Field(
        default=SubscriptionStatus.ACTIVE,
        description="Current status"
    )
    start_date: date = Field(
        ...,
        description="Subscription start date"
    )
    expiry_date: date = Field(
        ...,
        description="Subscription expiry date"
    )
    
    # Trial handling
    is_trial: bool = Field(
        default=False,
        description="Whether this is a trial"
    )
    trial_end_date: Optional[date] = Field(
        default=None,
        description="Trial end date"
    )
    
    # Active flag (only one active per user)
    is_active: bool = Field(
        default=True,
        description="Whether subscription is currently active"
    )
    
    # Feature flags (embedded)
    features: FeatureFlags = Field(
        default_factory=FeatureFlags,
        description="Feature access flags"
    )
    
    # Payment info (embedded)
    payment_info: Optional[PaymentInfo] = Field(
        default=None,
        description="Payment transaction details"
    )
    
    # Institute override (for B2B)
    institute_id: Optional[PyObjectId] = Field(
        default=None,
        description="Institute providing the subscription"
    )
    is_institute_provided: bool = Field(
        default=False,
        description="Whether institute is paying"
    )
    
    # Cancellation
    cancelled_at: Optional[datetime] = Field(
        default=None,
        description="Cancellation timestamp"
    )
    cancellation_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason for cancellation"
    )
    
    # Auto-renewal
    auto_renew: bool = Field(
        default=True,
        description="Auto-renewal enabled"
    )
    renewal_reminder_sent: bool = Field(
        default=False,
        description="Whether renewal reminder was sent"
    )
    
    # Upgrade/downgrade tracking
    previous_plan: Optional[SubscriptionPlan] = Field(
        default=None,
        description="Previous plan (if changed)"
    )
    plan_changed_at: Optional[datetime] = Field(
        default=None,
        description="When plan was changed"
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if subscription is expired."""
        return date.today() > self.expiry_date
    
    @property
    def days_until_expiry(self) -> int:
        """Days remaining until expiry."""
        delta = self.expiry_date - date.today()
        return max(0, delta.days)


# -----------------------------------------------------------------------------
# Pricing Model (reference data)
# -----------------------------------------------------------------------------

class PlanPricingModel(MongoBaseModel):
    """
    Plan pricing reference.
    
    Collection: plan_pricing
    
    Indexes:
    - (plan, billing_cycle) unique compound
    - is_active
    """
    
    plan: SubscriptionPlan = Field(
        ...,
        description="Plan type"
    )
    billing_cycle: BillingCycle = Field(
        ...,
        description="Billing cycle"
    )
    
    # Pricing
    base_price: float = Field(
        ...,
        ge=0,
        description="Base price in INR"
    )
    discount_percentage: float = Field(
        default=0,
        ge=0,
        le=100,
        description="Discount percentage"
    )
    final_price: float = Field(
        ...,
        ge=0,
        description="Final price after discount"
    )
    
    # GST
    gst_percentage: float = Field(
        default=18.0,
        description="GST percentage"
    )
    gst_amount: float = Field(
        default=0,
        ge=0,
        description="GST amount"
    )
    total_price: float = Field(
        ...,
        ge=0,
        description="Total including GST"
    )
    
    # Validity
    is_active: bool = Field(
        default=True,
        description="Whether pricing is active"
    )
    valid_from: date = Field(
        ...,
        description="Pricing valid from"
    )
    valid_until: Optional[date] = Field(
        default=None,
        description="Pricing valid until"
    )


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------

class SubscriptionCreateDTO(BaseModel):
    """DTO for creating subscription."""
    
    plan: SubscriptionPlan
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    payment_info: Optional[PaymentInfo] = None


class SubscriptionUpgradeDTO(BaseModel):
    """DTO for upgrading subscription."""
    
    new_plan: SubscriptionPlan
    billing_cycle: BillingCycle
    prorate: bool = True
