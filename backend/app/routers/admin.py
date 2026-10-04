"""Admin panel API: platform analytics, user management, and management of
every student's tasks. Every route requires an administrator (require_admin).

This deliberately sits outside FR-21's per-user scoping: FR-21/NFR-05 govern
what *students* can see; admins are a separate, explicitly privileged role.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_admin
from app.models import ROOT_ADMIN_ID, Difficulty, PriorityLevel, Task, User
from app.routers.tasks import apply_task_update
from app.schemas import (
    AdminStats,
    AdminTaskOut,
    AdminTaskPage,
    AdminUserCreate,
    AdminUserDetail,
    AdminUserOut,
    AdminUserUpdate,
    DailyActivity,
    LabelCount,
    StudentAtRisk,
    SubjectStat,
    TaskOut,
    TaskUpdate,
)
from app.security import hash_password, verify_password
from app.task_service import (
    as_utc,
    deadline_sort_key,
    is_overdue,
    priority_sort_key,
    refresh_priorities,
    to_out,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

LEVELS_LOW_TO_HIGH = [PriorityLevel.LOW, PriorityLevel.MEDIUM, PriorityLevel.HIGH, PriorityLevel.CRITICAL]
DIFFICULTIES = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD, Difficulty.VERY_HARD]
# Same bands as the spec's Deadline Score table (Section 3), most urgent first.
DEADLINE_BANDS = ["Overdue", "< 24 hours", "1-2 days", "3-6 days", "7-14 days", "> 14 days"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _deadline_band(deadline: datetime, now: datetime) -> str:
    hours = (as_utc(deadline) - now).total_seconds() / 3600
    days = hours / 24
    if hours < 0:
        return "Overdue"
    if hours < 24:
        return "< 24 hours"
    if days <= 2:
        return "1-2 days"
    if days <= 6:
        return "3-6 days"
    if days <= 14:
        return "7-14 days"
    return "> 14 days"


def _admin_task_out(task: Task) -> AdminTaskOut:
    base: TaskOut = to_out(task)
    return AdminTaskOut(
        **base.model_dump(),
        owner_name=task.owner.name,
        owner_email=task.owner.email,
    )


def _user_stats(user: User, tasks: list[Task], now: datetime) -> AdminUserOut:
    open_tasks = [t for t in tasks if not t.completed]
    activity = [as_utc(t.updated_at) for t in tasks if t.updated_at is not None]
    return AdminUserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at,
        total_tasks=len(tasks),
        open_tasks=len(open_tasks),
        completed_tasks=len(tasks) - len(open_tasks),
        overdue_tasks=sum(1 for t in open_tasks if is_overdue(t, now)),
        critical_open=sum(1 for t in open_tasks if t.priority_level == PriorityLevel.CRITICAL),
        last_activity=max(activity) if activity else None,
    )


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


def _get_task_or_404(db: Session, task_id: str) -> Task:
    task = db.query(Task).options(joinedload(Task.owner)).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


def _active_admin_count(db: Session) -> int:
    return db.query(func.count(User.id)).filter(User.is_admin.is_(True), User.is_active.is_(True)).scalar()


# ---------------------------------------------------------------------------
# analytics
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=AdminStats)
def platform_stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    users = db.query(User).all()
    tasks = db.query(Task).options(joinedload(Task.owner)).all()
    refresh_priorities(db, tasks)

    open_tasks = [t for t in tasks if not t.completed]
    done_tasks = [t for t in tasks if t.completed]
    overdue = [t for t in open_tasks if is_overdue(t, now)]

    tasks_by_owner: dict[int, list[Task]] = defaultdict(list)
    for t in tasks:
        tasks_by_owner[t.owner_id].append(t)

    students = [u for u in users if not u.is_admin]

    # Subjects: top 8 by total volume.
    subj: dict[str, dict[str, int]] = defaultdict(lambda: {"open": 0, "completed": 0, "overdue": 0})
    for t in tasks:
        row = subj[t.subject]
        if t.completed:
            row["completed"] += 1
        else:
            row["open"] += 1
            if is_overdue(t, now):
                row["overdue"] += 1
    subjects = sorted(subj.items(), key=lambda kv: -(kv[1]["open"] + kv[1]["completed"]))[:8]

    # Daily created vs completed, last 14 days (UTC days), oldest first.
    today = now.date()
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    created_by_day: dict = defaultdict(int)
    completed_by_day: dict = defaultdict(int)
    for t in tasks:
        created_by_day[as_utc(t.created_at).date()] += 1
        if t.completed_at is not None:
            completed_by_day[as_utc(t.completed_at).date()] += 1

    # Students at risk: most overdue, then most critical open work.
    at_risk = []
    for u in students:
        s = _user_stats(u, tasks_by_owner.get(u.id, []), now)
        if s.overdue_tasks or s.critical_open:
            at_risk.append(
                StudentAtRisk(
                    user_id=u.id,
                    name=u.name,
                    email=u.email,
                    open=s.open_tasks,
                    overdue=s.overdue_tasks,
                    critical_open=s.critical_open,
                )
            )
    at_risk.sort(key=lambda r: (-r.overdue, -r.critical_open, -r.open))

    band_counts = defaultdict(int)
    for t in open_tasks:
        band_counts[_deadline_band(t.deadline, now)] += 1

    recent = sorted(tasks, key=lambda t: as_utc(t.created_at), reverse=True)[:8]

    return AdminStats(
        users_total=len(users),
        students_total=len(students),
        admins_total=len(users) - len(students),
        active_users=sum(1 for u in users if u.is_active),
        new_users_7d=sum(1 for u in users if as_utc(u.created_at) >= now - timedelta(days=7)),
        students_with_overdue=len({t.owner_id for t in overdue if not t.owner.is_admin}),
        tasks_total=len(tasks),
        tasks_open=len(open_tasks),
        tasks_completed=len(done_tasks),
        tasks_overdue=len(overdue),
        critical_open=sum(1 for t in open_tasks if t.priority_level == PriorityLevel.CRITICAL),
        completion_rate=round(100 * len(done_tasks) / len(tasks), 1) if tasks else 0.0,
        open_hours=round(sum(t.estimated_hours for t in open_tasks), 2),
        priority_distribution=[
            LabelCount(label=lvl.value, count=sum(1 for t in open_tasks if t.priority_level == lvl))
            for lvl in LEVELS_LOW_TO_HIGH
        ],
        difficulty_distribution=[
            LabelCount(label=d.value, count=sum(1 for t in open_tasks if t.difficulty == d))
            for d in DIFFICULTIES
        ],
        deadline_pressure=[LabelCount(label=b, count=band_counts[b]) for b in DEADLINE_BANDS],
        subjects=[SubjectStat(subject=name, **counts) for name, counts in subjects],
        daily_activity=[
            DailyActivity(day=d, created=created_by_day[d], completed=completed_by_day[d]) for d in days
        ],
        students_at_risk=at_risk[:8],
        recent_tasks=[_admin_task_out(t) for t in recent],
    )


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, description="Matches name or email, or an exact user ID"),
    role: Literal["all", "admin", "student"] = "all",
    status_filter: Literal["all", "active", "inactive"] = Query(default="all", alias="status"),
    sort_by: Literal["name", "created", "open", "overdue"] = "created",
):
    now = datetime.now(timezone.utc)
    query = db.query(User)
    if search:
        term = search.strip().lstrip("#")
        if term.isdigit():
            # A number (or "#3") means "user ID 3" exactly — not every email containing a 3.
            query = query.filter(User.id == int(term))
        else:
            like = f"%{term}%"
            query = query.filter(or_(User.name.ilike(like), User.email.ilike(like)))
    if role != "all":
        query = query.filter(User.is_admin.is_(role == "admin"))
    if status_filter != "all":
        query = query.filter(User.is_active.is_(status_filter == "active"))
    users = query.all()

    ids = [u.id for u in users]
    tasks = db.query(Task).filter(Task.owner_id.in_(ids)).all() if ids else []
    refresh_priorities(db, tasks)
    by_owner: dict[int, list[Task]] = defaultdict(list)
    for t in tasks:
        by_owner[t.owner_id].append(t)

    rows = [_user_stats(u, by_owner.get(u.id, []), now) for u in users]
    sorters = {
        "name": lambda r: r.name.lower(),
        "created": lambda r: -as_utc(r.created_at).timestamp(),
        "open": lambda r: -r.open_tasks,
        "overdue": lambda r: (-r.overdue_tasks, -r.open_tasks),
    }
    rows.sort(key=sorters[sort_by])
    return rows


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: AdminUserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_stats(user, [], datetime.now(timezone.utc))


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = _get_user_or_404(db, user_id)
    tasks = db.query(Task).options(joinedload(Task.owner)).filter(Task.owner_id == user.id).all()
    refresh_priorities(db, tasks)
    tasks.sort(key=lambda t: (t.completed, priority_sort_key(t)))
    return AdminUserDetail(
        user=_user_stats(user, tasks, datetime.now(timezone.utc)),
        tasks=[_admin_task_out(t) for t in tasks],
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)
    data = payload.model_dump(exclude_unset=True)

    if user.id == ROOT_ADMIN_ID:
        # The main administrator (ID 1) has a fixed email, is always an active
        # admin, and changes their password only from their own profile page.
        if "email" in data and data["email"].lower() != user.email.lower():
            raise HTTPException(status_code=403, detail="The main administrator's email (user ID 1) can't be changed.")
        if data.get("is_admin") is False or data.get("is_active") is False:
            raise HTTPException(status_code=403, detail="The main administrator (user ID 1) must stay an active admin.")
        if "password" in data:
            raise HTTPException(
                status_code=403,
                detail="The main administrator's password can only be changed from their own profile page.",
            )

    if user.id == admin.id:
        if data.get("is_admin") is False:
            raise HTTPException(status_code=400, detail="You can't remove your own admin access.")
        if data.get("is_active") is False:
            raise HTTPException(status_code=400, detail="You can't deactivate your own account.")

    losing_admin = user.is_admin and user.is_active and (
        data.get("is_admin") is False or data.get("is_active") is False
    )
    if losing_admin and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="There must always be at least one active admin.")

    if "email" in data and data["email"] != user.email:
        clash = db.query(User).filter(User.email == data["email"], User.id != user.id).first()
        if clash:
            raise HTTPException(status_code=409, detail="Another account already uses this email.")

    if "password" in data:
        new_password = data.pop("password")
        if verify_password(new_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="The new password must be different from the user's current password.")
        user.hashed_password = hash_password(new_password)
    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    tasks = db.query(Task).filter(Task.owner_id == user.id).all()
    return _user_stats(user, tasks, datetime.now(timezone.utc))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)
    if user.id == ROOT_ADMIN_ID:
        raise HTTPException(status_code=403, detail="The main administrator (user ID 1) can't be deleted.")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You can't delete your own account.")
    if user.is_admin and user.is_active and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="There must always be at least one active admin.")
    db.delete(user)  # tasks are removed via the relationship's delete-orphan cascade
    db.commit()
    return None


# ---------------------------------------------------------------------------
# tasks (all users)
# ---------------------------------------------------------------------------


@router.get("/tasks", response_model=AdminTaskPage)
def list_all_tasks(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, description="Matches title, subject, student name or email"),
    owner_id: int | None = None,
    subject: str | None = None,
    completed: bool | None = None,
    priority_level: PriorityLevel | None = None,
    overdue_only: bool = False,
    sort_by: Literal["priority", "deadline", "created"] = "priority",
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    query = db.query(Task).join(User, Task.owner_id == User.id).options(joinedload(Task.owner))
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(Task.title.ilike(like), Task.subject.ilike(like), User.name.ilike(like), User.email.ilike(like))
        )
    if owner_id is not None:
        query = query.filter(Task.owner_id == owner_id)
    if subject:
        query = query.filter(Task.subject == subject)
    if completed is not None:
        query = query.filter(Task.completed.is_(completed))

    tasks = query.all()
    refresh_priorities(db, tasks)

    if priority_level is not None:
        tasks = [t for t in tasks if t.priority_level == priority_level]
    if overdue_only:
        tasks = [t for t in tasks if is_overdue(t)]

    if sort_by == "priority":
        tasks.sort(key=priority_sort_key)
    elif sort_by == "deadline":
        tasks.sort(key=deadline_sort_key)
    else:
        tasks.sort(key=lambda t: as_utc(t.created_at), reverse=True)

    page = tasks[offset : offset + limit]
    return AdminTaskPage(items=[_admin_task_out(t) for t in page], total=len(tasks))


@router.get("/subjects", response_model=list[str])
def list_all_subjects(db: Session = Depends(get_db)):
    rows = db.query(Task.subject).distinct().all()
    return sorted(r[0] for r in rows)


@router.patch("/tasks/{task_id}", response_model=AdminTaskOut)
def admin_update_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, task_id)
    return _admin_task_out(apply_task_update(db, task, payload))


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_task(task_id: str, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, task_id)
    db.delete(task)
    db.commit()
    return None
