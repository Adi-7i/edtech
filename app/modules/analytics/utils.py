"""
Analytics Utilities

Deterministic calculation formulas for honest metrics.
No score inflation, no vanity metrics.
"""

from datetime import date
from typing import Dict, List


def calculate_consistency_score(
    total_days: int,
    study_days: int,
    partial_days: int,
    consecutive_streak: int
) -> int:
    """
    Calculate consistency score (0-100).
    
    Philosophy: Consistency is key. Missing days hurts significantly.
    
    Formula:
    - Base score: (study_days / total_days) * 100
    - Penalty: -5 points per missed day (capped at -30)
    - Partial penalty: -2 points per partial day
    - Streak bonus: +1 point per consecutive day (capped at +15)
    - Final: clamp(score, 0, 100)
    
    Args:
        total_days: Total days since profile creation
        study_days: Days with at least one completed task
        partial_days: Days with partial task completion
        consecutive_streak: Current consecutive study days
    
    Returns:
        Consistency score (0-100)
    
    Example:
        - 7 days total, 7 study days, 0 partial, 7 streak → ~100
        - 7 days total, 4 study days, 1 partial, 2 streak → ~60
        - 7 days total, 2 study days, 0 partial, 0 streak → ~3
    """
    if total_days == 0:
        return 0
    
    # Base score from study days ratio
    base_score = (study_days / total_days) * 100
    
    # Calculate missed days
    missed_days = total_days - study_days
    
    # Penalties
    missed_penalty = min(30, missed_days * 5)  # -5 per miss, max -30
    partial_penalty = partial_days * 2  # -2 per partial day
    
    # Bonuses
    streak_bonus = min(15, consecutive_streak)  # +1 per day, max +15
    
    # Final calculation
    score = base_score - missed_penalty - partial_penalty + streak_bonus
    
    # Clamp to 0-100
    return max(0, min(100, int(score)))


def calculate_exam_readiness(
    syllabus_coverage_pct: float,
    revision_completion_pct: float,
    days_until_exam: int,
    weak_chapter_count: int,
    total_chapters: int
) -> int:
    """
    Calculate realistic exam readiness score (0-100).
    
    Philosophy: Honest assessment of preparation state.
    
    Formula:
    - Coverage weight: 40% (syllabus_coverage_pct * 0.4)
    - Revision weight: 30% (revision_completion_pct * 0.3)
    - Time weight: 30% based on days_until_exam
      - < 7 days: 30 points if ready (90% coverage + 75% revisions), else 0
      - 7-14 days: proportional score
      - > 14 days: full 30 points
    - Weak penalty: -3 points per weak chapter (capped at -20)
    
    Args:
        syllabus_coverage_pct: Percentage of syllabus covered (0-100)
        revision_completion_pct: Percentage of revisions done (0-100)
        days_until_exam: Days remaining until exam
        weak_chapter_count: Number of weak chapters
        total_chapters: Total chapters across all subjects
    
    Returns:
        Exam readiness score (0-100)
    
    Example:
        - 100% coverage, 100% revisions, 30 days, 0 weak → 100
        - 50% coverage, 0% revisions, 5 days, 5 weak → ~5
        - 90% coverage, 75% revisions, 10 days, 2 weak → ~84
    """
    # Coverage component (40% weight)
    coverage_score = syllabus_coverage_pct * 0.4
    
    # Revision component (30% weight)
    revision_score = revision_completion_pct * 0.3
    
    # Time component (30% weight)
    if days_until_exam < 0:
        # Exam has passed
        time_score = 0
    elif days_until_exam < 7:
        # Crunch time - only award points if well-prepared
        if syllabus_coverage_pct >= 90 and revision_completion_pct >= 75:
            time_score = 30
        else:
            time_score = 0  # Not enough time to prepare properly!
    elif days_until_exam < 14:
        # 1-2 weeks out - proportional score
        time_score = (days_until_exam / 14) * 30
    else:
        # Plenty of time
        time_score = 30
    
    # Weak chapter penalty
    weak_penalty = min(20, weak_chapter_count * 3)
    
    # Final calculation
    score = coverage_score + revision_score + time_score - weak_penalty
    
    # Clamp to 0-100
    return max(0, min(100, int(score)))


