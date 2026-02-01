"""
Study Profile Router

API endpoints for:
- Profile management (CRUD)
- Subject management
- Chapter management

All endpoints require authentication.
"""

from typing import List

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_profile import StudyProfileModel
from app.core.database.models.user import UserModel
from app.core.database.mongo import get_database
from app.core.responses.base import SuccessResponse
from app.modules.auth.dependencies import get_current_active_user
from app.modules.study_profile.dependencies import (
    get_user_chapter,
    get_user_subject,
    require_profile_exists,
)
from app.modules.study_profile.models import UserChapterModel, UserSubjectModel
from app.modules.study_profile.schemas import (
    ChapterAddRequest,
    ChapterListResponse,
    ChapterResponse,
    ChapterUpdateRequest,
    StudyProfileCreateRequest,
    StudyProfileResponse,
    StudyProfileUpdateRequest,
    SubjectAddRequest,
    SubjectListResponse,
    SubjectResponse,
    SubjectUpdateRequest,
)
from app.modules.study_profile.service import (
    ChapterService,
    StudyProfileService,
    SubjectService,
)


# -----------------------------------------------------------------------------
# Router Setup
# -----------------------------------------------------------------------------

router = APIRouter(tags=["Study Profile"])


# -----------------------------------------------------------------------------
# Profile Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "",
    response_model=SuccessResponse[StudyProfileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Study Profile",
    description="Create a new study profile for the authenticated user. Only one profile per user is allowed."
)
async def create_profile(
    request: StudyProfileCreateRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a new study profile.
    
    - **exam_type**: Target exam name (e.g., "NEET", "JEE Main")
    - **exam_date**: Target exam date (must be in the future)
    - **daily_study_hours**: Average daily study hours (0.5 - 16)
    """
    service = StudyProfileService(db)
    profile = await service.create_profile(str(current_user.id), request)
    
    return SuccessResponse(
        success=True,
        message="Study profile created successfully",
        status_code=status.HTTP_201_CREATED,
        data=profile
    )


@router.get(
    "",
    response_model=SuccessResponse[StudyProfileResponse],
    summary="Get Study Profile",
    description="Get the authenticated user's study profile."
)
async def get_profile(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get current user's study profile."""
    service = StudyProfileService(db)
    profile = await service.get_profile(str(current_user.id))
    
    return SuccessResponse(
        success=True,
        message="Profile retrieved successfully",
        status_code=status.HTTP_200_OK,
        data=profile
    )


@router.put(
    "",
    response_model=SuccessResponse[StudyProfileResponse],
    summary="Update Study Profile",
    description="Update the authenticated user's study profile."
)
async def update_profile(
    request: StudyProfileUpdateRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update current user's study profile."""
    service = StudyProfileService(db)
    profile = await service.update_profile(str(current_user.id), request)
    
    return SuccessResponse(
        success=True,
        message="Profile updated successfully",
        status_code=status.HTTP_200_OK,
        data=profile
    )


@router.delete(
    "",
    response_model=SuccessResponse[dict],
    summary="Delete Study Profile",
    description="Delete the authenticated user's study profile and all associated data."
)
async def delete_profile(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete current user's study profile.
    
    WARNING: This also deletes all associated subjects and chapters.
    """
    service = StudyProfileService(db)
    await service.delete_profile(str(current_user.id))
    
    return SuccessResponse(
        success=True,
        message="Profile deleted successfully",
        status_code=status.HTTP_200_OK,
        data={"deleted": True}
    )


# -----------------------------------------------------------------------------
# Subject Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/subjects",
    response_model=SuccessResponse[List[SubjectResponse]],
    status_code=status.HTTP_201_CREATED,
    summary="Add Subjects",
    description="Add subjects to the user's study profile."
)
async def add_subjects(
    request: SubjectAddRequest,
    profile: StudyProfileModel = Depends(require_profile_exists),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Add subjects to profile.
    
    - **subject_ids**: List of master subject IDs to add
    - Maximum 15 subjects per profile
    - Duplicates are silently skipped
    """
    service = SubjectService(db)
    subjects = await service.add_subjects(
        str(profile.id),
        str(current_user.id),
        request.subject_ids
    )
    
    return SuccessResponse(
        success=True,
        message=f"Added {len(subjects)} subject(s)",
        status_code=status.HTTP_201_CREATED,
        data=subjects
    )


@router.get(
    "/subjects",
    response_model=SuccessResponse[SubjectListResponse],
    summary="Get Subjects",
    description="Get all subjects in the user's study profile."
)
async def get_subjects(
    enabled_only: bool = False,
    profile: StudyProfileModel = Depends(require_profile_exists),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all subjects for current profile."""
    service = SubjectService(db)
    subjects = await service.get_subjects(str(profile.id), enabled_only)
    
    enabled_count = sum(1 for s in subjects if s.is_enabled)
    
    return SuccessResponse(
        success=True,
        message="Subjects retrieved successfully",
        status_code=status.HTTP_200_OK,
        data=SubjectListResponse(
            subjects=subjects,
            total=len(subjects),
            enabled_count=enabled_count
        )
    )


@router.put(
    "/subjects/{subject_id}",
    response_model=SuccessResponse[SubjectResponse],
    summary="Update Subject",
    description="Update a subject's settings (enabled, priority, strength)."
)
async def update_subject(
    request: SubjectUpdateRequest,
    subject: UserSubjectModel = Depends(get_user_subject),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a subject's configuration."""
    service = SubjectService(db)
    updated = await service.update_subject(
        str(subject.id),
        str(current_user.id),
        request
    )
    
    return SuccessResponse(
        success=True,
        message="Subject updated successfully",
        status_code=status.HTTP_200_OK,
        data=updated
    )


# -----------------------------------------------------------------------------
# Chapter Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/subjects/{subject_id}/chapters",
    response_model=SuccessResponse[List[ChapterResponse]],
    status_code=status.HTTP_201_CREATED,
    summary="Add Chapters",
    description="Add chapters to a subject."
)
async def add_chapters(
    request: ChapterAddRequest,
    subject: UserSubjectModel = Depends(get_user_subject),
    profile: StudyProfileModel = Depends(require_profile_exists),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Add chapters to a subject.
    
    - **chapter_ids**: List of master chapter IDs to add
    - Chapters must belong to the specified subject
    """
    service = ChapterService(db)
    chapters = await service.add_chapters(
        str(subject.id),
        str(profile.id),
        str(current_user.id),
        request.chapter_ids
    )
    
    return SuccessResponse(
        success=True,
        message=f"Added {len(chapters)} chapter(s)",
        status_code=status.HTTP_201_CREATED,
        data=chapters
    )


@router.get(
    "/subjects/{subject_id}/chapters",
    response_model=SuccessResponse[ChapterListResponse],
    summary="Get Chapters",
    description="Get all chapters for a subject."
)
async def get_chapters(
    subject: UserSubjectModel = Depends(get_user_subject),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all chapters for a subject."""
    service = ChapterService(db)
    chapters = await service.get_chapters(str(subject.id), str(current_user.id))
    
    completed_count = sum(1 for c in chapters if c.is_completed)
    weak_count = sum(1 for c in chapters if c.strength == "weak")
    
    return SuccessResponse(
        success=True,
        message="Chapters retrieved successfully",
        status_code=status.HTTP_200_OK,
        data=ChapterListResponse(
            chapters=chapters,
            total=len(chapters),
            completed_count=completed_count,
            weak_count=weak_count
        )
    )


@router.put(
    "/chapters/{chapter_id}",
    response_model=SuccessResponse[ChapterResponse],
    summary="Update Chapter",
    description="Update a chapter's settings (strength, estimated hours, completion)."
)
async def update_chapter(
    request: ChapterUpdateRequest,
    chapter: UserChapterModel = Depends(get_user_chapter),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a chapter's configuration."""
    service = ChapterService(db)
    updated = await service.update_chapter(
        str(chapter.id),
        str(current_user.id),
        request
    )
    
    return SuccessResponse(
        success=True,
        message="Chapter updated successfully",
        status_code=status.HTTP_200_OK,
        data=updated
    )


@router.delete(
    "/chapters/{chapter_id}",
    response_model=SuccessResponse[dict],
    summary="Delete Chapter",
    description="Remove a chapter from the study profile."
)
async def delete_chapter(
    chapter: UserChapterModel = Depends(get_user_chapter),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a chapter from the profile."""
    service = ChapterService(db)
    await service.delete_chapter(str(chapter.id), str(current_user.id))
    
    return SuccessResponse(
        success=True,
        message="Chapter deleted successfully",
        status_code=status.HTTP_200_OK,
        data={"deleted": True}
    )
