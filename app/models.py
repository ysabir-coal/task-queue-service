"""Pydantic models for task queue service."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskPriority(int, Enum):
    LOW = 1
    MEDIUM = 5
    HIGH = 10
    CRITICAL = 20


class CreateTaskRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    callback_url: Optional[str] = None
    max_retries: Optional[int] = None
    timeout_seconds: Optional[int] = None


class TaskResponse(BaseModel):
    task_id: str
    name: str
    status: TaskStatus
    priority: TaskPriority
    payload: dict[str, Any]
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int
