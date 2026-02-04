"""
Notification Schemas

Request and response models for notification API endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------

class NotificationPreferencesRequest(BaseModel):
    """Request to update user's notification preferences."""
    
    study_start_enabled: Optional[bool] = Field(None, description="Enable study start reminders")
    break_enabled: Optional[bool] = Field(None, description="Enable break reminders")
    revision_enabled: Optional[bool] = Field(None, description="Enable revision reminders")
    missed_task_enabled: Optional[bool] = Field(None, description="Enable missed task alerts")
    exam_enabled: Optional[bool] = Field(None, description="Enable exam reminders")
    silent_hours_start: Optional[str] = Field(
        None,
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
        description="Silent hours start (HH:MM format, 24-hour)",
        example="22:00"
    )
    silent_hours_end: Optional[str] = Field(
        None,
        pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$",
        description="Silent hours end (HH:MM format, 24-hour)",
        example="07:00"
    )


class AcknowledgeNotificationRequest(BaseModel):
    """Request to acknowledge (mark as read) a notification."""
    pass  # No body needed, notification ID in URL


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------

class NotificationPreferencesResponse(BaseModel):
    """User's notification preferences."""
    
    study_start_enabled: bool
    break_enabled: bool
    revision_enabled: bool
    missed_task_enabled: bool
    exam_enabled: bool
    silent_hours_start: str = Field(..., description="HH:MM format (24-hour)")
    silent_hours_end: str = Field(..., description="HH:MM format (24-hour)")
    created_at: str
    updated_at: str


class NotificationResponse(BaseModel):
    """Single notification event."""
    
    id: str
    type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Short notification title")
    message: str = Field(..., description="Detailed notification message")
    metadata: dict = Field(default_factory=dict, description="Context data")
    status: str = Field(..., description="Delivery status: pending, sent, acknowledged, failed")
    scheduled_for: str = Field(..., description="When to send (ISO format)")
    created_at: str = Field(..., description="When created (ISO format)")
    acknowledged_at: Optional[str] = Field(None, description="When acknowledged (ISO format)")


class TodaysNotificationsResponse(BaseModel):
    """Response for GET /notifications/today."""
    
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    notifications: List[NotificationResponse] = Field(
        default_factory=list,
        description="List of notifications for today"
    )
    total_count: int = Field(..., ge=0, description="Total notifications today")
    pending_count: int = Field(..., ge=0, description="Notifications pending delivery")
    acknowledged_count: int = Field(..., ge=0, description="Notifications user has acknowledged")


class GenerateNotificationsResponse(BaseModel):
    """Response for POST /notifications/generate."""
    
    generated_count: int = Field(..., ge=0, description="Number of notifications generated")
    notifications: List[NotificationResponse] = Field(
        default_factory=list,
        description="Newly generated notifications"
    )
    skipped_count: int = Field(
        ...,
        ge=0,
        description="Number skipped (duplicates or disabled)"
    )
