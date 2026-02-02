"""
Planner Utility Functions

Helper algorithms for study plan generation:
- Priority calculation
- Time allocation
- Chapter distribution
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple

from app.core.database.models.study_profile import StrengthLevel


# -----------------------------------------------------------------------------
# Priority Calculation
# -----------------------------------------------------------------------------

def calculate_chapter_priority(strength: str) -> float:
    """
    Calculate priority weight for a chapter based on strength.
    
    Higher weight = higher priority = earlier in schedule.
    
    Args:
        strength: 'weak', 'medium', or 'strong'
    
    Returns:
        Priority weight (1.0 - 3.0)
    """
    priority_map = {
        StrengthLevel.WEAK: 3.0,      # Highest priority
        StrengthLevel.MEDIUM: 2.0,     # Medium priority
        StrengthLevel.STRONG: 1.0,     # Lowest priority
        # String fallbacks
        "weak": 3.0,
        "medium": 2.0,
        "strong": 1.0,
    }
    
    return priority_map.get(strength, 2.0)  # Default to medium


def estimate_chapter_hours(strength: str, base_hours: float = 2.0) -> float:
    """
    Estimate study hours needed for a chapter based on strength.
    
    Weak chapters need more time, strong chapters need less.
    
    Args:
        strength: 'weak', 'medium', or 'strong'
        base_hours: Base time allocation (default 2.0)
    
    Returns:
        Estimated hours (0.5 - 4.0)
    """
    multiplier_map = {
        StrengthLevel.WEAK: 1.5,       # 50% more time
        StrengthLevel.MEDIUM: 1.0,     # Standard time
        StrengthLevel.STRONG: 0.75,    # 25% less time
        # String fallbacks
        "weak": 1.5,
        "medium": 1.0,
        "strong": 0.75,
    }
    
    multiplier = multiplier_map.get(strength, 1.0)
    estimated = base_hours * multiplier
    
    # Clamp between 0.5 and 4.0 hours
    return max(0.5, min(4.0, estimated))


# -----------------------------------------------------------------------------
# Time Distribution
# -----------------------------------------------------------------------------

def distribute_chapters_across_days(
    chapters: List[Dict],
    daily_limit_hours: float,
    total_days: int,
    buffer_days: int = 0
) -> Tuple[List[Dict], List[str]]:
    """
    Distribute chapters across available days.
    
    Algorithm:
    1. Sort chapters by priority (weak first)
    2. Fill each day up to daily_limit_hours
    3. Split large chapters if needed
    4. Return distribution + warnings
    
    Args:
        chapters: List of chapter dicts with 'id', 'priority', 'estimated_hours'
        daily_limit_hours: Max hours per day
        total_days: Days available
        buffer_days: Reserve N days at end (for revision)
    
    Returns:
        Tuple of (distribution, warnings)
        - distribution: List of dicts {date, chapters: [{id, hours}]}
        - warnings: List of warning messages
    """
    warnings = []
    distribution = []
    
    # Calculate available days
    available_days = total_days - buffer_days
    if available_days <= 0:
        warnings.append("No days available after buffer. Plan cannot be generated.")
        return [], warnings
    
    # Sort chapters by priority (descending = weak first)
    sorted_chapters = sorted(
        chapters,
        key=lambda c: c.get("priority", 2.0),
        reverse=True
    )
    
    # Calculate total hours needed
    total_hours_needed = sum(c.get("estimated_hours", 2.0) for c in sorted_chapters)
    total_hours_available = daily_limit_hours * available_days
    
    # Check feasibility
    if total_hours_needed > total_hours_available * 1.2:  # 20% buffer
        warnings.append(
            f"Insufficient time. Need {total_hours_needed:.1f}h, "
            f"available {total_hours_available:.1f}h"
        )
        # Scale down all chapters proportionally
        scale_factor = (total_hours_available * 0.9) / total_hours_needed
        for chapter in sorted_chapters:
            chapter["estimated_hours"] *= scale_factor
    
    # Distribute chapters across days
    current_day = 0
    current_day_hours = 0.0
    current_day_chapters = []
    
    start_date = date.today()
    
    for chapter in sorted_chapters:
        chapter_hours = chapter.get("estimated_hours", 2.0)
        
        # If chapter fits in current day
        if current_day_hours + chapter_hours <= daily_limit_hours:
            current_day_chapters.append({
                "chapter_id": chapter["id"],
                "chapter_name": chapter.get("name", "Unknown"),
                "subject_name": chapter.get("subject_name", "Unknown"),
                "allocated_hours": chapter_hours,
                "priority": chapter.get("priority", 2.0),
                "strength": chapter.get("strength", "medium")
            })
            current_day_hours += chapter_hours
        
        else:
            # Save current day and move to next
            if current_day_chapters:
                distribution.append({
                    "date": start_date + timedelta(days=current_day),
                    "total_hours": current_day_hours,
                    "chapters": current_day_chapters
                })
            
            current_day += 1
           
            if current_day >= available_days:
                warnings.append(
                    f"Ran out of days. {len(sorted_chapters) - sorted_chapters.index(chapter)} "
                    "chapters could not be scheduled."
                )
                break
            
            # Start new day with this chapter
            current_day_chapters = [{
                "chapter_id": chapter["id"],
                "chapter_name": chapter.get("name", "Unknown"),
                "subject_name": chapter.get("subject_name", "Unknown"),
                "allocated_hours": chapter_hours,
                "priority": chapter.get("priority", 2.0),
                "strength": chapter.get("strength", "medium")
            }]
            current_day_hours = chapter_hours
    
    # Save last day
    if current_day_chapters and current_day < available_days:
        distribution.append({
            "date": start_date + timedelta(days=current_day),
            "total_hours": current_day_hours,
            "chapters": current_day_chapters
        })
    
    return distribution, warnings


# -----------------------------------------------------------------------------
# Date Utilities
# -----------------------------------------------------------------------------

def calculate_days_until_exam(exam_date: date, buffer_days: int = 0) -> int:
    """
    Calculate remaining days until exam (excluding buffer).
    
    Args:
        exam_date: The exam date
        buffer_days: Days to reserve before exam
    
    Returns:
        Number of available study days
    """
    today = date.today()
    total_days = (exam_date - today).days
    
    # Subtract 1 for exam day itself, plus buffer
    available_days = total_days - 1 - buffer_days
    
    return max(0, available_days)


def generate_date_range(start_date: date, end_date: date) -> List[date]:
    """
    Generate list of dates between start and end (inclusive).
    
    Args:
        start_date: Start date
        end_date: End date
    
    Returns:
        List of dates
    """
    dates = []
    current = start_date
    
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    return dates


# -----------------------------------------------------------------------------
# Feasibility Analysis
# -----------------------------------------------------------------------------

def analyze_plan_feasibility(
    total_hours_needed: float,
    total_hours_available: float
) -> Tuple[str, float]:
    """
    Analyze if plan is feasible based on time.
    
    Args:
        total_hours_needed: Total study hours required
        total_hours_available: Total hours available
    
    Returns:
        Tuple of (feasibility_label, buffer_percentage)
    """
    buffer_percentage = ((total_hours_available - total_hours_needed) / total_hours_needed) * 100
    
    if buffer_percentage >= 30:
        return "COMFORTABLE", buffer_percentage
    elif buffer_percentage >= 10:
        return "TIGHT", buffer_percentage
    elif buffer_percentage >= -10:
        return "CHALLENGING", buffer_percentage
    else:
        return "UNFEASIBLE", buffer_percentage
