"""Dataset writer for persisting TaskRun, Steps, and generating Markdown tutorials."""

import json
from pathlib import Path
from typing import List

from models import Step, TaskRun


class DatasetWriter:
    """Handles writing task runs, steps, and generating tutorials."""

    def __init__(self, base_output_dir: Path = Path("outputs")):
        """Initialize dataset writer.

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

    def generate_tutorial(self, task_dir: Path, task_run: TaskRun, steps: List[Step]) -> Path:
        """Generate Markdown tutorial file.

        Args:
            task_dir: Directory for this task run
            task_run: TaskRun metadata
            steps: List of captured steps

        Returns:
            Path to generated tutorial file
        """
        tutorial_path = task_dir / "tutorial.md"

        # Build tutorial content as instructions for Agent A
        lines = [
            f"# How to {task_run.task_instruction}",
            "",
            f"**Status:** {task_run.status.value}",
            f"**Total Steps:** {len(steps)}",
            "",
            "---",
            "",
            "## Instructions",
            "",
            "Follow these steps to complete the task:",
            "",
        ]

        # Track previous URL to infer actions
        previous_url = None
        previous_step = None
        
        # Add each step as an instruction
        for step in sorted(steps, key=lambda s: s.step_index):
            step_num = step.step_index + 1
            
            # Skip the first step if it's just "initial state"
            if step_num == 1 and "initial state" in step.state_description.lower():
                previous_url = step.url
                previous_step = step
                continue
            
            lines.append(f"### Step {step_num}")
            lines.append("")
            
            # Generate instruction based on available information
            instruction = None
            
            # First priority: Use LLM-enhanced instruction if available
            if step.llm_enhanced_instruction:
                instruction = step.llm_enhanced_instruction
            # Second priority: Use action description
            elif step.action_from_previous and step.action_from_previous.description:
                instruction = step.action_from_previous.description
                # Clean up generic descriptions
                if instruction.lower() in ["execute action", "executed action", "interact with the page"]:
                    instruction = None
                # Clean up "After other:" prefixes
                if instruction and "after other:" in instruction.lower():
                    instruction = None
            
            # If no good action description, infer from context
            if not instruction or instruction.lower() in ["execute action", "executed action"]:
                # Infer from URL change
                if previous_url and step.url != previous_url:
                    from urllib.parse import urlparse
                    prev_domain = urlparse(previous_url).netloc.replace("www.", "")
                    curr_domain = urlparse(step.url).netloc.replace("www.", "")
                    if prev_domain != curr_domain:
                        instruction = f"Navigate to {curr_domain}"
                    else:
                        # Same domain, likely clicked a link
                        # Extract page name from URL if possible
                        path_parts = urlparse(step.url).path.strip("/").split("/")
                        if len(path_parts) > 0 and path_parts[-1]:
                            # Remove UUID-like suffixes (long hex strings)
                            page_name = path_parts[-1]
                            # Check if it ends with a UUID pattern (32+ char hex)
                            import re
                            uuid_pattern = r'-[a-f0-9]{32,}$'
                            if re.search(uuid_pattern, page_name, re.IGNORECASE):
                                # Remove UUID suffix
                                page_name = re.sub(uuid_pattern, '', page_name, flags=re.IGNORECASE)
                            
                            # Clean up the page name
                            page_name = page_name.replace("-", " ").title()
                            # Remove any remaining hex-like parts
                            words = page_name.split()
                            # Filter out words that look like hex IDs (long alphanumeric)
                            words = [w for w in words if not (len(w) > 20 and all(c in '0123456789abcdefABCDEF' for c in w))]
                            page_name = " ".join(words)
                            
                            if page_name:
                                instruction = f"Click on '{page_name}'"
                            else:
                                instruction = "Click on a link to navigate"
                        else:
                            instruction = "Click on a link to navigate"
                elif previous_step and not step.has_unique_url:
                    # Same URL, likely an interaction (click, type, etc.)
                    if step.action_from_previous:
                        if step.action_from_previous.type == "click":
                            instruction = "Click on an element"
                        elif step.action_from_previous.type == "type":
                            instruction = "Type text into a field"
                        elif step.action_from_previous.type == "scroll":
                            instruction = "Scroll the page"
                        else:
                            instruction = "Interact with the page"
                    else:
                        instruction = "Interact with the page"
                else:
                    # Use state description if available
                    if step.state_description and "initial" not in step.state_description.lower():
                        instruction = step.state_description
                    else:
                        instruction = "Navigate to the page"
            
            # Make it more instruction-like
            if instruction:
                if not instruction[0].isupper():
                    instruction = instruction[0].upper() + instruction[1:]
                # Remove "After other:" prefix if present
                instruction = instruction.replace("After other: ", "").replace("After click: ", "").replace("After type: ", "")
                lines.append(instruction)
            else:
                lines.append("Navigate to the page")
            
            lines.append("")
            
            # Add screenshot
            screenshot_rel = step.screenshot_path
            lines.append(f"![Step {step_num}]({screenshot_rel})")
            lines.append("")
            
            # Add context - prefer LLM context if available, otherwise use URL-based context
            if step.llm_context:
                lines.append(f"*{step.llm_context}*")
            else:
                # Fallback to URL-based context
                from urllib.parse import urlparse
                import re
                parsed = urlparse(step.url)
                domain = parsed.netloc.replace("www.", "")
                path_info = ""
                if parsed.path and parsed.path != "/":
                    path_parts = parsed.path.strip("/").split("/")
                    if len(path_parts) > 0:
                        page_name = path_parts[-1]
                        # Remove UUID-like suffixes
                        uuid_pattern = r'-[a-f0-9]{32,}$'
                        if re.search(uuid_pattern, page_name, re.IGNORECASE):
                            page_name = re.sub(uuid_pattern, '', page_name, flags=re.IGNORECASE)
                        page_name = page_name.replace("-", " ").title()
                        # Clean up hex IDs
                        words = page_name.split()
                        words = [w for w in words if not (len(w) > 20 and all(c in '0123456789abcdefABCDEF' for c in w))]
                        page_name = " ".join(words)
                        if page_name:
                            path_info = f" - {page_name}"
                
                if path_info:
                    lines.append(f"*You should now be on {domain}{path_info}*")
                else:
                    lines.append(f"*You should now be on {domain}*")
            lines.append("")
            lines.append("---")
            lines.append("")
            
            # Update for next iteration
            previous_url = step.url
            previous_step = step

        # Write tutorial
        with open(tutorial_path, "w") as f:
            f.write("\n".join(lines))

        return tutorial_path

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a string for use as a filename.

        Args:
            filename: Original filename string

        Returns:
            Sanitized filename safe for filesystem
        """
        # Replace spaces and special characters
        sanitized = filename.lower().replace(" ", "_")
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")
        # Remove multiple underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        return sanitized

