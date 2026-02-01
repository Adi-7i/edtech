"""
AI Usage Tracking Model for Smart Study Planner.

Collection: ai_usage_logs

Tracks AI feature usage per user:
- Daily query counts and limits
- Plan-based access control
- Ethical usage monitoring
- Usage patterns for optimization

Design decisions:
- One document per user per date
- Query details stored with bounded array
- Ethical flags for content moderation

Indexes (to be created):
- (user_id, date) unique compound
- user_id
- date
- (user_id, ethical_flag) for moderation
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .base import MongoBaseModel, PyObjectId


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class AIFeatureType(str, Enum):
    """Types of AI features."""
    STUDY_PLAN_GENERATION = "study_plan_generation"
    DOUBT_SOLVING = "doubt_solving"
    PERSONALIZED_TIPS = "personalized_tips"
    CONTENT_SUMMARIZATION = "content_summarization"
    PRACTICE_GENERATION = "practice_generation"
    EXAM_STRATEGY = "exam_strategy"
    MOTIVATION = "motivation"
    OTHER = "other"


class QueryStatus(str, Enum):
    """Query processing status."""
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"  # Blocked due to ethical violation
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"


class EthicalFlag(str, Enum):
    """Ethical usage flags."""
    NONE = "none"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    CHEATING_ATTEMPT = "cheating_attempt"
    HARMFUL_REQUEST = "harmful_request"
    SPAM = "spam"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


# -----------------------------------------------------------------------------
# Embedded Documents
# -----------------------------------------------------------------------------

class AIQuery(BaseModel):
    """
    Individual AI query record (embedded).
    Max 100 queries stored per day for detailed tracking.
    """
    
    query_id: str = Field(
        ...,
        description="Unique query ID"
    )
    feature_type: AIFeatureType = Field(
        ...,
        description="Type of AI feature used"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Query timestamp"
    )
    
    # Query details (truncated for storage)
    query_preview: Optional[str] = Field(
        default=None,
        max_length=200,
        description="First 200 chars of query"
    )
    
    # Processing metrics
    status: QueryStatus = Field(
        default=QueryStatus.SUCCESS,
        description="Processing status"
    )
    response_time_ms: int = Field(
        default=0,
        ge=0,
        description="Response time in milliseconds"
    )
    tokens_used: int = Field(
        default=0,
        ge=0,
        description="Tokens consumed"
    )
    
    # Ethical flags
    ethical_flag: EthicalFlag = Field(
        default=EthicalFlag.NONE,
        description="Ethical usage flag"
    )
    
    # Context
    chapter_id: Optional[PyObjectId] = Field(
        default=None,
        description="Related chapter (if applicable)"
    )
    subject_context: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Subject context"
    )


class UsageByFeature(BaseModel):
    """Usage breakdown by feature type (embedded)."""
    
    feature_type: AIFeatureType = Field(
        ...,
        description="Feature type"
    )
    count: int = Field(
        default=0,
        ge=0,
        description="Usage count"
    )
    tokens_used: int = Field(
        default=0,
        ge=0,
        description="Total tokens used"
    )
    avg_response_time_ms: float = Field(
        default=0.0,
        ge=0,
        description="Average response time"
    )


# -----------------------------------------------------------------------------
# Main AI Usage Model
# -----------------------------------------------------------------------------

class AIUsageModel(MongoBaseModel):
    """
    Daily AI usage log document.
    
    Collection: ai_usage_logs
    
    Indexes:
    - (user_id, date) unique compound
    - user_id
    - date
    - (user_id, has_ethical_violations) for moderation
    - total_queries (for usage analytics)
    """
    
    # User reference
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    
    # Usage date
    usage_date: date = Field(
        ...,
        description="Usage date"
    )
    
    # Daily limits (from subscription)
    daily_limit: int = Field(
        default=5,
        ge=0,
        description="Daily query limit"
    )
    
    # Usage counts
    total_queries: int = Field(
        default=0,
        ge=0,
        description="Total queries today"
    )
    successful_queries: int = Field(
        default=0,
        ge=0,
        description="Successful queries"
    )
    failed_queries: int = Field(
        default=0,
        ge=0,
        description="Failed queries"
    )
    blocked_queries: int = Field(
        default=0,
        ge=0,
        description="Blocked queries"
    )
    
    # Token usage
    total_tokens_used: int = Field(
        default=0,
        ge=0,
        description="Total tokens consumed"
    )
    
    # Queries (bounded, max 100 stored)
    queries: list[AIQuery] = Field(
        default_factory=list,
        max_length=100,
        description="Query records"
    )
    
    # Usage by feature (max 10)
    usage_by_feature: list[UsageByFeature] = Field(
        default_factory=list,
        max_length=10,
        description="Usage breakdown by feature"
    )
    
    # Ethical tracking
    has_ethical_violations: bool = Field(
        default=False,
        description="Whether any ethical violations occurred"
    )
    ethical_violation_count: int = Field(
        default=0,
        ge=0,
        description="Number of violations"
    )
    violation_types: list[EthicalFlag] = Field(
        default_factory=list,
        max_length=5,
        description="Types of violations"
    )
    
    # Rate limiting
    rate_limited_count: int = Field(
        default=0,
        ge=0,
        description="Times rate limited"
    )
    last_rate_limited_at: Optional[datetime] = Field(
        default=None,
        description="Last rate limit timestamp"
    )
    
    # Performance metrics
    avg_response_time_ms: float = Field(
        default=0.0,
        ge=0,
        description="Average response time"
    )
    peak_usage_hour: Optional[int] = Field(
        default=None,
        ge=0,
        le=23,
        description="Hour with most usage"
    )
    
    @property
    def remaining_queries(self) -> int:
        """Calculate remaining queries for the day."""
        return max(0, self.daily_limit - self.total_queries)
    
    @property
    def is_limit_reached(self) -> bool:
        """Check if daily limit is reached."""
        return self.total_queries >= self.daily_limit


# -----------------------------------------------------------------------------
# AI Usage Summary (aggregated for admin/analytics)
# -----------------------------------------------------------------------------

class AIUsageSummaryModel(MongoBaseModel):
    """
    Aggregated AI usage summary (monthly).
    
    Collection: ai_usage_summaries
    
    Indexes:
    - user_id
    - (user_id, month, year) unique compound
    """
    
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    month: int = Field(
        ...,
        ge=1,
        le=12,
        description="Month (1-12)"
    )
    year: int = Field(
        ...,
        ge=2024,
        description="Year"
    )
    
    # Totals
    total_queries: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    active_days: int = Field(default=0, ge=0, le=31)
    
    # Feature breakdown (max 10)
    feature_usage: list[UsageByFeature] = Field(
        default_factory=list,
        max_length=10
    )
    
    # Quality metrics
    avg_response_time_ms: float = Field(default=0.0, ge=0)
    success_rate: float = Field(default=0.0, ge=0, le=100)
    
    # Ethical tracking
    total_violations: int = Field(default=0, ge=0)
    is_flagged: bool = Field(default=False)


# -----------------------------------------------------------------------------
# Ethical Review Queue
# -----------------------------------------------------------------------------

class EthicalReviewModel(MongoBaseModel):
    """
    Queue for ethical review of flagged content.
    
    Collection: ethical_reviews
    
    Indexes:
    - status
    - user_id
    - created_at
    """
    
    # User reference
    user_id: PyObjectId = Field(
        ...,
        description="Reference to user"
    )
    
    # Query reference
    usage_log_id: PyObjectId = Field(
        ...,
        description="Reference to AI usage log"
    )
    query_id: str = Field(
        ...,
        description="Query ID within usage log"
    )
    
    # Content
    query_content: str = Field(
        ...,
        max_length=1000,
        description="Full query content for review"
    )
    ai_response_preview: Optional[str] = Field(
        default=None,
        max_length=500,
        description="AI response preview"
    )
    
    # Flag details
    flag_type: EthicalFlag = Field(
        ...,
        description="Type of flag"
    )
    auto_detected: bool = Field(
        default=True,
        description="Whether auto-detected by AI"
    )
    detection_confidence: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Detection confidence score"
    )
    
    # Review status
    status: str = Field(
        default="pending",
        description="Review status (pending/reviewed/dismissed)"
    )
    reviewed_by: Optional[str] = Field(
        default=None,
        description="Reviewer ID"
    )
    reviewed_at: Optional[datetime] = Field(
        default=None,
        description="Review timestamp"
    )
    review_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reviewer notes"
    )
    
    # Action taken
    action_taken: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Action taken (warning/suspend/none)"
    )


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------

class AIQueryCreateDTO(BaseModel):
    """DTO for logging an AI query."""
    
    feature_type: AIFeatureType
    query_preview: Optional[str] = None
    chapter_id: Optional[PyObjectId] = None
    subject_context: Optional[str] = None


class AIQueryResultDTO(BaseModel):
    """DTO for recording query result."""
    
    query_id: str
    status: QueryStatus
    response_time_ms: int
    tokens_used: int
    ethical_flag: EthicalFlag = EthicalFlag.NONE
