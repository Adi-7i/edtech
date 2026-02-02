"""
Task Execution Dependencies

Reusable dependencies for ownership and validation.
"""

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_plan import StudyTaskModel
from app.core.database.models.user import UserModel
from app.core.database.mongo import get_database
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.auth.dependencies import get_current_user
from app.modules.tasks.repository import TaskExecutionRepository


async def verify_task_ownership(
    task_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> StudyTaskModel:
    """
    Verify task belongs to current user.
    
    Args:
        task_id: Task ID from path
        current_user: Current authenticated user
        db: Database connection
    
    Returns:
        StudyTaskModel if found and owned
    
    Raises:
        NotFoundException: Task not found
        ForbiddenException: Task not owned by user
    """
    task_repo = TaskExecutionRepository(db)
    
    task = await task_repo.find_by_id(task_id)
    if not task:
        raise NotFoundException(message="Task not found")
    
    # Verify ownership
    if str(task.user_id) != str(current_user.id):
        raise ForbiddenException(message="You do not own this task")
    
    return task
