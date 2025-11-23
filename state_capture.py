"""State capture layer that decides when to capture UI states and builds Step objects."""

import base64
from datetime import datetime
from pathlib import Path
from typing import Optional

from browser_use.browser.views import BrowserStateSummary

from models import ActionFromPrevious, ActionType, Step


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
        # Always capture initial state
        if is_initial:
            return True

        # Always capture final/success state
        if is_final:
            return True

        # Capture if URL changed (new page loaded)
        url_changed = self.previous_url is not None and state.url != self.previous_url
        if url_changed:
            return True

        # Capture if modal/dialog detected
        if self._has_modal_or_dialog(state):
            return True

        # Capture after significant actions (clicks, form inputs)
        if action and action.type in [ActionType.CLICK, ActionType.TYPE]:
            return True

        # Capture after navigation
        if action and action.type == ActionType.NAVIGATE:
            return True

        # For v1, we capture states that meet the above criteria
        # No deduplication, but we don't capture every single state
        return False

    def _has_modal_or_dialog(self, state: BrowserStateSummary) -> bool:
        """Check if state contains a modal or dialog.

        Args:
            state: Browser state to check

        Returns:
            True if modal/dialog detected
        """
        if not state.dom_state or not state.dom_state.selector_map:
            return False

        # Check for dialog/modal roles in DOM
        # This is a simplified check - in practice, you'd parse the DOM more carefully
        dom_text = state.dom_state.llm_representation().lower()
        modal_indicators = ["role=dialog", "role=alertdialog", "modal", "dialog"]

        for indicator in modal_indicators:
            if indicator in dom_text:
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

