"""Wrapper around browser-use Agent for clean interface to state and actions."""

import asyncio
import os
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from browser_use import Agent, BrowserProfile, ChatBrowserUse
from browser_use.browser.views import BrowserStateSummary
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# Models
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


# OpenAI prompt for task instruction conversion
TASK_CONVERSION_PROMPT = """You are a task instruction converter. Your job is to convert user questions or requests into CONCISE, high-level instructions that a browser automation agent can follow efficiently.

Keep instructions SIMPLE and MINIMAL. The agent should take FEWER steps, not more.

Convert questions like "how can I create a notion database?" into simple instructions like:
1. Go to notion.so
2. Create a new page
3. Make it into a database


The instructions should be:
- VERY concise (3-5 steps maximum for most tasks)
- High-level (don't specify clicks, just the actions)
- Actionable for a browser automation agent
- Include specific websites/URLs when relevant

When converting a user request:
- Express the **core task** in the FEWEST possible steps
- Include **relevant URLs** (e.g., "Go to https://www.notion.so")
- Don't create steps to configure or do things that are not part of the core task.
- Use **semantic actions** that combine multiple clicks:
  - *Create a new database* (not "click New, click Database, click Empty")
  - *Fill in the form* (not "type in field 1, type in field 2")
- Return **only the converted instructions** (no explanations or additional text)
"""


class BrowserAgent:
    """Thin wrapper around browser-use Agent providing clean interface."""

    def __init__(
        self,
        task_instruction: str,
        browser_profile: Optional[BrowserProfile] = None,
    ):
        """Initialize the browser agent wrapper.

        Args:
            task_instruction: Natural language task description
            browser_profile: BrowserProfile for authenticated sessions
            api_key: Browser-use API key (if None, loads from env)
        """
        self.task_instruction = task_instruction
        self.browser_profile = browser_profile
        
        # Load API keys from environment
        load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Set it in .env file."
            )

        self.openai_model = OpenAI(api_key=openai_api_key)

        browser_use_api_key = os.getenv("BROWSER_USE_API_KEY")
        if not browser_use_api_key:
            raise ValueError(
                "BROWSER_USE_API_KEY not found in environment. "
                "Set it in .env file or pass as browser_use_api_key parameter."
            )

        # Initialize LLM and Agent
        self.llm = ChatBrowserUse(api_key=browser_use_api_key)
        self.agent: Optional[Agent] = None
        self._last_action_result = None
        self._last_extracted_content = None

    async def initialize(self) -> None:
        """Initialize the browser agent and start the browser session."""
        if self.agent is not None:
            return

        # Convert task into concise instructions
        response = self.openai_model.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": TASK_CONVERSION_PROMPT},
                {
                    "role": "user",
                    "content": f"Convert this task into concise, minimal instructions (3-5 steps max): {self.task_instruction}"
                },
            ],
        )
        
        converted_instruction = response.choices[0].message.content.strip()
        efficiency_directive = "\n\nIMPORTANT: Complete this task in the MINIMUM number of steps. Be direct and efficient - combine related actions and skip unnecessary intermediate steps."
        final_instruction = converted_instruction + efficiency_directive
        print(f"Final instruction: {final_instruction}")
        
        self.original_task_instruction = self.task_instruction
        self.converted_task_instruction = final_instruction

        self.agent = Agent(
            task=final_instruction,
            llm=self.llm,
            browser_profile=self.browser_profile,
        )

        if self.agent.browser_session:
            await self.agent.browser_session.start()
            await self.agent.browser_session.attach_all_watchdogs()
            self.agent.state.session_initialized = True
            await asyncio.sleep(1)

    async def get_state(self) -> BrowserStateSummary:
        """Get the current browser state with screenshot.

        Returns:
            BrowserStateSummary containing DOM, screenshot, URL, etc.
        """
        if self.agent is None or self.agent.browser_session is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        return await self.agent.browser_session.get_browser_state_summary(
            include_screenshot=True,
            include_recent_events=False,
        )

    async def step(self) -> None:
        """Execute one step of the agent (plan and act)."""
        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        try:
            await self.agent.step()
        except Exception as e:
            traceback.print_exc()
            raise

        # Store last action result for state capture
        self._last_action_result = self.agent.state.last_result
        if self._last_action_result and len(self._last_action_result) > 0:
            last_result = self._last_action_result[-1]
            self._last_extracted_content = getattr(last_result, 'extracted_content', None)
        else:
            self._last_extracted_content = None

    def get_last_action(self, browser_state=None) -> Optional[ActionFromPrevious]:
        """Extract basic action info (type + minimal description).
        
        Since the LLM tutorial enhancer will rewrite descriptions anyway,
        we only need enough info for state capture decisions.
        """
        # Try extracted content first
        if self._last_extracted_content:
            action_type = self._detect_type_from_text(self._last_extracted_content)
            if action_type:
                return ActionFromPrevious(
                    type=action_type,
                    description=self._last_extracted_content[:100],
                    element_index=None
                )

        # Fall back to model output
        if not self.agent or not self.agent.state.last_model_output:
            return None

        model_output = self.agent.state.last_model_output
        actions = getattr(model_output, 'action', None) or []
        if not actions:
            return None

        # Detect type from first action
        action = actions[0]
        action_type = self._detect_type_from_action(action)
        
        # Minimal description - LLM will enhance it later
        desc = getattr(action, "description", None) or getattr(action, "reasoning", None)
        if not desc:
            desc = f"{action_type.value} action"
        
        return ActionFromPrevious(
            type=action_type,
            description=desc[:100],
            element_index=getattr(action, "index", None)
        )

    def _detect_type_from_text(self, text: str) -> Optional[ActionType]:
        """Detect action type from text description."""
        text_lower = text.lower()
        if "click" in text_lower:
            return ActionType.CLICK
        elif "type" in text_lower or "input" in text_lower:
            return ActionType.TYPE
        elif "navigate" in text_lower or "goto" in text_lower:
            return ActionType.NAVIGATE
        elif "scroll" in text_lower:
            return ActionType.SCROLL
        return None

    def _detect_type_from_action(self, action) -> ActionType:
        """Detect action type from action object."""
        # Check model fields first
        if hasattr(action, 'model_fields'):
            fields = action.model_fields.keys()
            if 'index' in fields and 'coordinate_x' in fields:
                return ActionType.CLICK
            elif 'text' in fields and 'index' in fields:
                return ActionType.TYPE
            elif 'url' in fields:
                return ActionType.NAVIGATE
            elif 'down' in fields and 'pages' in fields:
                return ActionType.SCROLL
        
        # Fall back to class name
        class_name = type(action).__name__.lower()
        if "click" in class_name:
            return ActionType.CLICK
        elif "type" in class_name or "input" in class_name:
            return ActionType.TYPE
        elif "navigate" in class_name or "goto" in class_name:
            return ActionType.NAVIGATE
        elif "scroll" in class_name:
            return ActionType.SCROLL
        
        return ActionType.OTHER

    def is_done(self) -> bool:
        """Check if the agent has completed the task.

        Returns:
            True if task is complete, False otherwise
        """
        if self.agent is None:
            return False

        # Check if agent marked itself as done
        if self.agent.state.last_result:
            for result in self.agent.state.last_result:
                if result.is_done:
                    return True

        return False

    async def close(self) -> None:
        """Clean up and close the browser session."""
        if self.agent and self.agent.browser_session:
            await self.agent.browser_session.close()
        self.agent = None
        self._last_action_result = None

