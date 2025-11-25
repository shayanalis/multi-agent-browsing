"""Shared models for Agent B."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task run."""

    SUCCESS = "success"
    TIMEOUT = "timeout"
    FAILURE = "failure"
    IN_PROGRESS = "in_progress"


class TaskRun(BaseModel):
    """Metadata for a complete task run."""

    task_id: str = Field(description="Unique identifier for this task run")
    task_instruction: str = Field(description="Natural language task description")
    status: TaskStatus = Field(default=TaskStatus.IN_PROGRESS, description="Current status of the task")
    start_time: datetime = Field(default_factory=datetime.now, description="When the task started")
    end_time: Optional[datetime] = Field(default=None, description="When the task completed")
    total_steps: int = Field(default=0, description="Total number of steps captured")
    session_profile_path: Optional[str] = Field(
        default=None, description="Path to browser profile used for authenticated session"
    )

