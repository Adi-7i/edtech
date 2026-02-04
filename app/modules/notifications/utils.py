"""
Notification Utilities

Rule evaluation functions for determining when to send notifications.
"""

from datetime import datetime, time
from typing import Dict, Optional

from app.core.database.models.notification import NotificationType


def is_within_silent_hours(
    current_time: datetime,
    silent_start: str,
    silent_end: str
) -> bool:
    """
    Check if current time is within user's silent hours.
    
    Args:
        current_time: Current datetime
        silent_start: Start time in HH:MM format (e.g., "22:00")
        silent_end: End time in HH:MM format (e.g., "07:00")
    
    Returns:
        True if within silent hours (no notifications should be sent)
    
    Example:
        - Silent hours: 22:00 - 07:00
        - Current time: 23:30 → True (within silent hours)
        - Current time: 08:00 → False (outside silent hours)
    
    Note:
        Handles ranges that cross midnight (e.g., 22:00-07:00)
    """
    try:
        # Parse silent hours
        start_hour, start_min = map(int, silent_start.split(":"))
        end_hour, end_min = map(int, silent_end.split(":"))
        
        start_time = time(start_hour, start_min)
        end_time = time(end_hour, end_min)
        current_time_only = current_time.time()
        
        # Check if range crosses midnight
        if start_time <= end_time:
            # Normal range (e.g., 08:00-17:00)
            return start_time <= current_time_only <= end_time
        else:
            # Crosses midnight (e.g., 22:00-07:00)
            return current_time_only >= start_time or current_time_only <= end_time
            
    except (ValueError, AttributeError):
        # Invalid format, default to not silent
        return False


def should_send_study_start_reminder(
    first_task_start_time: datetime,
    current_time: datetime,
    window_minutes_before: int = 15,
    tolerance_minutes: int = 5
) -> bool:
    """
    Determine if study start reminder should be sent.
    
    Args:
        first_task_start_time: When the first task is scheduled to start
        current_time: Current datetime
        window_minutes_before: How many minutes before to send (default 15)
        tolerance_minutes: Tolerance window (default 5, so 10-20 min before)
    
    Returns:
        True if reminder should be sent now
    
    Logic:
        - Send if current time is 10-20 minutes before task start
        - Don't send if too early or too late
    """
    minutes_until_task = (first_task_start_time - current_time).total_seconds() / 60
    
    # Window: window_minutes_before ± tolerance_minutes
    min_minutes = window_minutes_before - tolerance_minutes
    max_minutes = window_minutes_before + tolerance_minutes
    
    return min_minutes <= minutes_until_task <= max_minutes


def should_send_break_reminder(
    continuous_study_minutes: int,
    break_threshold_minutes: int = 90
) -> bool:
    """
    Determine if break reminder should be sent.
    
    Args:
        continuous_study_minutes: Minutes of continuous study
        break_threshold_minutes: Threshold to suggest break (default 90)
    
    Returns:
        True if break reminder should be sent
    
    Logic:
        - Send if user has studied continuously for >= threshold
        - Prevents burnout and maintains productivity
    """
    return continuous_study_minutes >= break_threshold_minutes


def generate_notification_title(
    notification_type: NotificationType,
    metadata: Dict
) -> str:
    """
    Generate user-friendly notification title.
    
    Args:
        notification_type: Type of notification
        metadata: Context data
    
    Returns:
        Short, actionable title
    """
    if notification_type == NotificationType.STUDY_START:
        return "Time to start studying!"
    
    elif notification_type == NotificationType.BREAK:
        return "Take a break!"
    
    elif notification_type == NotificationType.REVISION:
        chapter_name = metadata.get("chapter_name", "a chapter")
        return f"Revision due: {chapter_name}"
    
    elif notification_type == NotificationType.MISSED_TASK:
        return "Tasks missed yesterday"
    
    elif notification_type == NotificationType.EXAM:
        days_left = metadata.get("days_left", 0)
        if days_left == 1:
            return "Exam tomorrow!"
        else:
            return f"{days_left} days until exam!"
    
    return "Study reminder"


def generate_notification_message(
    notification_type: NotificationType,
    metadata: Dict
) -> str:
    """
    Generate detailed notification message.
    
    Args:
        notification_type: Type of notification
        metadata: Context data
    
    Returns:
        Detailed, actionable message
    """
    if notification_type == NotificationType.STUDY_START:
        task_name = metadata.get("task_name", "your first task")
        start_time = metadata.get("start_time", "soon")
        return f"Your first task '{task_name}' starts at {start_time}. Get ready!"
    
    elif notification_type == NotificationType.BREAK:
        duration = metadata.get("session_duration", 0)
        return f"You've been studying for {duration} minutes. Time for a 10-15 minute break to recharge."
    
    elif notification_type == NotificationType.REVISION:
        chapter_name = metadata.get("chapter_name", "a chapter")
        subject_name = metadata.get("subject_name", "")
        cycle_day = metadata.get("cycle_day", 1)
        
        if subject_name:
            return f"Time to revise {chapter_name} from {subject_name}. This is your Day {cycle_day} revision."
        else:
            return f"Time to revise {chapter_name}. This is your Day {cycle_day} revision."
    
    elif notification_type == NotificationType.MISSED_TASK:
        missed_count = metadata.get("missed_count", 0)
        completion_rate = metadata.get("completion_rate", 0)
        return f"You missed {missed_count} tasks yesterday ({completion_rate:.0f}% completion). Today is a new opportunity to stay consistent!"
    
    elif notification_type == NotificationType.EXAM:
        days_left = metadata.get("days_left", 0)
        readiness_score = metadata.get("readiness_score", 0)
        weak_chapters = metadata.get("weak_chapters", 0)
        
        message = f"Your exam is in {days_left} day{'s' if days_left != 1 else ''}. "
        message += f"Current readiness: {readiness_score}%. "
        
        if weak_chapters > 0:
            message += f"Focus on {weak_chapters} weak chapter{'s' if weak_chapters != 1 else ''}. "
        
        if readiness_score >= 80:
            message += "Great preparation! Continue with scheduled revisions."
        elif readiness_score >= 60:
            message += "Good progress! Increase revision frequency."
        else:
            message += "Urgent: Prioritize completing remaining chapters."
        
        return message
    
    return "You have a study reminder."


def format_time_12hr(hour: int, minute: int = 0) -> str:
    """
    Format time in 12-hour format with AM/PM.
    
    Args:
        hour: Hour (0-23)
        minute: Minute (0-59)
    
    Returns:
        Formatted time string (e.g., "3:30 PM")
    """
    period = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    display_hour = 12 if display_hour == 0 else display_hour
    
    if minute == 0:
        return f"{display_hour} {period}"
    else:
        return f"{display_hour}:{minute:02d} {period}"
