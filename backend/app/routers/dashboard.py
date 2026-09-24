"""Dashboard summary + daily recommendation (FR-19, FR-20)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import PriorityLevel, Task, User
from app.routers.tasks import _is_overdue, _to_out
from app.schemas import DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=7)

    all_tasks = db.query(Task).filter(Task.owner_id == current_user.id).all()  # FR-21
    incomplete = [t for t in all_tasks if not t.completed]
    completed = [t for t in all_tasks if t.completed]
    high_priority = [
        t for t in incomplete if t.priority_level in (PriorityLevel.HIGH, PriorityLevel.CRITICAL)
    ]
    upcoming = sorted(
        [t for t in incomplete if t.deadline <= horizon], key=lambda t: t.deadline
    )
    overdue = [t for t in incomplete if _is_overdue(t, now)]

    # FR-20: highest-priority incomplete task; FR-14 tie-break by earlier deadline.
    recommended = None
    if incomplete:
        recommended = min(incomplete, key=lambda t: (-t.priority_score, t.deadline))

    return DashboardOut(
        incomplete_count=len(incomplete),
        completed_count=len(completed),
        high_priority_count=len(high_priority),
        upcoming_count=len(upcoming),
        overdue_count=len(overdue),
        upcoming_tasks=[_to_out(t) for t in upcoming],
        recommended_task=_to_out(recommended) if recommended else None,
    )
