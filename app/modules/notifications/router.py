"""
Notification Router

API endpoints for notification event management.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.database.mongo import get_database
from app.core.responses.base import SuccessResponse
from app.modules.auth.dependencies import get_current_user
from app.modules.notifications.schemas import (
    GenerateNotificationsResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    NotificationResponse,
    TodaysNotificationsResponse,
)
from app.modules.notifications.service import NotificationService
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> NotificationService:
    """Dependency injection for notification service."""
    return NotificationService(db)


@router.post(
    "/generate",
    response_model=SuccessResponse[GenerateNotificationsResponse],
    summary="Generate Notifications",
    description="""
    Manually trigger notification generation for a date.
    
    **System evaluates all notification types:**
    1. Study Start Reminder (15 min before first task)
    2. Revision Reminders (when revisions due, max 2/day)
    3. Missed Task Alert (if yesterday completion < 70%)
    4. Exam Reminders (at T-30, T-7, T-1 days)
    
    **Rules Applied:**
    - Respects user preferences (enabled/disabled)
    - Enforces silent hours
    - Prevents duplicates (max 1 per type per day)
    - Checks eligibility for each type
    
    **Note:** This creates notification *events* in DB. 
    External systems poll GET /notifications/today for delivery.
    """
)
async def generate_notifications(
    date_param: Optional[str] = Query(
        None,
        alias="date",
        description="Date to generate for (YYYY-MM-DD, defaults to today)",
        example="2026-02-04"
    ),
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Generate notifications for a date.
    
    Query Parameters:
    - date: Optional date in YYYY-MM-DD format
    
    Returns:
    - GenerateNotificationsResponse with generated notifications
    """
    user_id = current_user["id"]
    
    # Parse date if provided
    if date_param:
        try:
            target_date = date.fromisoformat(date_param)
        except ValueError:
            from app.core.exceptions import BadRequestException
            raise BadRequestException(message="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = None  # Defaults to today
    
    result = await service.generate_notifications(user_id, target_date)
    
    return SuccessResponse(
        message=f"Generated {result.generated_count} notification(s), skipped {result.skipped_count}",
        status_code=200,
        data=result
    )


@router.get(
    "/today",
    response_model=SuccessResponse[TodaysNotificationsResponse],
    summary="Get Today's Notifications",
    description="""
    Get all notifications for today.
    
    **Use Case:**
    External delivery systems (mobile app, email service) poll this endpoint
    to retrieve pending notifications for delivery.
    
    **Response Includes:**
    - All notifications scheduled for today
    - Count by status (pending, acknowledged)
    - Full notification details (title, message, metadata)
    
    **Status Values:**
    - `pending`: Not delivered yet
    - `sent`: Delivered by external system
    - `acknowledged`: User has read/dismissed
    - `failed`: Delivery failed
    """
)
async def get_todays_notifications(
    date_param: Optional[str] = Query(
        None,
        alias="date",
        description="Date to get notifications for (YYYY-MM-DD, defaults to today)",
        example="2026-02-04"
    ),
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Get all notifications for a date.
    
    Query Parameters:
    - date: Optional date in YYYY-MM-DD format
    
    Returns:
    - TodaysNotificationsResponse
    """
    user_id = current_user["id"]
    
    # Parse date if provided
    if date_param:
        try:
            target_date = date.fromisoformat(date_param)
        except ValueError:
            from app.core.exceptions import BadRequestException
            raise BadRequestException(message="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = None
    
    result = await service.get_todays_notifications(user_id, target_date)
    
    return SuccessResponse(
        message="Notifications retrieved successfully",
        status_code=200,
        data=result
    )


@router.put(
    "/{notification_id}/ack",
    response_model=SuccessResponse[NotificationResponse],
    summary="Acknowledge Notification",
    description="""
    Mark a notification as acknowledged (read/dismissed by user).
    
    **Use Case:**
    When user interacts with notification (clicks, dismisses, or views),
    the client app calls this endpoint to mark it as acknowledged.
    
    **Effect:**
    - Status changes to `acknowledged`
    - `acknowledged_at` timestamp set
    - Won't appear in "unread" filters
    """
)
async def acknowledge_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Mark notification as acknowledged.
    
    Path Parameters:
    - notification_id: Notification ID to acknowledge
    
    Returns:
    - Updated NotificationResponse
    """
    user_id = current_user["id"]
    
    result = await service.acknowledge_notification(notification_id, user_id)
    
    return SuccessResponse(
        message="Notification acknowledged",
        status_code=200,
        data=result
    )


@router.get(
    "/preferences",
    response_model=SuccessResponse[NotificationPreferencesResponse],
    summary="Get Notification Preferences",
    description="""
    Get user's notification preferences.
    
    **Includes:**
    - Toggle for each notification type (study_start, break, revision, etc.)
    - Silent hours configuration (start/end time)
    
    **Defaults:**
    - All notification types: enabled
    - Silent hours: 22:00 - 07:00 (10 PM to 7 AM)
    """
)
async def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Get user's notification preferences.
    
    Returns:
    - NotificationPreferencesResponse
    """
    user_id = current_user["id"]
    
    result = await service.get_user_preferences(user_id)
    
    return SuccessResponse(
        message="Preferences retrieved successfully",
        status_code=200,
        data=result
    )


@router.put(
    "/preferences",
    response_model=SuccessResponse[NotificationPreferencesResponse],
    summary="Update Notification Preferences",
    description="""
    Update user's notification preferences.
    
    **Configurable:**
    - Enable/disable each notification type individually
    - Set silent hours (no notifications during this period)
    
    **Silent Hours Format:**
    - 24-hour format: HH:MM (e.g., "22:00", "07:00")
    - Can cross midnight (e.g., 22:00 - 07:00)
    
    **Partial Updates:**
    Only provided fields are updated. Omitted fields remain unchanged.
    """
)
async def update_notification_preferences(
    preferences: NotificationPreferencesRequest,
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service)
):
    """
    Update user's notification preferences.
    
    Body:
    - NotificationPreferencesRequest (partial updates supported)
    
    Returns:
    - Updated NotificationPreferencesResponse
    """
    user_id = current_user["id"]
    
    # Convert to dict and remove None values
    preferences_dict = preferences.model_dump(exclude_unset=True)
    
    result = await service.update_user_preferences(user_id, preferences_dict)
    
    return SuccessResponse(
        message="Preferences updated successfully",
        status_code=200,
        data=result
    )
