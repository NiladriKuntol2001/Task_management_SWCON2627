"""Task CRUD, validation, filtering and sorting (FR-04..FR-18, FR-21)."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Task, User
from app.priority import compute_priority
from app.schemas import TaskCreate, TaskOut, TaskUpdate
from app.task_service import (
    as_utc,
    deadline_sort_key,
    is_overdue,
    priority_sort_key,
    refresh_priorities,
    to_out,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_owned_task_or_404(db: Session, task_id: str, user: User) -> Task:
    """FR-21/NFR-05: a task is only ever fetched scoped to its owner, so a
    task belonging to another user is indistinguishable from a nonexistent one."""
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user.id).first()
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
    return to_out(task)


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
    refresh_priorities(db, tasks)

    if overdue_only:
        tasks = [t for t in tasks if is_overdue(t)]  # FR-18

    tasks.sort(key=priority_sort_key if sort_by == "priority" else deadline_sort_key)  # FR-16/FR-14
    return [to_out(t) for t in tasks]


@router.get("/subjects", response_model=list[str])
def list_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All distinct subjects for the current user (feeds the subject filter,
    independent of whichever filter is currently applied)."""
    rows = db.query(Task.subject).filter(Task.owner_id == current_user.id).distinct().all()
    return sorted(r[0] for r in rows)


@router.get("/upcoming", response_model=list[TaskOut])
def upcoming_deadlines(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """FR-17: incomplete tasks due within the next `days` days (overdue tasks
    included, since they still need attention)."""
    horizon = datetime.now(timezone.utc) + timedelta(days=days)
    tasks = (
        db.query(Task)
        .filter(Task.owner_id == current_user.id, Task.completed.is_(False))
        .all()
    )
    refresh_priorities(db, tasks)
    upcoming = sorted([t for t in tasks if as_utc(t.deadline) <= horizon], key=deadline_sort_key)
    return [to_out(t) for t in upcoming]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task_or_404(db, task_id, current_user)  # FR-09
    refresh_priorities(db, [task])
    return to_out(task)


def apply_task_update(db: Session, task: Task, payload: TaskUpdate) -> Task:
    """Shared by the student and admin edit endpoints."""
    data = payload.model_dump(exclude_unset=True)
    was_completed = task.completed
    for field, value in data.items():
        setattr(task, field, value)

    if "completed" in data:
        if task.completed and not was_completed:
            task.completed_at = datetime.now(timezone.utc)
        elif not task.completed:
            task.completed_at = None

    # FR-13: recalculate priority whenever deadline, difficulty or estimated hours change.
    if {"deadline", "difficulty", "estimated_hours"} & data.keys():
        score, level = compute_priority(task.deadline, task.difficulty, task.estimated_hours)
        task.priority_score = score
        task.priority_level = level

    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task_or_404(db, task_id, current_user)  # FR-06
    return to_out(apply_task_update(db, task, payload))


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_task_or_404(db, task_id, current_user)  # FR-08
    if not task.completed:
        task.completed = True
        task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return to_out(task)


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
