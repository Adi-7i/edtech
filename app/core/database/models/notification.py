"""
Notification Models

Database models for notification events and user preferences.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.database.models.base import MongoBaseModel
from bson import ObjectId


class NotificationType(str, Enum):
    """Types of notifications supported by the system."""
    
    STUDY_START = "study_start"  # Reminder before first task
    BREAK = "break"  # Reminder to take a break
    REVISION = "revision"  # Revision due reminder
    MISSED_TASK = "missed_task"  # Alert for missed tasks
    EXAM = "exam"  # Exam countdown reminder


class NotificationStatus(str, Enum):
    """Status of notification delivery."""
    
    PENDING = "pending"  # Created, waiting for delivery
    SENT = "sent"  # Delivered by external system
    ACKNOWLEDGED = "acknowledged"  # User acknowledged/read
    FAILED = "failed"  # Delivery failed


class NotificationModel(MongoBaseModel):
    """
    Notification event stored for external delivery systems.
    
    External systems poll GET /notifications/today to retrieve
    pending notifications and deliver via push/email/SMS.
    """
    
    user_id: ObjectId = Field(..., description="Owner of this notification")
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(..., max_length=100, description="Short notification title")
    message: str = Field(..., max_length=500, description="Detailed notification message")
    metadata: dict = Field(default_factory=dict, description="Context data (task_id, chapter_name, etc.)")
    status: NotificationStatus = Field(
        default=NotificationStatus.PENDING,
        description="Delivery status"
    )
    scheduled_for: datetime = Field(..., description="When this notification should be sent")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When notification was created")
    acknowledged_at: Optional[datetime] = Field(None, description="When user acknowledged this notification")
    
    class Config:
        collection_name = "notifications"


class UserNotificationPreferences(MongoBaseModel):
    """
    User's notification preferences and silent hours configuration.
    
    Each user has one preferences document.
    """
    
    user_id: ObjectId = Field(..., description="User ID (unique index)")
    
    # Notification type toggles
    study_start_enabled: bool = Field(True, description="Enable study start reminders")
    break_enabled: bool = Field(True, description="Enable break reminders")
    revision_enabled: bool = Field(True, description="Enable revision reminders")
    missed_task_enabled: bool = Field(True, description="Enable missed task alerts")
    exam_enabled: bool = Field(True, description="Enable exam countdown reminders")
    
    # Silent hours (no notifications during this period)
    silent_hours_start: str = Field(
        "22:00",
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
        description="Silent hours start time (HH:MM format, 24-hour)"
    )
    silent_hours_end: str = Field(
        "07:00",
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
        description="Silent hours end time (HH:MM format, 24-hour)"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        collection_name = "user_notification_preferences"
