"""
Extract Working Chrome Session for Apollo.io
This creates a trusted session by letting you manually log in,
then captures the full session state including Cloudflare tokens.
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def extract_chrome_session():
    """Extract working session from manual Chrome login"""
    
    print("🚀 Starting Edge session extractor...")
    print("📋 Instructions:")
    print("1. Edge will open to Apollo login")
    print("2. Log in manually (solve any Cloudflare challenges)")
    print("3. Navigate to the people search page")
    print("4. Press Enter here when you're fully logged in and on Apollo dashboard")
    print("-" * 60)
    
    async with async_playwright() as p:
        # Launch Edge with persistent context (keeps profile data)
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./edge_profile",  # Persistent profile directory
            headless=False,
            channel="msedge",  # Use Microsoft Edge
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--no-first-run",
                "--no-default-browser-check"
            ],
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # Navigate to Apollo
        print("🌐 Opening Apollo.io in Edge...")
        await page.goto("https://app.apollo.io")
        
        # Wait for manual login
        input("\n⏳ Complete login manually, then press Enter to capture session...")
        
        # Verify they're logged in
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        if "login" in current_url.lower():
            print("⚠️ Warning: Still on login page. Make sure you're fully logged in.")
            input("Press Enter when logged in...")
        
        # Save the full session state
        storage_state = await context.storage_state()
        
        # Save to file
        storage_file = Path("cookies/verified_storage_state.json")
        storage_file.parent.mkdir(exist_ok=True)
        
        import json
        with open(storage_file, 'w') as f:
            json.dump(storage_state, f, indent=2)
        
        print(f"✅ Session saved to: {storage_file}")
        
        # Test the session
        print("\n🧪 Testing saved session...")
        await page.goto("https://app.apollo.io/#/people")
        await page.wait_for_timeout(3000)
        
        final_url = page.url
        if "people" in final_url and "login" not in final_url:
            print("✅ Session test PASSED! You can access Apollo people search.")
        else:
            print(f"⚠️ Session test unclear. Final URL: {final_url}")
        
        await context.close()
        
        print("\n🎉 Session extraction complete!")
        print("📄 Next steps:")
        print("1. Run main.py - it will use the verified session")
        print("2. The session includes Cloudflare clearance tokens")
        
        return str(storage_file)

if __name__ == "__main__":
    asyncio.run(extract_chrome_session())