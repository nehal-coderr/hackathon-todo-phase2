# Task ID: T012 - Task SQLModel per data-model.md
"""Task model with SQLModel for database operations."""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class TaskBase(SQLModel):
    """Base task attributes for create/update."""

    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None)


class Task(TaskBase, table=True):
    """Task database model.

    Per clarification session 2026-01-02:
    - Task IDs are auto-increment integers (not UUIDs)
    - user_id derived exclusively from JWT token
    """

    __tablename__ = "task"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(nullable=False, index=True)  # UUID string from JWT
    is_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskCreate(TaskBase):
    """Schema for task creation.

    Per FR-010: title required (1-200 chars), description optional.
    """

    pass


class TaskUpdate(SQLModel):
    """Schema for task update (all fields optional).

    Per FR-013: Allow updating title, description, or completion status.
    """

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_completed: Optional[bool] = None


class TaskRead(TaskBase):
    """Schema for task response.

    Per FR-019: Do not expose user_id in API responses.
    """

    id: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime
