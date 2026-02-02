"""
Task Execution Repository

Database operations for task execution and tracking.
Extends StudyTaskRepository from planner module.
"""

from datetime import date, datetime
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_plan import StudyTaskModel, TaskStatus
from app.modules.planner.repository import StudyTaskRepository, DailyPlanRepository


class TaskExecutionRepository(StudyTaskRepository):
    """Repository for task execution operations."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)
        self.daily_plan_repo = DailyPlanRepository(db)
    
    async def find_by_date_and_user(
        self,
        user_id: str,
        task_date: date
    ) -> List[StudyTaskModel]:
        """
        Get all tasks for a user on a specific date.
        
        Args:
            user_id: User ID
            task_date: Date to fetch tasks for
        
        Returns:
            List of tasks ordered by order_in_day
        """
        try:
            # First, find the daily plan for this date
            daily_plan = await self.daily_plan_repo.find_by_user_and_date(
                user_id,
                task_date
            )
            
            if not daily_plan:
                return []
            
            # Get tasks for this daily plan
            tasks = await self.find_by_daily_plan(str(daily_plan.id))
            return tasks
            
        except Exception as e:
            raise Exception(f"Error fetching tasks by date: {str(e)}")
    
    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        notes: Optional[str] = None
    ) -> Optional[StudyTaskModel]:
        """
        Update task status and related fields.
        
        Args:
            task_id: Task ID
            status: New status
            notes: Optional notes
        
        Returns:
            Updated task model
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            # Set is_completed flag
            if status == TaskStatus.COMPLETED:
                update_data["is_completed"] = True
                update_data["completed_at"] = datetime.utcnow()
            elif status == TaskStatus.PARTIAL:
                update_data["is_completed"] = False
            elif status == TaskStatus.MISSED:
                update_data["is_completed"] = False
            
            # Add notes if provided
            if notes is not None:
                update_data["notes"] = notes
            
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(task_id)},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                return StudyTaskModel.from_mongo(result)
            return None
            
        except Exception as e:
            raise Exception(f"Error updating task status: {str(e)}")
    
    async def update_actual_time(
        self,
        task_id: str,
        actual_hours: float
    ) -> Optional[StudyTaskModel]:
        """
        Update actual time spent on a task.
        
        Args:
            task_id: Task ID
            actual_hours: New actual hours value
        
        Returns:
            Updated task model
        """
        try:
            update_data = {
                "actual_hours": actual_hours,
                "updated_at": datetime.utcnow()
            }
            
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(task_id)},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                return StudyTaskModel.from_mongo(result)
            return None
            
        except Exception as e:
            raise Exception(f"Error updating task time: {str(e)}")
    
    async def bulk_update_to_missed(
        self,
        task_ids: List[str]
    ) -> int:
        """
        Mark multiple tasks as missed.
        
        Args:
            task_ids: List of task IDs
        
        Returns:
            Number of tasks updated
        """
        try:
            if not task_ids:
                return 0
            
            object_ids = [ObjectId(tid) for tid in task_ids]
            
            result = await self.collection.update_many(
                {"_id": {"$in": object_ids}},
                {
                    "$set": {
                        "status": TaskStatus.MISSED,
                        "is_completed": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count
            
        except Exception as e:
            raise Exception(f"Error bulk updating to missed: {str(e)}")
    
    async def bulk_update_to_partial(
        self,
        task_ids: List[str]
    ) -> int:
        """
        Mark multiple tasks as partial.
        
        Args:
            task_ids: List of task IDs
        
        Returns:
            Number of tasks updated
        """
        try:
            if not task_ids:
                return 0
            
            object_ids = [ObjectId(tid) for tid in task_ids]
            
            result = await self.collection.update_many(
                {"_id": {"$in": object_ids}},
                {
                    "$set": {
                        "status": TaskStatus.PARTIAL,
                        "is_completed": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count
            
        except Exception as e:
            raise Exception(f"Error bulk updating to partial: {str(e)}")
