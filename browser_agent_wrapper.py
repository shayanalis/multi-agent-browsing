"""Wrapper around browser-use Agent for clean interface to state and actions."""

import os
from pathlib import Path
from typing import Optional

from browser_use import Agent, BrowserProfile, ChatBrowserUse
from browser_use.browser.views import BrowserStateSummary
from dotenv import load_dotenv
from openai import OpenAI

from models import ActionFromPrevious, ActionType


class BrowserAgentWrapper:
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
        
        # Load OpenAI API key from environment
        load_dotenv(dotenv_path=Path(__file__).parent / ".env")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Set it in .env file."
            )

        self.openai_model = OpenAI(api_key=openai_api_key)

        # Load API key from environment if not provided
        load_dotenv(dotenv_path=Path(__file__).parent / ".env")
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

        # Convert the question/task into detailed high-level instructions
        print("Converting task into detailed instructions...")
        response = self.openai_model.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a task instruction converter. Your job is to convert user questions or requests into clear, step-by-step instructions that a browser automation agent can follow.

Convert questions like "how can I create a notion database?" into detailed instructions like:
"Navigate to notion.so, create a new database, configure the database structure, and save it."

The instructions should be:
- High-level and clear
- Actionable for a browser automation agent
- Suitable for creating a tutorial
- Include specific websites/URLs when relevant
- Be concise but complete

