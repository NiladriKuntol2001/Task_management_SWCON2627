"""Pydantic request/response schemas, incl. input validation (FR-10, NFR-06, NFR-12)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
    id: str
    name: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


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
    owner_id: str
    title: str
    subject: str
    deadline: datetime
    difficulty: Difficulty
    estimated_hours: float
    completed: bool
    priority_score: float
    priority_level: PriorityLevel
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False

    model_config = ConfigDict(from_attributes=True)


class DashboardOut(BaseModel):
    incomplete_count: int
    completed_count: int
    high_priority_count: int  # High or Critical, incomplete
    upcoming_count: int  # incomplete, due within next 7 days
    overdue_count: int
    upcoming_tasks: list[TaskOut]
    recommended_task: TaskOut | None
