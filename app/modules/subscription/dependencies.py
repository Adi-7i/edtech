"""
Subscription Dependencies

Centralized permission system for feature access control.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.mongo import get_database
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.auth.dependencies import get_current_user
from app.modules.subscription.models import (
    FeatureFlag,
    PlanType,
    SubscriptionModel,
    SubscriptionStatus,
    get_required_plan_for_feature,
    has_feature_access,
    meets_plan_requirement,
)


async def get_subscription_model(
    user_id: str,
    db: AsyncIOMotorDatabase
) -> SubscriptionModel:
    """
    Get user's subscription model (internal helper).
    
    Creates Free subscription if none exists.
    
    Args:
        user_id: User ID
        db: Database instance
    
    Returns:
        SubscriptionModel
    """
    subscriptions_collection = db.subscriptions
    
    # Try to find existing subscription
    sub_doc = await subscriptions_collection.find_one({
        "user_id": ObjectId(user_id)
    })
    
    if sub_doc:
        return SubscriptionModel(**sub_doc)
    
    # Create Free subscription for new user
    new_subscription = SubscriptionModel(
        user_id=ObjectId(user_id),
        plan_type=PlanType.FREE,
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime.utcnow(),
        end_date=None,  # Free never expires
        auto_renew=True
    )
    
    await subscriptions_collection.insert_one(new_subscription.to_mongo())
    
    return new_subscription


async def get_subscription(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> SubscriptionModel:
    """
    Dependency to get user's subscription.
    
    Used in routers to access subscription data.
    Creates Free subscription if none exists.
    
    Returns:
        SubscriptionModel
    """
    user_id = current_user["id"]
    return await get_subscription_model(user_id, db)


def require_feature(feature: FeatureFlag):
    """
    Dependency factory to enforce feature access.
    
    Usage in routers:
    ```python
    @router.post(
        "/revision/schedule",
        dependencies=[Depends(require_feature(FeatureFlag.SMART_REVISION))]
    )
    async def schedule_revision(...):
        # Feature logic - no plan checks needed!
    ```
    
    Args:
        feature: Feature flag to check
    
    Returns:
        Dependency function that raises 403 if access denied
    """
    async def check_access(
        subscription: SubscriptionModel = Depends(get_subscription)
    ):
        """Check if user has access to the feature."""
        
        # Check if subscription is active (or in grace period)
        if subscription.status not in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.GRACE_PERIOD
        ]:
            raise ForbiddenException(
                message=f"Subscription expired. Please renew to access {feature.value}"
            )
        
        # Check if plan includes this feature
        if not has_feature_access(subscription.plan_type, feature):
            required_plan = get_required_plan_for_feature(feature)
            raise ForbiddenException(
                message=f"Feature '{feature.value}' requires {required_plan.value} plan or higher"
            )
    
    return check_access


def require_plan(min_plan: PlanType):
    """
    Dependency factory to enforce minimum plan level.
    
    Usage in routers:
    ```python
    @router.get(
        "/analytics/advanced",
        dependencies=[Depends(require_plan(PlanType.PRO))]
    )
    async def get_advanced_analytics(...):
        # Feature logic
    ```
    
    Args:
        min_plan: Minimum required plan type
    
    Returns:
        Dependency function that raises 403 if plan insufficient
    """
    async def check_plan(
        subscription: SubscriptionModel = Depends(get_subscription)
    ):
        """Check if user's plan meets minimum requirement."""
        
        # Check if subscription is active
        if subscription.status not in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.GRACE_PERIOD
        ]:
            raise ForbiddenException(
                message=f"Subscription expired. Please renew to continue"
            )
        
        # Check plan level
        if not meets_plan_requirement(subscription.plan_type, min_plan):
            raise ForbiddenException(
                message=f"This feature requires {min_plan.value} plan or higher. You are on {subscription.plan_type.value}."
            )
    
    return check_plan
