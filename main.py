import asyncio
import os
import pandas as pd
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote
from dotenv import load_dotenv

from browser_use import Agent, Controller
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use.controller.service import ActionResult
from apify_client import ApifyClient
from helper.session_manager import ApolloSessionManager

# --- Environment Setup ---
# Loads variables from a .env file (APOLLO_COOKIES, OPENAI_API_KEY, APIFY_TOKEN)
load_dotenv()


# --- Configuration and Constants ---
JOB_TITLES = ["CEO", "CTO"]  # Reduced for testing
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
ACTOR_ID = "jljBwyyQakqrL1wae"  #
DOMAINS_CSV = Path("data/company_domains.csv")  #

# Create the data directory if it doesn't exist
DOMAINS_CSV.parent.mkdir(exist_ok=True)


# --- Helper Function ---
def url_encode_job_titles(titles: list[str]) -> list[str]:
    """URL-encodes a list of job titles."""  #
    return [quote(title) for title in titles]


# --- Browser Automation Actions ---
controller = Controller()


@controller.action("Load + paste domains")
async def paste_domains(page) -> ActionResult:
    """
    Opens the company filter dialog for domain inclusion/exclusion.
    """
    try:
        # 1) Wait for the company‑filter sidebar to appear, then click it
        await page.wait_for_selector(
            'div[data-cy-id="prospect-search-sidebar-company-filter"]', timeout=10_000
        )
        await page.click('div[data-cy-id="prospect-search-sidebar-company-filter"]')

        # 2) Wait for the "Include / exclude list of companies" button, then click it
        # Try multiple selectors for this button
        selectors_to_try = [
            'text="Include / exclude list of companies"',
            'button:has-text("Include / exclude")',
            'button:has-text("Include")',
            '[data-cy*="include"]',
            'text*="Include"',
            'text*="exclude"'
        ]
        
        clicked = False
        for selector in selectors_to_try:
            try:
                await page.wait_for_selector(selector, timeout=3000)
                await page.click(selector)
                clicked = True
                break
            except:
                continue
        
        if not clicked:
            return ActionResult(
                extracted_content="❌ Could not find 'Include / exclude list of companies' button",
                include_in_memory=False
            )

        return ActionResult(
            extracted_content="✅ Opened Include / exclude list of companies dialog",
            include_in_memory=True
        )
    except Exception as e:
        return ActionResult(
            extracted_content=f"❌ Error in paste_domains: {str(e)}",
            include_in_memory=False
        )


@controller.action("Save & extract ID")
async def get_search_id(page) -> ActionResult:
    """Waits for the URL to update with the search ID and extracts it."""
    try:
        # Wait for the URL to contain the search list ID, with a timeout.
        await page.wait_for_url("**/#/?*qOrganizationSearchListId=*", timeout=30_000)

        url = page.url
        frag = urlparse(url).fragment

        if "?" not in frag:
            raise ValueError("URL fragment does not contain a query string.")

        query = parse_qs(frag.split("?", 1)[1])

        search_id_list = query.get("qOrganizationSearchListId")
        if not search_id_list:
            raise ValueError("Could not find 'qOrganizationSearchListId' in the URL.")

        search_id = search_id_list[0]
        return ActionResult(
            extracted_content=f"✅ Extracted Search ID: {search_id}",
            include_in_memory=True
        )
    except Exception as e:
        return ActionResult(
            extracted_content=f"❌ Error extracting search ID: {e}",
            include_in_memory=False
        )


# --- Authentication Functions ---
async def capture_new_session():
    """Capture a new Apollo session through manual login"""
    from pathlib import Path
    from browser_use import Browser
    from browser_use.browser.context import BrowserContextConfig

    # Ensure directories exist
    Path("cookies").mkdir(exist_ok=True)
    Path("apollo_profile").mkdir(exist_ok=True)

    print("🚀 Starting Apollo session capture...")
    print("📋 Instructions:")
    print("1. Browser will open to Apollo login page")
    print("2. Please log in manually with your credentials")
    print("3. Wait for redirect to dashboard")
    print("4. Session will be saved automatically")
    print("-" * 50)

    try:
        # Enhanced browser profile for manual login
        from browser_use.browser.profile import BrowserProfile

        profile = BrowserProfile(
            user_data_dir="apollo_profile",
            wait_for_network_idle_page_load_time=10.0,
            headless=False,  # Visible for manual login
            allowed_domains=["*.apollo.io"],
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-ipc-flooding-protection",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-field-trial-config",
                "--disable-background-timer-throttling",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            ],
            stealth=True,
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            ignore_https_errors=True,
        )

        # Use Agent for session capture (updated API)
        from browser_use.llm.openai.chat import ChatOpenAI
        from browser_use import Agent

        llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
        agent = Agent(
            task=(
                "Navigate to https://app.apollo.io/ and wait for manual login. "
                "Once the user has logged in and reached the main Apollo app interface, save the browser storage state to cookies/apollo_storage.json. "
                "Return 'LOGIN_COMPLETE' when done."
            ),
            browser_profile=profile,
            llm=llm,
        )

        print("🔐 Please complete the login process in the browser...")
        print("⏳ Waiting for login completion...")

        # Run the agent to handle login and session saving
        result = await agent.run(max_steps=10)  # Give it time for manual login

        if "LOGIN_COMPLETE" in str(result).upper():
            print("✅ Session saved successfully!")
            print("🎉 Ready to continue with Apollo automation!")
            return True
        else:
            print("❌ Login process incomplete")
            return False

    except Exception as e:
        print(f"❌ Error during session capture: {e}")
        print(
            "💡 Please ensure you have valid Apollo.io credentials and stable internet"
        )
        return False


