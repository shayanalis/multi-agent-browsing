# Loom Demo Quick Reference Card

## 🎬 Pre-Recording (2 min setup)

```bash
# 1. Activate environment
conda activate agentic-browsing

# 2. Navigate to project
cd /Users/shayan/Agentic_Browsing

# 3. Test command (don't run full task yet)
python -m agent_a.agent_a --help
```

---

## 📝 Demo Flow (15-20 min total)

### 1. Intro (2-3 min)
- Problem: Need to capture UI states (including modals/forms without URLs)
- Solution: Multi-agent system (Agent A → Agent B)
- Show project structure

### 2. Architecture (2-3 min)
- Agent A: Receives tasks, spawns Agent B
- Agent B: Executes task, captures states, generates tutorial
- Show key files: `task_runner.py`, `state_capture.py`, `browser_agent.py`

### 3. Live Demo (5-7 min) ⭐ **MAIN EVENT**
```bash
python -m agent_a.agent_a --task "How can I create a new database in Notion?"
```

**While running, explain:**
- Converting task to instructions
- Browser automation happening
- State capture after each action
- **KEY MOMENT**: Show modal opening (no URL change but state captured)

### 4. Results (3-4 min)
```bash
# Show output directory
ls outputs/2025-11-24_*/

# Open files:
# - Screenshots (step_000.png, step_001.png, etc.)
# - JSON metadata (show has_unique_url: false for modals)
# - tutorial.md
```

**Highlight:**
- Screenshots of each state
- JSON showing `has_unique_url: false` for modals
- Complete tutorial with instructions

### 5. Tutorial (2-3 min)
- Open `tutorial.md`
- Show: Clear instructions, screenshots, natural language
- Explain: LLM-enhanced, no coordinates, actionable

### 6. Key Features (2-3 min)
- ✅ Generalizable (no app-specific code)
- ✅ Captures non-URL states (modals, forms)
- ✅ Real-time execution
- ✅ Smart state capture (not every action)

### 7. Conclusion (1-2 min)
- Summary of capabilities
- Dataset organization
- Works across different apps

---

## 🎯 Key Talking Points

### Problem Statement
- "Not every UI state has a URL - modals, forms, dropdowns don't have unique URLs"
- "We need to capture these states programmatically in real-time"

### Solution
- "Multi-agent system: Agent A receives tasks, Agent B executes and captures"
- "Generalizable approach using browser-use library"

### Key Feature
- "Captures states even when URL doesn't change - this is the critical feature"
- "Tracks `has_unique_url` flag to identify non-URL states"

### Generalization
- "No app-specific logic - works with any web app"
- "Tested with Notion, could work with Linear, Asana, etc."

---

## 🔑 Key Moments to Highlight

1. **Modal Opens** - URL doesn't change, but state is captured
2. **Form Filled** - No URL change, but screenshot captured
3. **JSON Metadata** - Show `has_unique_url: false`
4. **Tutorial Quality** - Natural language, no coordinates, clear instructions

---

## 📂 Files to Show

### Code Files
- `agent_a/agent_a.py` - Entry point
- `agent_b/task_runner.py` - Orchestration
- `agent_b/state_capture.py` - Capture logic (show `should_capture` method)
- `agent_b/browser_agent.py` - Browser automation

### Output Files
- `outputs/YYYY-MM-DD_HH-MM/step_XXX.png` - Screenshots
- `outputs/YYYY-MM-DD_HH-MM/step_XXX.json` - Metadata (show `has_unique_url`)
- `outputs/YYYY-MM-DD_HH-MM/tutorial.md` - Generated tutorial

---

## ⚡ Quick Commands

```bash
# Run task
python -m agent_a.agent_a --task "How can I create a new database in Notion?"

# Show latest output
ls -lt outputs/ | head -2

# View tutorial
cat outputs/$(ls -t outputs/ | head -1)/tutorial.md

# View step JSON
cat outputs/$(ls -t outputs/ | head -1)/step_001.json
```

---

## 🎬 Recording Tips

- **Split screen**: Terminal + Browser
- **Zoom in**: When showing code/files
- **Pause**: When showing important details
- **Narrate**: Explain what's happening
- **Practice**: Run through once before recording

---

## 🚨 Troubleshooting

**If task fails:**
- Check API keys in `.env`
- Verify browser is installed
- Check internet connection
- Try a simpler task

**If recording issues:**
- Close unnecessary apps
- Check microphone
- Ensure screen is readable
- Test recording setup first

---

## 📊 Success Metrics to Mention

- ✅ Captures 3-5 different tasks
- ✅ Handles non-URL states (modals, forms)
- ✅ Generates clear tutorials
- ✅ Works across different apps
- ✅ Real-time execution on live apps

