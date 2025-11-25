"""Tutorial agent that generates markdown tutorials using OpenAI LLM."""

import json
import os
import re
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from .state_capture import Step


class TutorialAgent:
    """Generates complete markdown tutorials from captured steps using LLM."""

    def __init__(self, model: str = "gpt-5", timeout: int = 60):
        """Initialize the tutorial agent.

        Args:
            model: OpenAI model to use (default: "gpt-4o-mini" for speed, "gpt-4o" or "gpt-5" for quality)
            timeout: Timeout in seconds for API calls (default: 60)
        """
        # Load API key from environment
        load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Set it in .env file or pass as api_key parameter."
            )

        self.client = OpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self.timeout = timeout

    def generate_tutorial_markdown(self, task_run, steps: List[Step], task_instruction: str) -> str:
        """Generate complete markdown tutorial using LLM in a single call.

        Args:
            task_run: TaskRun metadata
            steps: List of Step objects (raw steps, will be enhanced by LLM)
            task_instruction: Original task instruction

        Returns:
            Complete markdown tutorial as a string
        """
        if not steps:
            return f"# How to {task_instruction}\n\nNo steps captured."

        # Sort steps by index
        sorted_steps = sorted(steps, key=lambda s: s.step_index)
        steps_to_include = []
        
        for step in sorted_steps:
            # Skip initial state (step 0) if it's just navigation
            if step.step_index == 0 and "initial state" in step.state_description.lower():
                continue
            
            # Include all other steps - even if URL is the same (modals, forms, etc. don't have unique URLs)
            steps_to_include.append(step)

        # Build step data for LLM (raw step info)
        steps_data = []
        for step in steps_to_include:
            step_info = {
                "step_number": step.step_index + 1,
                "screenshot_path": step.screenshot_path,
                "url": step.url,
                "state_description": step.state_description,
                "has_unique_url": step.has_unique_url,
            }
            
            if step.action_from_previous:
                step_info["action_type"] = step.action_from_previous.type.value
                step_info["action_description"] = step.action_from_previous.description
                
                # Check for coordinates
                desc_lower = step.action_from_previous.description.lower()
                if re.search(r'\b\d{3,4}[,\s]+?\d{3,4}\b', step.action_from_previous.description) or \
                   'coordinate' in desc_lower or 'at coordinates' in desc_lower:
                    step_info["has_coordinates"] = True
            else:
                step_info["action_type"] = None
                step_info["action_description"] = None
            
            steps_data.append(step_info)
            print(f"{steps_data}")

        prompt = f"""Generate a complete, well-formatted Markdown tutorial document for the following task.

Task: {task_instruction}

Raw steps captured during execution:
{json.dumps(steps_data, indent=2)}

CRITICAL INSTRUCTIONS:
- NEVER mention coordinates - ALWAYS describe UI elements by name, label, or location
- Create clear, actionable instructions that explain WHAT to do and WHY
- Use descriptive element names: "the 'Create Database' button", "the sidebar menu", "the text field labeled 'Name'"
- Include location hints: "in the sidebar", "at the top right", "in the dropdown menu"
- Connect steps narratively to show progress toward the goal
- Make expectations specific with visual cues

Create a professional tutorial markdown document that:
1. Has a clear, descriptive title
2. Includes a brief introduction explaining what the tutorial will teach
3. Lists EACH AND EVERY step in order (do not skip or combine steps):
   - Number each step sequentially (Step 1, Step 2, Step 3, etc.)
   - Include the screenshot image reference for EVERY step (use: ![Step X](screenshot_path))
   - Write clear, actionable instructions (describe UI elements, not coordinates)
   - Add helpful context about what the user should see/expect
4. Has a conclusion or summary
5. Uses proper Markdown formatting (headers, lists, emphasis, etc.)
6. Is beginner-friendly and easy to follow

CRITICAL: You MUST include ALL {len(steps_to_include)} steps with their screenshots. Do not skip any steps or combine them. Each step should have its own section with its screenshot.

Return ONLY the markdown content, no explanations or code blocks."""

        try:
            import time
            start_time = time.time()
            print(f"  Generating tutorial markdown (using {self.model})...", end="", flush=True)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical writer who creates clear, professional tutorial documentation. Always respond with valid Markdown only, no code blocks or explanations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                timeout=self.timeout,
            )
            
            elapsed = time.time() - start_time
            markdown_content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if markdown_content.startswith("```markdown"):
                markdown_content = markdown_content[11:]
            if markdown_content.startswith("```"):
                markdown_content = markdown_content[3:]
            if markdown_content.endswith("```"):
                markdown_content = markdown_content[:-3]
            
            print(f" ({elapsed:.1f}s) ✓")
            return markdown_content.strip()
            
        except Exception as e:
            print(f" ✗ Error: {e}")

