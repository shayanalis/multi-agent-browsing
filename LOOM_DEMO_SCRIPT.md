# Loom Demo Script: Agentic Browsing System

## Pre-Recording Checklist

- [ ] Terminal ready with conda environment activated
- [ ] Browser (Arc/Chrome) installed and accessible
- [ ] `.env` file configured with API keys
- [ ] Project directory open in IDE/terminal
- [ ] Have a test task ready (e.g., "How can I create a new database in Notion?")
- [ ] Close unnecessary applications for clean screen
- [ ] Test your microphone and screen recording setup

---

## Demo Script (15-20 minutes)

### Part 1: Introduction & Problem Statement (2-3 min)

**Screen: Show project README or codebase overview**

**Talking Points:**
- "Hi, I'm [your name], and I'm going to show you an AI multi-agent system I built for capturing UI states during browser automation."
- "The problem we're solving: When you want to teach an AI agent how to perform a task in a web app, you need to capture screenshots of each UI state in the workflow."
- "The challenge: Not every UI state has a URL. For example, when creating a project in Linear:
  - The project list page has a URL ✓
  - But the 'Create Project' modal doesn't have a URL ✗
  - The form fields don't have URLs ✗
  - The success state might not have a unique URL ✗"
- "So we need a system that can navigate live applications and capture these states programmatically in real-time."

**Action:** 
- Show the project structure briefly
- Point out the key components

---

### Part 2: System Architecture Overview (2-3 min)

**Screen: Show codebase structure or architecture diagram**

**Talking Points:**
- "This is a multi-agent system with two main components:
  - **Agent A**: Receives task instructions and spawns Agent B
  - **Agent B**: Executes the task and captures UI states"
- "Here's how it works:
  1. Agent A receives a natural language task like 'How can I create a new database in Notion?'
  2. Agent A spawns Agent B with this task
  3. Agent B converts the task into concise instructions
  4. Agent B navigates the browser and executes the task
  5. As it works, it captures screenshots of each important UI state
  6. Finally, it generates a step-by-step tutorial with all the screenshots"

**Action:**
- Navigate through the codebase showing:
  - `agent_a/agent_a.py` - Entry point
  - `agent_b/task_runner.py` - Orchestration
  - `agent_b/browser_agent.py` - Browser automation
  - `agent_b/state_capture.py` - State capture logic
  - `agent_b/tutorial_agent.py` - Tutorial generation

**Key Point:** "The system is generalizable - it doesn't have any app-specific logic. It uses the browser-use library which can work with any web application."

---

### Part 3: Running a Live Task (5-7 min)

**Screen: Terminal + Browser (split screen if possible)**

**Talking Points:**
- "Now let's see it in action. I'll run a real task: creating a new database in Notion."
- "First, I'll activate the environment and run Agent A with a task instruction."

**Action:**
```bash
# Show terminal
conda activate agentic-browsing
cd /Users/shayan/Agentic_Browsing

# Run the task
python -m agent_a.agent_a --task "How can I create a new database in Notion?"
```

**Talking Points (while it runs):**
- "As you can see, Agent B is:
  1. Converting the task into concise instructions
  2. Opening the browser
  3. Navigating to Notion
  4. Executing each step of the task"
- "Watch the browser - you'll see it automatically:
  - Navigate to the right page
  - Click buttons
  - Fill in forms
  - Interact with the UI"
- "In the terminal, you can see it's capturing states after each significant action."

**Key Moments to Highlight:**
- When it navigates to Notion
- When it clicks "New page" or similar
- When it opens a modal (no URL change, but state is captured)
- When it fills in a form field
- When it completes the task

**Talking Points:**
- "Notice how it captures states even when the URL doesn't change - like when the modal opens. This is the key feature: capturing non-URL states."
- "The system is smart about when to capture - it captures after clicks, form inputs, and navigation, but not after every tiny action."

---

### Part 4: Examining Captured States (3-4 min)

**Screen: Show output directory with captured files**

**Talking Points:**
- "Let's look at what was captured. After the task completes, Agent B saves everything to an output directory."

**Action:**
```bash
# Show the output directory
ls -la outputs/
# Show the most recent task directory
ls -la outputs/2025-11-24_*/
```

**Talking Points:**
- "Each task creates a timestamped directory with:
  - Screenshots: `step_000.png`, `step_001.png`, etc.
  - Step metadata: JSON files with information about each step
  - Task metadata: Overall task information
  - Tutorial: A complete markdown tutorial"

**Action:**
- Open a few screenshot files to show:
  - Initial state (navigation)
  - Modal/form states (no URL change)
  - Final success state
