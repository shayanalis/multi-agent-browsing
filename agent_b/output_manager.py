"""Output manager for persisting TaskRun, Steps, and generating Markdown tutorials."""

import json
from pathlib import Path
from typing import List

from .models import TaskRun
from .state_capture import Step


class OutputManager:
    """Handles writing task runs, steps, and generating tutorials."""

    def __init__(self, base_output_dir: Path = Path("outputs")):
        """Initialize output manager.

        Args:
            base_output_dir: Base directory for all outputs
        """
        self.base_output_dir = base_output_dir
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

    def create_task_directory(self, timestamp: str) -> Path:
        """Create directory structure for a task run.

        Args:
            timestamp: Timestamp string for uniqueness

        Returns:
            Path to the created task directory
        """
        # Use timestamp for directory name
        task_dir = self.base_output_dir / timestamp
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir

    def save_task_metadata(self, task_dir: Path, task_run: TaskRun) -> Path:
        """Save task metadata JSON.

        Args:
            task_dir: Directory for this task run
            task_run: TaskRun object to save

        Returns:
            Path to saved metadata file
        """
        metadata_path = task_dir / "task_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(task_run.model_dump(mode="json"), f, indent=2, default=str)
        return metadata_path

    def save_step(self, task_dir: Path, step: Step) -> Path:
        """Save step JSON file.

        Args:
            task_dir: Directory for this task run
            step: Step object to save

        Returns:
            Path to saved step JSON file
        """
        step_filename = f"step_{step.step_index:03d}.json"
        step_path = task_dir / step_filename
        with open(step_path, "w") as f:
            json.dump(step.model_dump(mode="json"), f, indent=2, default=str)
        return step_path

    def generate_tutorial(
        self, 
        task_dir: Path, 
        task_run: TaskRun, 
        steps: List[Step],
        tutorial_agent=None,
        task_instruction: str = None
    ) -> Path:
        """Generate Markdown tutorial file using the tutorial enhancer.

        Args:
            task_dir: Directory for this task run
            task_run: TaskRun metadata
            steps: List of captured steps
            tutorial_agent: TutorialAgent instance (required for markdown generation)
            task_instruction: Original task instruction (optional, falls back to task_run.task_instruction)

        Returns:
            Path to generated tutorial file
        """
        tutorial_path = task_dir / "tutorial.md"
        instruction = task_instruction or task_run.task_instruction

        if tutorial_agent:
            markdown_content = tutorial_agent.generate_tutorial_markdown(
                task_run, steps, instruction
            )
        else:
            raise ValueError("Tutorial agent is required")

        # Write tutorial
        with open(tutorial_path, "w") as f:
            f.write(markdown_content)

        return tutorial_path

