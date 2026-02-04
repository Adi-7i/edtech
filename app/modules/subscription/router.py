"""
Subscription Router

API endpoints for subscription and feature control.
"""

from typing import List

from fastapi import APIRouter, Depends

from app.core.database.mongo import get_database
from app.core.responses.base import SuccessResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.subscription.models import PlanType
from app.modules.subscription.schemas import (
    DowngradeRequest,
    PlanComparisonResponse,
    PlanFeaturesResponse,
    SubscriptionResponse,
    UpgradeRequest,
    UsageLimitResponse,
)
from app.modules.subscription.service import SubscriptionService
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/subscription", tags=["Subscription"])


def get_subscription_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> SubscriptionService:
    """Dependency injection for subscription service."""
    return SubscriptionService(db)


@router.get(
    "/current",
    response_model=SuccessResponse[SubscriptionResponse],
    summary="Get Current Subscription",
    description="""
    Get user's current subscription details.
    
    **Returns:**
    - Plan type (free, pro, smart_pack)
    - Status (active, cancelled, expired, grace_period)
    - Start and end dates
    - Days remaining
    - Auto-renewal status
    - Grace period status
    
    **Note:** Creates Free subscription if none exists.
    """
)
async def get_current_subscription(
    current_user: dict = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get user's current subscription.
    
    Returns:
    - SubscriptionResponse
    """
    user_id = current_user["id"]
    
    result = await service.get_current_subscription(user_id)
    
    return SuccessResponse(
        message="Subscription retrieved successfully",
        status_code=200,
        data=result
    )


@router.post(
    "/upgrade",
    response_model=SuccessResponse[SubscriptionResponse],
    summary="Upgrade Plan",
    description="""
    Upgrade to a higher plan (Pro or Smart Pack).
    
    **Rules:**
    - Immediate effect
    - Usage limits expanded immediately
    - New features unlocked
    - End date set to 30 days from now
    
    **Examples:**
    - Free → Pro
    - Free → Smart Pack
    - Pro → Smart Pack
    
    **Note:** This API does NOT handle payment. Payment integration is external.
    """
)
async def upgrade_plan(
    request: UpgradeRequest,
    current_user: dict = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Upgrade user's plan.
    
    Body:
    - UpgradeRequest with new_plan
    
    Returns:
    - Updated SubscriptionResponse
    """
    user_id = current_user["id"]
    
    # Convert string to enum
    new_plan = PlanType(request.new_plan)
    
    result = await service.upgrade_plan(user_id, new_plan)
    
    return SuccessResponse(
        message=f"Successfully upgraded to {new_plan.value} plan",
        status_code=200,
        data=result
    )


@router.post(
    "/downgrade",
    response_model=SuccessResponse[SubscriptionResponse],
    summary="Downgrade Plan",
    description="""
    Downgrade to a lower plan (Pro or Free).
    
    **Rules:**
    - Effective at current period end
    - Grace period: 7 days after end_date
    - Features remain accessible during grace period
    - Data preserved (but hidden if over new limits)
    
    **Examples:**
    - Smart Pack → Pro
    - Smart Pack → Free
    - Pro → Free
    
    **Status Changes:**
    1. Request downgrade → Status: grace_period
    2. After grace period → External job changes plan_type
    """
)
async def downgrade_plan(
    request: DowngradeRequest,
    current_user: dict = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Downgrade user's plan.
    
    Body:
    - DowngradeRequest with new_plan
    
    Returns:
    - Updated SubscriptionResponse
    """
    user_id = current_user["id"]
    
    # Convert string to enum
    new_plan = PlanType(request.new_plan)
    
    result = await service.downgrade_plan(user_id, new_plan)
    
    return SuccessResponse(
        message=f"Downgrade to {new_plan.value} plan scheduled. Grace period active.",
        status_code=200,
        data=result
    )


@router.post(
    "/cancel",
    response_model=SuccessResponse[SubscriptionResponse],
    summary="Cancel Subscription",
    description="""
    Cancel current subscription.
    
    **Rules:**
    - Status changes to "cancelled"
    - Access continues until end_date
    - No auto-renewal
    - Reverts to Free plan after end_date
    - Can reactivate before end_date by upgrading
    
    **Note:** Cannot cancel Free plan (already free!).
    """
)
async def cancel_subscription(
    current_user: dict = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Cancel user's subscription.
    
    Returns:
    - Updated SubscriptionResponse
    """
    user_id = current_user["id"]
    
    result = await service.cancel_subscription(user_id)
    
    return SuccessResponse(
        message="Subscription cancelled. Access continues until end date.",
        status_code=200,
        data=result
    )


@router.get(
    "/features",
    response_model=SuccessResponse[PlanFeaturesResponse],
    summary="Get Plan Features",
    description="""
    Get features available in user's current plan.
    
    **Returns:**
    - List of all features with availability status
    - Usage limits for current plan
    
    **Use Case:**
    - Display feature list in settings
    - Show upgrade prompts for locked features
    - Feature comparison in upgrade flow
    """
)
async def get_plan_features(
    current_user: dict = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get features for user's plan.
    
    Returns:
    - PlanFeaturesResponse
    """
    user_id = current_user["id"]
    
    result = await service.get_plan_features(user_id)
    
    return SuccessResponse(
        message="Features retrieved successfully",
        status_code=200,
        data=result
    )


@router.get(
    "/usage",
    response_model=SuccessResponse[List[UsageLimitResponse]],
    summary="Get Usage Limits",
    description="""
    Get usage limits status for user's plan.
    
    **Returns:**
    - Current usage for each limit type
    - Limit value (-1 = unlimited)
    - Percentage used
    - Availability status
    
    **Limit Types:**
    - subjects: Total subjects created
    - tasks_per_day: Tasks created today
    - chapters: Total chapters created
    
    **Use Case:**
    - Display usage meters in UI
    - Show "upgrade to create more" prompts
    - Track limit approaching
    """
)
async def get_usage_limits(
    current_user: dict = Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get all usage limits for user.
    
    Returns:
    - List of UsageLimitResponse
    """
    user_id = current_user["id"]
    
    result = await service.get_all_usage_limits(user_id)
    
    return SuccessResponse(
        message="Usage limits retrieved successfully",
        status_code=200,
        data=result
    )


@router.get(
    "/plans",
    response_model=SuccessResponse[PlanComparisonResponse],
    summary="Compare Plans",
    description="""
    Get comparison of all available plans.
    
    **Public endpoint** - No authentication required.
    
    **Returns:**
    - Details for all plans
    - Features per plan
    - Limits per plan
    - Pricing (placeholder values)
    
    **Use Case:**
    - Display pricing page
    - Upgrade flow plan selection
    - Marketing material
    """
)
async def compare_plans(
    service: SubscriptionService = Depends(get_subscription_service)
):
    """
    Get plan comparison.
    
    Returns:
    - PlanComparisonResponse
    """
    result = service.get_plan_comparison()
    
    return SuccessResponse(
        message="Plans retrieved successfully",
        status_code=200,
        data=result
    )