- Open a step JSON file to show metadata:
  - URL
  - `has_unique_url` flag (show how it's false for modals)
  - Action that led to this state
  - State description

**Talking Points:**
- "See this step? The URL is the same as the previous step, but `has_unique_url` is false. This means it captured a modal or form that doesn't have its own URL."
- "This is exactly what we needed - capturing non-URL states in real-time."

---

### Part 5: Generated Tutorial (2-3 min)

**Screen: Show the generated tutorial.md file**

**Talking Points:**
- "The final output is a complete tutorial that Agent A can use to learn how to perform the task."

**Action:**
- Open the `tutorial.md` file
- Scroll through it showing:
  - Title and introduction
  - Step-by-step instructions
  - Screenshot references
  - Clear, actionable language

**Talking Points:**
- "The tutorial is generated by an LLM that:
  - Takes all the captured steps
  - Enhances them with clear, descriptive instructions
  - Avoids technical details like coordinates
  - Uses natural language like 'click the Create button' instead of 'click at coordinates 500, 300'"
- "Each step includes:
  - A screenshot showing what the UI looks like
  - Clear instructions on what to do
  - Context about what the user should see or expect"
- "This tutorial can be used by Agent A or any other system to learn how to perform the task."

---

### Part 6: Key Features & Generalization (2-3 min)

**Screen: Show code snippets or architecture**

**Talking Points:**
- "Let me highlight a few key features that make this system powerful:"

**1. Generalization:**
- "The system doesn't have any app-specific logic. It uses the browser-use library which works with any web application."
- "We've tested it with Notion, and it could work with Linear, Asana, or any other web app."

**2. Smart State Capture:**
- "The state capture logic is intelligent - it captures:
  - Initial and final states
  - States after URL changes
  - States after significant actions (clicks, form inputs)
  - But it doesn't capture every tiny action, keeping the dataset clean"

**3. Non-URL State Handling:**
- "The system tracks whether each state has a unique URL using the `has_unique_url` flag."
- "This allows it to capture modals, forms, dropdowns, and other UI elements that don't have URLs."

**4. Real-time Execution:**
- "Everything happens in real-time - the agent navigates the live application, not a static mockup."
- "This means it works with the actual, current version of the app."

**Action:** Show a code snippet from `state_capture.py`:
```python
def should_capture(self, state, action=None):
    # Capture if URL changed
    if state.url != self.previous_url:
        return True
    # Capture after significant actions
    if action and action.type in [ActionType.CLICK, ActionType.TYPE]:
        return True
```

---

### Part 7: Conclusion & Next Steps (1-2 min)

**Screen: Show project overview or README**

**Talking Points:**
- "To summarize, this system:
  - Automatically navigates live web applications
  - Captures UI states including modals and forms (non-URL states)
  - Generates clear, actionable tutorials
  - Works across different web apps without app-specific code"
- "For the submission, I've captured 3-5 different tasks across Notion, demonstrating the system's ability to handle various workflows."
- "The dataset includes screenshots, metadata, and tutorials for each task, organized by task in the outputs directory."

**Action:**
- Show the outputs directory structure
- Mention the dataset organization

**Closing:**
- "This system could be extended to work with any web application, making it a powerful tool for teaching AI agents how to interact with web UIs."
- "Thank you for watching!"

---

## Post-Recording Checklist

- [ ] Review the recording for clarity
- [ ] Check that all key moments are captured
- [ ] Ensure audio is clear
- [ ] Verify screen is readable
- [ ] Trim any unnecessary pauses
- [ ] Add any annotations if needed (arrows, highlights)

---

## Tips for Recording

1. **Practice First**: Run through the demo once without recording to ensure everything works
2. **Split Screen**: If possible, show terminal and browser side-by-side
3. **Zoom In**: When showing code or output files, zoom in so text is readable
4. **Pause for Clarity**: Don't rush - pause when showing important details
5. **Explain as You Go**: Narrate what's happening, especially during the live execution
6. **Highlight Key Moments**: 
   - When a modal opens (no URL change)
   - When state is captured
   - When tutorial is generated
7. **Keep It Focused**: Stay on topic, avoid tangents
8. **Show, Don't Just Tell**: Actually run a task, don't just describe it

---

## Alternative Shorter Version (10 min)

If you need a shorter demo:

1. **Introduction** (1 min) - Problem statement
2. **Live Demo** (5 min) - Run a task, show it working
3. **Results** (3 min) - Show captured states and tutorial
4. **Conclusion** (1 min) - Key features and generalization

---

## Sample Task Suggestions

Choose one that demonstrates non-URL states well:

1. **Notion**: "How can I create a new database with a chart view?"
   - Shows: Navigation, modal (create database), form (chart config), success state

2. **Notion**: "How can I filter a database by a specific property?"
   - Shows: Navigation, filter modal, dropdown selection

3. **Notion**: "How can I create a new page and add a table?"
   - Shows: Navigation, page creation, table insertion modal

Pick the one you're most comfortable with and that works reliably!

