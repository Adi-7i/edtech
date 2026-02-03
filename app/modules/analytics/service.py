"""
Analytics Service

Core business logic for calculating honest, actionable analytics.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import (
    ConsistencyMetrics,
    DailyAnalyticsResponse,
    DailyTaskSummary,
    ExamReadiness,
    OverviewAnalyticsResponse,
    SubjectProgress,
    WeeklyAnalyticsResponse,
)
from app.modules.analytics.utils import (
    calculate_average_completion_rate,
    calculate_completion_ratio,
    calculate_consistency_score,
    calculate_exam_readiness,
    calculate_subject_coverage,
    generate_exam_readiness_recommendations,
    is_analytics_frozen,
)


class AnalyticsService:
    """Service for calculating and providing analytics insights."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.repository = AnalyticsRepository(db)
        self.profiles_collection = db.study_profiles
    
    async def get_daily_analytics(
        self,
        user_id: str,
        target_date: Optional[date] = None
    ) -> DailyAnalyticsResponse:
        """
        Get analytics for a specific day.
        
        Args:
            user_id: User ID
            target_date: Date to get analytics for (defaults to today)
        
        Returns:
            DailyAnalyticsResponse with day's metrics
        
        Raises:
            NotFoundException: If user profile not found
        """
        if target_date is None:
            target_date = date.today()
        
        # Verify profile exists
        profile = await self.profiles_collection.find_one({"user_id": ObjectId(user_id)})
        if not profile:
            raise NotFoundException(message="Study profile not found")
        
        # Get daily task summary
        summary_data = await self.repository.get_daily_task_summary(user_id, target_date)
        
        # Calculate completion percentage
        if summary_data["planned_tasks"] > 0:
            completion_pct = calculate_completion_ratio(
                summary_data["completed_tasks"],
                summary_data["planned_tasks"]
            )
        else:
            completion_pct = 0.0
        
        # Build task summary
        task_summary = DailyTaskSummary(
            date=target_date.isoformat(),
            planned_tasks=summary_data["planned_tasks"],
            completed_tasks=summary_data["completed_tasks"],
            partial_tasks=summary_data["partial_tasks"],
            missed_tasks=summary_data["missed_tasks"],
            planned_minutes=summary_data["planned_minutes"],
            actual_minutes=summary_data["actual_minutes"],
            completion_percentage=completion_pct
        )
        
        # Consistency maintained if >= 70% completion
        consistency_maintained = completion_pct >= 70.0
        
        return DailyAnalyticsResponse(
            date=target_date.isoformat(),
            task_summary=task_summary,
            study_minutes=summary_data["actual_minutes"],
            consistency_maintained=consistency_maintained,
            has_plan=summary_data["has_plan"]
        )
    
    async def get_weekly_analytics(
        self,
        user_id: str,
        week_start: Optional[date] = None
    ) -> WeeklyAnalyticsResponse:
        """
        Get analytics for a 7-day week.
        
        Args:
            user_id: User ID
            week_start: Start of week (defaults to Monday of current week)
        
        Returns:
            WeeklyAnalyticsResponse with week's metrics
        
        Raises:
            NotFoundException: If user profile not found
        """
        # Verify profile exists
        profile = await self.profiles_collection.find_one({"user_id": ObjectId(user_id)})
        if not profile:
            raise NotFoundException(message="Study profile not found")
        
        # Default to current week's Monday
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        # Get daily summaries for the week
        summaries_data = await self.repository.get_tasks_in_date_range(
            user_id,
            week_start,
            week_end
        )
        
        # Build daily summaries
        daily_summaries = []
        total_study_minutes = 0
        completion_rates = []
        active_days = 0
        study_days = 0
        partial_days = 0
        
        for data in summaries_data:
            # Calculate completion percentage
            if data["planned_tasks"] > 0:
                completion_pct = calculate_completion_ratio(
                    data["completed_tasks"],
                    data["planned_tasks"]
                )
            else:
                completion_pct = 0.0
            
            completion_rates.append(completion_pct)
            total_study_minutes += data["actual_minutes"]
            
            # Count active days
            if data["completed_tasks"] > 0 or data["partial_tasks"] > 0:
                active_days += 1
            
            if data["completed_tasks"] > 0:
                study_days += 1
            
            if data["partial_tasks"] > 0 and data["completed_tasks"] == 0:
                partial_days += 1
            
            daily_summaries.append(DailyTaskSummary(
                date=data["date"],
                planned_tasks=data["planned_tasks"],
                completed_tasks=data["completed_tasks"],
                partial_tasks=data["partial_tasks"],
                missed_tasks=data["missed_tasks"],
                planned_minutes=data["planned_minutes"],
                actual_minutes=data["actual_minutes"],
                completion_percentage=completion_pct
            ))
        
        # Calculate average completion rate
        avg_completion = calculate_average_completion_rate(completion_rates)
        
        # Calculate weekly consistency score
        consistency = calculate_consistency_score(
            total_days=7,
            study_days=study_days,
            partial_days=partial_days,
            consecutive_streak=0  # Not applicable for weekly view
        )
        
        return WeeklyAnalyticsResponse(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            daily_summaries=daily_summaries,
            total_study_minutes=total_study_minutes,
            average_completion_rate=avg_completion,
            consistency_score=consistency,
            active_days=active_days
        )
    
    async def get_overview_analytics(
        self,
        user_id: str
    ) -> OverviewAnalyticsResponse:
        """
        Get comprehensive analytics overview.
        
        Args:
            user_id: User ID
        
        Returns:
            OverviewAnalyticsResponse with all metrics
        
        Raises:
            NotFoundException: If user profile not found
        """
        # Get profile
        profile = await self.profiles_collection.find_one({"user_id": ObjectId(user_id)})
        if not profile:
            raise NotFoundException(message="Study profile not found")
        
        exam_date_dt = profile.get("exam_date")
        if isinstance(exam_date_dt, datetime):
            exam_date = exam_date_dt.date()
        else:
            exam_date = exam_date_dt
        
        created_at = profile.get("created_at")
        if isinstance(created_at, datetime):
            profile_start_date = created_at.date()
        else:
            profile_start_date = date.today()
        
        # Check if analytics should be frozen
        frozen = is_analytics_frozen(exam_date, date.today())
        
        # Calculate consistency metrics
        consistency = await self._calculate_consistency_metrics(
            user_id,
            profile_start_date,
            exam_date if frozen else date.today()
        )
        
        # Get all subjects statistics
        subjects_data = await self.repository.get_all_subjects_stats(user_id)
        
        # Calculate exam readiness
        exam_readiness = await self._calculate_exam_readiness(
            user_id,
            exam_date,
            subjects_data
        )
        
        # Build subject progress list
        subjects = []
        total_chapters = 0
        completed_chapters = 0
        
        for subject_doc, stats in subjects_data:
            coverage_data = calculate_subject_coverage(
                stats.completed_chapters,
                stats.total_chapters,
                stats.revised_count
            )
            
            subjects.append(SubjectProgress(
                subject_id=str(subject_doc["_id"]),
                subject_name=subject_doc.get("name", "Unknown"),
                total_chapters=stats.total_chapters,
                completed_chapters=stats.completed_chapters,
                coverage_percentage=coverage_data["coverage_percentage"],
                weak_chapters=stats.weak_count,
                medium_chapters=stats.medium_count,
                strong_chapters=stats.strong_count,
                revised_chapters=stats.revised_count,
                revision_coverage=coverage_data["revision_coverage"],
                completion_status=coverage_data["completion_status"]
            ))
            
            total_chapters += stats.total_chapters
            completed_chapters += stats.completed_chapters
        
        # Calculate overall progress
        overall_progress = calculate_completion_ratio(completed_chapters, total_chapters)
        
        # Get total study hours
        total_hours = await self.repository.count_total_study_hours(user_id)
        
        return OverviewAnalyticsResponse(
            consistency=consistency,
            exam_readiness=exam_readiness,
            subjects=subjects,
            overall_progress=overall_progress,
            total_study_hours=round(total_hours, 2),
            exam_date=exam_date.isoformat(),
            analytics_frozen=frozen,
            profile_created_date=profile_start_date.isoformat()
        )
    
    async def _calculate_consistency_metrics(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> ConsistencyMetrics:
        """
        Calculate comprehensive consistency metrics.
        
        Args:
            user_id: User ID
            start_date: Profile creation date
            end_date: End date (today or exam date if frozen)
        
        Returns:
            ConsistencyMetrics with all metrics
        """
        # Get streak data
        streak_data = await self.repository.get_study_streak(user_id, end_date)
        
        # Calculate total days
        total_days = (end_date - start_date).days + 1
        missed_days = total_days - streak_data.total_study_days
        
        # Calculate consistency score
        score = calculate_consistency_score(
            total_days=total_days,
            study_days=streak_data.total_study_days,
            partial_days=streak_data.partial_days,
            consecutive_streak=streak_data.current_streak
        )
        
        return ConsistencyMetrics(
            score=score,
            current_streak=streak_data.current_streak,
            longest_streak=streak_data.longest_streak,
            total_study_days=streak_data.total_study_days,
            total_days=total_days,
            missed_days=missed_days,
            partial_days=streak_data.partial_days
        )
    
    async def _calculate_exam_readiness(
        self,
        user_id: str,
        exam_date: date,
        subjects_data: list
    ) -> ExamReadiness:
        """
        Calculate realistic exam readiness score.
        
        Args:
            user_id: User ID
            exam_date: Target exam date
            subjects_data: List of (subject_doc, statistics) tuples
        
        Returns:
            ExamReadiness with score and recommendations
        """
        # Calculate overall syllabus coverage
        total_chapters = sum(stats.total_chapters for _, stats in subjects_data)
        completed_chapters = sum(stats.completed_chapters for _, stats in subjects_data)
        
        if total_chapters > 0:
            syllabus_coverage = (completed_chapters / total_chapters) * 100
        else:
            syllabus_coverage = 0.0
        
        # Calculate revision completion
        total_revised = sum(stats.revised_count for _, stats in subjects_data)
        if completed_chapters > 0:
            revision_completion = (total_revised / completed_chapters) * 100
        else:
            revision_completion = 0.0
        
        # Calculate days until exam
        days_until = (exam_date - date.today()).days
        
        # Count weak chapters
        weak_count = sum(stats.weak_count for _, stats in subjects_data)
        
        # Calculate readiness score
        score = calculate_exam_readiness(
            syllabus_coverage_pct=syllabus_coverage,
            revision_completion_pct=revision_completion,
            days_until_exam=days_until,
            weak_chapter_count=weak_count,
            total_chapters=total_chapters
        )
        
        # Generate recommendations
        recommendations = generate_exam_readiness_recommendations(
            syllabus_coverage=syllabus_coverage,
            revision_completion=revision_completion,
            days_until_exam=days_until,
            weak_chapter_count=weak_count
        )
        
        return ExamReadiness(
            score=score,
            syllabus_coverage=round(syllabus_coverage, 2),
            revision_completion=round(revision_completion, 2),
            days_until_exam=days_until,
            weak_chapter_count=weak_count,
            total_chapters=total_chapters,
            is_ready=(score >= 80),
            recommendations=recommendations
        )
