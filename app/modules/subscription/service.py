"""
Subscription Service

Business logic for subscription management and feature access control.
"""

from datetime import date, datetime, timedelta
from typing import List

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.subscription.dependencies import get_subscription_model
from app.modules.subscription.models import (
    PLAN_FEATURES,
    PLAN_HIERARCHY,
    PLAN_LIMITS,
    FeatureFlag,
    PlanType,
    SubscriptionStatus,
    get_plan_limit,
    has_feature_access,
)
from app.modules.subscription.repository import SubscriptionRepository, UsageRepository
from app.modules.subscription.schemas import (
    PlanComparisonResponse,
    PlanDetailsResponse,
    PlanFeatureResponse,
    PlanFeaturesResponse,
    SubscriptionResponse,
    UsageLimitResponse,
)


class SubscriptionService:
    """Service for subscription management."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.subscription_repo = SubscriptionRepository(db)
        self.usage_repo = UsageRepository(db)
    
    async def get_current_subscription(
        self,
        user_id: str
    ) -> SubscriptionResponse:
        """
        Get user's current subscription.
        
        Creates Free subscription if none exists.
        
        Args:
            user_id: User ID
        
        Returns:
            SubscriptionResponse
        """
        # Get or create subscription
        subscription = await get_subscription_model(user_id, self.db)
        
        # Calculate days remaining
        days_remaining = None
        if subscription.end_date:
            delta = subscription.end_date - datetime.utcnow()
            days_remaining = max(0, delta.days)
        
        # Check if active
        is_active = subscription.status in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.GRACE_PERIOD
        ]
        
        # Check grace period
        in_grace_period = subscription.status == SubscriptionStatus.GRACE_PERIOD
        
        return SubscriptionResponse(
            plan_type=subscription.plan_type.value,
            status=subscription.status.value,
            start_date=subscription.start_date.isoformat(),
            end_date=subscription.end_date.isoformat() if subscription.end_date else None,
            is_active=is_active,
            days_remaining=days_remaining,
            auto_renew=subscription.auto_renew,
            in_grace_period=in_grace_period,
            grace_period_until=subscription.grace_period_until.isoformat() if subscription.grace_period_until else None
        )
    
    async def upgrade_plan(
        self,
        user_id: str,
        new_plan: PlanType
    ) -> SubscriptionResponse:
        """
        Upgrade user's plan.
        
        Rules:
        - Immediate effect
        - Usage limits expanded
        - Features unlocked
        - End date set to 30 days from now
        
        Args:
            user_id: User ID
            new_plan: Target plan (must be higher than current)
        
        Returns:
            Updated SubscriptionResponse
        
        Raises:
            BadRequestException: If invalid upgrade
        """
        # Get current subscription
        subscription = await get_subscription_model(user_id, self.db)
        
        # Validate upgrade
        current_level = PLAN_HIERARCHY.get(subscription.plan_type, 0)
        new_level = PLAN_HIERARCHY.get(new_plan, 0)
        
        if new_level <= current_level:
            raise BadRequestException(
                message=f"Cannot upgrade from {subscription.plan_type.value} to {new_plan.value}"
            )
        
        # Calculate new end date (30 days from now for paid plans)
        new_end_date = datetime.utcnow() + timedelta(days=30)
        
        # Update subscription (immediate effect)
        updates = {
            "plan_type": new_plan.value,
            "status": SubscriptionStatus.ACTIVE.value,
            "start_date": datetime.utcnow(),
            "end_date": new_end_date,
            "previous_plan": subscription.plan_type.value,
            "grace_period_until": None,  # Clear any grace period
            "auto_renew": True
        }
        
        updated = await self.subscription_repo.update_subscription(
            str(subscription.id),
            user_id,
            updates
        )
        
        if not updated:
            raise NotFoundException(message="Subscription not found")
        
        return await self.get_current_subscription(user_id)
    
    async def downgrade_plan(
        self,
        user_id: str,
        new_plan: PlanType
    ) -> SubscriptionResponse:
        """
        Downgrade user's plan.
        
        Rules:
        - Effective at current period end
        - Grace period: 7 days after end_date
        - Features locked after grace period
        - Data preserved (but hidden if over limits)
        
        Args:
            user_id: User ID
            new_plan: Target plan (must be lower than current)
        
        Returns:
            Updated SubscriptionResponse
        
        Raises:
            BadRequestException: If invalid downgrade
        """
        # Get current subscription
        subscription = await get_subscription_model(user_id, self.db)
        
        # Validate downgrade
        current_level = PLAN_HIERARCHY.get(subscription.plan_type, 0)
        new_level = PLAN_HIERARCHY.get(new_plan, 0)
        
        if new_level >= current_level:
            raise BadRequestException(
                message=f"Cannot downgrade from {subscription.plan_type.value} to {new_plan.value}"
            )
        
        # Calculate grace period (7 days after current end_date)
        if subscription.end_date:
            grace_period_until = subscription.end_date + timedelta(days=7)
        else:
            # Current is Free (no end_date), should not happen
            grace_period_until = datetime.utcnow() + timedelta(days=7)
        
        # Update subscription (enters grace period)
        updates = {
            "status": SubscriptionStatus.GRACE_PERIOD.value,
            "previous_plan": subscription.plan_type.value,
            "grace_period_until": grace_period_until,
            # Plan type remains same during grace period
            # External job will change plan_type after grace period
        }
        
        updated = await self.subscription_repo.update_subscription(
            str(subscription.id),
            user_id,
            updates
        )
        
        if not updated:
            raise NotFoundException(message="Subscription not found")
        
        return await self.get_current_subscription(user_id)
    
    async def cancel_subscription(
        self,
        user_id: str
    ) -> SubscriptionResponse:
        """
        Cancel subscription.
        
        Rules:
        - Status → cancelled
        - Access continues until end_date
        - No auto-renewal
        - Reverts to Free after end_date
        
        Args:
            user_id: User ID
        
        Returns:
            Updated SubscriptionResponse
        
        Raises:
            NotFoundException: If subscription not found
        """
        # Get current subscription
        subscription = await get_subscription_model(user_id, self.db)
        
        # Can't cancel Free plan
        if subscription.plan_type == PlanType.FREE:
            raise BadRequestException(
                message="Cannot cancel Free plan"
            )
        
        # Cancel subscription
        cancelled = await self.subscription_repo.cancel_subscription(
            str(subscription.id),
            user_id
        )
        
        if not cancelled:
            raise NotFoundException(message="Subscription not found")
        
        return await self.get_current_subscription(user_id)
    
    async def get_plan_features(
        self,
        user_id: str
    ) -> PlanFeaturesResponse:
        """
        Get features available in user's plan.
        
        Args:
            user_id: User ID
        
        Returns:
            PlanFeaturesResponse with features and limits
        """
        # Get subscription
        subscription = await get_subscription_model(user_id, self.db)
        
        # Get plan features
        plan_features = PLAN_FEATURES.get(subscription.plan_type, set())
        
        # Build feature list with descriptions
        feature_responses = []
        
        feature_descriptions = {
            FeatureFlag.STUDY_PROFILE: ("Study Profile", "Create and manage study profiles"),
            FeatureFlag.DAILY_PLANNER: ("Daily Planner", "Plan your daily study tasks"),
            FeatureFlag.TASK_EXECUTION: ("Task Execution", "Track task completion and progress"),
            FeatureFlag.BASIC_ANALYTICS: ("Basic Analytics", "View last 7 days analytics"),
            FeatureFlag.SMART_REVISION: ("Smart Revision", "AI-powered spaced repetition system"),
            FeatureFlag.ADVANCED_ANALYTICS: ("Advanced Analytics", "90-day analytics history"),
            FeatureFlag.NOTIFICATIONS: ("Notifications", "Smart study reminders"),
            FeatureFlag.DATA_EXPORT: ("Data Export", "Export your study data"),
            FeatureFlag.AI_PLANNER: ("AI Study Planner", "AI-generated study schedules"),
            FeatureFlag.AI_PRIORITIZATION: ("AI Prioritization", "Smart task prioritization"),
            FeatureFlag.PRIORITY_SUPPORT: ("Priority Support", "Priority customer support"),
            FeatureFlag.EARLY_ACCESS: ("Early Access", "Early access to new features"),
        }
        
        for feature in FeatureFlag:
            name, description = feature_descriptions.get(feature, (feature.value, ""))
            available = feature in plan_features
            
            feature_responses.append(PlanFeatureResponse(
                feature=feature.value,
                name=name,
                description=description,
                available=available
            ))
        
        # Get plan limits
        limits = PLAN_LIMITS.get(subscription.plan_type, {})
        
        return PlanFeaturesResponse(
            plan_type=subscription.plan_type.value,
            features=feature_responses,
            limits=limits
        )
    
    async def check_usage_limit(
        self,
        user_id: str,
        limit_type: str
    ) -> UsageLimitResponse:
        """
        Check usage limit status.
        
        Args:
            user_id: User ID
            limit_type: Limit to check (subjects, tasks_per_day, chapters)
        
        Returns:
            UsageLimitResponse
        """
        # Get subscription
        subscription = await get_subscription_model(user_id, self.db)
        
        # Get limit for this plan
        limit = get_plan_limit(subscription.plan_type, limit_type)
        
        # Get current usage
        if limit_type == "tasks_per_day":
            # Daily limit
            current_usage = await self.usage_repo.get_daily_usage(
                user_id, limit_type, date.today()
            )
        else:
            # Monthly limit (subjects, chapters)
            current_month = date.today().strftime("%Y-%m")
            current_usage = await self.usage_repo.get_monthly_usage(
                user_id, limit_type, current_month
            )
        
        # Calculate percentage
        if limit == -1:
            # Unlimited
            percentage = 0.0
            is_available = True
        else:
            percentage = (current_usage / limit * 100) if limit > 0 else 100.0
            is_available = current_usage < limit
        
        return UsageLimitResponse(
            limit_type=limit_type,
            current_usage=current_usage,
            limit=limit,
            percentage_used=min(100.0, percentage),
            is_available=is_available
        )
    
    async def get_all_usage_limits(
        self,
        user_id: str
    ) -> List[UsageLimitResponse]:
        """
        Get all usage limits for user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of UsageLimitResponse
        """
        limit_types = ["subjects", "tasks_per_day", "chapters"]
        limits = []
        
        for limit_type in limit_types:
            limit_response = await self.check_usage_limit(user_id, limit_type)
            limits.append(limit_response)
        
        return limits
    
    async def track_usage(
        self,
        user_id: str,
        feature: str
    ):
        """
        Track feature usage (increment counter).
        
        Args:
            user_id: User ID
            feature: Feature to track (subjects, tasks_per_day, chapters)
        """
        if feature == "tasks_per_day":
            # Daily tracking
            await self.usage_repo.increment_daily_usage(
                user_id, feature, date.today()
            )
        else:
            # Monthly tracking
            current_month = date.today().strftime("%Y-%m")
            await self.usage_repo.increment_monthly_usage(
                user_id, feature, current_month
            )
    
    def get_plan_comparison(self) -> PlanComparisonResponse:
        """
        Get comparison of all available plans.
        
        Returns:
            PlanComparisonResponse
        """
        plans = []
        
        # Free Plan
        plans.append(PlanDetailsResponse(
            plan_type="free",
            name="Free Plan",
            description="Get started with basic study planning",
            price_monthly=0.0,
            features=[
                "Study Profile",
                "Daily Planner (5 tasks/day)",
                "Basic Analytics (7 days)"
            ],
            limits=PLAN_LIMITS[PlanType.FREE]
        ))
        
        # Pro Plan
        plans.append(PlanDetailsResponse(
            plan_type="pro",
            name="Pro Plan",
            description="Advanced features for serious students",
            price_monthly=9.99,
            features=[
                "All Free features",
                "Smart Revision Engine",
                "Advanced Analytics (90 days)",
                "Notifications",
                "Data Export",
                "Unlimited tasks"
            ],
            limits=PLAN_LIMITS[PlanType.PRO]
        ))
        
        # Smart Pack Plan
        plans.append(PlanDetailsResponse(
            plan_type="smart_pack",
            name="Smart Pack",
            description="Full AI-powered study experience",
            price_monthly=19.99,
            features=[
                "All Pro features",
                "AI Study Planner",
                "AI Task Prioritization",
                "Priority Support",
                "Early Access to new features",
                "Unlimited everything"
            ],
            limits=PLAN_LIMITS[PlanType.SMART_PACK]
        ))
        
        return PlanComparisonResponse(plans=plans)
