"""
Study Profile Repository Layer

Database access layer for:
- Study profiles
- User subjects
- User chapters
"""

from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_profile import StudyProfileModel
from app.modules.study_profile.models import UserChapterModel, UserSubjectModel
from app.shared.constants import Collections


# -----------------------------------------------------------------------------
# Study Profile Repository
# -----------------------------------------------------------------------------

class StudyProfileRepository:
    """Repository for study profile database operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[Collections.STUDY_PROFILES]
    
    async def create(self, profile: StudyProfileModel) -> StudyProfileModel:
        """Create a new study profile."""
        profile_dict = profile.model_dump_mongo()
        result = await self.collection.insert_one(profile_dict)
        profile.id = result.inserted_id
        return profile
    
    async def find_by_user_id(self, user_id: str) -> Optional[StudyProfileModel]:
        """Find profile by user ID (one profile per user)."""
        try:
            doc = await self.collection.find_one({"user_id": ObjectId(user_id)})
            if doc:
                return StudyProfileModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def find_by_id(self, profile_id: str) -> Optional[StudyProfileModel]:
        """Find profile by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(profile_id)})
            if doc:
                return StudyProfileModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def update(
        self,
        profile_id: str,
        update_data: dict
    ) -> Optional[StudyProfileModel]:
        """Update a study profile."""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(profile_id)},
                {"$set": update_data},
                return_document=True
            )
            if result:
                return StudyProfileModel.from_mongo(result)
        except Exception:
            pass
        return None
    
    async def delete(self, profile_id: str) -> bool:
        """Delete a study profile."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(profile_id)})
            return result.deleted_count > 0
        except Exception:
            return False
    
    async def exists_for_user(self, user_id: str) -> bool:
        """Check if profile exists for user."""
        try:
            count = await self.collection.count_documents(
                {"user_id": ObjectId(user_id)},
                limit=1
            )
            return count > 0
        except Exception:
            return False


# -----------------------------------------------------------------------------
# User Subject Repository
# -----------------------------------------------------------------------------

class UserSubjectRepository:
    """Repository for user subject database operations."""
    
    COLLECTION_NAME = "user_subjects"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
    
    async def create(self, subject: UserSubjectModel) -> UserSubjectModel:
        """Create a new user subject."""
        subject_dict = subject.model_dump_mongo()
        result = await self.collection.insert_one(subject_dict)
        subject.id = result.inserted_id
        return subject
    
    async def create_many(
        self,
        subjects: List[UserSubjectModel]
    ) -> List[UserSubjectModel]:
        """Create multiple user subjects."""
        if not subjects:
            return []
        
        subject_dicts = [s.model_dump_mongo() for s in subjects]
        result = await self.collection.insert_many(subject_dicts)
        
        for i, inserted_id in enumerate(result.inserted_ids):
            subjects[i].id = inserted_id
        
        return subjects
    
    async def find_by_profile(
        self,
        profile_id: str,
        enabled_only: bool = False
    ) -> List[UserSubjectModel]:
        """Find all subjects for a profile."""
        try:
            query = {"profile_id": ObjectId(profile_id)}
            if enabled_only:
                query["is_enabled"] = True
            
            cursor = self.collection.find(query).sort("priority", 1)
            subjects = []
            async for doc in cursor:
                subjects.append(UserSubjectModel.from_mongo(doc))
            return subjects
        except Exception:
            return []
    
    async def find_by_id(self, subject_id: str) -> Optional[UserSubjectModel]:
        """Find user subject by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(subject_id)})
            if doc:
                return UserSubjectModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def find_by_profile_and_subject(
        self,
        profile_id: str,
        master_subject_id: str
    ) -> Optional[UserSubjectModel]:
        """Find user subject by profile and master subject ID."""
        try:
            doc = await self.collection.find_one({
                "profile_id": ObjectId(profile_id),
                "subject_id": ObjectId(master_subject_id)
            })
            if doc:
                return UserSubjectModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def update(
        self,
        subject_id: str,
        update_data: dict
    ) -> Optional[UserSubjectModel]:
        """Update a user subject."""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(subject_id)},
                {"$set": update_data},
                return_document=True
            )
            if result:
                return UserSubjectModel.from_mongo(result)
        except Exception:
            pass
        return None
    
    async def delete_by_profile(self, profile_id: str) -> int:
        """Delete all subjects for a profile."""
        try:
            result = await self.collection.delete_many({
                "profile_id": ObjectId(profile_id)
            })
            return result.deleted_count
        except Exception:
            return 0
    
    async def increment_chapters_completed(
        self,
        subject_id: str,
        increment: int = 1
    ) -> bool:
        """Increment chapters completed count."""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(subject_id)},
                {
                    "$inc": {"chapters_completed": increment},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )
            return result.modified_count > 0
        except Exception:
            return False