Return only the converted instructions, no additional explanation."""
                },
                {
                    "role": "user",
                    "content": f"Convert this task into detailed instructions: {self.task_instruction}"
                },
            ],
            temperature=0.3,
        )
        
        # Extract the converted instruction
        converted_instruction = response.choices[0].message.content.strip()
        print(f"Converted instruction: {converted_instruction}")
        
        # Store the original and converted instructions
        self.original_task_instruction = self.task_instruction
        self.converted_task_instruction = converted_instruction

        # Use the converted instruction for the agent
        self.agent = Agent(
            task=converted_instruction,
            llm=self.llm,
            browser_profile=self.browser_profile,
        )

        # Start the browser session (normally done in Agent.run(), but we're using step() directly)
        if self.agent.browser_session:
            print("Starting browser session...")
            await self.agent.browser_session.start()
            print("Browser session started, attaching watchdogs...")
            # Attach watchdogs (normally done in Agent.run())
            await self.agent.browser_session.attach_all_watchdogs()
            print("Watchdogs attached")
            
            # Skip event dispatch - it might cause hangs and agent.step() will handle what it needs
            # Just mark as initialized so we don't try again
            self.agent.state.session_initialized = True
            print("Session initialized")
            
            # Wait a bit for browser to be ready
            import asyncio
            await asyncio.sleep(1)
            print("Browser ready")

    async def get_state(self) -> BrowserStateSummary:
        """Get the current browser state with screenshot.

        Returns:
            BrowserStateSummary containing DOM, screenshot, URL, etc.
        """
        import time
        print(f"  [State] Getting browser state...")
        state_start = time.time()
        
        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        if self.agent.browser_session is None:
            raise RuntimeError("Browser session not initialized. Call initialize() first.")

        # Get browser state with screenshot
        print(f"  [State] Calling get_browser_state_summary...")
        summary_start = time.time()
        state = await self.agent.browser_session.get_browser_state_summary(
            include_screenshot=True,
            include_recent_events=False,
        )
        summary_duration = time.time() - summary_start
        state_duration = time.time() - state_start
        
        print(f"  [State] State retrieved in {state_duration:.2f}s (summary call: {summary_duration:.2f}s)")
        print(f"  [State] State details: URL={state.url}, title={state.title}")
        print(f"  [State] Screenshot: {'present' if state.screenshot else 'missing'}, DOM elements: {len(state.dom_state.selector_map) if state.dom_state and state.dom_state.selector_map else 0}")
        
        return state

    async def step(self) -> None:
        """Execute one step of the agent (plan and act).

        This calls Agent.step() which:
        1. Gets browser state
        2. Plans next action(s) via LLM
        3. Executes action(s)
        4. Updates agent state
        """
        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        import time
        print(f"  [Agent] Calling agent.step() (current step: {self.agent.state.n_steps})...")
        step_start = time.time()
        try:
            await self.agent.step()
            step_duration = time.time() - step_start
            print(f"  [Agent] Step completed in {step_duration:.2f}s")
            
            if self.agent.state.last_result:
                print(f"  [Agent] Last result: {len(self.agent.state.last_result)} result(s)")
                for i, result in enumerate(self.agent.state.last_result):
                    print(f"    Result {i}: is_done={result.is_done}, success={result.success}")
                    if hasattr(result, 'extracted_content') and result.extracted_content:
                        print(f"      Extracted content: {result.extracted_content}")
                    if hasattr(result, 'error') and result.error:
                        print(f"      Error: {result.error}")
            else:
                print(f"  [Agent] No last_result available")
                
            if self.agent.state.last_model_output:
                action_count = len(self.agent.state.last_model_output.action) if self.agent.state.last_model_output.action else 0
                print(f"  [Agent] Model output: {action_count} action(s)")
                if self.agent.state.last_model_output.action:
                    for i, action in enumerate(self.agent.state.last_model_output.action):
                        action_type = type(action).__name__
                        print(f"    Action {i}: {action_type}")
                        # Print action attributes
                        if hasattr(action, 'index'):
                            print(f"      Index: {action.index}")
                        if hasattr(action, 'text'):
                            print(f"      Text: {action.text}")
                        if hasattr(action, 'url'):
                            print(f"      URL: {action.url}")
            else:
                print(f"  [Agent] No last_model_output available")
        except Exception as e:
            step_duration = time.time() - step_start
            print(f"  [Agent] ERROR in agent.step() after {step_duration:.2f}s: {e}")
            import traceback
            traceback.print_exc()
            raise

        # Store last action result for state capture
        if self.agent.state.last_result:
            self._last_action_result = self.agent.state.last_result
            print(f"  [Agent] Stored last_action_result: {len(self._last_action_result)} result(s)")
            # Also store the extracted content which has better descriptions
            if self.agent.state.last_result and len(self.agent.state.last_result) > 0:
                last_result = self.agent.state.last_result[-1]
                if hasattr(last_result, 'extracted_content') and last_result.extracted_content:
                    self._last_extracted_content = last_result.extracted_content
                    print(f"  [Agent] Stored extracted_content: {self._last_extracted_content}")
                else:
                    self._last_extracted_content = None
                    print(f"  [Agent] No extracted_content in last result")
            else:
                self._last_extracted_content = None
        else:
            print(f"  [Agent] No last_result to store")

    def get_last_action(self, browser_state=None) -> Optional[ActionFromPrevious]:
        """Extract information about the last executed action.

        Returns:
            ActionFromPrevious if action was executed, None otherwise
        """
        import time
        action_start = time.time()
        print(f"  [Action] Starting get_last_action()...")
        
        # First, try to use extracted_content from ActionResult - it has the best descriptions
        print(f"  [Action] Checking _last_action_result...")
        if self._last_action_result and len(self._last_action_result) > 0:
            print(f"  [Action] Found {len(self._last_action_result)} result(s)")
            last_result = self._last_action_result[-1]
            print(f"  [Action] Checking extracted_content in last_result...")
            if hasattr(last_result, 'extracted_content') and last_result.extracted_content:
                extracted = last_result.extracted_content
                print(f"  [Action] Found extracted_content: {extracted}")
                # Parse extracted_content for better action description
                # Examples: "Clicked a role=link 'Career Goals'", "Typed 'text' into field", etc.
                import re
                if "Clicked" in extracted or "clicked" in extracted:
                    print(f"  [Action] Parsing click action...")
                    # Extract the element description from "Clicked a role=link 'Career Goals'"
                    # Try to extract quoted text
                    match = re.search(r"['\"]([^'\"]+)['\"]", extracted)
                    if match:
                        element_name = match.group(1)
                        print(f"  [Action] Extracted element name: {element_name}")
                        result = ActionFromPrevious(
                            type=ActionType.CLICK,
                            description=f"Click on '{element_name}'",
                            element_index=None,
                        )
                        print(f"  [Action] Returning click action in {time.time() - action_start:.2f}s")
                        return result
                    else:
                        # Clean up the extracted content
                        desc = extracted.replace("Clicked a ", "").replace("clicked a ", "")
                        print(f"  [Action] Using cleaned description: {desc}")
                        result = ActionFromPrevious(
                            type=ActionType.CLICK,
                            description=desc,
                            element_index=None,
                        )
                        print(f"  [Action] Returning click action in {time.time() - action_start:.2f}s")
                        return result
                elif "Typed" in extracted or "typed" in extracted:
                    print(f"  [Action] Parsing type action...")
                    # Extract what was typed
                    match = re.search(r"['\"]([^'\"]+)['\"]", extracted)
                    if match:
                        typed_text = match.group(1)
                        print(f"  [Action] Extracted typed text: {typed_text}")
                        result = ActionFromPrevious(
                            type=ActionType.TYPE,
                            description=f"Type '{typed_text}'",
                            element_index=None,
                        )
                        print(f"  [Action] Returning type action in {time.time() - action_start:.2f}s")
                        return result
                    else:
                        print(f"  [Action] Using extracted content as-is: {extracted}")
                        result = ActionFromPrevious(
                            type=ActionType.TYPE,
                            description=extracted,
                            element_index=None,
                        )
                        print(f"  [Action] Returning type action in {time.time() - action_start:.2f}s")
                        return result
                elif "Navigated" in extracted or "navigated" in extracted:
                    print(f"  [Action] Parsing navigate action...")
                    result = ActionFromPrevious(
                        type=ActionType.NAVIGATE,
                        description=extracted,
                        element_index=None,
                    )
                    print(f"  [Action] Returning navigate action in {time.time() - action_start:.2f}s")
                    return result
                elif "Searched" in extracted or "searched" in extracted:
                    print(f"  [Action] Parsing search action...")
                    match = re.search(r"['\"]([^'\"]+)['\"]", extracted)
                    if match:
                        query = match.group(1)
                        print(f"  [Action] Extracted search query: {query}")
                        result = ActionFromPrevious(
                            type=ActionType.OTHER,
                            description=f"Search for '{query}'",
                            element_index=None,
                        )
                        print(f"  [Action] Returning search action in {time.time() - action_start:.2f}s")
                        return result
                    else:
                        result = ActionFromPrevious(
                            type=ActionType.OTHER,
                            description=extracted,
                            element_index=None,
                        )
                        print(f"  [Action] Returning search action in {time.time() - action_start:.2f}s")
                        return result
            else:
                print(f"  [Action] No extracted_content found")

        print(f"  [Action] Checking agent and model_output...")
        if not self.agent or not self.agent.state.last_model_output:
            print(f"  [Action] No agent or last_model_output, returning None")
            return None

        # Get the last model output which contains the actions
        print(f"  [Action] Getting model_output...")
        model_output = self.agent.state.last_model_output
        if not model_output.action or len(model_output.action) == 0:
            print(f"  [Action] No actions in model_output, returning None")
            return None

        # Get all actions from the last step
        print(f"  [Action] Processing {len(model_output.action)} action(s)...")
        actions = model_output.action
        if not actions or len(actions) == 0:
            print(f"  [Action] Actions list is empty, returning None")
            return None

        # Try to get reasoning/thinking from model output for better descriptions
        print(f"  [Action] Extracting reasoning...")
        reasoning = None
        if hasattr(model_output, 'thinking') and model_output.thinking:
            reasoning = model_output.thinking
            print(f"  [Action] Found thinking: {reasoning[:100] if len(reasoning) > 100 else reasoning}")
        elif hasattr(model_output, 'reasoning') and model_output.reasoning:
            reasoning = model_output.reasoning
            print(f"  [Action] Found reasoning: {reasoning[:100] if len(reasoning) > 100 else reasoning}")
        elif hasattr(model_output, 'next_goal') and model_output.next_goal:
            reasoning = model_output.next_goal
            print(f"  [Action] Found next_goal: {reasoning[:100] if len(reasoning) > 100 else reasoning}")

        # Use provided browser_state or try to get from agent
        print(f"  [Action] Checking browser_state...")
        if browser_state is None:
            try:
                if self.agent.browser_session:
                    # Get the most recent browser state from agent history if available
                    if hasattr(self.agent, 'state') and hasattr(self.agent.state, 'last_browser_state'):
                        browser_state = self.agent.state.last_browser_state
                        print(f"  [Action] Got browser_state from agent.state")
            except Exception as e:
                print(f"  [Action] Error getting browser_state: {e}")
                pass
        else:
            print(f"  [Action] Using provided browser_state")

        # Combine all actions into a single description
        print(f"  [Action] Processing {len(actions)} action(s) to build description...")
        action_descriptions = []
        action_type = ActionType.OTHER
        element_index = None

        for i, action in enumerate(actions):
            print(f"  [Action] Processing action {i}/{len(actions)-1}...")
            # Get the actual class name
            action_class_name = type(action).__name__
            action_str = action_class_name.lower()
            
            # Check model_fields to determine actual action type
            action_type_name = None
            if hasattr(action, 'model_fields'):
                # Check what fields this action has to determine type
                fields = action.model_fields.keys()
                print(f"  [Action] Action fields: {list(fields)}")
                if 'index' in fields and 'coordinate_x' in fields:
                    action_type_name = 'click'
                elif 'text' in fields and 'index' in fields and 'clear' in fields:
                    action_type_name = 'input'
                elif 'url' in fields:
                    action_type_name = 'navigate'
                elif 'down' in fields and 'pages' in fields:
                    action_type_name = 'scroll'
                elif 'query' in fields and 'engine' in fields:
                    action_type_name = 'search'
                elif 'query' in fields and 'extract_links' in fields:
                    action_type_name = 'extract'
            
            print(f"  [Action] Action class: {action_class_name}, inferred type: {action_type_name}")
            
            # Extract action details based on type
            if action_type_name == 'click' or "click" in action_str or "ClickElement" in action_class_name:
                action_type = ActionType.CLICK
                # Get element index
                idx = getattr(action, "index", None)
                if idx is not None:
                    element_index = idx
                    # Try to get element description from browser state (with timeout protection)
                    print(f"  [Action] Attempting to get element description for index {idx}...")
                    try:
                        element_desc = self._get_element_description(idx, browser_state)
                        if element_desc:
                            print(f"  [Action] Found element description: {element_desc}")
                            action_descriptions.append(f"Click on '{element_desc}'")
                        else:
                            print(f"  [Action] No element description found for index {idx}")
                            action_descriptions.append(f"Click on element at index {idx}")
                    except Exception as e:
                        print(f"  [Action] Error getting element description: {e}")
                        action_descriptions.append(f"Click on element at index {idx}")
                elif hasattr(action, "coordinate_x") and hasattr(action, "coordinate_y"):
                    x = getattr(action, "coordinate_x")
                    y = getattr(action, "coordinate_y")
                    action_descriptions.append(f"Click at coordinates ({x}, {y})")
                else:
                    action_descriptions.append("Click on element")
                    
            elif action_type_name == 'input' or "type" in action_str or "input" in action_str or "InputText" in action_class_name:
                action_type = ActionType.TYPE
                text = getattr(action, "text", None) or getattr(action, "input", None)
                idx = getattr(action, "index", None)
                if text and idx is not None:
                    print(f"  [Action] Attempting to get element description for input index {idx}...")
                    try:
                        element_desc = self._get_element_description(idx, browser_state)
                        if element_desc:
                            print(f"  [Action] Found element description: {element_desc}")
                            action_descriptions.append(f"Type '{text}' into '{element_desc}'")
                        else:
                            print(f"  [Action] No element description found for index {idx}")
                            action_descriptions.append(f"Type '{text}' into element at index {idx}")
                    except Exception as e:
                        print(f"  [Action] Error getting element description: {e}")
                        action_descriptions.append(f"Type '{text}' into element at index {idx}")
                elif text:
                    action_descriptions.append(f"Type '{text}'")
                else:
                    action_descriptions.append("Type text")
                    
            elif action_type_name == 'navigate' or "navigate" in action_str or "goto" in action_str or "Navigate" in action_class_name or "GoToUrl" in action_class_name:
                action_type = ActionType.NAVIGATE
                url = getattr(action, "url", None)
                if url:
                    # Extract domain for cleaner description
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace("www.", "")
                    action_descriptions.append(f"Navigate to {domain}")
                else:
                    action_descriptions.append("Navigate to page")
                    
            elif action_type_name == 'scroll' or "scroll" in action_str or "Scroll" in action_class_name:
                action_type = ActionType.SCROLL
                down = getattr(action, "down", True)
                direction = "down" if down else "up"
                pages = getattr(action, "pages", 1.0)
                if pages != 1.0:
                    action_descriptions.append(f"Scroll {direction} {pages} pages")
                else:
                    action_descriptions.append(f"Scroll {direction}")
                
            elif action_type_name == 'search' or "search" in action_str or "Search" in action_class_name:
                query = getattr(action, "query", None) or getattr(action, "text", None)
                if query:
                    action_descriptions.append(f"Search for '{query}'")
                else:
                    action_descriptions.append("Search")
                    
            elif action_type_name == 'extract' or "extract" in action_str or "Extract" in action_class_name:
                query = getattr(action, "query", None)
                if query:
                    action_descriptions.append(f"Extract information: '{query}'")
                else:
                    action_descriptions.append("Extract information")
            else:
                # Try to get any description or reasoning from action
                desc = getattr(action, "description", None) or getattr(action, "reasoning", None)
                if desc:
                    action_descriptions.append(desc)
                else:
                    # Use reasoning from model output if available
                    if reasoning:
                        # Extract a short description from reasoning
                        reasoning_short = reasoning[:100].strip()
                        if reasoning_short:
                            action_descriptions.append(reasoning_short)
                    else:
                        action_descriptions.append("Execute action")

        # Combine all action descriptions
        print(f"  [Action] Combining {len(action_descriptions)} description(s)...")
        action_desc = "; ".join(action_descriptions) if action_descriptions else "Execute action"
        print(f"  [Action] Final description: {action_desc}")

        result = ActionFromPrevious(
            type=action_type,
            description=action_desc,
            element_index=element_index,
        )
        duration = time.time() - action_start
        print(f"  [Action] Returning action in {duration:.2f}s: type={action_type.value}, desc={action_desc[:50]}")
        return result

    def _get_element_description(self, index: int, browser_state) -> Optional[str]:
        """Get element description from browser state using index.
        
        Args:
            index: Element index
            browser_state: BrowserStateSummary or similar
            
        Returns:
            Element description text if available, None otherwise
        """
        import time
        desc_start = time.time()
        print(f"    [Element] Getting description for index {index}...")
        
        if not browser_state or not hasattr(browser_state, 'dom_state'):
            print(f"    [Element] No browser_state or dom_state")
            return None
            
        try:
            dom_state = browser_state.dom_state
            print(f"    [Element] Got dom_state, checking selector_map...")
            if hasattr(dom_state, 'selector_map') and dom_state.selector_map:
                print(f"    [Element] Selector map has {len(dom_state.selector_map)} elements")
                if index in dom_state.selector_map:
                    print(f"    [Element] Found element at index {index}")
                    element = dom_state.selector_map[index]
                    # Try to get text or description from element
                    if hasattr(element, 'text') and element.text:
                        desc = element.text.strip()[:50]  # Limit length
                        print(f"    [Element] Got text: {desc} (took {time.time() - desc_start:.2f}s)")
                        return desc
                    elif hasattr(element, 'description') and element.description:
                        desc = element.description.strip()[:50]
                        print(f"    [Element] Got description: {desc} (took {time.time() - desc_start:.2f}s)")
                        return desc
                    elif hasattr(element, 'aria_label') and element.aria_label:
                        desc = element.aria_label.strip()[:50]
                        print(f"    [Element] Got aria_label: {desc} (took {time.time() - desc_start:.2f}s)")
                        return desc
                    else:
                        print(f"    [Element] Element found but no text/description/aria_label")
                else:
                    print(f"    [Element] Index {index} not found in selector_map")
            else:
                print(f"    [Element] No selector_map available")
        except Exception as e:
            print(f"    [Element] Exception getting element description: {e}")
            import traceback
            traceback.print_exc()
            pass
        
        print(f"    [Element] Returning None (took {time.time() - desc_start:.2f}s)")
        return None

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

