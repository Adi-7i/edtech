"""
AI Assistant Router

API endpoints for controlled, ethical AI study coaching.
"""

from fastapi import APIRouter, Depends

from app.core.database.mongo import get_database
from app.core.database.models.ai_query import QueryType
from app.core.responses.base import SuccessResponse
from app.modules.ai_assistant.dependencies import check_daily_limit, get_user_context
from app.modules.ai_assistant.schemas import (
    AskAIRequest,
    AskAIResponse,
    SuggestionsResponse,
    UsageResponse,
)
from app.modules.ai_assistant.service import AIAssistantService
from app.modules.auth.dependencies import get_current_user
from app.modules.subscription.dependencies import require_feature
from app.modules.subscription.models import FeatureFlag
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


def get_ai_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> AIAssistantService:
    """Dependency injection for AI service."""
    return AIAssistantService(db)


@router.post(
    "/ask",
    response_model=SuccessResponse[AskAIResponse],
    dependencies=[
        Depends(require_feature(FeatureFlag.AI_PLANNER)),  # Smart Pack only
        Depends(check_daily_limit)  # 50 queries/day
    ],
    summary="Ask AI Study Coach",
    description="""
    Ask the AI study coach a question.
    
    **Access Control:**
    - Smart Pack users only
    - Daily limit: 50 queries
    - Resets at midnight UTC
    
    **Supported Query Types:**
    - `concept_explanation`: Explain a concept or topic
    - `study_guidance`: Get personalized study advice
    - `revision_summary`: Summarize revision progress
    - `motivation`: Get motivation and productivity tips
    
    **Ethical Guardrails (Enforced):**
    - ❌ Blocks assignment solving
    - ❌ Blocks exam question prediction
    - ❌ Blocks direct answer requests
    - ✅ Encourages learning and understanding
    
    **Context-Aware:**
    - Automatically injects your study profile
    - Considers your weak subjects
    - Personalized to exam timeline
    - References your current progress
    
    **Examples:**
    - ✅ "Explain Newton's laws of motion"
    - ✅ "How should I prioritize my subjects?"
    - ✅ "I'm feeling unmotivated, help me"
    - ❌ "Solve this assignment question" (blocked)
    - ❌ "What will come in tomorrow's exam?" (blocked)
    """
)
async def ask_ai_assistant(
    request: AskAIRequest,
    current_user: dict = Depends(get_current_user),
    context: dict = Depends(get_user_context),
    service: AIAssistantService = Depends(get_ai_service)
):
    """
    Ask AI study coach a question.
    
    Request:
    - query: Your question (5-500 chars)
    - query_type: Type of query
    
    Returns:
    - AI-generated response
    - Context used
    - Metadata (tokens, response time)
    """
    user_id = current_user["id"]
    
    # Convert string to enum
    query_type = QueryType(request.query_type)
    
    result = await service.ask_assistant(
        user_id=user_id,
        query=request.query,
        query_type=query_type,
        context=context
    )
    
    return SuccessResponse(
        message="AI response generated successfully",
        status_code=200,
        data=result
    )


@router.get(
    "/usage",
    response_model=SuccessResponse[UsageResponse],
    dependencies=[Depends(require_feature(FeatureFlag.AI_PLANNER))],
    summary="Get AI Usage Statistics",
    description="""
    Get your AI assistant usage statistics for today.
    
    **Returns:**
    - Queries used today
    - Daily limit (50)
    - Queries available
    - Percentage used
    
    **Use Cases:**
    - Display usage meter in UI
    - Show "X queries remaining" message
    - Warn when approaching limit
    """
)
async def get_ai_usage(
    current_user: dict = Depends(get_current_user),
    service: AIAssistantService = Depends(get_ai_service)
):
    """
    Get AI usage statistics for today.
    
    Returns:
    - Usage stats (queries used, available, percentage)
    """
    user_id = current_user["id"]
    
    result = await service.get_daily_usage(user_id)
    
    return SuccessResponse(
        message="Usage statistics retrieved successfully",
        status_code=200,
        data=result
    )


@router.get(
    "/suggestions",
    response_model=SuccessResponse[SuggestionsResponse],
    dependencies=[Depends(require_feature(FeatureFlag.AI_PLANNER))],
    summary="Get Personalized Suggestions",
    description="""
    Get personalized study suggestions (no query needed).
    
    **AI analyzes your profile and suggests:**
    - Areas to focus on (weak subjects)
    - Timeline-based guidance (exam approaching)
    - Consistency improvements
    - Habit-building tips
    
    **Proactive Coaching:**
    - No query required
    - Based on your actual data
    - Prioritized (high/medium/low)
    - Actionable advice
    
    **Use Cases:**
    - Display on dashboard
    - Daily study tips
    - Proactive notifications
    """
)
async def get_ai_suggestions(
    current_user: dict = Depends(get_current_user),
    context: dict = Depends(get_user_context),
    service: AIAssistantService = Depends(get_ai_service)
):
    """
    Get personalized study suggestions.
    
    Returns:
    - 2-3 personalized suggestions
    - Based on weak subjects, timeline, consistency
    """
    user_id = current_user["id"]
    
    result = await service.get_personalized_suggestions(
        user_id=user_id,
        context=context
    )
    
    return SuccessResponse(
        message="Suggestions generated successfully",
        status_code=200,
        data=result
    )
