"""Data models for the UI state capture agent system."""

from datetime import datetime
from enum import Enum
from pathlib import Path
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


class ActionType(str, Enum):
    """Type of action executed."""

    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    SCROLL = "scroll"
    WAIT = "wait"
    OTHER = "other"


class ActionFromPrevious(BaseModel):
    """Information about the action that led to this state."""

    type: ActionType = Field(description="Type of action executed")
    description: str = Field(description="Natural language description of the action")
    element_index: Optional[int] = Field(default=None, description="Index of element interacted with")


class Step(BaseModel):
    """Metadata for a single captured UI state."""

    step_index: int = Field(description="Zero-indexed step number")
    screenshot_path: str = Field(description="Relative path to screenshot PNG file")
    url: str = Field(description="URL of the page when screenshot was taken")
    has_unique_url: bool = Field(
        description="Whether this state has a unique URL (False for modals, dropdowns, etc.)"
    )
    action_from_previous: Optional[ActionFromPrevious] = Field(
        default=None, description="Action that led to this state"
    )
    state_description: str = Field(
        default="", description="Description of what this screen represents"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="When this step was captured")
    llm_enhanced_instruction: Optional[str] = Field(
        default=None, description="LLM-generated clear, actionable instruction for this step"
    )
    llm_context: Optional[str] = Field(
        default=None, description="LLM-generated context about what the user should see/expect"
    )