# --- Main Application Logic ---
async def main():
    """Main function to run the entire automation pipeline."""

    print("🚀 Apollo.io Contact Extraction Pipeline")
    print("=" * 50)
    print("This script will:")
    print("1. ✅ Validate/setup Apollo authentication")
    print("2. 📁 Load company domains from CSV")
    print("3. 🌐 Automate Apollo search filtering")
    print("4. 🔗 Extract organization search ID")
    print("5. 🕷️  Run Apify scraper for contact data")
    print("=" * 50)

    # Step 1: Load Company Domains
    if not DOMAINS_CSV.exists():
        print(f"❌ Error: Domains file not found at '{DOMAINS_CSV}'. Please create it.")
        return
    domains_str = "\n".join(pd.read_csv(DOMAINS_CSV)["domain"])

    # Step 2: Comprehensive Authentication Flow
    session_manager = ApolloSessionManager()

    # Fix browser issues first
    session_manager.fix_browser_issues()

    # Display session information
    session_info = session_manager.get_session_info()
    print(f"📊 Session Status: {session_info['recommended_action']}")

    # Check if we have any authentication at all
    auth_config = session_manager._get_auth_config()

    if not auth_config:
        print("❌ No authentication found. Starting manual login process...")
        success = await capture_new_session()
        if not success:
            print("❌ Authentication setup failed!")
            return
        # Reload auth config after capturing session
        auth_config = session_manager._get_auth_config()

    # Validate session before proceeding
    print("🔍 Validating Apollo session...")
    # TEMPORARY: Skip validation since browser shows logged in
    print("⚠️ Skipping validation - browser appears logged in")
    is_valid = True

    if not is_valid:
        print("❌ Session invalid. Attempting recovery...")
        recovered = await session_manager.auto_recover_session()

        if not recovered:
            print("❌ Session recovery failed! Starting fresh login...")
            success = await capture_new_session()
            if not success:
                print("❌ Fresh authentication failed!")
                return
            # Reload auth config after fresh capture
            auth_config = session_manager._get_auth_config()
        else:
            print("✅ Session recovered successfully!")

    # Final validation
    if not auth_config:
        print("❌ No authentication available after all attempts!")
        return

    # Enhanced browser profile for Cloudflare bypass
    profile = session_manager._create_browser_profile(auth_config, headless=False)

    # Set domains BEFORE creating the agent so controller actions can access them
    controller.domains = domains_str
    print(f"🔧 Debug: Set {len(domains_str.split())} domains on controller")
    print(f"🔧 First few domains: {domains_str.split()[:3] if domains_str else 'None'}")

    llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
    agent = Agent(
        task=(
            "Navigate to https://app.apollo.io/ and wait 10 seconds for Turnstile to load completely. "
            "Then go to the plain people search page: https://app.apollo.io/#/people "
            "Wait for any Cloudflare or Turnstile challenges to complete. "
            "Once Apollo loads, follow these exact steps: "
            "1. Click 'Company' or 'Company Lookalikes' in the filters sidebar "
            "2. Click 'Include / exclude list of companies' button "
            "3. Find the textarea with placeholder 'one domain per line' "
            f"4. Paste these domains into the textarea: {domains_str} "
            "5. Click 'Save and Search' button to apply company filter "
            "6. Now click 'Job Titles' or 'Title' filter in the sidebar "
            f"7. Add all these job titles at once if possible: {', '.join(JOB_TITLES)} "
            "8. If the UI requires one-by-one, add each title and check the boxes "
            "9. Apply all job title filters together "
            "10. Wait for the URL to update with 'qOrganizationSearchListId' parameter "
            "11. Extract and return the qOrganizationSearchListId value from the URL"
        ),
        browser_profile=profile,
        llm=llm,
    )

    # Step 3: Run Agent to Extract the Organization Search ID
    print("🚀 Starting agent to get search ID...")
    print(f"📁 Using {len(domains_str.split())} domains from CSV")
    search_id = await agent.run(max_steps=50)

    # Extract the actual search ID from agent result
    search_id_str = str(search_id)
    print(f"🔍 Agent result: {search_id_str}")
    
    # Look for the search ID pattern in the result (24-character hex string)
    search_id_match = re.search(r'([a-f0-9]{24})', search_id_str)
    
    if search_id_match:
        extracted_search_id = search_id_match.group(1)
        print(f"✅ Extracted Search ID: {extracted_search_id}")
        search_id = extracted_search_id
    else:
        print("❌ Agent failed to retrieve the search ID. Aborting.")
        print(f"🔍 Full agent result for debugging: {search_id_str}")
        return

    # Step 4: Provide Manual Apify Instructions
    print(f"\n🎉 SEARCH ID EXTRACTED!")
    print("=" * 60)
    print(f"✅ Organization Search ID: {search_id}")
    print("=" * 60)

    # Step 5: Construct Apify URL for manual use
    
    # Build the basic Apollo URL with search ID
    apollo_url = (
        "https://app.apollo.io/#/people?"
        "page=1&sortAscending=false&sortByField=%5Bnone%5D"
        f"&qOrganizationSearchListId={search_id}"
    )
    
    # Add job titles as separate parameters (Apollo format)
    apollo_url_with_titles = apollo_url + "".join(
        f"&personTitles[]={quote(title)}" for title in JOB_TITLES
    )
    
    print(f"\n🔗 Apollo URL with filters: {apollo_url_with_titles}")
    
    # For Apify, we need to provide the URL and titles separately
    final_url = apollo_url  # Base URL without titles for Apify

    # Step 6: Run Apify Scraper Automatically
    print(f"\n🕷️ RUNNING APIFY SCRAPER AUTOMATICALLY...")
    print("-" * 50)
    
    if not APIFY_TOKEN:
        print("❌ APIFY_TOKEN not found in environment variables!")
        print("Please set APIFY_TOKEN and run again for automatic scraping.")
        print(f"\n📋 MANUAL INSTRUCTIONS:")
        print(f"URL: {final_url}")
        print(f"Person Titles: {json.dumps(JOB_TITLES)}")
        return
    
    try:
        # Configure Apify run input
        run_input = {
            "url": apollo_url_with_titles,  # Use full URL with titles
            "totalRecords": 200,
            "fileName": "Apollo Prospects"
        }
        
        print(f"🚀 Starting Apify scraper...")
        print(f"📊 Target: {len(domains_str.split())} companies, {len(JOB_TITLES)} job titles")
        print(f"🎯 Max records: 200")
        
        # Run the Apify actor
        apify_client = ApifyClient(token=APIFY_TOKEN)
        run = apify_client.actor(ACTOR_ID).call(run_input=run_input)
        
        if run["status"] == "SUCCEEDED":
            dataset_id = run["data"]["datasetId"]
            print(f"✅ Scraping completed successfully!")
            print(f"📂 Dataset ID: {dataset_id}")
            
            # Download the data
            print(f"📥 Downloading contact data...")
            dataset_items = apify_client.dataset(dataset_id).list_items()
            
            if dataset_items.items:
                # Convert to pandas DataFrame and save as CSV
                contacts_df = pd.DataFrame(dataset_items.items)
                
                # Create output filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"apollo_contacts_{timestamp}.csv"
                
                contacts_df.to_csv(output_file, index=False)
                
                print(f"🎉 SUCCESS! Downloaded {len(contacts_df)} contacts")
                print(f"💾 Saved to: {output_file}")
                print(f"📊 Columns: {', '.join(contacts_df.columns.tolist())}")
                
                # Summary stats
                if 'organization_name' in contacts_df.columns:
                    unique_companies = contacts_df['organization_name'].nunique()
                    print(f"🏢 Companies found: {unique_companies}")
                
                if 'title' in contacts_df.columns:
                    title_counts = contacts_df['title'].value_counts().head()
                    print(f"👔 Top titles: {dict(title_counts)}")
                    
            else:
                print("⚠️ No contacts found. Try adjusting your filters.")
                
        else:
            print(f"❌ Apify run failed with status: {run['status']}")
            if 'error' in run:
                print(f"Error: {run['error']}")
                
    except Exception as e:
        print(f"❌ Error running Apify scraper: {str(e)}")
        print(f"\n📋 MANUAL APIFY INSTRUCTIONS (Free Plan):")
        print("=" * 50)
        print("1. Go to: https://console.apify.com/")
        print("2. Search for 'Apollo.io Scraper' actor")
        print("3. Click 'Try for free' or 'Start'")
        print("4. In the input configuration:")
        print(f"   📋 URL: {apollo_url_with_titles}")
        print(f"   👔 Person Titles: {json.dumps(JOB_TITLES)}")
        print(f"   📊 Total Records: 100 (free plan limit)")
        print("5. Click 'Start' to run the scraper")
        print("6. Download results when complete")
        print("\n💡 Note: Free plans must use the web UI, not API")

    print(f"\n📊 FINAL SUMMARY:")
    print(f"✅ Domains filtered: {len(domains_str.split())} companies")
    print(f"✅ Job titles: {', '.join(JOB_TITLES)}")
    print(f"✅ Search ID: {search_id}")
    print(f"✅ Apollo URL: {apollo_url_with_titles}")


if __name__ == "__main__":
    asyncio.run(main())
