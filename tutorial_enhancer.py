import json
import os
import re
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from models import Step


class TutorialEnhancer:
    """Enhances tutorial steps using OpenAI LLM to generate clear, actionable instructions."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5"):
        """Initialize the tutorial enhancer.

        Args:
            api_key: OpenAI API key (if None, loads from env)
            model: OpenAI model to use (default: "gpt-4o-mini" for speed, "gpt-4o" for quality)
        """
        # Load API key from environment if not provided
        if api_key is None:
            load_dotenv(dotenv_path=Path(__file__).parent / ".env")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not found in environment. "
                    "Set it in .env file or pass as api_key parameter."
                )

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def enhance_all_steps(self, steps: List[Step], task_instruction: str) -> List[Step]:
        """Enhance all steps with LLM-generated content in a single batch call.

        Args:
            steps: List of Step objects to enhance
            task_instruction: Original task instruction

        Returns:
            List of enhanced Step objects (with llm_enhanced_instruction and llm_context fields)
        """
        if not steps:
            return steps

        # Sort steps by step_index to ensure correct order
        sorted_steps = sorted(steps, key=lambda s: s.step_index)
        
        print(f"  Enhancing {len(sorted_steps)} steps in one batch...", end="", flush=True)
        
        try:
            # Build prompt with all steps
            steps_data = []
            for step in sorted_steps:
                step_info = {
                    "step_number": step.step_index + 1,
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
            
            prompt = f"""You are creating a clear, step-by-step tutorial for a web automation task. Your goal is to write instructions that are tutorial-friendly, explaining both WHAT to do and WHY.

Overall Task Goal: {task_instruction}

Here are all the steps that were captured during the task execution:

{json.dumps(steps_data, indent=2)}

CRITICAL INSTRUCTIONS:
For EACH step, generate:
1. A CLEAR, ACTIONABLE instruction (1-2 sentences max) that:
   - NEVER mentions coordinates - ALWAYS describe the UI element instead
   - Explains the PURPOSE: Use phrases like "to create...", "in order to...", "which will..." to explain why
   - Uses descriptive element names: "the 'Create Database' button", "the sidebar menu", "the text field labeled 'Name'"
   - Includes location hints: "in the sidebar", "at the top right", "in the dropdown menu", "on the left panel"
   - Connects to previous steps: Reference what was accomplished (e.g., "Now that you've opened the database, click...")
   - Is beginner-friendly: Assume the user is new to the interface
   - If coordinates are mentioned, infer the UI element from context (button, link, field, etc.) and describe it

2. A SPECIFIC context/expectation (1 sentence) that:
   - Describes exactly what appears or changes (not just "you should see")
   - Includes visual cues: "a new dialog box", "the database interface", "a confirmation message"
   - References progress toward the goal: "You're now one step closer to creating your database"
   - Is specific: Instead of "you should see something", say "you should see a blank database page with column headers"

Examples of GOOD instructions:
- "Click on the 'New Database' button in the left sidebar to start creating your database."
- "In the text field labeled 'Database Name', type 'My Projects' to name your new database."
- "Select 'Empty database' from the template options to create a blank database from scratch."

Examples of BAD instructions (DO NOT DO THIS):
- "Click on the area at coordinates 799, 728" ❌
- "Click on the button" ❌ (too vague)
- "Execute the action" ❌ (generic)
- "Interact with the page" ❌ (not helpful)

Return a JSON object with a "steps" array. Each element should have:
- "step_number": the step number (1-indexed)
- "instruction": "clear, tutorial-friendly instruction here"
- "context": "specific expectation with visual cues here"

Format:
{{
    "steps": [
        {{
            "step_number": 1,
            "instruction": "...",
            "context": "..."
        }},
        {{
            "step_number": 2,
            "instruction": "...",
            "context": "..."
        }}
    ]
}}

Only return the JSON, no other text."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert technical writer specializing in creating clear, tutorial-friendly step-by-step guides for web automation tasks.

Your expertise includes:
- Converting technical actions into beginner-friendly instructions
- Explaining the purpose and context of each step
- Describing UI elements clearly without using coordinates
- Creating narrative flow between steps
- Writing expectations that help users verify they're on the right track

CRITICAL RULES:
1. NEVER use coordinates - always describe UI elements by name, label, or location
2. ALWAYS explain WHY each step is needed (purpose)
3. Connect steps narratively to show progress toward the goal
4. Use specific, descriptive language for UI elements
5. Make expectations specific with visual cues

Always respond with valid JSON only.""",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            enhanced_steps_data = result.get("steps", [])
            
            # Create a mapping of step_number to enhancement
            enhancement_map = {
                item["step_number"]: {
                    "instruction": item.get("instruction", ""),
                    "context": item.get("context", ""),
                }
                for item in enhanced_steps_data
            }
            
            # Apply enhancements to steps
            enhanced_steps = []
            for step in sorted_steps:
                step_num = step.step_index + 1
                enhancement = enhancement_map.get(step_num, {"instruction": None, "context": None})
                
                # Create updated step with LLM fields
                step_dict = step.model_dump()
                step_dict["llm_enhanced_instruction"] = enhancement.get("instruction")
                step_dict["llm_context"] = enhancement.get("context")
                
                # Create new Step object with updated fields
                enhanced_step = Step(**step_dict)
                enhanced_steps.append(enhanced_step)
            
            print(" ✓")
            return enhanced_steps
            
        except Exception as e:
            # Fallback if LLM call fails
            print(f" ✗ Error: {e}")
            print("  Continuing with original steps (no enhancement)...")
            # Return steps without enhancement
            return sorted_steps
