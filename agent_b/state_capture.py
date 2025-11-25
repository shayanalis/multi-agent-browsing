"""State capture layer that decides when to capture UI states and builds Step objects."""

import base64
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from browser_use.browser.views import BrowserStateSummary
from pydantic import BaseModel, Field

from .browser_agent import ActionFromPrevious, ActionType


# Models
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


class StateCapture:
    """Handles decision logic for when to capture UI states and builds Step objects."""

    def __init__(self, output_dir: Path):
        """Initialize state capture.

        Args:
            output_dir: Directory where screenshots and step files will be saved
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.step_index = 0
        self.previous_url: Optional[str] = None

    def should_capture(
        self,
        state: BrowserStateSummary,
        is_initial: bool = False,
        is_final: bool = False,
        action: Optional[ActionFromPrevious] = None,
    ) -> bool:
        """Determine if this state should be captured as a step.

        Args:
            state: Current browser state
            is_initial: Whether this is the initial state (always capture)
            is_final: Whether this is the final/success state (always capture)
            action: Action that led to this state

        Returns:
            True if state should be captured, False otherwise
        """
        # Always capture initial and final states
        if is_initial or is_final:
            return True

        # Capture if URL changed (new page loaded)
        if self.previous_url is not None and state.url != self.previous_url:
            return True

        # Capture after significant actions (clicks, form inputs, navigation)
        if action and action.type in [ActionType.CLICK, ActionType.TYPE, ActionType.NAVIGATE]:
            return True

        return False

    def capture_step(
        self,
        state: BrowserStateSummary,
        action: Optional[ActionFromPrevious] = None,
        state_description: str = "",
    ) -> Step:
        """Capture a UI state as a Step.

        Args:
            state: Browser state to capture
            action: Action that led to this state
            state_description: Human-readable description of this state

        Returns:
            Step object with metadata
        """
        # Determine if URL is unique
        has_unique_url = state.url != self.previous_url if self.previous_url else True

        # Save screenshot
        screenshot_path = self._save_screenshot(state, self.step_index)

        # Build Step object
        step = Step(
            step_index=self.step_index,
            screenshot_path=str(screenshot_path.relative_to(self.output_dir)),
            url=state.url,
            has_unique_url=has_unique_url,
            action_from_previous=action,
            state_description=state_description or f"Step {self.step_index}",
            timestamp=datetime.now(),
        )

        # Update for next step
        self.previous_url = state.url
        self.step_index += 1

        return step

    def _save_screenshot(self, state: BrowserStateSummary, step_index: int) -> Path:
        """Save screenshot from browser state to disk.

        Args:
            state: Browser state containing screenshot
            step_index: Step number for filename

        Returns:
            Path to saved screenshot file
        """
        if not state.screenshot:
            raise ValueError(f"No screenshot in browser state for step {step_index}")

        # Decode base64 screenshot
        screenshot_data = base64.b64decode(state.screenshot)

        # Save as PNG
        screenshot_path = self.output_dir / f"step_{step_index:03d}.png"
        screenshot_path.write_bytes(screenshot_data)

        return screenshot_path

    def get_step_index(self) -> int:
        """Get the current step index."""
        return self.step_index

