"""Shared task helpers used by the student, dashboard and admin routers."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Task
from app.priority import compute_priority
from app.schemas import TaskOut


def as_utc(dt: datetime) -> datetime:
    """Some databases (SQLite in tests) return naive datetimes. All deadlines
    are stored in UTC, so a naive value is treated as UTC. This keeps
    comparisons against `datetime.now(timezone.utc)` from raising TypeError."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def is_overdue(task: Task, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return (not task.completed) and as_utc(task.deadline) < now


def to_out(task: Task) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.is_overdue = is_overdue(task)
    return out


def priority_sort_key(task: Task):
    """FR-16 + FR-14: highest score first, ties broken by the earlier deadline."""
    return (-task.priority_score, as_utc(task.deadline))


def deadline_sort_key(task: Task):
    return as_utc(task.deadline)


def refresh_priorities(db: Session, tasks: list[Task]) -> None:
    """Deadline urgency depends on the current time, so a score stored when the
    task was created goes stale as the deadline approaches. Recompute scores for
    incomplete tasks on read and persist any that changed, so sorting, the
    dashboard and the recommendation always reflect today's urgency."""
    changed = False
    for task in tasks:
        if task.completed:
            continue
        score, level = compute_priority(task.deadline, task.difficulty, task.estimated_hours)
        if score != task.priority_score or level != task.priority_level:
            task.priority_score = score
            task.priority_level = level
            changed = True
    if changed:
        db.commit()
