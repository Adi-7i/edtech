"""
AI Assistant Dependencies

Access control and context retrieval for AI endpoints.
"""

from datetime import date, datetime
from typing import Optional

from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.mongo import get_database
from app.core.exceptions import TooManyRequestsException
from app.modules.auth.dependencies import get_current_user


async def check_daily_limit(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Dependency to enforce daily AI query limit.
    
    Smart Pack users get 50 queries per day.
    Resets at midnight UTC.
    
    Raises:
        TooManyRequestsException: If daily limit exceeded
    """
    user_id = current_user["id"]
    today = datetime.combine(date.today(), datetime.min.time())
    
    # Get today's usage
    usage_doc = await db.ai_daily_usage.find_one({
        "user_id": ObjectId(user_id),
        "date": today
    })
    
    query_count = usage_doc["query_count"] if usage_doc else 0
    daily_limit = usage_doc["daily_limit"] if usage_doc else 50
    
    if query_count >= daily_limit:
        raise TooManyRequestsException(
            message=f"Daily AI query limit reached ({daily_limit}). Resets tomorrow at midnight UTC."
        )


async def get_user_context(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    """
    Dependency to retrieve user context for AI prompts.
    
    Fetches:
    - Study profile (exam, subjects)
    - Today's plan (tasks, completion)
    - Analytics (consistency, readiness)
    - Weak subjects (from performance data)
    
    Returns:
        Dictionary with context for prompt injection
    """
    user_id = current_user["id"]
    
    # Get study profile
    profile = await db.study_profiles.find_one({"user_id": ObjectId(user_id)})
    
    # Get today's plan
    today = date.today()
    plan = await db.daily_plans.find_one({
        "user_id": ObjectId(user_id),
        "date": datetime.combine(today, datetime.min.time())
    })
    
    # Build context
    context = {}
    
    # Exam information
    if profile:
        context["exam_name"] = profile.get("exam_name", "your upcoming exam")
        exam_date = profile.get("exam_date")
        
        if exam_date and isinstance(exam_date, datetime):
            context["exam_date"] = exam_date.strftime("%Y-%m-%d")
            days_left = (exam_date - datetime.utcnow()).days
            context["days_left"] = max(0, days_left)
        else:
            context["exam_date"] = "Not set"
            context["days_left"] = 0
        
        # Subjects
        subjects = profile.get("subjects", [])
        context["subjects"] = ", ".join([s.get("name", "Unknown") for s in subjects]) or "No subjects"
    else:
        context["exam_name"] = "your exam"
        context["exam_date"] = "Not set"
        context["days_left"] = 0
        context["subjects"] = "No subjects"
    
    # Today's plan data
    if plan:
        tasks = plan.get("tasks", [])
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
        
        context["total_tasks"] = total_tasks
        context["tasks_completed"] = completed_tasks
        context["completion_percentage"] = round(
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            1
        )
    else:
        context["total_tasks"] = 0
        context["tasks_completed"] = 0
        context["completion_percentage"] = 0
    
    # Analytics data (simplified - would be more sophisticated in production)
    # For now, use placeholder values
    # In production, this would call the analytics service
    context["consistency_score"] = 85  # Placeholder
    context["exam_readiness"] = 68  # Placeholder
    context["weak_subjects"] = "Physics, Chemistry"  # Placeholder
    
    # Revision summary (for revision_summary query type)
    context["revision_summary"] = "No recent revision data"  # Placeholder
    
    return context
