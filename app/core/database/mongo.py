"""
Smart Study Planner - MongoDB Connection Management

Async MongoDB connection using Motor (async driver for MongoDB).
Provides database lifecycle management and connection pooling.

Usage:
    from app.core.database.mongo import get_database
    
    async def some_function():
        db = await get_database()
        collection = db[Collections.USERS]
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Global MongoDB Client
# -----------------------------------------------------------------------------

# Motor client instance (initialized on startup)
_mongodb_client: Optional[AsyncIOMotorClient] = None
_mongodb_database: Optional[AsyncIOMotorDatabase] = None


# -----------------------------------------------------------------------------
# Connection Management
# -----------------------------------------------------------------------------

async def connect_to_mongodb() -> None:
    """
    Initialize MongoDB connection.
    
    Called during application startup.
    Creates connection pool and validates connection.
    
    Raises:
        Exception: If connection fails
    """
    global _mongodb_client, _mongodb_database
    
    settings = get_settings()
    
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}")
        
        # Create Motor client with connection pooling
        _mongodb_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            **settings.mongodb_connection_params,
        )
        
        # Get database instance
        _mongodb_database = _mongodb_client[settings.MONGODB_DB_NAME]
        
        # Verify connection by pinging
        await _mongodb_client.admin.command("ping")
        
        logger.info(
            f"Successfully connected to MongoDB database: {settings.MONGODB_DB_NAME}"
        )
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongodb_connection() -> None:
    """
    Close MongoDB connection.
    
    Called during application shutdown.
    Ensures all connections are properly closed.
    """
    global _mongodb_client, _mongodb_database
    
    if _mongodb_client:
        logger.info("Closing MongoDB connection")
        _mongodb_client.close()
        _mongodb_client = None
        _mongodb_database = None
        logger.info("MongoDB connection closed")


# -----------------------------------------------------------------------------
# Database Accessor
# -----------------------------------------------------------------------------

async def get_database() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance.
    
    This is the primary way to access the database throughout the application.
    Use as a dependency in FastAPI routes or service layers.
    
    Returns:
        AsyncIOMotorDatabase: MongoDB database instance
    
    Raises:
        RuntimeError: If database is not initialized
    
    Example:
        ```python
        async def get_user(user_id: str):
            db = await get_database()
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            return user
        ```
    """
    if _mongodb_database is None:
        raise RuntimeError(
            "Database is not initialized. Ensure connect_to_mongodb() "
            "is called during application startup."
        )
    return _mongodb_database


def get_client() -> AsyncIOMotorClient:
    """
    Get MongoDB client instance.
    
    Use this only when you need client-level operations
    (e.g., transactions, admin commands).
    
    For regular database operations, use get_database() instead.
    
    Returns:
        AsyncIOMotorClient: MongoDB client instance
    
    Raises:
        RuntimeError: If client is not initialized
    """
    if _mongodb_client is None:
        raise RuntimeError(
            "MongoDB client is not initialized. Ensure connect_to_mongodb() "
            "is called during application startup."
        )
    return _mongodb_client


# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------

async def check_database_health() -> bool:
    """
    Check MongoDB connection health.
    
    Used by health check endpoints to verify database connectivity.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        if _mongodb_client is None:
            return False
        
        # Ping database with timeout
        await _mongodb_client.admin.command("ping", serverSelectionTimeoutMS=2000)
        return True
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
