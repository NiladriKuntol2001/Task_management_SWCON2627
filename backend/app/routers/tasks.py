"""Task CRUD, validation, filtering and sorting (FR-04..FR-18, FR-21)."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Difficulty, PriorityLevel, Task, User
from app.priority import compute_priority
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _is_overdue(task: Task, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    deadline = task.deadline if task.deadline.tzinfo else task.deadline.replace(tzinfo=timezone.utc)
    return (not task.completed) and deadline < now


def _to_out(task: Task) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.is_overdue = _is_overdue(task)
    return out


def _get_owned_task_or_404(db: Session, task_id: str, user: User) -> Task:
    """FR-21/NFR-05: a task is only ever fetched scoped to its owner, so a
    task belonging to another user is indistinguishable from a nonexistent one."""
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.owner_id == user.id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    score, level = compute_priority(payload.deadline, payload.difficulty, payload.estimated_hours)
    task = Task(
        owner_id=current_user.id,
        title=payload.title,
        subject=payload.subject,
        deadline=payload.deadline,
        difficulty=payload.difficulty,
        estimated_hours=payload.estimated_hours,
        priority_score=score,
        priority_level=level,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _to_out(task)


@router.get("", response_model=list[TaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    subject: str | None = Query(default=None, description="Filter by exact subject"),
    completed: bool | None = Query(default=None, description="Filter by completion status"),
    overdue_only: bool = Query(default=False, description="Only return overdue, incomplete tasks"),
    sort_by: Literal["priority", "deadline"] = Query(default="priority"),
):
    query = db.query(Task).filter(Task.owner_id == current_user.id)  # FR-21

    if subject:
        query = query.filter(Task.subject == subject)  # FR-15
    if completed is not None:
        query = query.filter(Task.completed == completed)  # FR-15

    tasks = query.all()

    if overdue_only:
        tasks = [t for t in tasks if _is_overdue(t)]  # FR-18

    # FR-16 sort, FR-14 tie-break: for priority sort, ties broken by earlier deadline first.
    if sort_by == "priority":
        tasks.sort(key=lambda t: (-t.priority_score, t.deadline))
    else:
        tasks.sort(key=lambda t: t.deadline)

    return [_to_out(t) for t in tasks]


@router.get("/upcoming", response_model=list[TaskOut])
def upcoming_deadlines(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """FR-17: incomplete tasks due within the next `days` days (overdue tasks included,
    since they still need attention)."""
    now = datetime.now(timezone.utc)
    horizon = now.replace(hour=23, minute=59, second=59) + timedelta(days=days)

    tasks = (
        db.query(Task)
        .filter(Task.owner_id == current_user.id, Task.completed.is_(False))
        .all()
    )
    upcoming = [t for t in tasks if t.deadline <= horizon]
    upcoming.sort(key=lambda t: t.deadline)
    return [_to_out(t) for t in upcoming]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task_or_404(db, task_id, current_user)  # FR-09
    return _to_out(task)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task_or_404(db, task_id, current_user)  # FR-06

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(task, field, value)

    # FR-13: recalculate priority whenever deadline, difficulty or estimated hours change.
    if {"deadline", "difficulty", "estimated_hours"} & data.keys():
        score, level = compute_priority(task.deadline, task.difficulty, task.estimated_hours)
        task.priority_score = score
        task.priority_level = level

    db.commit()
    db.refresh(task)
    return _to_out(task)


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task_or_404(db, task_id, current_user)  # FR-08
    task.completed = True
    db.commit()
    db.refresh(task)
    return _to_out(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task_or_404(db, task_id, current_user)  # FR-07
    db.delete(task)
    db.commit()
    return None
