"""
AI Assistant Repository

Data access layer for AI query logging and usage tracking.
"""

from datetime import date, datetime
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.ai_query import AIDailyUsage, AIQueryLog, QueryType


class AIAssistantRepository:
    """Repository for AI assistant operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.query_logs = db.ai_query_logs
        self.daily_usage = db.ai_daily_usage
    
    async def log_query(
        self,
        user_id: str,
        query: str,
        query_type: QueryType,
        response: str,
        tokens_used: int,
        response_time_ms: int,
        context: dict
    ) -> AIQueryLog:
        """
        Log AI query for transparency and analytics.
        
        Args:
            user_id: User ID
            query: User's question
            query_type: Type of query
            response: AI-generated response
            tokens_used: Tokens consumed
            response_time_ms: Response time in milliseconds
            context: User context injected into prompt
        
        Returns:
            Created AIQueryLog
        """
        log_entry = AIQueryLog(
            user_id=ObjectId(user_id),
            query=query,
            query_type=query_type,
            response=response,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            context_injected=context
        )
        
        result = await self.query_logs.insert_one(log_entry.to_mongo())
        log_entry.id = result.inserted_id
        
        return log_entry
    
    async def get_daily_usage(
        self,
        user_id: str,
        target_date: date
    ) -> int:
        """
        Get query count for a specific date.
        
        Args:
            user_id: User ID
            target_date: Date to check
        
        Returns:
            Number of queries used on that date
        """
        date_dt = datetime.combine(target_date, datetime.min.time())
        
        doc = await self.daily_usage.find_one({
            "user_id": ObjectId(user_id),
            "date": date_dt
        })
        
        if doc:
            return doc.get("query_count", 0)
        
        return 0
    
    async def increment_daily_usage(
        self,
        user_id: str,
        target_date: date
    ) -> AIDailyUsage:
        """
        Increment daily usage counter.
        
        Creates document if it doesn't exist (upsert).
        
        Args:
            user_id: User ID
            target_date: Date to increment
        
        Returns:
            Updated AIDailyUsage
        """
        date_dt = datetime.combine(target_date, datetime.min.time())
        
        result = await self.daily_usage.find_one_and_update(
            {
                "user_id": ObjectId(user_id),
                "date": date_dt
            },
            {
                "$inc": {"query_count": 1},
                "$setOnInsert": {
                    "user_id": ObjectId(user_id),
                    "date": date_dt,
                    "daily_limit": 50,
                    "created_at": datetime.utcnow()
                },
                "$set": {"updated_at": datetime.utcnow()}
            },
            upsert=True,
            return_document=True
        )
        
        return AIDailyUsage(**result)
    
    async def get_recent_queries(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[AIQueryLog]:
        """
        Get recent query history for user.
        
        Args:
            user_id: User ID
            limit: Maximum number of queries to return
        
        Returns:
            List of AIQueryLog (most recent first)
        """
        cursor = self.query_logs.find({
            "user_id": ObjectId(user_id)
        }).sort("created_at", -1).limit(limit)
        
        queries = []
        async for doc in cursor:
            queries.append(AIQueryLog(**doc))
        
        return queries
    
    async def get_total_queries(
        self,
        user_id: str
    ) -> int:
        """
        Get total number of queries by user (all time).
        
        Args:
            user_id: User ID
        
        Returns:
            Total query count
        """
        count = await self.query_logs.count_documents({
            "user_id": ObjectId(user_id)
        })
        
        return count
