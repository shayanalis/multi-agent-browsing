# Questions to Consider Before Building

This document outlines key questions to think about when aligning the codebase with the original task requirements.

## 1. Agent A & Agent B Communication

### Current State
- Agent A is a CLI that takes `--task` argument
- Agent B executes the task and captures states

### Questions to Consider
- ✅ **Q: Is CLI acceptable for "runtime" communication?** 
  - **Your answer:** Keep CLI (acceptable for demo)
  - **Consideration:** The task says "at runtime" - CLI might be acceptable for demo, but consider if you need to show it can handle dynamic requests

- **Q: Should Agent A be able to send multiple tasks sequentially?**
  - Currently each run is independent
  - Should there be a batch mode or session mode?

- **Q: How should Agent A handle errors or incomplete tasks?**
  - What happens if Agent B fails mid-task?
  - Should Agent A retry or report back?

## 2. Dataset Organization & Submission

### Current State
- Each task creates: `outputs/YYYY-MM-DD_HH-MM/` with screenshots, JSON, tutorial
- No unified dataset structure

### Questions to Consider
- ✅ **Q: How should dataset be organized?**
  - **Your answer:** Keep current structure
  - **Consideration:** Task requires "organized by task" - current structure works, but consider:
    - Should there be a master index/README listing all tasks?
    - Should each task folder have a brief description blurb?

- **Q: What metadata should accompany each task in the dataset?**
  - Task description
  - App name
  - Task category (e.g., "create", "filter", "settings")
  - Success/failure status
  - Number of steps captured

- **Q: Should the dataset include a summary document?**
  - Overview of all tasks
  - Statistics (total steps, apps tested, etc.)
  - Brief explanation of each task

## 3. Task Selection & Coverage

### Current State
- Examples show Notion tasks
- Need 3-5 tasks across 1-2 apps

### Questions to Consider
- ✅ **Q: Which apps to focus on?**
  - **Your answer:** Notion only
  - **Consideration:** Task mentions Linear and Notion as examples. If doing Notion only:
    - Choose diverse task types (create, filter, modify, settings, etc.)
    - Ensure tasks demonstrate different UI patterns (modals, forms, dropdowns)

- **Q: What types of tasks best demonstrate the system?**
  - Tasks with modals (no URL)
  - Tasks with forms (no URL)
  - Tasks with multiple steps
  - Tasks that require navigation
  - Tasks that show success states

- **Q: Should tasks be of varying complexity?**
  - Simple (2-3 steps)
  - Medium (4-6 steps)
  - Complex (7+ steps)

## 4. State Capture & Non-URL States

### Current State
- Captures states after clicks, types, navigation
- Tracks URL changes
- Has `has_unique_url` flag

### Questions to Consider
- **Q: Are we capturing all important non-URL states?**
  - Modals (create project, settings)
  - Forms (input fields, dropdowns)
  - Dropdown menus
  - Success/confirmation states
  - Error states (if applicable)

- **Q: How do we ensure we're not missing intermediate states?**
  - Current logic: captures after significant actions
  - Is this sufficient, or should we be more aggressive?

- **Q: Should we capture "before" states (e.g., before clicking a button)?**
  - Currently captures "after" states
  - Might be useful for tutorials to show "before clicking" vs "after clicking"

## 5. Generalization & Robustness

### Current State
- Uses browser-use library (general purpose)
- No app-specific hardcoding visible
- Task instruction converted to concise steps

### Questions to Consider
- ✅ **Q: How to demonstrate generalization?**
  - **Your answer:** Just run tasks (implicit)
  - **Consideration:** While running tasks shows it works, consider:
    - Documenting why the approach generalizes (in README)
    - Showing it works across different UI patterns
    - Ensuring no app-specific logic

- **Q: What edge cases should we handle?**
  - Authentication (logged in vs logged out)
  - Different screen sizes
  - Slow loading pages
  - Dynamic content that loads after page load