def calculate_subject_coverage(
    chapters_completed: int,
    total_chapters: int,
    chapters_revised: int
) -> Dict[str, float]:
    """
    Calculate subject progress metrics.
    
    Args:
        chapters_completed: Number of completed chapters
        total_chapters: Total chapters in subject
        chapters_revised: Number of chapters with revisions
    
    Returns:
        Dictionary with:
        - coverage_percentage: % of chapters completed
        - revision_coverage: % of completed chapters that are revised
        - completion_status: "not_started", "in_progress", "completed"
    """
    if total_chapters == 0:
        return {
            "coverage_percentage": 0.0,
            "revision_coverage": 0.0,
            "completion_status": "not_started"
        }
    
    # Coverage percentage
    coverage_pct = (chapters_completed / total_chapters) * 100
    
    # Revision coverage (of completed chapters)
    if chapters_completed > 0:
        revision_coverage = (chapters_revised / chapters_completed) * 100
    else:
        revision_coverage = 0.0
    
    # Completion status
    if chapters_completed == 0:
        status = "not_started"
    elif chapters_completed < total_chapters:
        status = "in_progress"
    else:
        status = "completed"
    
    return {
        "coverage_percentage": round(coverage_pct, 2),
        "revision_coverage": round(revision_coverage, 2),
        "completion_status": status
    }


def calculate_completion_ratio(
    completed: int,
    total: int
) -> float:
    """
    Calculate completion ratio as percentage.
    
    Args:
        completed: Number of completed items
        total: Total number of items
    
    Returns:
        Completion percentage (0-100)
    """
    if total == 0:
        return 0.0
    
    return round((completed / total) * 100, 2)


def calculate_average_completion_rate(
    daily_rates: List[float]
) -> float:
    """
    Calculate average completion rate from daily rates.
    
    Args:
        daily_rates: List of daily completion percentages
    
    Returns:
        Average completion rate
    """
    if not daily_rates:
        return 0.0
    
    return round(sum(daily_rates) / len(daily_rates), 2)


def is_analytics_frozen(exam_date: date, current_date: date) -> bool:
    """
    Check if analytics should be frozen (exam has passed).
    
    Args:
        exam_date: Target exam date
        current_date: Current date
    
    Returns:
        True if analytics should be frozen (read-only)
    """
    return current_date > exam_date


def generate_exam_readiness_recommendations(
    syllabus_coverage: float,
    revision_completion: float,
    days_until_exam: int,
    weak_chapter_count: int
) -> List[str]:
    """
    Generate actionable recommendations based on exam readiness.
    
    Args:
        syllabus_coverage: Percentage of syllabus covered
        revision_completion: Percentage of revisions completed
        days_until_exam: Days until exam
        weak_chapter_count: Number of weak chapters
    
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # Coverage recommendations
    if syllabus_coverage < 50:
        recommendations.append("⚠️ Low syllabus coverage - prioritize completing chapters")
    elif syllabus_coverage < 80:
        recommendations.append("📚 Focus on completing remaining chapters")
    
    # Revision recommendations
    if revision_completion < 30 and syllabus_coverage > 60:
        recommendations.append("🔄 Start revising completed chapters immediately")
    elif revision_completion < 70:
        recommendations.append("🔄 Increase revision frequency")
    
    # Time pressure recommendations
    if days_until_exam < 7:
        if syllabus_coverage < 90:
            recommendations.append("🚨 URGENT: Less than a week! Focus on high-priority topics")
        recommendations.append("⏰ Daily revisions critical at this stage")
    elif days_until_exam < 14:
        recommendations.append("⏰ Two weeks left - maintain consistent daily study")
    
    # Weak chapter recommendations
    if weak_chapter_count > 5:
        recommendations.append("💪 Many weak chapters - allocate extra time for practice")
    elif weak_chapter_count > 0:
        recommendations.append("💪 Focus on strengthening weak chapters")
    
    # Positive feedback
    if syllabus_coverage >= 90 and revision_completion >= 80:
        recommendations.append("✅ Excellent preparation! Continue with scheduled revisions")
    
    if not recommendations:
        recommendations.append("📈 Keep up the consistent study pace")
    
    return recommendations
