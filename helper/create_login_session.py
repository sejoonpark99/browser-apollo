"""
Apollo.io Manual Login Session Capture
======================================

This script opens a browser for manual login to Apollo.io and captures
the complete authenticated session state for later use.

Usage:
    python create_login_session.py

After running:
1. Browser will open to Apollo login page
2. Manually log in to your Apollo account
3. Wait for redirect to dashboard
4. Session will be automatically saved to cookies/apollo_storage.json
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI

# Load environment variables
load_dotenv()


async def capture_apollo_session():
    """Capture authenticated Apollo session through manual login"""

    # Ensure cookies directory exists
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(exist_ok=True)

    # Create profile directory for persistent browser data
    profile_dir = Path("apollo_profile")
    profile_dir.mkdir(exist_ok=True)

    print("🚀 Starting Apollo session capture...")
    print("📋 Instructions:")
    print("1. Browser will open to Apollo login page")
    print("2. Please log in manually with your credentials")
    print("3. Wait for redirect to dashboard (app.apollo.io/#/dashboard or similar)")
    print("4. Session will be saved automatically")
    print("-" * 50)

    # Enhanced browser profile to avoid detection
    from browser_use.browser.profile import BrowserProfile

    profile = BrowserProfile(
        user_data_dir=str(profile_dir),  # Persistent profile
        wait_for_network_idle_page_load_time=60.0,  # Longer wait for Cloudflare and login
        headless=False,  # Visible browser for manual login
        allowed_domains=["*.apollo.io"],
        args=[
            "--disable-blink-features=AutomationControlled",  # Hide automation
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-web-security",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ],
    )

    # Initialize LLM (required for Agent)
    llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

    try:
        # Start the browser session using Agent
        print("🌐 Opening browser for manual login...")

        agent = Agent(
            task=(
                "Navigate to https://app.apollo.io/ and wait patiently for the user to manually log in. "
                "DO NOT proceed until you see the user is fully logged into the Apollo dashboard (URL should contain app.apollo.io and show the main interface). "
                "Once logged in, save the browser storage state and return 'SESSION_SAVED'."
            ),
            browser_profile=profile,
            llm=llm,
        )

        print("🔐 Please complete the login process in the browser...")
        print("⏳ Waiting for login completion (dashboard URL detection)...")

        # Run the agent to handle manual login and session saving
        result = await agent.run(max_steps=30)  # Allow 30 seconds for manual login

        if "SESSION_SAVED" in str(result).upper():
            print("✅ Session saved successfully to: cookies/storage_state.json")
            print("🎉 Apollo session capture complete!")
            print("-" * 50)
            print("Next steps:")
            print("1. Run main.py - it will use the saved session automatically")
            print("2. If you encounter Cloudflare blocks, re-run this script")
        else:
            raise Exception("Session capture incomplete")

    except Exception as e:
        print(f"❌ Error during session capture: {e}")
        print("💡 Tips:")
        print("- Make sure you have valid Apollo.io credentials")
        print("- Check your internet connection")
        print("- Try running the script again")
        raise


async def validate_existing_session():
    """Check if saved session is still valid"""
    storage_path = Path("cookies/storage_state.json")

    if not storage_path.exists():
        print("❌ No saved session found. Please run session capture first.")
        return False

    print("🔍 Validating existing session...")

    try:
        from browser_use.browser.profile import BrowserProfile

        profile = BrowserProfile(
            storage_state=str(storage_path),
            headless=True,
            allowed_domains=["*.apollo.io"],
            args=[
                "--disable-blink-features=AutomationControlled",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ],
        )

        # Use Agent for validation
        llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
        agent = Agent(
            task="Navigate to https://app.apollo.io/ and check if we're logged in. Return 'VALID_SESSION' if you see the main Apollo app interface, 'EXPIRED_SESSION' if you see the login page.",
            browser_profile=profile,
            llm=llm,
        )

        result = await agent.run(max_steps=2)

        if "VALID_SESSION" in str(result).upper():
            print("✅ Session is valid!")
            return True
        else:
            print("❌ Session expired - please re-capture")
            return False

    except Exception as e:
        print(f"❌ Session validation failed: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        # Validate existing session
        asyncio.run(validate_existing_session())
    else:
        # Capture new session
        asyncio.run(capture_apollo_session())