# -----------------------------------------------------------------------------
# User Chapter Repository
# -----------------------------------------------------------------------------

class UserChapterRepository:
    """Repository for user chapter database operations."""
    
    COLLECTION_NAME = "user_chapters"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
    
    async def create(self, chapter: UserChapterModel) -> UserChapterModel:
        """Create a new user chapter."""
        chapter_dict = chapter.model_dump_mongo()
        result = await self.collection.insert_one(chapter_dict)
        chapter.id = result.inserted_id
        return chapter
    
    async def create_many(
        self,
        chapters: List[UserChapterModel]
    ) -> List[UserChapterModel]:
        """Create multiple user chapters."""
        if not chapters:
            return []
        
        chapter_dicts = [c.model_dump_mongo() for c in chapters]
        result = await self.collection.insert_many(chapter_dicts)
        
        for i, inserted_id in enumerate(result.inserted_ids):
            chapters[i].id = inserted_id
        
        return chapters
    
    async def find_by_user_subject(
        self,
        user_subject_id: str
    ) -> List[UserChapterModel]:
        """Find all chapters for a user subject."""
        try:
            cursor = self.collection.find({
                "user_subject_id": ObjectId(user_subject_id)
            })
            chapters = []
            async for doc in cursor:
                chapters.append(UserChapterModel.from_mongo(doc))
            return chapters
        except Exception:
            return []
    
    async def find_by_profile(
        self,
        profile_id: str,
        strength_filter: Optional[str] = None
    ) -> List[UserChapterModel]:
        """Find all chapters for a profile."""
        try:
            query = {"profile_id": ObjectId(profile_id)}
            if strength_filter:
                query["strength"] = strength_filter
            
            cursor = self.collection.find(query)
            chapters = []
            async for doc in cursor:
                chapters.append(UserChapterModel.from_mongo(doc))
            return chapters
        except Exception:
            return []
    
    async def find_by_id(self, chapter_id: str) -> Optional[UserChapterModel]:
        """Find user chapter by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(chapter_id)})
            if doc:
                return UserChapterModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def update(
        self,
        chapter_id: str,
        update_data: dict
    ) -> Optional[UserChapterModel]:
        """Update a user chapter."""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(chapter_id)},
                {"$set": update_data},
                return_document=True
            )
            if result:
                return UserChapterModel.from_mongo(result)
        except Exception:
            pass
        return None
    
    async def delete(self, chapter_id: str) -> bool:
        """Delete a user chapter."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(chapter_id)})
            return result.deleted_count > 0
        except Exception:
            return False
    
    async def delete_by_profile(self, profile_id: str) -> int:
        """Delete all chapters for a profile."""
        try:
            result = await self.collection.delete_many({
                "profile_id": ObjectId(profile_id)
            })
            return result.deleted_count
        except Exception:
            return 0
    
    async def delete_by_user_subject(self, user_subject_id: str) -> int:
        """Delete all chapters for a user subject."""
        try:
            result = await self.collection.delete_many({
                "user_subject_id": ObjectId(user_subject_id)
            })
            return result.deleted_count
        except Exception:
            return 0
