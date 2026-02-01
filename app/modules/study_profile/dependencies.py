"""
Study Profile Dependencies

FastAPI dependencies for:
- Access control
- Ownership verification
- Profile retrieval
"""

from typing import Optional

from bson import ObjectId
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_profile import StudyProfileModel
from app.core.database.models.user import UserModel
from app.core.database.mongo import get_database
from app.core.exceptions.handlers import ForbiddenException, NotFoundException
from app.modules.auth.dependencies import get_current_active_user
from app.modules.study_profile.models import UserChapterModel, UserSubjectModel
from app.modules.study_profile.repository import (
    StudyProfileRepository,
    UserChapterRepository,
    UserSubjectRepository,
)


# -----------------------------------------------------------------------------
# Profile Dependencies
# -----------------------------------------------------------------------------

async def get_user_profile(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Optional[StudyProfileModel]:
    """
    Get current user's study profile.
    
    Returns None if no profile exists (doesn't raise error).
    Use require_profile_exists for routes that need a profile.
    """
    repo = StudyProfileRepository(db)
    return await repo.find_by_user_id(str(current_user.id))


async def require_profile_exists(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> StudyProfileModel:
    """
    Require that user has a study profile.
    
    Raises 404 if no profile exists.
    """
    repo = StudyProfileRepository(db)
    profile = await repo.find_by_user_id(str(current_user.id))
    
    if not profile:
        raise NotFoundException(
            message="Study profile not found. Please create a profile first."
        )
    
    return profile


# -----------------------------------------------------------------------------
# Subject Dependencies
# -----------------------------------------------------------------------------

async def get_user_subject(
    subject_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> UserSubjectModel:
    """
    Get a user subject and verify ownership.
    
    Raises 404 if not found, 403 if not owned by user.
    """
    # Validate ObjectId format
    try:
        ObjectId(subject_id)
    except Exception:
        raise NotFoundException(message="Invalid subject ID format")
    
    repo = UserSubjectRepository(db)
    subject = await repo.find_by_id(subject_id)
    
    if not subject:
        raise NotFoundException(message="Subject not found")
    
    # Verify ownership
    if str(subject.user_id) != str(current_user.id):
        raise ForbiddenException(message="Not authorized to access this subject")
    
    return subject


# -----------------------------------------------------------------------------
# Chapter Dependencies
# -----------------------------------------------------------------------------

async def get_user_chapter(
    chapter_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> UserChapterModel:
    """
    Get a user chapter and verify ownership.
    
    Raises 404 if not found, 403 if not owned by user.
    """
    # Validate ObjectId format
    try:
        ObjectId(chapter_id)
    except Exception:
        raise NotFoundException(message="Invalid chapter ID format")
    
    repo = UserChapterRepository(db)
    chapter = await repo.find_by_id(chapter_id)
    
    if not chapter:
        raise NotFoundException(message="Chapter not found")
    
    # Verify ownership
    if str(chapter.user_id) != str(current_user.id):
        raise ForbiddenException(message="Not authorized to access this chapter")
    
    return chapter


# -----------------------------------------------------------------------------
# Utility Dependencies
# -----------------------------------------------------------------------------

def validate_object_id(id_value: str, field_name: str = "ID") -> ObjectId:
    """
    Validate and convert string to ObjectId.
    
    Raises BadRequestException if invalid format.
    """
    try:
        return ObjectId(id_value)
    except Exception:
        raise NotFoundException(message=f"Invalid {field_name} format")
