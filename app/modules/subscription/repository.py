"""
Subscription Repository

Data access layer for subscriptions and usage tracking.
"""

from datetime import date, datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.subscription.models import (
    PlanType,
    SubscriptionModel,
    SubscriptionStatus,
    UsageTrackingModel,
)


class SubscriptionRepository:
    """Repository for subscription operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.subscriptions
    
    async def get_subscription(
        self,
        user_id: str
    ) -> Optional[SubscriptionModel]:
        """
        Get user's subscription.
        
        Args:
            user_id: User ID
        
        Returns:
            SubscriptionModel if found, None otherwise
        """
        doc = await self.collection.find_one({
            "user_id": ObjectId(user_id)
        })
        
        if doc:
            return SubscriptionModel(**doc)
        
        return None
    
    async def create_subscription(
        self,
        user_id: str,
        plan_type: PlanType,
        end_date: Optional[datetime] = None
    ) -> SubscriptionModel:
        """
        Create new subscription.
        
        Args:
            user_id: User ID
            plan_type: Plan type
            end_date: When subscription expires (None for Free)
        
        Returns:
            Created SubscriptionModel
        """
        subscription = SubscriptionModel(
            user_id=ObjectId(user_id),
            plan_type=plan_type,
            status=SubscriptionStatus.ACTIVE,
            start_date=datetime.utcnow(),
            end_date=end_date,
            auto_renew=True
        )
        
        result = await self.collection.insert_one(subscription.to_mongo())
        subscription.id = result.inserted_id
        
        return subscription
    
    async def update_subscription(
        self,
        subscription_id: str,
        user_id: str,
        updates: dict
    ) -> Optional[SubscriptionModel]:
        """
        Update subscription.
        
        Args:
            subscription_id: Subscription ID
            user_id: User ID (for ownership check)
            updates: Fields to update
        
        Returns:
            Updated SubscriptionModel if found, None otherwise
        """
        # Add updated_at timestamp
        updates["updated_at"] = datetime.utcnow()
        
        result = await self.collection.find_one_and_update(
            {
                "_id": ObjectId(subscription_id),
                "user_id": ObjectId(user_id)
            },
            {"$set": updates},
            return_document=True
        )
        
        if result:
            return SubscriptionModel(**result)
        
        return None
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        user_id: str
    ) -> Optional[SubscriptionModel]:
        """
        Cancel subscription.
        
        Sets status to cancelled and auto_renew to False.
        Access continues until end_date.
        
        Args:
            subscription_id: Subscription ID
            user_id: User ID (for ownership check)
        
        Returns:
            Updated SubscriptionModel if found, None otherwise
        """
        result = await self.collection.find_one_and_update(
            {
                "_id": ObjectId(subscription_id),
                "user_id": ObjectId(user_id)
            },
            {
                "$set": {
                    "status": SubscriptionStatus.CANCELLED.value,
                    "auto_renew": False,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        
        if result:
            return SubscriptionModel(**result)
        
        return None


class UsageRepository:
    """Repository for usage tracking operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.usage_tracking
    
    async def get_daily_usage(
        self,
        user_id: str,
        feature: str,
        target_date: date
    ) -> int:
        """
        Get usage count for a feature on a specific date.
        
        Args:
            user_id: User ID
            feature: Feature name (e.g., "tasks_per_day")
            target_date: Date to check
        
        Returns:
            Usage count (0 if no tracking record exists)
        """
        # Convert date to datetime for MongoDB
        date_dt = datetime.combine(target_date, datetime.min.time())
        
        doc = await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "feature": feature,
            "period": "daily",
            "date": date_dt
        })
        
        if doc:
            return doc.get("count", 0)
        
        return 0
    
    async def get_monthly_usage(
        self,
        user_id: str,
        feature: str,
        month: str  # YYYY-MM format
    ) -> int:
        """
        Get usage count for a feature in a month.
        
        Args:
            user_id: User ID
            feature: Feature name (e.g., "subjects", "chapters")
            month: Month in YYYY-MM format
        
        Returns:
            Usage count (0 if no tracking record exists)
        """
        doc = await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "feature": feature,
            "period": "monthly",
            "month": month
        })
        
        if doc:
            return doc.get("count", 0)
        
        return 0
    
    async def increment_daily_usage(
        self,
        user_id: str,
        feature: str,
        target_date: date,
        increment: int = 1
    ) -> UsageTrackingModel:
        """
        Increment daily usage counter.
        
        Args:
            user_id: User ID
            feature: Feature name
            target_date: Date to track
            increment: Amount to increment (default 1)
        
        Returns:
            Updated UsageTrackingModel
        """
        date_dt = datetime.combine(target_date, datetime.min.time())
        
        result = await self.collection.find_one_and_update(
            {
                "user_id": ObjectId(user_id),
                "feature": feature,
                "period": "daily",
                "date": date_dt
            },
            {
                "$inc": {"count": increment},
                "$setOnInsert": {
                    "user_id": ObjectId(user_id),
                    "feature": feature,
                    "period": "daily",
                    "date": date_dt,
                    "created_at": datetime.utcnow()
                },
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True,
            return_document=True
        )
        
        return UsageTrackingModel(**result)
    
    async def increment_monthly_usage(
        self,
        user_id: str,
        feature: str,
        month: str,  # YYYY-MM format
        increment: int = 1
    ) -> UsageTrackingModel:
        """
        Increment monthly usage counter.
        
        Args:
            user_id: User ID
            feature: Feature name
            month: Month in YYYY-MM format
            increment: Amount to increment (default 1)
        
        Returns:
            Updated UsageTrackingModel
        """
        result = await self.collection.find_one_and_update(
            {
                "user_id": ObjectId(user_id),
                "feature": feature,
                "period": "monthly",
                "month": month
            },
            {
                "$inc": {"count": increment},
                "$setOnInsert": {
                    "user_id": ObjectId(user_id),
                    "feature": feature,
                    "period": "monthly",
                    "month": month,
                    "created_at": datetime.utcnow()
                },
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True,
            return_document=True
        )
        
        return UsageTrackingModel(**result)
