"""Student dashboard summary + daily recommendation (FR-19, FR-20)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import PriorityLevel, Task, User
from app.schemas import DashboardOut, LabelCount
from app.task_service import (
    as_utc,
    deadline_sort_key,
    is_overdue,
    priority_sort_key,
    refresh_priorities,
    to_out,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

LEVELS_HIGH_TO_LOW = [
    PriorityLevel.CRITICAL,
    PriorityLevel.HIGH,
    PriorityLevel.MEDIUM,
    PriorityLevel.LOW,
]


@router.get("", response_model=DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=7)

    all_tasks = db.query(Task).filter(Task.owner_id == current_user.id).all()  # FR-21
    refresh_priorities(db, all_tasks)

    incomplete = [t for t in all_tasks if not t.completed]
    completed = [t for t in all_tasks if t.completed]
    high_priority = [
        t for t in incomplete if t.priority_level in (PriorityLevel.HIGH, PriorityLevel.CRITICAL)
    ]
    upcoming = sorted(
        [t for t in incomplete if as_utc(t.deadline) <= horizon], key=deadline_sort_key
    )
    overdue = sorted([t for t in incomplete if is_overdue(t, now)], key=deadline_sort_key)

    # FR-20: highest-priority incomplete task; FR-14 tie-break by earlier deadline.
    by_priority = sorted(incomplete, key=priority_sort_key)
    recommended = by_priority[0] if by_priority else None

    completion_rate = round(100 * len(completed) / len(all_tasks), 1) if all_tasks else 0.0

    return DashboardOut(
        incomplete_count=len(incomplete),
        completed_count=len(completed),
        high_priority_count=len(high_priority),
        upcoming_count=len(upcoming),
        overdue_count=len(overdue),
        completion_rate=completion_rate,
        hours_due_this_week=round(sum(t.estimated_hours for t in upcoming), 2),
        priority_breakdown=[
            LabelCount(label=level.value, count=sum(1 for t in incomplete if t.priority_level == level))
            for level in LEVELS_HIGH_TO_LOW
        ],
        upcoming_tasks=[to_out(t) for t in upcoming],
        overdue_tasks=[to_out(t) for t in overdue],
        priority_queue=[to_out(t) for t in by_priority[1:6]],
        recommended_task=to_out(recommended) if recommended else None,
    )
