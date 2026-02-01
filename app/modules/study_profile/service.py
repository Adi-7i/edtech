"""
Study Profile Service Layer

Business logic for:
- Study profile management
- Subject management
- Chapter management
"""

from datetime import date, datetime, timezone
from typing import List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_profile import (
    DailyAvailability,
    ExamCategory,
    PreferredTimeSlot,
    StudyPreferences,
    StudyProfileModel,
)
from app.core.exceptions.handlers import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.modules.study_profile.models import UserChapterModel, UserSubjectModel
from app.modules.study_profile.repository import (
    StudyProfileRepository,
    UserChapterRepository,
    UserSubjectRepository,
)
from app.modules.study_profile.schemas import (
    ChapterResponse,
    ChapterUpdateRequest,
    StudyProfileCreateRequest,
    StudyProfileResponse,
    StudyProfileUpdateRequest,
    SubjectResponse,
    SubjectUpdateRequest,
)
from app.shared.constants import Collections


# -----------------------------------------------------------------------------
# Study Profile Service
# -----------------------------------------------------------------------------

class StudyProfileService:
    """Service for study profile business logic."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.profile_repo = StudyProfileRepository(db)
        self.subject_repo = UserSubjectRepository(db)
        self.chapter_repo = UserChapterRepository(db)
    
    async def create_profile(
        self,
        user_id: str,
        request: StudyProfileCreateRequest
    ) -> StudyProfileResponse:
        """
        Create a new study profile.
        
        Business Rules:
        - One profile per user (enforced)
        - Exam date must be in future (validated in schema)
        - Daily study hours must be realistic (validated in schema)
        """
        # Check if profile already exists
        if await self.profile_repo.exists_for_user(user_id):
            raise ConflictException(
                message="Study profile already exists. Use UPDATE to modify."
            )
        
        # Build daily availability if not provided
        daily_availability = request.daily_availability
        if daily_availability is None:
            # Create uniform availability from daily_study_hours
            daily_availability = DailyAvailability(
                monday=request.daily_study_hours,
                tuesday=request.daily_study_hours,
                wednesday=request.daily_study_hours,
                thursday=request.daily_study_hours,
                friday=request.daily_study_hours,
                saturday=request.daily_study_hours + 2,  # More time on weekends
                sunday=request.daily_study_hours + 2,
            )
        
        # Create profile model
        profile = StudyProfileModel(
            user_id=ObjectId(user_id),
            exam_type=request.exam_type,
            exam_category=request.exam_category,
            exam_date=request.exam_date,
            preparation_start_date=date.today(),
            daily_availability=daily_availability,
            preferred_time_slot=request.preferred_time_slot or PreferredTimeSlot(),
            preferences=request.preferences or StudyPreferences(),
            is_complete=False,
            onboarding_step=1,
        )
        
        # Save to database
        created_profile = await self.profile_repo.create(profile)
        
        return self._profile_to_response(created_profile)
    
    async def get_profile(self, user_id: str) -> StudyProfileResponse:
        """Get user's study profile."""
        profile = await self.profile_repo.find_by_user_id(user_id)
        if not profile:
            raise NotFoundException(message="Study profile not found")
        
        return self._profile_to_response(profile)
    
    async def get_profile_model(self, user_id: str) -> Optional[StudyProfileModel]:
        """Get profile model (internal use)."""
        return await self.profile_repo.find_by_user_id(user_id)
    
    async def update_profile(
        self,
        user_id: str,
        request: StudyProfileUpdateRequest
    ) -> StudyProfileResponse:
        """
        Update study profile.
        
        Business Rules:
        - Only owner can update
        - Exam date must remain in future
        """
        # Find existing profile
        profile = await self.profile_repo.find_by_user_id(user_id)
        if not profile:
            raise NotFoundException(message="Study profile not found")
        
        # Build update data (only non-None fields)
        update_data = {}
        
        if request.exam_type is not None:
            update_data["exam_type"] = request.exam_type
        
        if request.exam_category is not None:
            update_data["exam_category"] = request.exam_category
        
        if request.exam_date is not None:
            update_data["exam_date"] = request.exam_date
        
        if request.daily_study_hours is not None:
            # Update all days uniformly
            update_data["daily_availability"] = DailyAvailability(
                monday=request.daily_study_hours,
                tuesday=request.daily_study_hours,
                wednesday=request.daily_study_hours,
                thursday=request.daily_study_hours,
                friday=request.daily_study_hours,
                saturday=request.daily_study_hours + 2,
                sunday=request.daily_study_hours + 2,
            ).model_dump()
        
        if request.daily_availability is not None:
            update_data["daily_availability"] = request.daily_availability.model_dump()
        
        if request.preferred_time_slot is not None:
            update_data["preferred_time_slot"] = request.preferred_time_slot.model_dump()
        
        if request.preferences is not None:
            update_data["preferences"] = request.preferences.model_dump()
        
        if not update_data:
            return self._profile_to_response(profile)
        
        # Update profile
        updated_profile = await self.profile_repo.update(str(profile.id), update_data)
        if not updated_profile:
            raise BadRequestException(message="Failed to update profile")
        
        return self._profile_to_response(updated_profile)
    
    async def delete_profile(self, user_id: str) -> bool:
        """
        Delete study profile and all associated data.
        
        This is a cascading delete that removes:
        - Study profile
        - User subjects
        - User chapters
        """
        profile = await self.profile_repo.find_by_user_id(user_id)
        if not profile:
            raise NotFoundException(message="Study profile not found")
        
        profile_id = str(profile.id)
        
        # Delete associated chapters first
        await self.chapter_repo.delete_by_profile(profile_id)
        
        # Delete associated subjects
        await self.subject_repo.delete_by_profile(profile_id)
        
        # Delete profile
        return await self.profile_repo.delete(profile_id)
    
    def _profile_to_response(self, profile: StudyProfileModel) -> StudyProfileResponse:
        """Convert profile model to response."""
        weekly_hours = profile.daily_availability.weekly_total if profile.daily_availability else 0
        
        return StudyProfileResponse(
            id=str(profile.id),
            user_id=str(profile.user_id),
            exam_type=profile.exam_type,
            exam_category=profile.exam_category.value if isinstance(profile.exam_category, ExamCategory) else profile.exam_category,
            exam_date=profile.exam_date.isoformat() if profile.exam_date else "",
            days_until_exam=profile.days_until_exam,
            daily_study_hours=weekly_hours / 7 if weekly_hours else 0,
            weekly_study_hours=weekly_hours,
            daily_availability=profile.daily_availability,
            preferred_time_slot=profile.preferred_time_slot,
            preferences=profile.preferences,
            is_complete=profile.is_complete,
            current_phase=profile.current_phase,
            created_at=profile.created_at.isoformat() if profile.created_at else "",
            updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
        )


