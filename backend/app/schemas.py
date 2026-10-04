"""Pydantic request/response schemas, incl. input validation (FR-10, NFR-06, NFR-12)."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationInfo, field_validator

from app.models import Difficulty, PriorityLevel

# ---------------------------------------------------------------------------
# Auth / users
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name must not be empty.")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int  # unique sequential user ID; the main admin is always 1
    name: str
    email: EmailStr
    is_admin: bool = False
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Profile (signed-in user changes their own email / password)
# ---------------------------------------------------------------------------


class EmailChange(BaseModel):
    new_email: EmailStr
    current_password: str = Field(min_length=1)  # re-confirm identity before changing login email


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str

    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("New password and confirmation do not match.")
        return v


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=120)
    deadline: datetime
    difficulty: Difficulty
    estimated_hours: float = Field(gt=0, le=1000)

    @field_validator("title", "subject")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field must not be empty.")
        return v.strip()


class TaskUpdate(BaseModel):
    """All fields optional: a client can PATCH just the fields it wants to change."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    subject: str | None = Field(default=None, min_length=1, max_length=120)
    deadline: datetime | None = None
    difficulty: Difficulty | None = None
    estimated_hours: float | None = Field(default=None, gt=0, le=1000)
    completed: bool | None = None

    @field_validator("title", "subject")
    @classmethod
    def not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("This field must not be empty.")
        return v.strip() if v is not None else v


class TaskOut(BaseModel):
    id: str
    owner_id: int
    title: str
    subject: str
    deadline: datetime
    difficulty: Difficulty
    estimated_hours: float
    completed: bool
    completed_at: datetime | None = None
    priority_score: float
    priority_level: PriorityLevel
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False

    model_config = ConfigDict(from_attributes=True)


class LabelCount(BaseModel):
    label: str
    count: int


class DashboardOut(BaseModel):
    incomplete_count: int
    completed_count: int
    high_priority_count: int  # High or Critical, incomplete
    upcoming_count: int  # incomplete, due within next 7 days
    overdue_count: int
    completion_rate: float  # 0-100, share of all tasks that are completed
    hours_due_this_week: float  # estimated hours of incomplete work due within 7 days (incl. overdue)
    priority_breakdown: list[LabelCount]  # incomplete tasks per level, Critical -> Low
    upcoming_tasks: list[TaskOut]
    overdue_tasks: list[TaskOut]
    priority_queue: list[TaskOut]  # next 5 incomplete tasks by priority, after the recommendation
    recommended_task: TaskOut | None


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


class AdminUserOut(UserOut):
    total_tasks: int = 0
    open_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0
    critical_open: int = 0
    last_activity: datetime | None = None


class AdminUserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Name must not be empty.")
        return v.strip() if v is not None else v


class AdminUserCreate(UserCreate):
    is_admin: bool = False


class AdminTaskOut(TaskOut):
    owner_name: str
    owner_email: str


class AdminUserDetail(BaseModel):
    user: AdminUserOut
    tasks: list[AdminTaskOut]


class AdminTaskPage(BaseModel):
    items: list[AdminTaskOut]
    total: int


class SubjectStat(BaseModel):
    subject: str
    open: int
    completed: int
    overdue: int


class DailyActivity(BaseModel):
    day: date
    created: int
    completed: int


class StudentAtRisk(BaseModel):
    user_id: int
    name: str
    email: str
    open: int
    overdue: int
    critical_open: int


class AdminStats(BaseModel):
    users_total: int
    students_total: int
    admins_total: int
    active_users: int
    new_users_7d: int
    students_with_overdue: int

    tasks_total: int
    tasks_open: int
    tasks_completed: int
    tasks_overdue: int
    critical_open: int
    completion_rate: float  # 0-100
    open_hours: float  # total estimated hours of incomplete work

    priority_distribution: list[LabelCount]  # open tasks, Low -> Critical
    difficulty_distribution: list[LabelCount]  # open tasks, Easy -> Very Hard
    deadline_pressure: list[LabelCount]  # open tasks by the spec's deadline bands
    subjects: list[SubjectStat]  # top subjects by task count
    daily_activity: list[DailyActivity]  # last 14 days, oldest first
    students_at_risk: list[StudentAtRisk]
    recent_tasks: list[AdminTaskOut]
