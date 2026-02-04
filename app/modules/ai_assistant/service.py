"""
AI Assistant Service

Core business logic for AI study coach with ethical guardrails.
"""

import time
from datetime import date
from typing import Dict, List

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.ai.ai_client import get_ai_client
from app.core.database.models.ai_query import QueryType
from app.core.exceptions import BadRequestException
from app.modules.ai_assistant.prompts import (
    CHEATING_KEYWORDS,
    CONTEXT_TEMPLATE,
    SHORTCUT_PHRASES,
    SYSTEM_PROMPT,
    get_prompt_for_query_type,
)
from app.modules.ai_assistant.repository import AIAssistantRepository
from app.modules.ai_assistant.schemas import (
    AskAIResponse,
    SuggestionItem,
    SuggestionsResponse,
    UsageResponse,
)


class AIAssistantService:
    """Service for AI assistant operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.repository = AIAssistantRepository(db)
        self.ai_client = get_ai_client()
    
    async def ask_assistant(
        self,
        user_id: str,
        query: str,
        query_type: QueryType,
        context: dict
    ) -> AskAIResponse:
        """
        Ask AI assistant a question with ethical guardrails.
        
        Flow:
        1. Check ethical guardrails (block cheating)
        2. Build context-aware prompt
        3. Call AI provider
        4. Log query for transparency
        5. Increment usage counter
        6. Return response
        
        Args:
            user_id: User ID
            query: User's question
            query_type: Type of query
            context: User context (exam, subjects, etc.)
        
        Returns:
            AskAIResponse with AI-generated response
        
        Raises:
            BadRequestException: If query violates ethical guidelines
        """
        # 1. Ethical guardrails (CRITICAL - block academic dishonesty)
        self._check_ethical_guardrails(query)
        
        # 2. Build context-aware prompt
        messages = self._build_prompt(query, query_type, context)
        
        # 3. Call AI provider (with timing)
        start_time = time.time()
        
        try:
            response_text, tokens_used = await self.ai_client.generate_response(
                messages=messages,
                temperature=0.7,  # Balanced creativity
                max_tokens=500  # Keep responses concise
            )
        except Exception as e:
            # If AI call fails, return helpful error
            raise BadRequestException(
                message=f"AI service temporarily unavailable. Please try again later. Error: {str(e)}"
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 4. Log query (transparency and analytics)
        await self.repository.log_query(
            user_id=user_id,
            query=query,
            query_type=query_type,
            response=response_text,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            context=context
        )
        
        # 5. Increment usage (enforce daily limit)
        await self.repository.increment_daily_usage(user_id, date.today())
        
        # 6. Return response
        return AskAIResponse(
            response=response_text,
            query_type=query_type.value,
            context_used={
                "exam_name": context.get("exam_name"),
                "days_left": context.get("days_left"),
                "weak_subjects": context.get("weak_subjects")
            },
            metadata={
                "tokens_used": tokens_used,
                "response_time_ms": response_time_ms
            }
        )
    
    def _check_ethical_guardrails(self, query: str):
        """
        Check if query violates ethical guidelines.
        
        Blocks:
        - Assignment solving
        - Exam question prediction
        - Direct answer requests
        - Essay writing
        
        Allows:
        - Concept explanations
        - Study guidance
        - Learning techniques
        - Motivation
        
        Args:
            query: User's question
        
        Raises:
            BadRequestException: If cheating detected
        """
        query_lower = query.lower()
        
        # Check for blatant cheating keywords
        for keyword in CHEATING_KEYWORDS:
            if keyword in query_lower:
                raise BadRequestException(
                    message="This AI assistant is for learning support, not for completing assessments. "
                           f"Please ask about concepts, study strategies, or learning techniques instead. "
                           f"Example: 'How do I approach this type of problem?' rather than 'Solve this for me.'"
                )
        
        # Check for shortcut phrases
        for phrase in SHORTCUT_PHRASES:
            if phrase in query_lower:
                raise BadRequestException(
                    message="It looks like you're asking for a direct solution. "
                           "This assistant helps you learn, not complete work for you. "
                           "Try asking 'How should I think about this?' or 'What's the approach?'"
                )
    
    def _build_prompt(
        self,
        query: str,
        query_type: QueryType,
        context: dict
    ) -> List[Dict[str, str]]:
        """
        Build context-aware prompt for AI.
        
        Constructs a messages array with:
        1. System message (AI persona)
        2. Context message (user's study profile)
        3. User message (query with use-case specific template)
        
        Args:
            query: User's question
            query_type: Type of query
            context: User context
        
        Returns:
            Messages array for AI provider
        """
        # Format context with safe defaults
        formatted_context = {
            "exam_name": context.get("exam_name", "your exam"),
            "exam_date": context.get("exam_date", "not set"),
            "days_left": context.get("days_left", 0),
            "subjects": context.get("subjects", "not set"),
            "weak_subjects": context.get("weak_subjects", "none identified"),
            "tasks_completed": context.get("tasks_completed", 0),
            "total_tasks": context.get("total_tasks", 0),
            "completion_percentage": context.get("completion_percentage", 0),
            "consistency_score": context.get("consistency_score", 0),
            "exam_readiness": context.get("exam_readiness", 0),
            "revision_summary": context.get("revision_summary", "No recent revision data")
        }
        
        # System message (AI persona + context)
        context_injection = CONTEXT_TEMPLATE.format(**formatted_context)
        system_message = SYSTEM_PROMPT + "\n\n" + context_injection
        
        # User message (query with use-case template)
        query_template = get_prompt_for_query_type(query_type.value)
        user_message = query_template.format(
            query=query,
            **formatted_context
        )
        
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
    
    async def get_daily_usage(
        self,
        user_id: str
    ) -> UsageResponse:
        """
        Get AI usage statistics for today.
        
        Args:
            user_id: User ID
        
        Returns:
            UsageResponse with usage stats
        """
        today = date.today()
        
        queries_used = await self.repository.get_daily_usage(user_id, today)
        daily_limit = 50
        queries_available = max(0, daily_limit - queries_used)
        percentage_used = (queries_used / daily_limit * 100) if daily_limit > 0 else 0
        
        return UsageResponse(
            date=today.isoformat(),
            queries_used=queries_used,
            daily_limit=daily_limit,
            queries_available=queries_available,
            percentage_used=round(percentage_used, 1)
        )
    
    async def get_personalized_suggestions(
        self,
        user_id: str,
        context: dict
    ) -> SuggestionsResponse:
        """
        Generate personalized study suggestions.
        
        No query needed - analyzes context to provide proactive guidance.
        
        Based on:
        - Weak subjects
        - Exam timeline
        - Consistency score
        - Recent completion rate
        
        Args:
            user_id: User ID
            context: User context
        
        Returns:
            SuggestionsResponse with 2-3 suggestions
        """
        suggestions = []
        
        # Suggestion 1: Weak areas
        weak_subjects = context.get("weak_subjects", "")
        if weak_subjects and weak_subjects != "none identified":
            # Extract first weak subject
            first_weak = weak_subjects.split(",")[0].strip()
            
            suggestions.append(SuggestionItem(
                title="Focus on weak areas",
                description=f"Your {first_weak} performance needs attention. "
                           f"Consider spending 2-3 extra hours this week on this subject.",
                priority="high"
            ))
        
        # Suggestion 2: Exam timeline
        days_left = context.get("days_left", 0)
        exam_name = context.get("exam_name", "your exam")
        
        if 0 < days_left <= 30:
            suggestions.append(SuggestionItem(
                title="Exam approaching soon",
                description=f"Only {days_left} days until {exam_name}. "
                           f"Shift focus to revision and practice tests now.",
                priority="high"
            ))
        elif 30 < days_left <= 60:
            suggestions.append(SuggestionItem(
                title="Build momentum now",
                description=f"{days_left} days until {exam_name}. "
                           f"Focus on completing syllabus coverage this month.",
                priority="medium"
            ))
        
        # Suggestion 3: Consistency
        consistency = context.get("consistency_score", 0)
        
        if consistency >= 80:
            suggestions.append(SuggestionItem(
                title="Great consistency!",
                description=f"You've maintained {consistency}% study consistency. "
                           f"Keep this habit going to maximize retention.",
                priority="low"
            ))
        elif consistency < 50:
            suggestions.append(SuggestionItem(
                title="Improve consistency",
                description=f"Your consistency is at {consistency}%. "
                           f"Try studying at the same time daily to build a habit.",
                priority="high"
            ))
        
        # Suggestion 4: Today's progress
        completion = context.get("completion_percentage", 0)
        
        if completion == 100:
            suggestions.append(SuggestionItem(
                title="Perfect day!",
                description="You completed all tasks today. Excellent work! "
                           "Maintain this momentum tomorrow.",
                priority="low"
            ))
        elif completion < 50 and context.get("total_tasks", 0) > 0:
            suggestions.append(SuggestionItem(
                title="Complete today's tasks",
                description=f"You've completed {context.get('tasks_completed', 0)}/{context.get('total_tasks', 0)} tasks. "
                           f"Finish remaining tasks before end of day.",
                priority="medium"
            ))
        
        # Return top 3 suggestions (prioritized)
        # Sort: high > medium > low
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))
        
        return SuggestionsResponse(
            suggestions=suggestions[:3]  # Max 3 suggestions
        )
