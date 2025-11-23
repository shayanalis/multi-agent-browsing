"""UI State Capture Agent - Wraps browser-use Agent to capture screenshots of UI states."""

import asyncio
import logging
from pathlib import Path
from typing import Any

from browser_use import Agent, BrowserProfile
from browser_use.agent.views import AgentHistoryList
from browser_use.browser.views import BrowserStateSummary
from browser_use.llm.base import BaseChatModel

from screenshot_manager import ScreenshotManager
from ui_change_detector import UIChangeDetector

logger = logging.getLogger(__name__)


class UIStateCaptureAgent:
    """Wraps browser-use Agent to automatically capture UI state screenshots."""

    def __init__(
        self,
        task: str,
        llm: BaseChatModel | None = None,
        browser_profile: BrowserProfile | None = None,
        output_dir: Path | str = "outputs",
        app: str | None = None,
        **agent_kwargs,
    ):
        """Initialize the UI State Capture Agent.

        Args:
            task: The task/question to execute
            llm: Language model for browser-use Agent
            browser_profile: Browser profile configuration
            output_dir: Directory to save screenshots and metadata
            app: Application name (e.g., "Notion")
            **agent_kwargs: Additional arguments to pass to browser-use Agent
        """
        self.task = task
        self.app = app
        self.screenshot_manager = ScreenshotManager(output_dir=output_dir)
        self.ui_change_detector: UIChangeDetector | None = None
        self.agent: Agent | None = None
        self._last_action: str | None = None
        self._capture_in_progress = False
        self._task_finalized = False

        # Initialize browser-use Agent
        self.agent = Agent(
            task=task,
            llm=llm,
            browser_profile=browser_profile,
            register_new_step_callback=self._on_step_callback,
            register_done_callback=self._on_done_callback,
            **agent_kwargs,
        )

    async def _on_step_callback(
        self, browser_state: BrowserStateSummary, agent_output: Any, step_number: int
    ):
        """Callback called after each agent step."""
        try:
            # Extract action description from agent output
            action_desc = f"Step {step_number}"
            if agent_output:
                # Try to extract action information
                if hasattr(agent_output, "current_state"):
                    state = agent_output.current_state
                    if hasattr(state, "next_goal") and state.next_goal:
                        action_desc = state.next_goal[:100]
                    elif hasattr(state, "thinking") and state.thinking:
                        action_desc = state.thinking[:100]

            # Small delay to let UI settle after action
            await asyncio.sleep(0.3)

            # Capture screenshot after each step
            await self._capture_screenshot(
                browser_state=browser_state,
                action=action_desc,
                step_number=step_number,
            )
        except Exception as e:
            logger.error(f"Error in step callback: {e}")

    async def _on_done_callback(self, history: AgentHistoryList):
        """Callback called when agent completes."""
        # Don't finalize here - let the run() method handle it in the finally block
        # This prevents double finalization
        pass

    async def _capture_screenshot(
        self,
        browser_state: BrowserStateSummary,
        action: str,
        step_number: int,
    ):
        """Capture a screenshot of the current UI state."""
        if self._capture_in_progress or self._task_finalized:
            return

        self._capture_in_progress = True
        try:
            if not browser_state.screenshot:
                # Request screenshot if not included
                if self.agent and self.agent.browser_session:
                    browser_state = await self.agent.browser_session.get_browser_state_summary(
                        include_screenshot=True
                    )

            if browser_state.screenshot:
                # Determine UI state description
                ui_state = self._determine_ui_state(browser_state)

                # Save screenshot
                filename, step_metadata = self.screenshot_manager.save_screenshot(
                    screenshot_data=browser_state.screenshot,
                    action=action,
                    url=browser_state.url,
                    ui_state=ui_state,
                )

                logger.debug(
                    f"Captured screenshot: {filename} (step {step_number}, action: {action})"
                )
        except RuntimeError as e:
            # Ignore "No active task" errors if task is already finalized
            if "No active task" not in str(e) or not self._task_finalized:
                logger.error(f"Failed to capture screenshot: {e}")
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
        finally:
            self._capture_in_progress = False

    def _determine_ui_state(self, browser_state: BrowserStateSummary) -> str:
        """Determine the UI state description from browser state."""
        url = browser_state.url or ""

        # Simple heuristics for UI state
        if "modal" in url.lower() or "dialog" in url.lower():
            return "modal_open"
        elif "form" in url.lower():
            return "form_visible"
        elif browser_state.title:
            # Use page title as hint
            title_lower = browser_state.title.lower()
            if "create" in title_lower or "new" in title_lower:
                return "creation_flow"
            elif "edit" in title_lower or "update" in title_lower:
                return "edit_mode"
            elif "settings" in title_lower:
                return "settings_page"

        return "page_loaded"

    async def run(self, max_steps: int | None = None) -> Path:
        """Run the agent and capture UI states.

        Args:
            max_steps: Maximum number of steps to execute

        Returns:
            Path to the output directory with screenshots and metadata
        """
        # Start task in screenshot manager
        task_dir = self.screenshot_manager.start_task(
            task=self.task, app=self.app
        )
        logger.info(f"Starting task: {self.task}")
        logger.info(f"Output directory: {task_dir}")

        # Initialize UI change detector (will start after browser is ready)
        if self.agent and self.agent.browser_session:
            self.ui_change_detector = UIChangeDetector(
                browser_session=self.agent.browser_session,
                change_callback=self._on_ui_change,
            )

        final_task_dir = None
        try:
            # Run the agent
            # Screenshots will be captured via the step callback
            await self.agent.run(max_steps=max_steps)
            
            # Try to start UI change detector after first step (browser should be ready)
            if self.ui_change_detector and self.agent and self.agent.browser_session:
                try:
                    # Wait a bit for browser to be fully ready
                    await asyncio.sleep(2)
                    await self.ui_change_detector.start_monitoring()
                except Exception as e:
                    logger.debug(f"Could not start UI change detector (non-critical): {e}")
        finally:
            # Stop UI change detector
            if self.ui_change_detector:
                try:
                    await self.ui_change_detector.stop_monitoring()
                except Exception:
                    pass

            # Finalize task (only if not already finalized)
            if not self._task_finalized:
                try:
                    final_task_dir = self.screenshot_manager.finalize_task()
                    self._task_finalized = True
                    logger.info(f"Task completed. All screenshots saved to: {final_task_dir}")
                except RuntimeError as e:
                    if "No active task" in str(e):
                        logger.debug("Task already finalized")
                        final_task_dir = self.screenshot_manager.output_dir
                    else:
                        logger.error(f"Error finalizing task: {e}")
                        final_task_dir = self.screenshot_manager.output_dir
                except Exception as e:
                    logger.error(f"Error finalizing task: {e}")
                    final_task_dir = self.screenshot_manager.output_dir
            else:
                final_task_dir = self.screenshot_manager.output_dir

        return final_task_dir or self.screenshot_manager.output_dir

    async def _on_ui_change(self):
        """Callback when UI change is detected."""
        if self.agent and self.agent.browser_session and not self._capture_in_progress:
            try:
                browser_state = await self.agent.browser_session.get_browser_state_summary(
                    include_screenshot=True
                )
                await self._capture_screenshot(
                    browser_state=browser_state,
                    action="UI state changed",
                    step_number=0,  # Will be updated by step callback
                )
            except Exception as e:
                logger.debug(f"Could not capture screenshot on UI change: {e}")

