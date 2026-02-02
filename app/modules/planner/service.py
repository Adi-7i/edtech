"""
Planner Service

Core business logic for study plan generation and management.

This is the HEART of the application - generates deterministic study plans
based on exam date, chapters, and student availability.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database.models.study_plan import (
    DailyPlanModel,
    PlanStatus,
    StudyPlanModel,
    StudyTaskModel,
    TaskStatus,
)
from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.planner.repository import (
    DailyPlanRepository,
    StudyPlanRepository,
    StudyTaskRepository,
)
from app.modules.planner.schemas import (
    DailyPlanResponse,
    PlanPreviewResponse,
    PlanResponse,
    PlanSummaryResponse,
    StudyTaskResponse,
)
from app.modules.planner.utils import (
    analyze_plan_feasibility,
    calculate_chapter_priority,
    calculate_days_until_exam,
    distribute_chapters_across_days,
    estimate_chapter_hours,
    generate_date_range,
)
from app.modules.study_profile.repository import (
    StudyProfileRepository,
    UserChapterRepository,
    UserSubjectRepository,
)


class PlannerService:
    """Service for study plan generation and management."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
        # Repositories
        self.plan_repo = StudyPlanRepository(db)
        self.daily_plan_repo = DailyPlanRepository(db)
        self.task_repo = StudyTaskRepository(db)
        
        # Profile-related repositories
        self.profile_repo = StudyProfileRepository(db)
        self.subject_repo = UserSubjectRepository(db)
        self.chapter_repo = UserChapterRepository(db)
    
    # -------------------------------------------------------------------------
    # Plan Generation (Core Algorithm)
    # -------------------------------------------------------------------------
    
    async def generate_plan(
        self,
        user_id: str,
        force_regenerate: bool = False,
        prioritize_weak_only: bool = False,
        buffer_days: int = 0
    ) -> PlanResponse:
        """
        Generate a new study plan for the user.
        
        Algorithm Flow:
        1. Gather input data (profile, subjects, chapters)
        2. Calculate timeline (days until exam)
        3. Prioritize chapters (weak first)
        4. Distribute chapters across days
        5. Generate daily plans and tasks
        6. Save to database
        
        Args:
            user_id: Student user ID
            force_regenerate: Delete existing active plan
            prioritize_weak_only: Only include weak chapters
            buffer_days: Reserve N days before exam
        
        Returns:
            PlanResponse with generated plan
        """
        # Step 1: Check for existing active plan
        existing_plan = await self.plan_repo.find_active_by_user(user_id)
        if existing_plan and not force_regenerate:
            raise BadRequestException(
                message="Active plan already exists. Use force_regenerate=true to create new plan."
            )
        
        # Step 2: Gather planning data
        profile, subjects, all_chapters = await self._gather_planning_data(user_id)
        
        if not subjects:
            raise BadRequestException(
                message="No subjects found. Please add subjects before generating plan."
            )
        
        if not all_chapters:
            raise BadRequestException(
                message="No chapters found. Please add chapters before generating plan."
            )
        
        # Step 3: Filter chapters if needed
        if prioritize_weak_only:
            all_chapters = [c for c in all_chapters if c.strength == "weak"]
            if not all_chapters:
                raise BadRequestException(
                    message="No weak chapters found to prioritize."
                )
        
        # Step 4: Calculate timeline
        exam_date = profile.exam_date  # Already a date object
        days_available = calculate_days_until_exam(exam_date, buffer_days)
        
        if days_available <= 0:
            raise BadRequestException(
                message="Exam date is too soon or has passed. Cannot generate plan."
            )
        
        plan_start_date = date.today()
        plan_end_date = exam_date - timedelta(days=1 + buffer_days)
        
        # Step 5: Prepare chapters with priorities
        chapters_data = await self._prepare_chapters_for_distribution(
            all_chapters,
            subjects
        )
        
        # Calculate daily study hours for use throughout
        daily_study_hours = self._calculate_daily_study_hours(profile)
        
        # Step 6: Distribute chapters across days
        distribution, warnings = distribute_chapters_across_days(
            chapters=chapters_data,
            daily_limit_hours=daily_study_hours,
            total_days=days_available,
            buffer_days=buffer_days
        )
        
        if not distribution:
            raise BadRequestException(
                message="Could not generate valid distribution. " + "; ".join(warnings)
            )
        
        # Step 7: Deactivate old plans if force regenerate
        if force_regenerate and existing_plan:
            await self.plan_repo.deactivate_user_plans(user_id)
            await self.daily_plan_repo.delete_by_plan(str(existing_plan.id))
            await self.task_repo.delete_by_plan(str(existing_plan.id))
        
        # Step 8: Create plan metadata
        total_chapters = len(chapters_data)
        total_tasks = sum(len(day["chapters"]) for day in distribution)
        total_allocated_hours = sum(day["total_hours"] for day in distribution)
        
        study_plan = StudyPlanModel(
            user_id=ObjectId(user_id),
            profile_id=profile.id,
            exam_type=profile.exam_type,
            exam_date=exam_date,
            plan_start_date=plan_start_date,
            plan_end_date=plan_end_date,
            total_days=days_available,
            total_subjects=len(subjects),
            total_chapters=total_chapters,
            daily_study_hours=daily_study_hours,
            total_allocated_hours=total_allocated_hours,
            status=PlanStatus.ACTIVE,
            is_active=True,
            total_tasks=total_tasks,
            generation_algorithm_version="v1.0"
        )
        
        created_plan = await self.plan_repo.create(study_plan)
        
        # Step 9: Create daily plans and tasks
        await self._create_daily_plans_and_tasks(
            created_plan, distribution, daily_study_hours, chapters_data
        )
        
        # Step 10: Get upcoming days and return response
        return await self.get_plan_with_upcoming_days(user_id)
    
    async def _gather_planning_data(
        self,
        user_id: str
    ) -> Tuple:
        """
        Gather all required data for planning.
        
        Returns:
            Tuple of (profile, subjects, chapters)
        """
        # Get profile
        profile = await self.profile_repo.find_by_user_id(user_id)
        if not profile:
            raise NotFoundException(message="Study profile not found")
        
        # Get subjects
        subjects = await self.subject_repo.find_by_profile(str(profile.id))
        
        # Get all chapters across all subjects
        all_chapters = []
        for subject in subjects:
            chapters = await self.chapter_repo.find_by_user_subject(str(subject.id))
            all_chapters.extend(chapters)
        
        return profile, subjects, all_chapters
    
    def _calculate_daily_study_hours(self, profile) -> float:
        """Calculate average daily study hours from profile availability."""
        if hasattr(profile, 'daily_availability') and profile.daily_availability:
            avail = profile.daily_availability
            # Calculate average from weekly schedule
            total =  (avail.monday + avail.tuesday + avail.wednesday + 
                     avail.thursday + avail.friday + avail.saturday + avail.sunday)
            return total / 7.0
        # Fallback
        return 6.0
    
    async def _prepare_chapters_for_distribution(
        self,
        chapters,
        subjects
    ) -> List[Dict]:
        """
        Prepare chapter data with priorities and estimated hours.
        
        Args:
            chapters: List of UserChapterModel instances
            subjects: List of UserSubjectModel instances
        
        Returns:
            List of chapter dicts ready for distribution
        """
        # Create subject lookup map
        subject_map = {str(s.id): s.subject_name for s in subjects}
        
        chapters_data = []
        for chapter in chapters:
            priority = calculate_chapter_priority(chapter.strength)
            estimated_hours = estimate_chapter_hours(chapter.strength)
            
            chapters_data.append({
                "id": str(chapter.id),
                "chapter_id": str(chapter.chapter_id),
                "subject_id": str(chapter.subject_id),
                "name": chapter.chapter_name,
                "subject_name": subject_map.get(str(chapter.subject_id), "Unknown"),
                "strength": chapter.strength,
                "priority": priority,
                "estimated_hours": estimated_hours
            })
        
        return chapters_data
    
    async def _create_daily_plans_and_tasks(
        self,
        plan: StudyPlanModel,
        distribution: List[Dict],
        daily_study_hours: float,
        chapters_data: List[Dict]
    ) -> None:
        """
        Create DailyPlan and StudyTask records from distribution.
        
        Args:
            plan: Created StudyPlanModel
            distribution: List of daily distributions
            daily_study_hours: Average daily  study hours
            chapters_data: Original chapter data for lookup
        """
        # Create chapter lookup map
        chapter_lookup = {c["id"]: c for c in chapters_data}
        for day_data in distribution:
            # Create daily plan
            daily_plan = DailyPlanModel(
                plan_id=plan.id,
                user_id=plan.user_id,
                profile_id=plan.profile_id,
                plan_date=day_data["date"],
                total_allocated_hours=day_data["total_hours"],
                daily_limit_hours=daily_study_hours,
                task_count=len(day_data["chapters"])
            )
            
            created_daily_plan = await self.daily_plan_repo.create(daily_plan)
            
            # Create tasks for this day
            tasks = []
            for idx, chapter_data in enumerate(day_data["chapters"], start=1):
                # Look up original chapter data
                user_chapter_id = chapter_data["chapter_id"]  # This is the user chapter ID
                original_chapter = chapter_lookup.get(user_chapter_id, {})
                
                task = StudyTaskModel(
                    daily_plan_id=created_daily_plan.id,
                    plan_id=plan.id,
                    user_id=plan.user_id,
                    profile_id=plan.profile_id,
                    subject_id=ObjectId(original_chapter.get("subject_id", "000000000000000000000000")),
                    chapter_id=ObjectId(original_chapter.get("chapter_id", "000000000000000000000000")),
                    subject_name=chapter_data["subject_name"],
                    chapter_name=chapter_data["chapter_name"],
                    allocated_hours=chapter_data["allocated_hours"],
                    priority_weight=chapter_data["priority"],
                    chapter_strength=chapter_data["strength"],
                    status=TaskStatus.PENDING,
                    order_in_day=idx
                )
                tasks.append(task)
            
            if tasks:
                await self.task_repo.create_many(tasks)
    
    # -------------------------------------------------------------------------
    # Plan Retrieval
    # -------------------------------------------------------------------------
    
    async def get_plan_with_upcoming_days(
        self,
        user_id: str,
        days_ahead: int = 7
    ) -> PlanResponse:
        """Get active plan with upcoming daily plans."""
        plan = await self.plan_repo.find_active_by_user(user_id)
        if not plan:
            raise NotFoundException(message="No active study plan found")
        
        # Get upcoming days
        today = date.today()
        end_date = min(today + timedelta(days=days_ahead), plan.plan_end_date)
        
        daily_plans = await self.daily_plan_repo.find_by_date_range(
            str(plan.id),
            today,
            end_date
        )
        
        # Get tasks for each daily plan
        upcoming_days = []
        for dp in daily_plans:
            tasks = await self.task_repo.find_by_daily_plan(str(dp.id))
            upcoming_days.append(self._daily_plan_to_response(dp, tasks))
        
        return PlanResponse(
            plan=self._plan_to_summary(plan),
            upcoming_days=upcoming_days
        )
    
    async def get_daily_plan(self, user_id: str, plan_date: date) -> DailyPlanResponse:
        """Get daily plan for specific date."""
        daily_plan = await self.daily_plan_repo.find_by_user_and_date(user_id, plan_date)
        if not daily_plan:
            raise NotFoundException(message=f"No plan found for {plan_date}")
        
        tasks = await self.task_repo.find_by_daily_plan(str(daily_plan.id))
        return self._daily_plan_to_response(daily_plan, tasks)
    
    async def preview_plan(
        self,
        user_id: str,
        buffer_days: int = 0
    ) -> PlanPreviewResponse:
        """Preview what would be generated without saving."""
        # Gather data
        profile, subjects, all_chapters = await self._gather_planning_data(user_id)
        
        if not subjects or not all_chapters:
            raise BadRequestException(
                message="Insufficient data for plan preview"
            )
        
        # Calculate timeline
        exam_date = profile.exam_date  # Already a date object
        days_available = calculate_days_until_exam(exam_date, buffer_days)
        
        # Analyze chapters
        weak_count = sum(1 for c in all_chapters if c.strength == "weak")
        medium_count = sum(1 for c in all_chapters if c.strength == "medium")
        strong_count = sum(1 for c in all_chapters if c.strength == "strong")
        
        # Calculate hours
        daily_study_hours = self._calculate_daily_study_hours(profile)
        total_hours_needed = sum(
            estimate_chapter_hours(c.strength) for c in all_chapters
        )
        total_hours_available = daily_study_hours * days_available
        
        feasibility, buffer_pct = analyze_plan_feasibility(
            total_hours_needed,
            total_hours_available
        )
        
        warnings = []
        if feasibility == "UNFEASIBLE":
            warnings.append("Insufficient time to cover all chapters")
        elif feasibility == "CHALLENGING":
            warnings.append("Very tight schedule. Consider increasing study hours.")
        
        return PlanPreviewResponse(
            exam_date=exam_date.isoformat(),
            plan_start_date=date.today().isoformat(),
            plan_end_date=(exam_date - timedelta(days=1 + buffer_days)).isoformat(),
            total_days=days_available,
            total_subjects=len(subjects),
            total_chapters=len(all_chapters),
            estimated_total_tasks=len(all_chapters),
            weak_chapters=weak_count,
            medium_chapters=medium_count,
            strong_chapters=strong_count,
            daily_study_hours=daily_study_hours,
            total_hours_needed=total_hours_needed,
            total_hours_available=total_hours_available,
            time_buffer_percentage=buffer_pct,
            warnings=warnings,
            feasibility_score=feasibility
        )
    
    async def delete_plan(self, user_id: str) -> bool:
        """Delete active plan for user."""
        plan = await self.plan_repo.find_active_by_user(user_id)
        if not plan:
            raise NotFoundException(message="No active plan found")
        
        # Delete all associated data
        await self.task_repo.delete_by_plan(str(plan.id))
        await self.daily_plan_repo.delete_by_plan(str(plan.id))
        await self.plan_repo.delete(str(plan.id))
        
        return True
    
    # -------------------------------------------------------------------------
    # Response Mapping
    # -------------------------------------------------------------------------
    
    def _plan_to_summary(self, plan: StudyPlanModel) -> PlanSummaryResponse:
        """Convert StudyPlanModel to PlanSummaryResponse."""
        today = date.today()
        days_completed = max(0, (today - plan.plan_start_date).days)
        days_remaining = max(0, (plan.plan_end_date - today).days)
        
        return PlanSummaryResponse(
            id=str(plan.id),
            exam_date=plan.exam_date.isoformat(),
            plan_start_date=plan.plan_start_date.isoformat(),
            plan_end_date=plan.plan_end_date.isoformat(),
            total_days=plan.total_days,
            days_completed=days_completed,
            days_remaining=days_remaining,
            total_subjects=plan.total_subjects,
            total_chapters=plan.total_chapters,
            total_tasks=plan.total_tasks,
            completed_tasks=plan.completed_tasks,
            completion_percentage=plan.completion_percentage,
            daily_study_hours=plan.daily_study_hours,
            total_allocated_hours=plan.total_allocated_hours,
            status=plan.status,
            is_active=plan.is_active,
            generated_at=plan.generated_at.isoformat()
        )
    
    def _daily_plan_to_response(
        self,
        daily_plan: DailyPlanModel,
        tasks: List[StudyTaskModel]
    ) -> DailyPlanResponse:
        """Convert DailyPlanModel to DailyPlanResponse."""
        task_responses = [self._task_to_response(t) for t in tasks]
        
        utilization = (
            (daily_plan.total_allocated_hours / daily_plan.daily_limit_hours) * 100
            if daily_plan.daily_limit_hours > 0 else 0
        )
        
        return DailyPlanResponse(
            id=str(daily_plan.id),
            date=daily_plan.plan_date.isoformat(),
            total_allocated_hours=daily_plan.total_allocated_hours,
            daily_limit_hours=daily_plan.daily_limit_hours,
            utilization_percentage=utilization,
            tasks=task_responses,
            task_count=daily_plan.task_count,
            completed_task_count=daily_plan.completed_task_count,
            is_fully_completed=daily_plan.is_fully_completed,
            completion_percentage=daily_plan.completion_percentage,
            notes=daily_plan.notes
        )
    
    def _task_to_response(self, task: StudyTaskModel) -> StudyTaskResponse:
        """Convert StudyTaskModel to StudyTaskResponse."""
        return StudyTaskResponse(
            id=str(task.id),
            subject_id=str(task.subject_id),
            chapter_id=str(task.chapter_id),
            subject_name=task.subject_name,
            chapter_name=task.chapter_name,
            allocated_hours=task.allocated_hours,
            actual_hours=task.actual_hours,
            priority_weight=task.priority_weight,
            chapter_strength=task.chapter_strength,
            order_in_day=task.order_in_day,
            status=task.status,
            is_completed=task.is_completed,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            notes=task.notes
        )
