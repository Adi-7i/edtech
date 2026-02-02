"""
Planner Repository

Database access layer for study plans, daily plans, and tasks.
"""

from datetime import date, datetime
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_plan import (
    DailyPlanModel,
    PlanStatus,
    StudyPlanModel,
    StudyTaskModel,
    TaskStatus,
)


class StudyPlanRepository:
    """Repository for StudyPlan operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[StudyPlanModel.Settings.name]
    
    async def create(self, plan: StudyPlanModel) -> StudyPlanModel:
        """Create a new study plan."""
        plan_dict = plan.model_dump_mongo()
        result = await self.collection.insert_one(plan_dict)
        plan.id = result.inserted_id
        return plan
    
    async def find_by_id(self, plan_id: str) -> Optional[StudyPlanModel]:
        """Find plan by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(plan_id)})
            if doc:
                return StudyPlanModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def find_active_by_user(self, user_id: str) -> Optional[StudyPlanModel]:
        """Find active plan for user."""
        try:
            doc = await self.collection.find_one({
                "user_id": ObjectId(user_id),
                "is_active": True,
                "status": PlanStatus.ACTIVE
            })
            if doc:
                return StudyPlanModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def deactivate_user_plans(self, user_id: str) -> int:
        """Deactivate all plans for a user."""
        try:
            result = await self.collection.update_many(
                {"user_id": ObjectId(user_id), "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "status": PlanStatus.ARCHIVED,
                        "last_updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count
        except Exception:
            return 0
    
    async def update(self, plan_id: str, updates: dict) -> Optional[StudyPlanModel]:
        """Update plan with given fields."""
        try:
            updates["last_updated_at"] = datetime.utcnow()
            await self.collection.update_one(
                {"_id": ObjectId(plan_id)},
                {"$set": updates}
            )
            return await self.find_by_id(plan_id)
        except Exception:
            return None
    
    async def delete(self, plan_id: str) -> bool:
        """Delete a plan."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(plan_id)})
            return result.deleted_count > 0
        except Exception:
            return False


class DailyPlanRepository:
    """Repository for DailyPlan operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[DailyPlanModel.Settings.name]
    
    async def create(self, daily_plan: DailyPlanModel) -> DailyPlanModel:
        """Create a new daily plan."""
        plan_dict = daily_plan.model_dump_mongo()
        result = await self.collection.insert_one(plan_dict)
        daily_plan.id = result.inserted_id
        return daily_plan
    
    async def create_many(self, daily_plans: List[DailyPlanModel]) -> List[DailyPlanModel]:
        """Create multiple daily plans."""
        if not daily_plans:
            return []
        
        plan_dicts = [p.model_dump_mongo() for p in daily_plans]
        result = await self.collection.insert_many(plan_dicts)
        
        for plan, inserted_id in zip(daily_plans, result.inserted_ids):
            plan.id = inserted_id
        
        return daily_plans
    
    async def find_by_id(self, daily_plan_id: str) -> Optional[DailyPlanModel]:
        """Find daily plan by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(daily_plan_id)})
            if doc:
                return DailyPlanModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def find_by_user_and_date(self, user_id: str, plan_date: date) -> Optional[DailyPlanModel]:
        """Find daily plan for user on specific date."""
        try:
            doc = await self.collection.find_one({
                "user_id": ObjectId(user_id),
                "plan_date": plan_date
            })
            if doc:
                return DailyPlanModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def find_by_plan(self, plan_id: str) -> List[DailyPlanModel]:
        """Find all daily plans for a study plan."""
        daily_plans = []
        try:
            cursor = self.collection.find({
                "plan_id": ObjectId(plan_id)
            }).sort("date", 1)
            
            async for doc in cursor:
                daily_plans.append(DailyPlanModel.from_mongo(doc))
        except Exception:
            pass
        return daily_plans
    
    async def find_by_date_range(
        self,
        plan_id: str,
        start_date: date,
        end_date: date
    ) -> List[DailyPlanModel]:
        """Find daily plans within date range."""
        daily_plans = []
        try:
            cursor = self.collection.find({
                "plan_id": ObjectId(plan_id),
                "plan_date": {"$gte": start_date, "$lte": end_date}
            }).sort("plan_date", 1)
            
            async for doc in cursor:
                daily_plans.append(DailyPlanModel.from_mongo(doc))
        except Exception:
            pass
        return daily_plans
    
    async def update(self, daily_plan_id: str, updates: dict) -> Optional[DailyPlanModel]:
        """Update daily plan."""
        try:
            await self.collection.update_one(
                {"_id": ObjectId(daily_plan_id)},
                {"$set": updates}
            )
            return await self.find_by_id(daily_plan_id)
        except Exception:
            return None
    
    async def delete_by_plan(self, plan_id: str) -> int:
        """Delete all daily plans for a study plan."""
        try:
            result = await self.collection.delete_many({"plan_id": ObjectId(plan_id)})
            return result.deleted_count
        except Exception:
            return 0


class StudyTaskRepository:
    """Repository for StudyTask operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[StudyTaskModel.Settings.name]
    
    async def create(self, task: StudyTaskModel) -> StudyTaskModel:
        """Create a new study task."""
        task_dict = task.model_dump_mongo()
        result = await self.collection.insert_one(task_dict)
        task.id = result.inserted_id
        return task
    
    async def create_many(self, tasks: List[StudyTaskModel]) -> List[StudyTaskModel]:
        """Create multiple tasks."""
        if not tasks:
            return []
        
        task_dicts = [t.model_dump_mongo() for t in tasks]
        result = await self.collection.insert_many(task_dicts)
        
        for task, inserted_id in zip(tasks, result.inserted_ids):
            task.id = inserted_id
        
        return tasks
    
    async def find_by_id(self, task_id: str) -> Optional[StudyTaskModel]:
        """Find task by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(task_id)})
            if doc:
                return StudyTaskModel.from_mongo(doc)
        except Exception:
            pass
        return None
    
    async def find_by_daily_plan(self, daily_plan_id: str) -> List[StudyTaskModel]:
        """Find all tasks for a daily plan."""
        tasks = []
        try:
            cursor = self.collection.find({
                "daily_plan_id": ObjectId(daily_plan_id)
            }).sort("order_in_day", 1)
            
            async for doc in cursor:
                tasks.append(StudyTaskModel.from_mongo(doc))
        except Exception:
            pass
        return tasks
    
    async def find_by_plan(self, plan_id: str) -> List[StudyTaskModel]:
        """Find all tasks for a study plan."""
        tasks = []
        try:
            cursor = self.collection.find({
                "plan_id": ObjectId(plan_id)
            })
            
            async for doc in cursor:
                tasks.append(StudyTaskModel.from_mongo(doc))
        except Exception:
            pass
        return tasks
    
    async def update(self, task_id: str, updates: dict) -> Optional[StudyTaskModel]:
        """Update task."""
        try:
            await self.collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": updates}
            )
            return await self.find_by_id(task_id)
        except Exception:
            return None
    
    async def mark_completed(self, task_id: str, actual_hours: float) -> Optional[StudyTaskModel]:
        """Mark task as completed."""
        updates = {
            "status": TaskStatus.COMPLETED,
            "is_completed": True,
            "completed_at": datetime.utcnow(),
            "actual_hours": actual_hours
        }
        return await self.update(task_id, updates)
    
    async def delete_by_plan(self, plan_id: str) -> int:
        """Delete all tasks for a study plan."""
        try:
            result = await self.collection.delete_many({"plan_id": ObjectId(plan_id)})
            return result.deleted_count
        except Exception:
            return 0
