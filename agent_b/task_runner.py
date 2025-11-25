"""Task runner orchestrator that drives the agent step loop and coordinates state capture."""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from browser_use import BrowserProfile
from enum import Enum
from pydantic import BaseModel, Field

from .browser_agent import BrowserAgent
from .output_manager import OutputManager
from .state_capture import StateCapture, Step
from .tutorial_agent import TutorialAgent


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


class TaskRunner:
    """Orchestrates task execution, state capture, and dataset writing."""

    def __init__(
        self,
        task_instruction: str,
        browser: str = "arc",
        max_steps: int = 20,
        output_base_dir: Path = Path("outputs"),
    ):

        self.task_instruction = task_instruction
        self.max_steps = max_steps

        # Create browser profile
        # Get browser executable path
        executable_path = self._get_browser_executable(browser)
        
        import tempfile
        # Always create a temporary user data directory
        temp_user_data_dir = Path(tempfile.mkdtemp(prefix=f"{browser}-automation-"))
        user_data_dir = str(temp_user_data_dir)
        
        self.browser_profile = BrowserProfile(
            executable_path=executable_path,
            headless=False,
            user_data_dir=user_data_dir,
            args=[
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        # Initialize components
        self.agent_wrapper: Optional[BrowserAgent] = None
        self.state_capture: Optional[StateCapture] = None
        self.output_manager = OutputManager(base_output_dir=output_base_dir)
        self.task_run: Optional[TaskRun] = None
        self.task_dir: Optional[Path] = None
        self.steps: list[Step] = []

    def run(self) -> TaskRun:
        """Execute the task and return TaskRun metadata.

        Returns:
            TaskRun object with execution results
        """
        return asyncio.run(self._run_async())

    async def _run_async(self) -> TaskRun:
        """Internal async method that executes the task.

        Returns:
            TaskRun object with execution results
        """
        # Generate task ID and timestamp (human-readable format: YYYY-MM-DD_HH-MM)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        task_id = f"task_{timestamp}"

        # Create TaskRun
        self.task_run = TaskRun(
            task_id=task_id,
            task_instruction=self.task_instruction,
            status=TaskStatus.IN_PROGRESS,
            session_profile_path=str(self.browser_profile.user_data_dir) if self.browser_profile else None,
        )

        # Create task directory
        self.task_dir = self.output_manager.create_task_directory(timestamp)

        # Initialize state capture
        self.state_capture = StateCapture(self.task_dir)

        try:
            # Initialize agent (api_key will be loaded from env by BrowserAgent)
            self.agent_wrapper = BrowserAgent(
                task_instruction=self.task_instruction,
                browser_profile=self.browser_profile,
            )
            print("Initializing agent...")
            await self.agent_wrapper.initialize()
            print("Agent initialized")

            # Don't capture initial state yet - let the agent navigate first
            # The first step will handle getting to the right page
            print("Skipping initial state capture - agent will navigate first")

            # Step loop
            import time
            for step_num in range(1, self.max_steps + 1):
                print(f"\n{'='*80}")
                print(f"[Step {step_num}/{self.max_steps}] ===== STARTING STEP {step_num} =====")
                print(f"{'='*80}")
                step_start_time = time.time()
                
                try:
                    print(f"[Step {step_num}] [1/5] Executing agent.step()...")
                    step_call_start = time.time()
                    await self.agent_wrapper.step()
                    step_call_duration = time.time() - step_call_start
                    print(f"[Step {step_num}] [1/5] ✓ Agent step completed in {step_call_duration:.2f}s")
                except Exception as e:
                    step_call_duration = time.time() - step_call_start
                    print(f"[Step {step_num}] [1/5] ✗ ERROR after {step_call_duration:.2f}s: {e}")
                    import traceback
                    traceback.print_exc()
                    raise

                # Get current state after the step
                print(f"[Step {step_num}] [2/5] Getting browser state...")
                state_start_time = time.time()
                try:
                    current_state = await self.agent_wrapper.get_state()
                    state_duration = time.time() - state_start_time
                    print(f"[Step {step_num}] [2/5] ✓ State retrieved in {state_duration:.2f}s")
                    print(f"[Step {step_num}]     URL: {current_state.url}")
                    print(f"[Step {step_num}]     Title: {current_state.title}")
                    print(f"[Step {step_num}]     DOM elements: {len(current_state.dom_state.selector_map) if current_state.dom_state and current_state.dom_state.selector_map else 0}")
                except Exception as e:
                    state_duration = time.time() - state_start_time
                    print(f"[Step {step_num}] [2/5] ✗ ERROR after {state_duration:.2f}s: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue to next step even if state capture fails
                    continue

                # Get last action (pass current state for element descriptions)
                print(f"[Step {step_num}] [3/5] Extracting last action...")
                action_start_time = time.time()
                last_action = self.agent_wrapper.get_last_action(current_state)
                action_duration = time.time() - action_start_time
                if last_action:
                    print(f"[Step {step_num}] [3/5] ✓ Action extracted in {action_duration:.2f}s")
                    print(f"[Step {step_num}]     Type: {last_action.type.value}")
                    print(f"[Step {step_num}]     Description: {last_action.description}")
                else:
                    print(f"[Step {step_num}] [3/5] ⚠ No action extracted (duration: {action_duration:.2f}s)")

                # For the first step, always capture (this is our "initial" state after navigation)
                print(f"[Step {step_num}] [4/5] Checking if state should be captured...")
                should_capture = (step_num == 1) or self.state_capture.should_capture(
                    current_state, action=last_action
                )
                print(f"[Step {step_num}] [4/5] Should capture: {should_capture}")

                if should_capture:
                    # Generate state description
                    print(f"[Step {step_num}] [4/5] Generating state description...")
                    if step_num == 1:
                        state_desc = f"Initial state after navigation: {self.task_instruction}"
                    else:
                        state_desc = self._generate_state_description(
                            current_state, last_action, step_num
                        )
                    print(f"[Step {step_num}]     Description: {state_desc}")

                    # Capture step
                    print(f"[Step {step_num}] [4/5] Capturing step (screenshot + metadata)...")
                    capture_start_time = time.time()
                    step = self.state_capture.capture_step(
                        current_state,
                        action=last_action,
                        state_description=state_desc,
                    )
                    capture_duration = time.time() - capture_start_time
                    print(f"[Step {step_num}] [4/5] ✓ Step captured in {capture_duration:.2f}s")
                    
                    print(f"[Step {step_num}] [4/5] Saving step to disk...")
                    save_start_time = time.time()
                    self.steps.append(step)
                    self.output_manager.save_step(self.task_dir, step)
                    save_duration = time.time() - save_start_time
                    print(f"[Step {step_num}] [4/5] ✓ Step saved in {save_duration:.2f}s: {step.screenshot_path}")
                else:
                    print(f"[Step {step_num}] [4/5] ⏭ Skipping capture (doesn't meet criteria)")

                # Check if task is complete
                print(f"[Step {step_num}] [5/5] Checking if task is complete...")
                is_done = self.agent_wrapper.is_done()
                print(f"[Step {step_num}] [5/5] Task complete: {is_done}")
                
                if is_done:
                    print(f"[Step {step_num}] [5/5] ✓✓✓ TASK COMPLETE! ✓✓✓")
                    # Capture final success state
                    print(f"[Step {step_num}] Capturing final success state...")
                    final_state = await self.agent_wrapper.get_state()
                    if self.state_capture.should_capture(final_state, is_final=True):
                        final_step = self.state_capture.capture_step(
                            final_state,
                            action=self.agent_wrapper.get_last_action(),
                            state_description="Task completed successfully",
                        )
                        self.steps.append(final_step)
                        self.output_manager.save_step(self.task_dir, final_step)
                        print(f"[Step {step_num}] Final step captured: {final_step.screenshot_path}")

                    self.task_run.status = TaskStatus.SUCCESS
                    break
                
                step_total_duration = time.time() - step_start_time
                print(f"[Step {step_num}] ===== STEP {step_num} COMPLETE (total: {step_total_duration:.2f}s) =====")
                print(f"{'='*80}\n")

            # If we exhausted steps without success
            if self.task_run.status == TaskStatus.IN_PROGRESS:
                self.task_run.status = TaskStatus.TIMEOUT

        except Exception as e:
            self.task_run.status = TaskStatus.FAILURE
            raise
        finally:
            # Update task run metadata
            self.task_run.end_time = datetime.now()
            self.task_run.total_steps = len(self.steps)

            # Save task metadata
            self.output_manager.save_task_metadata(self.task_dir, self.task_run)

            # Generate tutorial with LLM (always enabled, api_key loaded from env)
            if self.steps:
                try:
                    print("Generating tutorial with LLM...")
                    tutorial_agent = TutorialAgent()  # Always load from environment
                    self.output_manager.generate_tutorial(
                        self.task_dir, self.task_run, self.steps, tutorial_agent=tutorial_agent, task_instruction=self.task_instruction
                    )
                    print("✓ Tutorial generated")
                except Exception as e:
                    print(f"Warning: LLM tutorial generation failed: {e}")
                    
            else:
                # No steps - skip tutorial generation
                print("No steps captured, skipping tutorial generation")

            # Clean up
            if self.agent_wrapper:
                await self.agent_wrapper.close()

        return self.task_run

    def _get_browser_executable(self, browser: str) -> str:
        """Get the executable path for the specified browser.

        Args:
            browser: Browser name ("arc", "chrome", "chromium", "safari")

        Returns:
            Path to browser executable

        Raises:
            ValueError: If browser is not supported or not found
        """
        browser_lower = browser.lower()
        
        # Browser executable paths (macOS)
        browser_paths = {
            "arc": "/Applications/Arc.app/Contents/MacOS/Arc",
            "chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "chromium": "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "safari": "/Applications/Safari.app/Contents/MacOS/Safari",
        }
        
        if browser_lower not in browser_paths:
            raise ValueError(
                f"Unsupported browser: {browser}. "
                f"Supported browsers: {', '.join(browser_paths.keys())}"
            )
        
        executable_path = browser_paths[browser_lower]
        
        # Check if browser exists
        from pathlib import Path
        if not Path(executable_path).exists():
            raise ValueError(
                f"Browser executable not found: {executable_path}. "
                f"Please ensure {browser.title()} is installed."
            )
        
        return executable_path

    def _generate_state_description(
        self,
        state,
        action,
        step_num: int,
    ) -> str:
        """Generate a human-readable description of the current state.

        Args:
            state: Current browser state
            action: Last action executed
            step_num: Current step number

        Returns:
            Description string
        """
        if action:
            return f"After {action.type.value}: {action.description}"
        return f"Step {step_num} - {state.title or state.url}"

    def get_output_directory(self) -> Optional[Path]:
        """Get the output directory for this task run."""
        return self.task_dir