# -----------------------------------------------------------------------------
# Subject Service
# -----------------------------------------------------------------------------

class SubjectService:
    """Service for user subject management."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.subject_repo = UserSubjectRepository(db)
        self.chapter_repo = UserChapterRepository(db)
        self.master_subjects = db[Collections.SUBJECTS]
    
    async def add_subjects(
        self,
        profile_id: str,
        user_id: str,
        subject_ids: List[str]
    ) -> List[SubjectResponse]:
        """
        Add subjects to user's profile.
        
        Business Rules:
        - Max 15 subjects per profile
        - Cannot add duplicate subjects
        - Must be valid master subject IDs
        """
        # Get existing subjects count
        existing = await self.subject_repo.find_by_profile(profile_id)
        if len(existing) + len(subject_ids) > 15:
            raise BadRequestException(
                message=f"Cannot exceed 15 subjects. Currently have {len(existing)}"
            )
        
        # Check for duplicates
        existing_subject_ids = {str(s.subject_id) for s in existing}
        new_subjects = []
        
        for subject_id in subject_ids:
            if subject_id in existing_subject_ids:
                continue  # Skip duplicates silently
            
            # Validate master subject exists
            try:
                oid = ObjectId(subject_id)
            except Exception:
                raise BadRequestException(message=f"Invalid subject ID format: {subject_id}")

            master = await self.master_subjects.find_one({"_id": oid})
            if not master:
                raise NotFoundException(message=f"Subject {subject_id} not found")
            
            # Create user subject
            user_subject = UserSubjectModel(
                profile_id=ObjectId(profile_id),
                user_id=ObjectId(user_id),
                subject_id=ObjectId(subject_id),
                subject_name=master["name"],
                subject_code=master.get("code"),
                exam_id=master["exam_id"],
                is_enabled=True,
                priority=len(existing) + len(new_subjects) + 1,
                chapters_total=master.get("total_chapters", 0),
            )
            new_subjects.append(user_subject)
        
        if new_subjects:
            created = await self.subject_repo.create_many(new_subjects)
            return [self._subject_to_response(s) for s in created]
        
        return []
    
    async def get_subjects(
        self,
        profile_id: str,
        enabled_only: bool = False
    ) -> List[SubjectResponse]:
        """Get all subjects for a profile."""
        subjects = await self.subject_repo.find_by_profile(profile_id, enabled_only)
        return [self._subject_to_response(s) for s in subjects]
    
    async def update_subject(
        self,
        subject_id: str,
        user_id: str,
        request: SubjectUpdateRequest
    ) -> SubjectResponse:
        """
        Update a user subject.
        
        Business Rules:
        - Only owner can update
        """
        subject = await self.subject_repo.find_by_id(subject_id)
        if not subject:
            raise NotFoundException(message="Subject not found")
        
        # Verify ownership
        if str(subject.user_id) != user_id:
            raise ForbiddenException(message="Not authorized to modify this subject")
        
        # Build update data
        update_data = {}
        
        if request.is_enabled is not None:
            update_data["is_enabled"] = request.is_enabled
        
        if request.priority is not None:
            update_data["priority"] = request.priority
        
        if request.strength is not None:
            update_data["strength"] = request.strength
        
        if request.target_completion_percentage is not None:
            update_data["target_completion_percentage"] = request.target_completion_percentage
        
        if not update_data:
            return self._subject_to_response(subject)
        
        updated = await self.subject_repo.update(subject_id, update_data)
        if not updated:
            raise BadRequestException(message="Failed to update subject")
        
        return self._subject_to_response(updated)
    
    def _subject_to_response(self, subject: UserSubjectModel) -> SubjectResponse:
        """Convert subject model to response."""
        return SubjectResponse(
            id=str(subject.id),
            subject_id=str(subject.subject_id),
            subject_name=subject.subject_name,
            subject_code=subject.subject_code,
            is_enabled=subject.is_enabled,
            priority=subject.priority,
            strength=subject.strength.value if hasattr(subject.strength, 'value') else subject.strength,
            chapters_total=subject.chapters_total,
            chapters_completed=subject.chapters_completed,
            completion_percentage=subject.completion_percentage,
            created_at=subject.created_at.isoformat() if subject.created_at else "",
        )


# -----------------------------------------------------------------------------
# Chapter Service
# -----------------------------------------------------------------------------

class ChapterService:
    """Service for user chapter management."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.chapter_repo = UserChapterRepository(db)
        self.subject_repo = UserSubjectRepository(db)
        self.master_chapters = db[Collections.CHAPTERS]
    
    async def add_chapters(
        self,
        user_subject_id: str,
        profile_id: str,
        user_id: str,
        chapter_ids: List[str]
    ) -> List[ChapterResponse]:
        """
        Add chapters to a user subject.
        
        Business Rules:
        - Must own the subject
        - Cannot add duplicate chapters
        - Must be valid master chapter IDs
        """
        # Verify subject ownership
        subject = await self.subject_repo.find_by_id(user_subject_id)
        if not subject:
            raise NotFoundException(message="Subject not found")
        
        if str(subject.user_id) != user_id:
            raise ForbiddenException(message="Not authorized to modify this subject")
        
        # Get existing chapters
        existing = await self.chapter_repo.find_by_user_subject(user_subject_id)
        existing_chapter_ids = {str(c.chapter_id) for c in existing}
        
        new_chapters = []
        
        for chapter_id in chapter_ids:
            if chapter_id in existing_chapter_ids:
                continue  # Skip duplicates
            
            # Validate master chapter exists
            master = await self.master_chapters.find_one({"_id": ObjectId(chapter_id)})
            if not master:
                raise NotFoundException(message=f"Chapter {chapter_id} not found")
            
            # Verify chapter belongs to same subject
            if str(master["subject_id"]) != str(subject.subject_id):
                raise BadRequestException(
                    message=f"Chapter {chapter_id} does not belong to this subject"
                )
            
            # Create user chapter
            user_chapter = UserChapterModel(
                profile_id=ObjectId(profile_id),
                user_id=ObjectId(user_id),
                user_subject_id=ObjectId(user_subject_id),
                chapter_id=ObjectId(chapter_id),
                subject_id=subject.subject_id,
                chapter_name=master["name"],
                chapter_code=master.get("code"),
                difficulty=master.get("difficulty", "medium"),
                importance_score=master.get("importance_score", 5),
                estimated_hours=master.get("estimated_hours", 2.0),
            )
            new_chapters.append(user_chapter)
        
        if new_chapters:
            created = await self.chapter_repo.create_many(new_chapters)
            
            # Update subject's chapter count
            await self.subject_repo.update(
                user_subject_id,
                {"chapters_total": len(existing) + len(created)}
            )
            
            return [self._chapter_to_response(c) for c in created]
        
        return []
    
    async def get_chapters(
        self,
        user_subject_id: str,
        user_id: str
    ) -> List[ChapterResponse]:
        """Get all chapters for a user subject."""
        subject = await self.subject_repo.find_by_id(user_subject_id)
        if not subject:
            raise NotFoundException(message="Subject not found")
        
        if str(subject.user_id) != user_id:
            raise ForbiddenException(message="Not authorized to view this subject")
        
        chapters = await self.chapter_repo.find_by_user_subject(user_subject_id)
        return [self._chapter_to_response(c) for c in chapters]
    
    async def update_chapter(
        self,
        chapter_id: str,
        user_id: str,
        request: ChapterUpdateRequest
    ) -> ChapterResponse:
        """
        Update a user chapter.
        
        Business Rules:
        - Only owner can update
        - Marking complete updates subject progress
        """
        chapter = await self.chapter_repo.find_by_id(chapter_id)
        if not chapter:
            raise NotFoundException(message="Chapter not found")
        
        # Verify ownership
        if str(chapter.user_id) != user_id:
            raise ForbiddenException(message="Not authorized to modify this chapter")
        
        # Build update data
        update_data = {}
        
        if request.strength is not None:
            update_data["strength"] = request.strength
        
        if request.estimated_hours is not None:
            update_data["estimated_hours"] = request.estimated_hours
        
        if request.notes is not None:
            update_data["notes"] = request.notes
        
        # Handle completion status
        if request.is_completed is not None:
            was_completed = chapter.is_completed
            update_data["is_completed"] = request.is_completed
            
            if request.is_completed:
                update_data["completion_percentage"] = 100.0
            
            # Update subject progress if completion changed
            if request.is_completed and not was_completed:
                await self.subject_repo.increment_chapters_completed(
                    str(chapter.user_subject_id), 1
                )
            elif not request.is_completed and was_completed:
                await self.subject_repo.increment_chapters_completed(
                    str(chapter.user_subject_id), -1
                )
        
        if not update_data:
            return self._chapter_to_response(chapter)
        
        updated = await self.chapter_repo.update(chapter_id, update_data)
        if not updated:
            raise BadRequestException(message="Failed to update chapter")
        
        return self._chapter_to_response(updated)
    
    async def delete_chapter(self, chapter_id: str, user_id: str) -> bool:
        """
        Delete a user chapter.
        
        Business Rules:
        - Only owner can delete
        - Updates subject chapter count
        """
        chapter = await self.chapter_repo.find_by_id(chapter_id)
        if not chapter:
            raise NotFoundException(message="Chapter not found")
        
        # Verify ownership
        if str(chapter.user_id) != user_id:
            raise ForbiddenException(message="Not authorized to delete this chapter")
        
        # Delete chapter
        result = await self.chapter_repo.delete(chapter_id)
        
        if result:
            # Update subject chapter count
            subject = await self.subject_repo.find_by_id(str(chapter.user_subject_id))
            if subject:
                new_total = max(0, subject.chapters_total - 1)
                new_completed = subject.chapters_completed
                if chapter.is_completed:
                    new_completed = max(0, new_completed - 1)
                
                await self.subject_repo.update(
                    str(chapter.user_subject_id),
                    {
                        "chapters_total": new_total,
                        "chapters_completed": new_completed
                    }
                )
        
        return result
    
    def _chapter_to_response(self, chapter: UserChapterModel) -> ChapterResponse:
        """Convert chapter model to response."""
        return ChapterResponse(
            id=str(chapter.id),
            chapter_id=str(chapter.chapter_id),
            subject_id=str(chapter.subject_id),
            chapter_name=chapter.chapter_name,
            chapter_code=chapter.chapter_code,
            strength=chapter.strength.value if hasattr(chapter.strength, 'value') else chapter.strength,
            estimated_hours=chapter.estimated_hours,
            is_completed=chapter.is_completed,
            difficulty=chapter.difficulty,
            importance_score=chapter.importance_score,
            notes=chapter.notes,
            created_at=chapter.created_at.isoformat() if chapter.created_at else "",
            last_studied_at=chapter.last_studied_at.isoformat() if chapter.last_studied_at else None,
        )
