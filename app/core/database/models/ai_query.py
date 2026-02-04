"""
AI Query Models

Database models for AI assistant query logging and usage tracking.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.database.models.base import MongoBaseModel
from bson import ObjectId


class QueryType(str, Enum):
    """AI query types."""
    
    CONCEPT_EXPLANATION = "concept_explanation"
    STUDY_GUIDANCE = "study_guidance"
    REVISION_SUMMARY = "revision_summary"
    MOTIVATION = "motivation"


class AIQueryLog(MongoBaseModel):
    """
    Log of AI assistant queries.
    
    Tracks all queries for:
    - Transparency (user can see query history)
    - Billing (tokens used)
    - Analytics (popular query types)
    - Quality assurance (review responses)
    """
    
    user_id: ObjectId = Field(..., description="User ID")
    query: str = Field(..., description="User's question")
    query_type: QueryType = Field(..., description="Type of query")
    response: str = Field(..., description="AI-generated response")
    tokens_used: int = Field(default=0, ge=0, description="Tokens consumed")
    response_time_ms: int = Field(default=0, ge=0, description="Response time in milliseconds")
    context_injected: dict = Field(
        default_factory=dict,
        description="User context used in prompt (exam, subjects, etc.)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        collection_name = "ai_query_logs"


class AIDailyUsage(MongoBaseModel):
    """
    Daily usage tracking for query limits.
    
    Each Smart Pack user gets 50 queries per day.
    Resets at midnight UTC.
    """
    
    user_id: ObjectId = Field(..., description="User ID")
    date: datetime = Field(..., description="Date (YYYY-MM-DD, time set to 00:00:00)")
    query_count: int = Field(default=0, ge=0, description="Number of queries today")
    daily_limit: int = Field(default=50, description="Daily query limit")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        collection_name = "ai_daily_usage"
