"""
Subscription Schemas

Request and response models for subscription API endpoints.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------

class SubscriptionResponse(BaseModel):
    """User's subscription details."""
    
    plan_type: str = Field(..., description="Current plan: free, pro, or smart_pack")
    status: str = Field(..., description="Status: active, expired, cancelled, grace_period")
    start_date: str = Field(..., description="When this plan started (ISO format)")
    end_date: Optional[str] = Field(None, description="When this plan expires (None for Free)")
    is_active: bool = Field(..., description="True if user can access features")
    days_remaining: Optional[int] = Field(None, description="Days until expiration (None for Free)")
    auto_renew: bool = Field(..., description="Auto-renewal enabled")
    in_grace_period: bool = Field(..., description="True if in downgrade grace period")
    grace_period_until: Optional[str] = Field(None, description="Grace period end date")


class PlanFeatureResponse(BaseModel):
    """Single feature details."""
    
    feature: str = Field(..., description="Feature flag name")
    name: str = Field(..., description="Human-readable feature name")
    description: str = Field(..., description="Feature description")
    available: bool = Field(..., description="True if available in current plan")


class PlanFeaturesResponse(BaseModel):
    """Complete plan features list."""
    
    plan_type: str
    features: List[PlanFeatureResponse]
    limits: Dict[str, int] = Field(
        ...,
        description="Usage limits (-1 = unlimited)"
    )


class UsageLimitResponse(BaseModel):
    """Usage limit status."""
    
    limit_type: str = Field(..., description="Limit type: subjects, tasks_per_day, chapters")
    current_usage: int = Field(..., ge=0, description="Current usage count")
    limit: int = Field(..., description="Limit value (-1 = unlimited)")
    percentage_used: float = Field(..., ge=0, le=100, description="Percentage of limit used")
    is_available: bool = Field(
        ...,
        description="True if user can create more (under limit or unlimited)"
    )


class PlanDetailsResponse(BaseModel):
    """Details for a single plan (for comparison)."""
    
    plan_type: str
    name: str
    description: str
    price_monthly: float  # Placeholder (no payment integration)
    features: List[str]
    limits: Dict[str, int]


class PlanComparisonResponse(BaseModel):
    """Compare all available plans."""
    
    plans: List[PlanDetailsResponse]


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------

class UpgradeRequest(BaseModel):
    """Request to upgrade plan."""
    
    new_plan: str = Field(
        ...,
        pattern="^(pro|smart_pack)$",
        description="Target plan: pro or smart_pack"
    )


class DowngradeRequest(BaseModel):
    """Request to downgrade plan."""
    
    new_plan: str = Field(
        ...,
        pattern="^(free|pro)$",
        description="Target plan: free or pro"
    )
