"""
Notification Service

Core business logic for generating notification events based on rules.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.notification import NotificationType, UserNotificationPreferences
from app.core.exceptions import NotFoundException
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import (
    GenerateNotificationsResponse,
    NotificationPreferencesResponse,
    NotificationResponse,
    TodaysNotificationsResponse,
)
from app.modules.notifications.utils import (
    generate_notification_message,
    generate_notification_title,
    is_within_silent_hours,
    should_send_study_start_reminder,
)


class NotificationService:
    """Service for generating and managing notification events."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.repository = NotificationRepository(db)
        
        # Collections for querying related data
        self.daily_plans_collection = db.daily_plans
        self.tasks_collection = db.study_tasks
        self.revisions_collection = db.revisions
        self.profiles_collection = db.study_profiles
    
    async def generate_notifications(
        self,
        user_id: str,
        target_date: Optional[date] = None
    ) -> GenerateNotificationsResponse:
        """
        Generate all applicable notifications for a user.
        
        Evaluates all notification types and creates events based on rules.
        
        Args:
            user_id: User ID
            target_date: Date to generate for (defaults to today)
        
        Returns:
            GenerateNotificationsResponse with generated notifications
        """
        if target_date is None:
            target_date = date.today()
        
        # Get user preferences
        preferences = await self.repository.get_user_preferences(user_id)
        
        generated_notifications = []
        skipped_count = 0
        
        # 1. Study Start Reminder
        if preferences.study_start_enabled:
            notification = await self._generate_study_start_reminder(
                user_id, target_date, preferences
            )
            if notification:
                generated_notifications.append(notification)
            else:
                skipped_count += 1
        
        # 2. Revision Reminders (max 2 per day)
        if preferences.revision_enabled:
            revision_notifications = await self._generate_revision_reminders(
                user_id, target_date, preferences
            )
            generated_notifications.extend(revision_notifications)
            if len(revision_notifications) == 0:
                skipped_count += 1
        
        # 3. Missed Task Alert (for yesterday)
        if preferences.missed_task_enabled:
            notification = await self._generate_missed_task_alert(
                user_id, target_date, preferences
            )
            if notification:
                generated_notifications.append(notification)
            else:
                skipped_count += 1
        
        # 4. Exam Reminders (at milestones)
        if preferences.exam_enabled:
            exam_notifications = await self._generate_exam_reminders(
                user_id, target_date, preferences
            )
            generated_notifications.extend(exam_notifications)
            if len(exam_notifications) == 0:
                skipped_count += 1
        
        # Convert to response format
        notification_responses = [
            self._to_notification_response(n) for n in generated_notifications
        ]
        
        return GenerateNotificationsResponse(
            generated_count=len(generated_notifications),
            notifications=notification_responses,
            skipped_count=skipped_count
        )
    
    async def get_todays_notifications(
        self,
        user_id: str,
        target_date: Optional[date] = None
    ) -> TodaysNotificationsResponse:
        """
        Get all notifications for today.
        
        Args:
            user_id: User ID
            target_date: Date to get notifications for (defaults to today)
        
        Returns:
            TodaysNotificationsResponse
        """
        if target_date is None:
            target_date = date.today()
        
        notifications = await self.repository.find_todays_notifications(
            user_id, target_date
        )
        
        # Convert to response format
        notification_responses = [
            self._to_notification_response(n) for n in notifications
        ]
        
        # Calculate counts
        total_count = len(notifications)
        pending_count = sum(1 for n in notifications if n.status.value == "pending")
        acknowledged_count = sum(1 for n in notifications if n.status.value == "acknowledged")
        
        return TodaysNotificationsResponse(
            date=target_date.isoformat(),
            notifications=notification_responses,
            total_count=total_count,
            pending_count=pending_count,
            acknowledged_count=acknowledged_count
        )
    
    async def acknowledge_notification(
        self,
        notification_id: str,
        user_id: str
    ) -> NotificationResponse:
        """
        Mark notification as acknowledged.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for ownership check)
        
        Returns:
            Updated NotificationResponse
        
        Raises:
            NotFoundException: If notification not found
        """
        updated = await self.repository.mark_as_acknowledged(
            notification_id, user_id
        )
        
        if not updated:
            raise NotFoundException(message="Notification not found")
        
        return self._to_notification_response(updated)
    
    async def get_user_preferences(
        self,
        user_id: str
    ) -> NotificationPreferencesResponse:
        """
        Get user's notification preferences.
        
        Args:
            user_id: User ID
        
        Returns:
            NotificationPreferencesResponse
        """
        preferences = await self.repository.get_user_preferences(user_id)
        
        return NotificationPreferencesResponse(
            study_start_enabled=preferences.study_start_enabled,
            break_enabled=preferences.break_enabled,
            revision_enabled=preferences.revision_enabled,
            missed_task_enabled=preferences.missed_task_enabled,
            exam_enabled=preferences.exam_enabled,
            silent_hours_start=preferences.silent_hours_start,
            silent_hours_end=preferences.silent_hours_end,
            created_at=preferences.created_at.isoformat(),
            updated_at=preferences.updated_at.isoformat()
        )
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences_data: dict
    ) -> NotificationPreferencesResponse:
        """
        Update user's notification preferences.
        
        Args:
            user_id: User ID
            preferences_data: Preferences to update
        
        Returns:
            Updated NotificationPreferencesResponse
        """
        # Remove None values
        update_data = {k: v for k, v in preferences_data.items() if v is not None}
        
        updated = await self.repository.update_user_preferences(
            user_id, update_data
        )
        
        return NotificationPreferencesResponse(
            study_start_enabled=updated.study_start_enabled,
            break_enabled=updated.break_enabled,
            revision_enabled=updated.revision_enabled,
            missed_task_enabled=updated.missed_task_enabled,
            exam_enabled=updated.exam_enabled,
            silent_hours_start=updated.silent_hours_start,
            silent_hours_end=updated.silent_hours_end,
            created_at=updated.created_at.isoformat(),
            updated_at=updated.updated_at.isoformat()
        )
    
    # -------------------------------------------------------------------------
    # Private Methods - Notification Generators
    # -------------------------------------------------------------------------
    
    async def _generate_study_start_reminder(
        self,
        user_id: str,
        target_date: date,
        preferences: UserNotificationPreferences
    ) -> Optional[object]:
        """
        Generate study start reminder.
        
        Rules:
        - Get daily plan for target_date
        - Find first task start time
        - Schedule 15 minutes before
        - Check silent hours
        - Check for duplicate
        
        Returns:
            NotificationModel if generated, None otherwise
        """
        # Check for duplicate
        duplicate = await self.repository.find_duplicate(
            user_id, NotificationType.STUDY_START, target_date
        )
        if duplicate:
            return None  # Already sent today
        
        # Get daily plan
        daily_plan = await self.daily_plans_collection.find_one({
            "user_id": ObjectId(user_id),
            "date": target_date
        })
        
        if not daily_plan:
            return None  # No plan for today
        
        # Get tasks for this plan
        tasks_cursor = self.tasks_collection.find({
            "daily_plan_id": daily_plan["_id"]
        }).sort("order", 1)
        
        tasks = await tasks_cursor.to_list(length=10)
        
        if not tasks:
            return None  # No tasks
        
        # Find first task start time (assuming tasks have start_time or use allocated_hours)
        # For simplicity, schedule for 8 AM if no specific time
        first_task = tasks[0]
        task_name = first_task.get("chapter_name", "your first task")
        
        # Schedule notification for 8:00 AM (15 min before 8:15 AM assumed start)
        notification_time = datetime.combine(target_date, datetime.min.time().replace(hour=8, minute=0))
        
        # Check silent hours
        if is_within_silent_hours(
            notification_time,
            preferences.silent_hours_start,
            preferences.silent_hours_end
        ):
            return None  # Within silent hours
        
        # Generate notification
        metadata = {
            "task_id": str(first_task["_id"]),
            "task_name": task_name,
            "start_time": "8:15 AM"
        }
        
        title = generate_notification_title(NotificationType.STUDY_START, metadata)
        message = generate_notification_message(NotificationType.STUDY_START, metadata)
        
        notification = await self.repository.create_notification(
            user_id=user_id,
            notification_type=NotificationType.STUDY_START,
            title=title,
            message=message,
            metadata=metadata,
            scheduled_for=notification_time
        )
        
        return notification
    
    async def _generate_revision_reminders(
        self,
        user_id: str,
        target_date: date,
        preferences: UserNotificationPreferences
    ) -> List[object]:
        """
        Generate revision reminders.
        
        Rules:
        - Query revisions due today
        - Max 2 per day
        - Priority: overdue first
        - Check silent hours
        
        Returns:
            List of NotificationModels
        """
        # Check how many already sent today
        existing_count = await self.repository.count_by_type_today(
            user_id, NotificationType.REVISION, target_date
        )
        
        if existing_count >= 2:
            return []  # Max 2 per day
        
        # Get revisions due today
        from bson import ObjectId
        
        revisions_cursor = self.revisions_collection.find({
            "user_id": ObjectId(user_id),
            "next_revision_date": target_date,
            "status": {"$ne": "completed"}
        }).limit(2 - existing_count)
        
        revisions = await revisions_cursor.to_list(length=2)
        
        notifications = []
        
        for revision in revisions:
            # Schedule for 9 AM
            notification_time = datetime.combine(
                target_date,
                datetime.min.time().replace(hour=9, minute=0)
            )
            
            # Check silent hours
            if is_within_silent_hours(
                notification_time,
                preferences.silent_hours_start,
                preferences.silent_hours_end
            ):
                continue
            
            metadata = {
                "revision_id": str(revision["_id"]),
                "chapter_id": str(revision.get("chapter_id", "")),
                "chapter_name": revision.get("chapter_name", "Chapter"),
                "subject_name": revision.get("subject_name", ""),
                "cycle_day": revision.get("current_cycle_day", 1)
            }
            
            title = generate_notification_title(NotificationType.REVISION, metadata)
            message = generate_notification_message(NotificationType.REVISION, metadata)
            
            notification = await self.repository.create_notification(
                user_id=user_id,
                notification_type=NotificationType.REVISION,
                title=title,
                message=message,
                metadata=metadata,
                scheduled_for=notification_time
            )
            
            notifications.append(notification)
        
        return notifications
    
    async def _generate_missed_task_alert(
        self,
        user_id: str,
        target_date: date,
        preferences: UserNotificationPreferences
    ) -> Optional[object]:
        """
        Generate missed task alert for yesterday.
        
        Rules:
        - Check yesterday's plan
        - Only if completion rate < 70%
        - Schedule for 8 PM
        - Max 1 per day
        
        Returns:
            NotificationModel if generated, None otherwise
        """
        # Check for duplicate
        duplicate = await self.repository.find_duplicate(
            user_id, NotificationType.MISSED_TASK, target_date
        )
        if duplicate:
            return None
        
        # Get yesterday's date
        yesterday = target_date - timedelta(days=1)
        
        # Get yesterday's plan
        from bson import ObjectId
        
        yesterday_plan = await self.daily_plans_collection.find_one({
            "user_id": ObjectId(user_id),
            "date": yesterday
        })
        
        if not yesterday_plan:
            return None  # No plan yesterday
        
        # Get tasks
        tasks_cursor = self.tasks_collection.find({
            "daily_plan_id": yesterday_plan["_id"]
        })
        
        tasks = await tasks_cursor.to_list(length=100)
        
        if not tasks:
            return None
        
        # Calculate completion rate
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
        completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        if completion_rate >= 70:
            return None  # Good enough
        
        missed_count = sum(1 for t in tasks if t.get("status") == "missed")
        
        # Schedule for 8 PM today
        notification_time = datetime.combine(
            target_date,
            datetime.min.time().replace(hour=20, minute=0)
        )
        
        # Check silent hours
        if is_within_silent_hours(
            notification_time,
            preferences.silent_hours_start,
            preferences.silent_hours_end
        ):
            return None
        
        metadata = {
            "missed_count": missed_count,
            "completion_rate": completion_rate,
            "date": yesterday.isoformat()
        }
        
        title = generate_notification_title(NotificationType.MISSED_TASK, metadata)
        message = generate_notification_message(NotificationType.MISSED_TASK, metadata)
        
        notification = await self.repository.create_notification(
            user_id=user_id,
            notification_type=NotificationType.MISSED_TASK,
            title=title,
            message=message,
            metadata=metadata,
            scheduled_for=notification_time
        )
        
        return notification
    
    async def _generate_exam_reminders(
        self,
        user_id: str,
        target_date: date,
        preferences: UserNotificationPreferences
    ) -> List[object]:
        """
        Generate exam reminders at milestones.
        
        Rules:
        - Check if T-30, T-7, or T-1 days
        - Include exam readiness
        - Schedule for 9 AM
        - One per milestone
        
        Returns:
            List of NotificationModels
        """
        from bson import ObjectId
        
        # Get profile to find exam date
        profile = await self.profiles_collection.find_one({
            "user_id": ObjectId(user_id)
        })
        
        if not profile:
            return []
        
        exam_date_dt = profile.get("exam_date")
        if isinstance(exam_date_dt, datetime):
            exam_date = exam_date_dt.date()
        else:
            exam_date = exam_date_dt
        
        if not exam_date:
            return []
        
        # Calculate days until exam
        days_until = (exam_date - target_date).days
        
        # Check if this is a milestone
        if days_until not in [30, 7, 1]:
            return []  # Not a milestone
        
        # Check for duplicate
        duplicate = await self.repository.find_duplicate(
            user_id, NotificationType.EXAM, target_date
        )
        if duplicate:
            return []
        
        # Schedule for 9 AM
        notification_time = datetime.combine(
            target_date,
            datetime.min.time().replace(hour=9, minute=0)
        )
        
        # Check silent hours (but exam T-1 is important, so only check for T-30 and T-7)
        if days_until != 1 and is_within_silent_hours(
            notification_time,
            preferences.silent_hours_start,
            preferences.silent_hours_end
        ):
            return []
        
        # Get exam readiness (simplified - would call analytics service in production)
        # For now, use placeholder
        readiness_score = 75
        weak_chapters = 2
        
        metadata = {
            "exam_date": exam_date.isoformat(),
            "days_left": days_until,
            "readiness_score": readiness_score,
            "weak_chapters": weak_chapters
        }
        
        title = generate_notification_title(NotificationType.EXAM, metadata)
        message = generate_notification_message(NotificationType.EXAM, metadata)
        
        notification = await self.repository.create_notification(
            user_id=user_id,
            notification_type=NotificationType.EXAM,
            title=title,
            message=message,
            metadata=metadata,
            scheduled_for=notification_time
        )
        
        return [notification]
    
    def _to_notification_response(self, notification) -> NotificationResponse:
        """Convert NotificationModel to NotificationResponse."""
        return NotificationResponse(
            id=str(notification.id),
            type=notification.type.value,
            title=notification.title,
            message=notification.message,
            metadata=notification.metadata,
            status=notification.status.value,
            scheduled_for=notification.scheduled_for.isoformat(),
            created_at=notification.created_at.isoformat(),
            acknowledged_at=notification.acknowledged_at.isoformat() if notification.acknowledged_at else None
        )