- **Q: How do we handle tasks that require authentication?**
  - Current: Uses browser profiles (can maintain sessions)
  - Should we document how to set up authenticated sessions?

## 6. Tutorial Generation

### Current State
- Generates markdown tutorials with screenshots
- Uses LLM to enhance instructions
- Avoids mentioning coordinates

### Questions to Consider
- **Q: Are tutorials clear enough for Agent A to follow?**
  - Task says "shows Agent A how to perform the requested task"
  - Should tutorials be optimized for AI agents or humans?

- **Q: Should tutorials include error handling or alternatives?**
  - What if a button isn't found?
  - What if UI changed?

- **Q: Should we validate tutorial quality?**
  - Test if someone (or Agent A) can follow the tutorial
  - Ensure screenshots match instructions

## 7. Deliverables Checklist

### Questions to Consider
- **Q: Code deliverable - what's included?**
  - ✅ Core system code
  - ✅ Setup instructions
  - ✅ Example usage
  - ❓ Tests? (probably not required, but consider)

- **Q: Loom video - what should it cover?**
  - Show agent running through a workflow
  - Explain how it works
  - Show captured states
  - Show generated tutorial

- **Q: Dataset - what format?**
  - ✅ Screenshots (PNG)
  - ✅ Step metadata (JSON)
  - ✅ Tutorials (Markdown)
  - ❓ Master index/README?
  - ❓ Task descriptions/blurbs?

## 8. Technical Implementation Gaps

### Questions to Consider
- **Q: Are there any hardcoded assumptions?**
  - Browser paths (currently macOS-specific)
  - App-specific selectors or logic
  - Task-specific logic

- **Q: Should we add better error handling?**
  - What if browser-use fails?
  - What if screenshot capture fails?
  - What if LLM generation fails?

- **Q: Should we add logging/monitoring?**
  - Track which states were captured
  - Track which actions were taken
  - Debug failed tasks

- **Q: Performance considerations?**
  - How long does each task take?
  - Can we optimize state capture?
  - Should we parallelize anything?

## 9. Testing & Validation

### Questions to Consider
- **Q: How do we validate the system works correctly?**
  - Manually review captured states?
  - Test tutorial quality?
  - Verify all steps are captured?

- **Q: Should we create a test suite?**
  - Unit tests for state capture logic?
  - Integration tests for full workflows?
  - Probably not required, but consider

- **Q: How do we ensure reproducibility?**
  - Same task should produce similar results
  - Document any non-deterministic behavior

## 10. Documentation & Submission

### Questions to Consider
- **Q: What documentation is needed?**
  - ✅ README (exists)
  - ✅ Setup instructions (exists)
  - ❓ Architecture explanation?
  - ❓ Design decisions?
  - ❓ Limitations?

- **Q: How should the submission be structured?**
  - GitHub repo organization
  - Dataset location (in repo or separate?)
  - Loom video link (in README?)

- **Q: Should we include a project summary?**
  - What was built
  - How it works
  - Key design decisions
  - Results/statistics

## Priority Questions (Based on Your Answers)

Given your responses, here are the most critical questions to address:

1. **Dataset Organization** - Even keeping current structure, consider:
   - Creating a master README/index in `outputs/` that lists all tasks
   - Adding a brief blurb/description for each task folder
   - Ensuring dataset is clearly organized for submission

2. **Task Selection for Notion** - Choose 3-5 diverse tasks:
   - Create database
   - Filter database
   - Create page
   - Change settings
   - Add view (chart, board, etc.)
   - Ensure mix of URL and non-URL states

3. **Tutorial Quality** - Verify tutorials are:
   - Clear and actionable
   - Include all necessary steps
   - Screenshots match instructions
   - Can be followed by Agent A (or a human)

4. **Submission Package** - Ensure you have:
   - Clean, well-documented code
   - Dataset with clear organization
   - Loom video showing workflow
   - README explaining the system

