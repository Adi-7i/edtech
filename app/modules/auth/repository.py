"""
Authentication Repository Layer

Database access layer for authentication operations.
Follows repository pattern for clean separation of concerns.
"""

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.user import UserModel
from app.modules.auth.models import RefreshTokenModel
from app.shared.constants import Collections


# -----------------------------------------------------------------------------
# User Repository
# -----------------------------------------------------------------------------

class UserRepository:
    """Repository for user database operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize user repository.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db[Collections.USERS]
    
    async def create_user(self, user: UserModel) -> UserModel:
        """
        Create a new user.
        
        Args:
            user: User model to create
        
        Returns:
            UserModel: Created user with ID
        """
        user_dict = user.model_dump_mongo()
        result = await self.collection.insert_one(user_dict)
        user.id = result.inserted_id
        return user
    
    async def find_by_email(self, email: str) -> Optional[UserModel]:
        """
        Find user by email address.
        
        Args:
            email: User email address
        
        Returns:
            UserModel: User if found, None otherwise
        """
        user_dict = await self.collection.find_one({"email": email.lower()})
        if user_dict:
            return UserModel.from_mongo(user_dict)
        return None
    
    async def find_by_id(self, user_id: str) -> Optional[UserModel]:
        """
        Find user by ID.
        
        Args:
            user_id: User ID string
        
        Returns:
            UserModel: User if found, None otherwise
        """
        try:
            user_dict = await self.collection.find_one({"_id": ObjectId(user_id)})
            if user_dict:
                return UserModel.from_mongo(user_dict)
        except Exception:
            pass
        return None
    
    async def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User ID
        
        Returns:
            bool: True if updated, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "last_login": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    async def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.
        
        Args:
            email: Email address to check
        
        Returns:
            bool: True if exists, False otherwise
        """
        count = await self.collection.count_documents(
            {"email": email.lower()},
            limit=1
        )
        return count > 0


# -----------------------------------------------------------------------------
# Refresh Token Repository
# -----------------------------------------------------------------------------

class RefreshTokenRepository:
    """Repository for refresh token database operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize refresh token repository.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db["refresh_tokens"]
    
    async def create_token(self, token: RefreshTokenModel) -> RefreshTokenModel:
        """
        Store a refresh token.
        
        Args:
            token: Refresh token model
        
        Returns:
            RefreshTokenModel: Created token with ID
        """
        token_dict = token.model_dump_mongo()
        result = await self.collection.insert_one(token_dict)
        token.id = result.inserted_id
        return token
    
    async def find_by_token(self, token: str) -> Optional[RefreshTokenModel]:
        """
        Find refresh token by token value.
        
        Args:
            token: Hashed refresh token
        
        Returns:
            RefreshTokenModel: Token if found, None otherwise
        """
        token_dict = await self.collection.find_one({"token": token})
        if token_dict:
            return RefreshTokenModel.from_mongo(token_dict)
        return None
    
    async def find_by_user(
        self,
        user_id: str,
        device_id: Optional[str] = None
    ) -> Optional[RefreshTokenModel]:
        """
        Find refresh token by user ID and optional device ID.
        
        Args:
            user_id: User ID
            device_id: Optional device ID
        
        Returns:
            RefreshTokenModel: Token if found, None otherwise
        """
        query = {
            "user_id": ObjectId(user_id),
            "is_revoked": False,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        }
        
        if device_id:
            query["device_id"] = device_id
        
        token_dict = await self.collection.find_one(query)
        if token_dict:
            return RefreshTokenModel.from_mongo(token_dict)
        return None
    
    async def revoke_token(self, token_id: str) -> bool:
        """
        Revoke a refresh token.
        
        Args:
            token_id: Token ID
        
        Returns:
            bool: True if revoked, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(token_id)},
                {
                    "$set": {
                        "is_revoked": True,
                        "revoked_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            int: Number of tokens revoked
        """
        try:
            result = await self.collection.update_many(
                {
                    "user_id": ObjectId(user_id),
                    "is_revoked": False
                },
                {
                    "$set": {
                        "is_revoked": True,
                        "revoked_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                }
            )
            return result.modified_count
        except Exception:
            return 0
    
    async def update_last_used(self, token_id: str) -> bool:
        """
        Update token's last used timestamp.
        
        Args:
            token_id: Token ID
        
        Returns:
            bool: True if updated, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(token_id)},
                {
                    "$set": {
                        "last_used_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Delete expired tokens (housekeeping).
        
        Returns:
            int: Number of tokens deleted
        """
        try:
            result = await self.collection.delete_many({
                "expires_at": {"$lt": datetime.now(timezone.utc)}
            })
            return result.deleted_count
        except Exception:
            return 0
