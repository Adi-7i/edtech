"""
Revision Utilities

Spaced repetition algorithm implementation using fixed intervals.
"""

from datetime import date, timedelta
from typing import Tuple

from app.core.database.models.revision import (
    SPACED_REPETITION_DAYS,
    RevisionQuality,
    RevisionStatus,
)


def calculate_next_revision_date(
    last_completion_date: date,
    current_cycle_index: int
) -> Tuple[date, int]:
    """
    Calculate next revision date based on spaced repetition intervals.
    
    Intervals: 1, 3, 7, 21 days after previous revision.
    
    Args:
        last_completion_date: Date when previous revision was completed
        current_cycle_index: Current position in cycle (0-3)
    
    Returns:
        Tuple of (next_revision_date, next_cycle_day)
    
    Example:
        - Completed on 2026-02-01
        - Current cycle index: 0 (Day 1)
        - Returns: (2026-02-04, 3) → 3 days later
    """
    if current_cycle_index >= len(SPACED_REPETITION_DAYS) - 1:
        # All cycles complete, schedule monthly review
        next_date = last_completion_date + timedelta(days=30)
        return next_date, 30
    
    # Get next interval
    next_index = current_cycle_index + 1
    next_cycle_day = SPACED_REPETITION_DAYS[next_index]
    
    # Calculate days from last completion
    if current_cycle_index == 0:
        # First revision: schedule based on learning date
        days_to_add = next_cycle_day
    else:
        # Subsequent revisions: interval from last completion
        current_day = SPACED_REPETITION_DAYS[current_cycle_index]
        days_to_add = next_cycle_day - current_day
    
    next_date = last_completion_date + timedelta(days=days_to_add)
    return next_date, next_cycle_day


def get_cycle_index_from_day(cycle_day: int) -> int:
    """
    Get array index from cycle day value.
    
    Args:
        cycle_day: Cycle day (1, 3, 7, or 21)
    
    Returns:
        Index in SPACED_REPETITION_DAYS array
    """
    try:
        return SPACED_REPETITION_DAYS.index(cycle_day)
    except ValueError:
        return 0


def should_advance_cycle(quality: RevisionQuality) -> bool:
    """
    Determine if user should advance to next cycle based on recall quality.
    
    Logic:
    - PERFECT, GOOD → advance to next interval
    - AVERAGE → repeat current interval  
    - POOR, FAILED → reset to Day 1
    
    Args:
        quality: User's self-reported recall quality
    
    Returns:
        True if should advance, False if should repeat/reset
    """
    return quality in [RevisionQuality.PERFECT, RevisionQuality.GOOD]


def calculate_adjusted_next_cycle(
    current_cycle_index: int,
    quality: RevisionQuality
) -> int:
    """
    Calculate next cycle index based on performance.
    
    Args:
        current_cycle_index: Current position (0-3)
        quality: Recall quality
    
    Returns:
        Next cycle index
    
    Logic:
    - PERFECT/GOOD → advance 1 level
    - AVERAGE → stay at same level
    - POOR/FAILED → reset to level 0
    """
    if quality in [RevisionQuality.PERFECT, RevisionQuality.GOOD]:
        # Advance to next level
        return min(current_cycle_index + 1, len(SPACED_REPETITION_DAYS) - 1)
    
    elif quality == RevisionQuality.AVERAGE:
        # Repeat current level
        return current_cycle_index
    
    else:  # POOR or FAILED
        # Reset to beginning
        return 0


def is_eligible_for_revision(
    chapter_completion_date: date,
    exam_date: date,
    today: date = None
) -> Tuple[bool, str]:
    """
    Check if a chapter is eligible for revision scheduling.
    
    Args:
        chapter_completion_date: When chapter was completed
        exam_date: Target exam date
        today: Current date (defaults to today)
    
    Returns:
        Tuple of (is_eligible, reason)
    """
    if today is None:
        today = date.today()
    
    # Must have completion date
    if chapter_completion_date is None:
        return False, "Chapter not yet completed"
    
    # Exam date must be in future
    if exam_date <= today:
        return False, "Exam date has passed"
    
    # Calculate if at least Day 1 revision can fit before exam
    day_1_revision = chapter_completion_date + timedelta(days=1)
    if day_1_revision > exam_date:
        return False, "Not enough time before exam for even first revision"
    
    return True, "Eligible"


def calculate_priority_score(
    next_revision_date: date,
    exam_date: date,
    missed_count: int,
    chapter_strength: str,
    today: date = None
) -> int:
    """
    Calculate priority score for revision ordering.
    
    Lower score = higher priority
    
    Factors:
    1. Overdue status (highest priority)
    2. Chapter weakness
    3. Proximity to exam
    4. Number of missed revisions
    
    Args:
        next_revision_date: Scheduled revision date
        exam_date: Target exam date
        missed_count: Number of previous misses
        chapter_strength: Chapter strength ("weak", "medium", "strong")
        today: Current date
    
    Returns:
        Priority score (1-10, where 1 is highest priority)
    """
    if today is None:
        today = date.today()
    
    score = 5  # Base score
    
    # Factor 1: Overdue (highest impact)
    if next_revision_date < today:
        overdue_days = (today - next_revision_date).days
        score -= min(overdue_days, 3)  # -1 to -3
    
    # Factor 2: Chapter weakness
    if chapter_strength == "weak":
        score -= 2
    elif chapter_strength == "medium":
        score -= 1
    
    # Factor 3: Exam proximity
    days_to_exam = (exam_date - today).days
    if days_to_exam <= 7:
        score -= 2
    elif days_to_exam <= 14:
        score -= 1
    
    # Factor 4: Missed count penalty
    score += min(missed_count, 2)
    
    # Clamp to 1-10
    return max(1, min(score, 10))
