"""
Notification Repository

Data access layer for notifications and user preferences.
"""

from datetime import date, datetime
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.notification import (
    NotificationModel,
    NotificationStatus,
    NotificationType,
    UserNotificationPreferences,
)


class NotificationRepository:
    """Repository for notification CRUD operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.notifications_collection = db.notifications
        self.preferences_collection = db.user_notification_preferences
    
    async def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        metadata: dict,
        scheduled_for: datetime
    ) -> NotificationModel:
        """
        Create a new notification event.
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            title: Short notification title
            message: Detailed message
            metadata: Context data
            scheduled_for: When to send this notification
        
        Returns:
            Created NotificationModel
        """
        notification = NotificationModel(
            user_id=ObjectId(user_id),
            type=notification_type,
            title=title,
            message=message,
            metadata=metadata,
            scheduled_for=scheduled_for
        )
        
        result = await self.notifications_collection.insert_one(
            notification.to_mongo()
        )
        
        notification.id = result.inserted_id
        return notification
    
    async def find_by_id(
        self,
        notification_id: str
    ) -> Optional[NotificationModel]:
        """
        Find notification by ID.
        
        Args:
            notification_id: Notification ID
        
        Returns:
            NotificationModel if found, None otherwise
        """
        doc = await self.notifications_collection.find_one({
            "_id": ObjectId(notification_id)
        })
        
        if doc:
            return NotificationModel(**doc)
        
        return None
    
    async def find_todays_notifications(
        self,
        user_id: str,
        target_date: date
    ) -> List[NotificationModel]:
        """
        Get all notifications for a specific date.
        
        Args:
            user_id: User ID
            target_date: Date to get notifications for
        
        Returns:
            List of notifications for the date
        """
        # Get start and end of day
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        cursor = self.notifications_collection.find({
            "user_id": ObjectId(user_id),
            "scheduled_for": {
                "$gte": start_of_day,
                "$lte": end_of_day
            }
        }).sort("scheduled_for", 1)
        
        docs = await cursor.to_list(length=100)
        
        return [NotificationModel(**doc) for doc in docs]
    
    async def find_duplicate(
        self,
        user_id: str,
        notification_type: NotificationType,
        target_date: date
    ) -> Optional[NotificationModel]:
        """
        Check if notification of same type exists for a date.
        
        Used for duplicate prevention (max 1 per type per day).
        
        Args:
            user_id: User ID
            notification_type: Type to check
            target_date: Date to check
        
        Returns:
            Existing notification if found, None otherwise
        """
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        doc = await self.notifications_collection.find_one({
            "user_id": ObjectId(user_id),
            "type": notification_type.value,
            "scheduled_for": {
                "$gte": start_of_day,
                "$lte": end_of_day
            }
        })
        
        if doc:
            return NotificationModel(**doc)
        
        return None
    
    async def count_by_type_today(
        self,
        user_id: str,
        notification_type: NotificationType,
        target_date: date
    ) -> int:
        """
        Count notifications of specific type for a date.
        
        Used for limits (e.g., max 3 break reminders per day).
        
        Args:
            user_id: User ID
            notification_type: Type to count
            target_date: Date to check
        
        Returns:
            Count of notifications
        """
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        count = await self.notifications_collection.count_documents({
            "user_id": ObjectId(user_id),
            "type": notification_type.value,
            "scheduled_for": {
                "$gte": start_of_day,
                "$lte": end_of_day
            }
        })
        
        return count
    
    async def mark_as_acknowledged(
        self,
        notification_id: str,
        user_id: str
    ) -> Optional[NotificationModel]:
        """
        Mark notification as acknowledged (read).
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for ownership check)
        
        Returns:
            Updated NotificationModel if found and updated, None otherwise
        """
        result = await self.notifications_collection.find_one_and_update(
            {
                "_id": ObjectId(notification_id),
                "user_id": ObjectId(user_id)
            },
            {
                "$set": {
                    "status": NotificationStatus.ACKNOWLEDGED.value,
                    "acknowledged_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        
        if result:
            return NotificationModel(**result)
        
        return None
    
    async def get_user_preferences(
        self,
        user_id: str
    ) -> UserNotificationPreferences:
        """
        Get user's notification preferences.
        
        Creates default preferences if none exist.
        
        Args:
            user_id: User ID
        
        Returns:
            UserNotificationPreferences
        """
        doc = await self.preferences_collection.find_one({
            "user_id": ObjectId(user_id)
        })
        
        if doc:
            return UserNotificationPreferences(**doc)
        
        # Create default preferences
        default_prefs = UserNotificationPreferences(
            user_id=ObjectId(user_id)
        )
        
        await self.preferences_collection.insert_one(
            default_prefs.to_mongo()
        )
        
        return default_prefs
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: dict
    ) -> UserNotificationPreferences:
        """
        Update user's notification preferences.
        
        Args:
            user_id: User ID
            preferences: Dictionary of preferences to update
        
        Returns:
            Updated UserNotificationPreferences
        """
        # Add updated timestamp
        preferences["updated_at"] = datetime.utcnow()
        
        result = await self.preferences_collection.find_one_and_update(
            {"user_id": ObjectId(user_id)},
            {"$set": preferences},
            upsert=True,
            return_document=True
        )
        
        return UserNotificationPreferences(**result)
