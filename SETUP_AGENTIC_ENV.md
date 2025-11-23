## Agentic Browsing Environment

### Conda environment
- Name: `agentic-browsing`
- Python: 3.11.14
- Exported spec: `environment-agentic-browsing.yml`
- Activate with `conda activate agentic-browsing`

### Tooling
- `uv==0.9.10` installed via `pip install uv`
- Use `uv pip install <pkg>` for subsequent Python dependencies

### Key libraries
- `playwright==1.49.1` (plus Chromium runtime via `playwright install chromium`)
- `openai==1.51.2`
- `httpx==0.27.2`, `websockets==13.1`
- `python-dotenv==1.0.1`, `typer==0.12.5`, `loguru==0.7.2`
- `beautifulsoup4==4.12.3`, `pandas==2.2.3`

These cover browser automation, API access, CLI ergonomics, logging, and data wrangling.

