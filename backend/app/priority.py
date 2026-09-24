"""Priority calculation — Section 3 of requirements-spec.md.

This formula is a *fixed part of the spec*: deadline urgency (50%) +
difficulty (30%) + estimated time (20%), producing a 0-100 score that is
then classified into Low/Medium/High/Critical. It must be implemented
exactly as specified, not reinvented (FR-11, FR-12, FR-13).
"""
from datetime import datetime, timezone

from app.models import Difficulty, PriorityLevel

DIFFICULTY_SCORES: dict[Difficulty, float] = {
    Difficulty.EASY: 20,
    Difficulty.MEDIUM: 50,
    Difficulty.HARD: 80,
    Difficulty.VERY_HARD: 100,
}

DEADLINE_WEIGHT = 0.50
DIFFICULTY_WEIGHT = 0.30
TIME_WEIGHT = 0.20


def _ensure_aware(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC so callers can pass either form safely."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def deadline_score(deadline: datetime, now: datetime | None = None) -> float:
    """Score based on time remaining until the deadline.

    | Time until deadline   | Score |
    |------------------------|-------|
    | More than 14 days      | 10    |
    | 7-14 days               | 25    |
    | 3-6 days                | 50    |
    | 1-2 days                | 75    |
    | Less than 24 hours      | 100   |
    | Overdue                 | 100   |
    """
    now = _ensure_aware(now or datetime.now(timezone.utc))
    deadline = _ensure_aware(deadline)

    remaining = deadline - now
    hours_remaining = remaining.total_seconds() / 3600
    days_remaining = hours_remaining / 24

    if hours_remaining < 0:
        return 100  # Overdue
    if hours_remaining < 24:
        return 100  # Less than 24 hours
    if days_remaining <= 2:
        return 75  # 1-2 days
    if days_remaining <= 6:
        return 50  # 3-6 days
    if days_remaining <= 14:
        return 25  # 7-14 days
    return 10  # More than 14 days


def difficulty_score(difficulty: Difficulty) -> float:
    return DIFFICULTY_SCORES[difficulty]


def time_score(estimated_hours: float) -> float:
    """Time Score = min(Estimated Hours x 10, 100)."""
    return min(estimated_hours * 10, 100)


def calculate_priority_score(
    deadline: datetime,
    difficulty: Difficulty,
    estimated_hours: float,
    now: datetime | None = None,
) -> float:
    score = (
        deadline_score(deadline, now) * DEADLINE_WEIGHT
        + difficulty_score(difficulty) * DIFFICULTY_WEIGHT
        + time_score(estimated_hours) * TIME_WEIGHT
    )
    return round(score, 2)


def classify_priority(score: float) -> PriorityLevel:
    """| Priority Score | Classification |
    |-----------------|-----------------|
    | 80-100          | Critical        |
    | 60-79           | High            |
    | 40-59           | Medium          |
    | 0-39            | Low             |
    """
    if score >= 80:
        return PriorityLevel.CRITICAL
    if score >= 60:
        return PriorityLevel.HIGH
    if score >= 40:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


def compute_priority(
    deadline: datetime,
    difficulty: Difficulty,
    estimated_hours: float,
    now: datetime | None = None,
) -> tuple[float, PriorityLevel]:
    score = calculate_priority_score(deadline, difficulty, estimated_hours, now)
    return score, classify_priority(score)
