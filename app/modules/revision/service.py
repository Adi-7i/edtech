"""
Revision Service

Core business logic for spaced repetition revision scheduling.
"""

from datetime import date, timedelta
from typing import List

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.revision import RevisionQuality, RevisionStatus
from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.revision.repository import RevisionRepository
from app.modules.revision.schemas import (
    ChapterInfo,
    DailyRevisionsResponse,
    RevisionResponse,
    RevisionScheduleResponse,
)
from app.modules.revision.utils import (
    calculate_adjusted_next_cycle,
    calculate_next_revision_date,
    calculate_priority_score,
    get_cycle_index_from_day,
    is_eligible_for_revision,
)
from app.modules.study_profile.repository import (
    StudyProfileRepository,
    UserChapterRepository,
)


class RevisionService:
    """Service for managing revision scheduling and tracking."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.revision_repo = RevisionRepository(db)
        self.chapter_repo = UserChapterRepository(db)
        self.profile_repo = StudyProfileRepository(db)
    
    async def schedule_revisions_for_chapter(
        self,
        user_id: str,
        chapter_id: str,
        force_reschedule: bool = False
    ) -> RevisionScheduleResponse:
        """
        Schedule spaced repetition revisions for a completed chapter.
        
        Logic:
        1. Verify chapter belongs to user and is completed
        2. Check no active revision schedule exists (unless force)
        3. Verify eligible (exam date not passed)
        4. Calculate first revision date (learning_date + 1 day)
        5. Create revision schedule
        
        Args:
            user_id: User ID
            chapter_id: User chapter ID
            force_reschedule: Delete existing and create new
        
        Returns:
            RevisionScheduleResponse
        
        Raises:
            NotFoundException: Chapter not found or not owned
            BadRequestException: Chapter not completed or ineligible
        """
        # Step 1: Get chapter
        chapter = await self.chapter_repo.find_by_id(chapter_id)
        if not chapter or str(chapter.user_id) != user_id:
            raise NotFoundException(message="Chapter not found")
        
        # Step 2: Verify chapter is completed
        if not chapter.is_completed:
            raise BadRequestException(
                message="Chapter must be completed before scheduling revisions"
            )
        
        # Step 3: Get user's exam date
        profile = await self.profile_repo.find_by_user_id(user_id)
        if not profile:
            raise BadRequestException(message="Study profile not found")
        
        exam_date = profile.exam_date
        
        # Step 4: Check eligibility
        completion_date = chapter.last_studied_at.date() if chapter.last_studied_at else date.today()
        eligible, reason = is_eligible_for_revision(completion_date, exam_date)
        
        if not eligible:
            raise BadRequestException(message=f"Chapter not eligible for revision: {reason}")
        
        # Step 5: Check existing revision schedule
        existing = await self.revision_repo.find_by_user_and_chapter(user_id, chapter_id)
        
        if existing and not force_reschedule:
            raise BadRequestException(
                message="Revision schedule already exists for this chapter. Use force_reschedule=true to recreate."
            )
        
        if existing and force_reschedule:
            # Delete existing
            await self.revision_repo.delete(str(existing.id))
        
        # Step 6: Calculate first revision date (Day 1 = tomorrow)
        first_revision_date = completion_date + timedelta(days=1)
        
        # Step 7: Create revision schedule
        revision = await self.revision_repo.create(
            user_id=user_id,
            chapter_id=chapter_id,
            subject_id=str(chapter.subject_id),
            chapter_name=chapter.chapter_name,
            subject_name=chapter.subject_name,  # Assuming this exists
            original_learning_date=completion_date,
            first_revision_date=first_revision_date,
            learning_task_id=None  # Could be enhanced to track original task
        )
        
        return RevisionScheduleResponse(
            revision_id=str(revision.id),
            chapter_id=chapter_id,
            chapter_name=chapter.chapter_name,
            original_learning_date=completion_date.isoformat(),
            next_revision_date=first_revision_date.isoformat(),
            current_cycle_day=1,
            message=f"Revision schedule created. First revision on {first_revision_date.isoformat()}"
        )
    
    async def get_todays_revisions(
        self,
        user_id: str
    ) -> DailyRevisionsResponse:
        """
        Fetch all revisions due today with priority ordering.
        
        Priority ordering:
        1. Overdue revisions first
        2. Weak chapters before strong
        3. Closer to exam date
        4. Lower interval level (newer revisions)
        
        Also auto-reschedules any missed revisions from past.
        
        Args:
            user_id: User ID
        
        Returns:
            DailyRevisionsResponse with ordered revisions
        """
        today = date.today()
        
        # Step 1: Auto-reschedule missed revisions
        auto_rescheduled = await self._auto_reschedule_missed(user_id, today)
        
        # Step 2: Get profile for exam date
        profile = await self.profile_repo.find_by_user_id(user_id)
        exam_date = profile.exam_date if profile else today + timedelta(days=365)
        
        # Step 3: Fetch revisions due today and overdue
        revisions = await self.revision_repo.find_due_revisions(user_id, today)
        
        # Step 4: Get chapter details for priority calculation
        revision_responses = []
        
        for rev in revisions:
            # Get chapter for strength info
            chapter = await self.chapter_repo.find_by_id(str(rev.chapter_id))
            chapter_strength = chapter.strength if chapter else "medium"
            
            # Calculate priority
            priority = calculate_priority_score(
                next_revision_date=rev.next_revision_date,
                exam_date=exam_date,
                missed_count=rev.missed_count,
                chapter_strength=chapter_strength,
                today=today
            )
            
            # Calculate days until due
            days_until = (rev.next_revision_date - today).days
            
            revision_responses.append(
                RevisionResponse(
                    id=str(rev.id),
                    chapter=ChapterInfo(
                        id=str(rev.chapter_id),
                        name=rev.chapter_name,
                        subject_id=str(rev.subject_id),
                        subject_name=rev.subject_name,
                        strength=chapter_strength
                    ),
                    current_cycle_day=rev.current_cycle_day,
                    next_revision_date=rev.next_revision_date.isoformat(),
                    status=rev.status.value,
                    cycles_completed=rev.cycles_completed,
                    is_mastered=rev.is_mastered,
                    missed_count=rev.missed_count,
                    consecutive_misses=rev.consecutive_misses,
                    average_recall_quality=rev.average_recall_quality,
                    priority_score=priority,
                    is_high_priority=priority <= 3,
                    is_overdue=rev.next_revision_date < today,
                    days_until_due=days_until
                )
            )
        
        # Step 5: Sort by priority (lower score = higher priority)
        revision_responses.sort(key=lambda x: (x.priority_score, x.days_until_due))
        
        # Step 6: Calculate counts
        due_today_count = len([r for r in revision_responses if r.days_until_due == 0])
        overdue_count = len([r for r in revision_responses if r.is_overdue])
        completed_count = len([r for r in revision_responses if r.status == RevisionStatus.COMPLETED.value])
        
        return DailyRevisionsResponse(
            date=today.isoformat(),
            revisions=revision_responses,
            total_revisions=len(revision_responses),
            due_today=due_today_count,
            overdue=overdue_count,
            completed_today=completed_count,
            priority_order="weak_chapters_first",
            auto_rescheduled_count=auto_rescheduled
        )
    
    async def update_revision_status(
        self,
        revision_id: str,
        user_id: str,
        status: RevisionStatus,
        quality: RevisionQuality = None,
        duration_minutes: int = 0,
        notes: str = None
    ) -> RevisionResponse:
        """
        Update revision status after completion or mark as missed.
        
        Logic for COMPLETED:
        1. Verify ownership
        2. Require quality rating
        3. Calculate next interval based on quality
        4. Schedule next revision
        5. Mark as mastered if all cycles complete
        
        Logic for MISSED/SKIPPED:
        1. Mark appropriately
        2. Reschedule to next valid date
        
        Args:
            revision_id: Revision ID
            user_id: User ID
            status: New status
            quality: Recall quality (required for completed)
            duration_minutes: Time spent
            notes: Optional notes
        
        Returns:
            RevisionResponse
        
        Raises:
            NotFoundException: Revision not found
            BadRequestException: Validation errors
        """
        # Step 1: Get revision
        revision = await self.revision_repo.find_by_id(revision_id)
        if not revision:
            raise NotFoundException(message="Revision not found")
        
        # Step 2: Verify ownership
        if str(revision.user_id) != user_id:
            raise NotFoundException(message="Revision not found")
        
        # Step 3: Handle based on status
        if status == RevisionStatus.COMPLETED:
            # Require quality rating
            if quality is None:
                raise BadRequestException(
                    message="Quality rating required when marking revision as completed"
                )
            
            # Calculate next cycle
            current_index = get_cycle_index_from_day(revision.current_cycle_day)
            next_index = calculate_adjusted_next_cycle(current_index, quality)
            
            # Calculate next revision date
            completed_date = date.today()
            next_date, next_cycle_day = calculate_next_revision_date(
                last_completion_date=completed_date,
                current_cycle_index=next_index
            )
            
            # Update revision
            updated_revision = await self.revision_repo.update_after_completion(
                revision_id=revision_id,
                completed_date=completed_date,
                quality=quality,
                duration_minutes=duration_minutes,
                notes=notes,
                next_cycle_day=next_cycle_day,
                next_revision_date=next_date
            )
            
            # Check if mastered (all 4 cycles complete)
            if updated_revision.cycles_completed >= 4:
                updated_revision = await self.revision_repo.mark_as_mastered(revision_id)
        
        else:
            # For MISSED or SKIPPED, reschedule
            next_date = date.today() + timedelta(days=1)
            updated_revision = await self.revision_repo.mark_as_missed(
                revision_id=revision_id,
                missed_date=date.today(),
                next_revision_date=next_date
            )
        
        # Step 4: Get chapter details for response
        chapter = await self.chapter_repo.find_by_id(str(updated_revision.chapter_id))
        chapter_strength = chapter.strength if chapter else "medium"
        
        # Step 5: Build response
        profile = await self.profile_repo.find_by_user_id(user_id)
        exam_date = profile.exam_date if profile else date.today() + timedelta(days=365)
        
        priority = calculate_priority_score(
            next_revision_date=updated_revision.next_revision_date,
            exam_date=exam_date,
            missed_count=updated_revision.missed_count,
            chapter_strength=chapter_strength,
            today=date.today()
        )
        
        days_until = (updated_revision.next_revision_date - date.today()).days
        
        return RevisionResponse(
            id=str(updated_revision.id),
            chapter=ChapterInfo(
                id=str(updated_revision.chapter_id),
                name=updated_revision.chapter_name,
                subject_id=str(updated_revision.subject_id),
                subject_name=updated_revision.subject_name,
                strength=chapter_strength
            ),
            current_cycle_day=updated_revision.current_cycle_day,
            next_revision_date=updated_revision.next_revision_date.isoformat(),
            status=updated_revision.status.value,
            cycles_completed=updated_revision.cycles_completed,
            is_mastered=updated_revision.is_mastered,
            missed_count=updated_revision.missed_count,
            consecutive_misses=updated_revision.consecutive_misses,
            average_recall_quality=updated_revision.average_recall_quality,
            priority_score=priority,
            is_high_priority=priority <= 3,
            is_overdue=updated_revision.next_revision_date < date.today(),
            days_until_due=days_until
        )
    
    async def _auto_reschedule_missed(
        self,
        user_id: str,
        today: date
    ) -> int:
        """
        Auto-reschedule missed revisions to tomorrow.
        
        Called internally by get_todays_revisions().
        
        Args:
            user_id: User ID
            today: Current date
        
        Returns:
            Number of revisions rescheduled
        """
        # Find overdue revisions
        overdue = await self.revision_repo.find_overdue_revisions(user_id, today)
        
        count = 0
        for revision in overdue:
            # Reschedule to tomorrow
            next_date = today + timedelta(days=1)
            await self.revision_repo.mark_as_missed(
                revision_id=str(revision.id),
                missed_date=revision.next_revision_date,
                next_revision_date=next_date
            )
            count += 1
        
        return count
