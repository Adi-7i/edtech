"""
Analytics Repository

Data aggregation from tasks, revisions, and study profiles.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_plan import StudyTaskModel, TaskStatus
from app.core.database.models.revision import RevisionModel, RevisionStatus
from app.modules.analytics.schemas import StudyStreakData, SubjectStatistics


class AnalyticsRepository:
    """Repository for aggregating analytics data."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.tasks_collection = db.study_tasks
        self.daily_plans_collection = db.daily_plans
        self.revisions_collection = db.revisions
        self.chapters_collection = db.user_chapters
        self.subjects_collection = db.user_subjects
        self.profiles_collection = db.study_profiles
    
    async def get_daily_task_summary(
        self,
        user_id: str,
        target_date: date
    ) -> Dict:
        """
        Aggregate task summary for a specific date.
        
        Args:
            user_id: User ID
            target_date: Date to get summary for
        
        Returns:
            Dictionary with task counts and time metrics
        """
        # Find daily plan for this date
        daily_plan = await self.daily_plans_collection.find_one({
            "user_id": ObjectId(user_id),
            "date": target_date
        })
        
        if not daily_plan:
            return {
                "planned_tasks": 0,
                "completed_tasks": 0,
                "partial_tasks": 0,
                "missed_tasks": 0,
                "planned_minutes": 0,
                "actual_minutes": 0,
                "has_plan": False
            }
        
        # Get all tasks for this daily plan
        tasks_cursor = self.tasks_collection.find({
            "daily_plan_id": daily_plan["_id"]
        })
        
        tasks = await tasks_cursor.to_list(length=100)
        
        # Calculate metrics
        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t.get("status") == TaskStatus.COMPLETED)
        partial = sum(1 for t in tasks if t.get("status") == TaskStatus.PARTIAL)
        missed = sum(1 for t in tasks if t.get("status") == TaskStatus.MISSED)
        
        # Calculate time
        total_allocated = sum(t.get("allocated_hours", 0) for t in tasks) * 60  # Convert to minutes
        total_actual = sum(t.get("actual_hours", 0) for t in tasks) * 60
        
        return {
            "planned_tasks": total_tasks,
            "completed_tasks": completed,
            "partial_tasks": partial,
            "missed_tasks": missed,
            "planned_minutes": int(total_allocated),
            "actual_minutes": int(total_actual),
            "has_plan": True
        }
    
    async def get_tasks_in_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Get all tasks within a date range.
        
        Args:
            user_id: User ID
            start_date: Range start (inclusive)
            end_date: Range end (inclusive)
        
        Returns:
            List of daily task summaries
        """
        summaries = []
        current_date = start_date
        
        while current_date <= end_date:
            summary = await self.get_daily_task_summary(user_id, current_date)
            summary["date"] = current_date.isoformat()
            summaries.append(summary)
            current_date += timedelta(days=1)
        
        return summaries
    
    async def get_study_streak(
        self,
        user_id: str,
        until_date: date
    ) -> StudyStreakData:
        """
        Calculate study streaks and activity metrics.
        
        Args:
            user_id: User ID
            until_date: Calculate streaks up to this date
        
        Returns:
            StudyStreakData with streak information
        """
        # Get profile to know start date
        profile = await self.profiles_collection.find_one({"user_id": ObjectId(user_id)})
        
        if not profile:
            return StudyStreakData(
                current_streak=0,
                longest_streak=0,
                total_study_days=0,
                partial_days=0
            )
        
        start_date = profile.get("created_at").date() if isinstance(profile.get("created_at"), datetime) else date.today()
        
        # Get all daily plans from start to until_date
        current_streak = 0
        longest_streak = 0
        temp_streak = 0
        total_study_days = 0
        partial_days = 0
        
        current_date = until_date
        
        # Calculate current streak (working backwards from until_date)
        while current_date >= start_date:
            summary = await self.get_daily_task_summary(user_id, current_date)
            
            if summary["completed_tasks"] > 0:
                current_streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        # Calculate longest streak and total stats (forward from start)
        current_date = start_date
        while current_date <= until_date:
            summary = await self.get_daily_task_summary(user_id, current_date)
            
            if summary["completed_tasks"] > 0 or summary["partial_tasks"] > 0:
                total_study_days += 1
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
                
                if summary["partial_tasks"] > 0 and summary["completed_tasks"] == 0:
                    partial_days += 1
            else:
                temp_streak = 0
            
            current_date += timedelta(days=1)
        
        return StudyStreakData(
            current_streak=current_streak,
            longest_streak=longest_streak,
            total_study_days=total_study_days,
            partial_days=partial_days
        )
    
    async def get_subject_statistics(
        self,
        user_id: str,
        subject_id: str
    ) -> SubjectStatistics:
        """
        Get comprehensive statistics for a subject.
        
        Args:
            user_id: User ID
            subject_id: Subject ID
        
        Returns:
            SubjectStatistics with detailed metrics
        """
        # Get all chapters for this subject
        chapters_cursor = self.chapters_collection.find({
            "user_id": ObjectId(user_id),
            "subject_id": ObjectId(subject_id)
        })
        
        chapters = await chapters_cursor.to_list(length=500)
        
        total = len(chapters)
        completed = sum(1 for c in chapters if c.get("is_completed", False))
        
        # Count by strength
        weak = sum(1 for c in chapters if c.get("strength") == "weak")
        medium = sum(1 for c in chapters if c.get("strength") == "medium")
        strong = sum(1 for c in chapters if c.get("strength") == "strong")
        
        # Count revised chapters
        chapter_ids = [c["_id"] for c in chapters]
        revised_count = 0
        
        for chapter_id in chapter_ids:
            revision = await self.revisions_collection.find_one({
                "user_id": ObjectId(user_id),
                "chapter_id": chapter_id
            })
            if revision:
                revised_count += 1
        
        return SubjectStatistics(
            total_chapters=total,
            completed_chapters=completed,
            weak_count=weak,
            medium_count=medium,
            strong_count=strong,
            revised_count=revised_count
        )
    
    async def get_all_subjects_stats(
        self,
        user_id: str
    ) -> List[Tuple[Dict, SubjectStatistics]]:
        """
        Get statistics for all user's subjects.
        
        Args:
            user_id: User ID
        
        Returns:
            List of tuples (subject_doc, statistics)
        """
        subjects_cursor = self.subjects_collection.find({
            "user_id": ObjectId(user_id)
        })
        
        subjects = await subjects_cursor.to_list(length=50)
        
        results = []
        for subject in subjects:
            stats = await self.get_subject_statistics(user_id, str(subject["_id"]))
            results.append((subject, stats))
        
        return results
    
    async def count_total_study_hours(
        self,
        user_id: str
    ) -> float:
        """
        Sum of all actual study hours from completed tasks.
        
        Args:
            user_id: User ID
        
        Returns:
            Total study hours (float)
        """
        # Aggregate all tasks for user
        pipeline = [
            {
                "$lookup": {
                    "from": "daily_plans",
                    "localField": "daily_plan_id",
                    "foreignField": "_id",
                    "as": "plan"
                }
            },
            {
                "$match": {
                    "plan.user_id": ObjectId(user_id),
                    "actual_hours": {"$exists": True, "$gt": 0}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_hours": {"$sum": "$actual_hours"}
                }
            }
        ]
        
        cursor = self.tasks_collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        
        if result:
            return float(result[0].get("total_hours", 0))
        
        return 0.0
    
    async def count_completed_revisions(
        self,
        user_id: str
    ) -> int:
        """
        Count total completed revisions.
        
        Args:
            user_id: User ID
        
        Returns:
            Number of completed revision cycles
        """
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id)
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_cycles": {"$sum": "$cycles_completed"}
                }
            }
        ]
        
        cursor = self.revisions_collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        
        if result:
            return int(result[0].get("total_cycles", 0))
        
        return 0
