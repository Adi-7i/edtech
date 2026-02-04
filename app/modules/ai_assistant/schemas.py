"""
AI Assistant Schemas

Request and response models for AI assistant API endpoints.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------

class AskAIRequest(BaseModel):
    """Request to ask AI assistant a question."""
    
    query: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="User's question (5-500 characters)",
        examples=["How should I prioritize my subjects?"]
    )
    query_type: str = Field(
        default="study_guidance",
        pattern="^(concept_explanation|study_guidance|revision_summary|motivation)$",
        description="Type of query",
        examples=["study_guidance"]
    )


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------

class AskAIResponse(BaseModel):
    """Response from AI assistant."""
    
    response: str = Field(..., description="AI-generated response")
    query_type: str = Field(..., description="Type of query")
    context_used: Dict = Field(
        ...,
        description="User context injected into prompt"
    )
    metadata: Dict = Field(
        ...,
        description="Response metadata (tokens, response time)"
    )


class UsageResponse(BaseModel):
    """AI assistant usage statistics."""
    
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    queries_used: int = Field(..., ge=0, description="Queries used today")
    daily_limit: int = Field(..., description="Daily query limit")
    queries_available: int = Field(..., ge=0, description="Queries remaining today")
    percentage_used: float = Field(..., ge=0, le=100, description="Percentage of limit used")


class SuggestionItem(BaseModel):
    """Single personalized suggestion."""
    
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Detailed description")
    priority: str = Field(
        ...,
        pattern="^(high|medium|low)$",
        description="Priority level"
    )


class SuggestionsResponse(BaseModel):
    """Personalized study suggestions."""
    
    suggestions: List[SuggestionItem] = Field(
        ...,
        description="List of personalized suggestions"
    )


class QueryHistoryItem(BaseModel):
    """Single query history entry."""
    
    query: str = Field(..., description="User's question")
    query_type: str = Field(..., description="Type of query")
    response_preview: str = Field(
        ...,
        description="First 150 characters of response"
    )
    created_at: str = Field(..., description="Timestamp (ISO format)")


class QueryHistoryResponse(BaseModel):
    """Query history list."""
    
    queries: List[QueryHistoryItem] = Field(
        ...,
        description="Recent queries"
    )
    total: int = Field(..., description="Total queries logged")
