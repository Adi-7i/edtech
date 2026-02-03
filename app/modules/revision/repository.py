"""
Revision Repository

Database operations for revision scheduling and tracking.
"""

from datetime import date, datetime
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.revision import (
    RevisionHistory,
    RevisionModel,
    RevisionQuality,
    RevisionStatus,
)


class RevisionRepository:
    """Repository for revision CRUD operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.revisions
    
    async def create(
        self,
        user_id: str,
        chapter_id: str,
        subject_id: str,
        chapter_name: str,
        subject_name: str,
        original_learning_date: date,
        first_revision_date: date,
        learning_task_id: Optional[str] = None
    ) -> RevisionModel:
        """
        Create a new revision schedule for a chapter.
        
        Args:
            user_id: User ID
            chapter_id: User chapter ID
            subject_id: Subject ID
            chapter_name: Chapter name
            subject_name: Subject name
            original_learning_date: Date chapter was learned
            first_revision_date: Date of first revision (Day 1)
            learning_task_id: Optional reference to learning task
        
        Returns:
            Created RevisionModel
        """
        revision = RevisionModel(
            user_id=ObjectId(user_id),
            chapter_id=ObjectId(chapter_id),
            subject_id=ObjectId(subject_id),
            chapter_name=chapter_name,
            subject_name=subject_name,
            original_learning_date=original_learning_date,
            learning_task_id=learning_task_id,
            current_cycle_day=1,
            next_revision_date=first_revision_date,
            status=RevisionStatus.SCHEDULED,
            cycles_completed=0,
            is_mastered=False,
            missed_count=0,
            consecutive_misses=0,
            history=[],
            topic_progress=[],
            total_revision_minutes=0,
            priority_score=5
        )
        
        doc = revision.to_mongo()
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        
        return RevisionModel.from_mongo(doc)
    
    async def find_by_id(self, revision_id: str) -> Optional[RevisionModel]:
        """Find revision by ID."""
        doc = await self.collection.find_one({"_id": ObjectId(revision_id)})
        return RevisionModel.from_mongo(doc) if doc else None
    
    async def find_by_user_and_chapter(
        self,
        user_id: str,
        chapter_id: str
    ) -> Optional[RevisionModel]:
        """
        Find active revision schedule for a user's chapter.
        
        Args:
            user_id: User ID
            chapter_id: Chapter ID
        
        Returns:
            RevisionModel if exists, else None
        """
        doc = await self.collection.find_one({
            "user_id": ObjectId(user_id),
            "chapter_id": ObjectId(chapter_id)
        })
        return RevisionModel.from_mongo(doc) if doc else None
    
    async def find_by_user_and_date(
        self,
        user_id: str,
        revision_date: date
    ) -> List[RevisionModel]:
        """
        Find all revisions scheduled for a specific date.
        
        Args:
            user_id: User ID
            revision_date: Target date
        
        Returns:
            List of RevisionModel
        """
        cursor = self.collection.find({
            "user_id": ObjectId(user_id),
            "next_revision_date": revision_date
        })
        
        docs = await cursor.to_list(length=100)
        return [RevisionModel.from_mongo(doc) for doc in docs]
    
    async def find_due_revisions(
        self,
        user_id: str,
        up_to_date: date
    ) -> List[RevisionModel]:
        """
        Find all revisions due up to a certain date.
        
        Args:
            user_id: User ID
            up_to_date: Find revisions due up to this date (inclusive)
        
        Returns:
            List of RevisionModel ordered by next_revision_date
        """
        cursor = self.collection.find({
            "user_id": ObjectId(user_id),
            "next_revision_date": {"$lte": up_to_date},
            "status": {"$nin": [RevisionStatus.COMPLETED]}
        }).sort("next_revision_date", 1)
        
        docs = await cursor.to_list(length=100)
        return [RevisionModel.from_mongo(doc) for doc in docs]
    
    async def find_overdue_revisions(
        self,
        user_id: str,
        today: date
    ) -> List[RevisionModel]:
        """
        Find all overdue revisions (scheduled before today, not completed).
        
        Args:
            user_id: User ID
            today: Current date
        
        Returns:
            List of overdue RevisionModel
        """
        cursor = self.collection.find({
            "user_id": ObjectId(user_id),
            "next_revision_date": {"$lt": today},
            "status": {"$in": [RevisionStatus.SCHEDULED, RevisionStatus.DUE]}
        })
        
        docs = await cursor.to_list(length=100)
        return [RevisionModel.from_mongo(doc) for doc in docs]
    
    async def update_after_completion(
        self,
        revision_id: str,
        completed_date: date,
        quality: RevisionQuality,
        duration_minutes: int,
        notes: Optional[str],
        next_cycle_day: int,
        next_revision_date: date
    ) -> Optional[RevisionModel]:
        """
        Update revision after successful completion.
        
        Args:
            revision_id: Revision ID
            completed_date: Date completed
            quality: Recall quality
            duration_minutes: Time spent
            notes: Optional notes
            next_cycle_day: Next cycle day value
            next_revision_date: Next scheduled date
        
        Returns:
            Updated RevisionModel
        """
        # Create history entry
        history_entry = RevisionHistory(
            revision_date=completed_date,
            cycle_day=next_cycle_day,
            status=RevisionStatus.COMPLETED,
            quality=quality,
            duration_minutes=duration_minutes,
            was_rescheduled=False,
            notes=notes
        )
        
        update_data = {
            "status": RevisionStatus.SCHEDULED,  # Reset to scheduled for next cycle
            "current_cycle_day": next_cycle_day,
            "next_revision_date": next_revision_date,
            "consecutive_misses": 0,  # Reset miss counter
            "$inc": {
                "cycles_completed": 1,
                "total_revision_minutes": duration_minutes
            },
            "$push": {
                "history": {
                    "$each": [history_entry.model_dump()],
                    "$slice": -10  # Keep last 10 entries
                }
            },
            "updated_at": datetime.utcnow()
        }
        
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(revision_id)},
            {"$set": update_data, **{k: v for k, v in update_data.items() if k.startswith("$")}},
            return_document=True
        )
        
        return RevisionModel.from_mongo(result) if result else None
    
    async def mark_as_missed(
        self,
        revision_id: str,
        missed_date: date,
        next_revision_date: date
    ) -> Optional[RevisionModel]:
        """
        Mark revision as missed and reschedule.
        
        Args:
            revision_id: Revision ID
            missed_date: Date that was missed
            next_revision_date: Rescheduled date
        
        Returns:
            Updated RevisionModel
        """
        # Create history entry
        history_entry = RevisionHistory(
            revision_date=missed_date,
            cycle_day=0,  # Missed
            status=RevisionStatus.MISSED,
            quality=None,
            duration_minutes=0,
            was_rescheduled=True,
            notes="Auto-rescheduled due to miss"
        )
        
        update_data = {
            "status": RevisionStatus.RESCHEDULED,
            "next_revision_date": next_revision_date,
            "last_missed_date": missed_date,
            "$inc": {
                "missed_count": 1,
                "consecutive_misses": 1
            },
            "$push": {
                "history": {
                    "$each": [history_entry.model_dump()],
                    "$slice": -10
                }
            },
            "updated_at": datetime.utcnow()
        }
        
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(revision_id)},
            {"$set": {k: v for k, v in update_data.items() if not k.startswith("$")},
             **{k: v for k, v in update_data.items() if k.startswith("$")}},
            return_document=True
        )
        
        return RevisionModel.from_mongo(result) if result else None
    
    async def mark_as_mastered(self, revision_id: str) -> Optional[RevisionModel]:
        """
        Mark revision schedule as mastered (all cycles complete).
        
        Args:
            revision_id: Revision ID
        
        Returns:
            Updated RevisionModel
        """
        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(revision_id)},
            {
                "$set": {
                    "is_mastered": True,
                    "status": RevisionStatus.COMPLETED,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        
        return RevisionModel.from_mongo(result) if result else None
    
    async def delete(self, revision_id: str) -> bool:
        """
        Delete a revision schedule.
        
        Args:
            revision_id: Revision ID
        
        Returns:
            True if deleted
        """
        result = await self.collection.delete_one({"_id": ObjectId(revision_id)})
        return result.deleted_count > 0
    
    async def find_all_by_user(
        self,
        user_id: str,
        include_mastered: bool = False
    ) -> List[RevisionModel]:
        """
        Find all revision schedules for a user.
        
        Args:
            user_id: User ID
            include_mastered: Include mastered revisions
        
        Returns:
            List of RevisionModel
        """
        query = {"user_id": ObjectId(user_id)}
        
        if not include_mastered:
            query["is_mastered"] = False
        
        cursor = self.collection.find(query).sort("next_revision_date", 1)
        docs = await cursor.to_list(length=500)
        
        return [RevisionModel.from_mongo(doc) for doc in docs]
