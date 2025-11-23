"""LLM-based tutorial enhancement using OpenAI SDK."""

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

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """Initialize the tutorial enhancer.

        Args:
            api_key: OpenAI API key (if None, loads from env)
            model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
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

    def enhance_step(
        self, step: Step, task_instruction: str, previous_steps: List[Step]
    ) -> dict:
        """Enhance a single step with LLM-generated instruction and context.

        Args:
            step: Step object to enhance
            task_instruction: Original task instruction
            previous_steps: List of previous steps for context

        Returns:
            Dictionary with 'enhanced_instruction' and 'context' keys
        """
        # Build context from previous steps (5-7 steps for better narrative flow)
        previous_context = ""
        if previous_steps:
            prev_descriptions = []
            # Use last 5-7 steps for better context
            context_steps = previous_steps[-7:] if len(previous_steps) >= 7 else previous_steps
            for prev_step in context_steps:
                if prev_step.action_from_previous:
                    # Include both action description and state description for context
                    step_info = f"Step {prev_step.step_index + 1}: {prev_step.action_from_previous.description}"
                    if prev_step.state_description:
                        step_info += f" (Result: {prev_step.state_description})"
                    prev_descriptions.append(step_info)
            if prev_descriptions:
                previous_context = "\n".join(prev_descriptions)

        # Build prompt
        action_info = ""
        if step.action_from_previous:
            action_info = f"""
Action Type: {step.action_from_previous.type.value}
Action Description: {step.action_from_previous.description}
"""
        else:
            action_info = "No action information available (this may be an initial state)."

        # Detect coordinate-based actions and flag them
        has_coordinates = False
        if step.action_from_previous and step.action_from_previous.description:
            desc_lower = step.action_from_previous.description.lower()
            # Check for coordinate patterns (e.g., "799, 728" or "at coordinates 799, 728")
            if re.search(r'\b\d{3,4}[,\s]+?\d{3,4}\b', step.action_from_previous.description) or \
               'coordinate' in desc_lower or 'at coordinates' in desc_lower:
                has_coordinates = True

        prompt = f"""You are creating a clear, step-by-step tutorial for a web automation task. Your goal is to write instructions that are tutorial-friendly, explaining both WHAT to do and WHY.

Overall Task Goal: {task_instruction}

Current Step Information:
- Step Number: {step.step_index + 1}
- URL: {step.url}
- State Description: {step.state_description}
{action_info}
- Has Unique URL: {step.has_unique_url}
{"⚠️ WARNING: The action description contains coordinates. You MUST convert this to a descriptive UI element name based on context." if has_coordinates else ""}

Previous Steps (for context and narrative flow):
{previous_context if previous_context else "This is one of the first steps in the tutorial."}

CRITICAL INSTRUCTIONS:
1. Generate a CLEAR, ACTIONABLE instruction (1-2 sentences max) that:
   - NEVER mentions coordinates (e.g., "at coordinates 799, 728") - ALWAYS describe the UI element instead
   - Explains the PURPOSE: Use phrases like "to create...", "in order to...", "which will..." to explain why
   - Uses descriptive element names: "the 'Create Database' button", "the sidebar menu", "the text field labeled 'Name'"
   - Includes location hints: "in the sidebar", "at the top right", "in the dropdown menu", "on the left panel"
   - Connects to previous steps: Reference what was accomplished (e.g., "Now that you've opened the database, click...")
   - Is beginner-friendly: Assume the user is new to the interface
   - If coordinates are mentioned, infer the UI element from context (button, link, field, etc.) and describe it

2. Generate a SPECIFIC context/expectation (1 sentence) that:
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

Format your response as JSON with two fields:
{{
    "instruction": "clear, tutorial-friendly instruction here",
    "context": "specific expectation with visual cues here"
}}

Only return the JSON, no other text."""

        try:
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
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return {
                "enhanced_instruction": result.get("instruction", ""),
                "context": result.get("context", ""),
            }
        except Exception as e:
            # Fallback if LLM call fails
            print(f"Warning: LLM enhancement failed for step {step.step_index}: {e}")
            return {
                "enhanced_instruction": None,
                "context": None,
            }

    def enhance_all_steps(self, steps: List[Step], task_instruction: str) -> List[Step]:
        """Enhance all steps with LLM-generated content.

        Args:
            steps: List of Step objects to enhance
            task_instruction: Original task instruction

        Returns:
            List of enhanced Step objects (with llm_enhanced_instruction and llm_context fields)
        """
        enhanced_steps = []
        sorted_steps = sorted(steps, key=lambda s: s.step_index)

        for i, step in enumerate(sorted_steps):
            previous_steps = sorted_steps[:i]
            enhancement = self.enhance_step(step, task_instruction, previous_steps)

            # Create updated step with LLM fields
            step_dict = step.model_dump()
            step_dict["llm_enhanced_instruction"] = enhancement.get("enhanced_instruction")
            step_dict["llm_context"] = enhancement.get("context")

            # Create new Step object with updated fields
            enhanced_step = Step(**step_dict)
            enhanced_steps.append(enhanced_step)

        return enhanced_steps

