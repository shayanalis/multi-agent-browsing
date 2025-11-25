"""Example script for using browser-use Agent directly (not through Agent B)."""

import asyncio
import os
from pathlib import Path

from browser_use import Agent, ChatBrowserUse, BrowserProfile
from dotenv import load_dotenv

# Ensure environment variables (API keys, etc.) are available to Browser Use
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Get API key from environment
BROWSER_USE_API_KEY = os.getenv("BROWSER_USE_API_KEY")
if not BROWSER_USE_API_KEY:
    raise ValueError(
        "BROWSER_USE_API_KEY not found in environment. "
        "Set it in .env file."
    )

QUERY = "AI engineer jobs posted in last 3 days"

TASK = f"""
open my gmail and check the latest email from from brian and read it out to me.8b
"""

# Launch a new Chromium window in incognito mode.
# Open https://www.google.com in the first tab.
# Search for "{QUERY}".
# go to the jobs tab in the search results.
# Then open each result and look at the job description and requirements one by one, until you find a job that requires less than 5 years of experience.
# Stay on the results page so I can review the listings.
# output the job title, company name, and location of the job


async def main() -> None:
    """
    Runs a Browser Use agent that opens an incognito Google search for fresh AI
    engineer job listings published within the last three days.
    """
    # Configure browser profile to use Arc browser instead of Chromium
    # Use a separate user data directory to avoid conflicts with running Arc instances
    import tempfile
    temp_user_data_dir = Path(tempfile.mkdtemp(prefix="arc-automation-"))
    
    browser_profile = BrowserProfile(
        executable_path="/Applications/Arc.app/Contents/MacOS/Arc",
        headless=False,  # Set to True if you want headless mode
        user_data_dir=temp_user_data_dir,  # Separate profile to avoid conflicts with running Arc
        args=[
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )
    
    llm = ChatBrowserUse(api_key=BROWSER_USE_API_KEY)
    agent = Agent(
        task=TASK.strip(), 
        llm=llm,
        browser_profile=browser_profile
    )
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

