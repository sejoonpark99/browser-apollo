import asyncio
import os
import pandas as pd
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote
from dotenv import load_dotenv

from browser_use import Agent, Browser, BrowserConfig, Controller
from browser_use.controller.service import ActionResult
from browser_use.browser.context import BrowserContextConfig
from browser_use.llm.openai.chat import ChatOpenAI
from apify_client import ApifyClient
from helper.session_manager import ApolloSessionManager

# --- Environment Setup ---
load_dotenv()

# --- Configuration and Constants ---
JOB_TITLES = ["CEO", "CTO", "CFO", "VP Sales", "VP Marketing"]
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
ACTOR_ID = "jljBwyyQakqrL1wae"
DOMAINS_CSV = Path("data/company_domains.csv")

# Create the data directory if it doesn't exist
DOMAINS_CSV.parent.mkdir(exist_ok=True)

# --- Helper Function ---
def url_encode_job_titles(titles: list[str]) -> list[str]:
    """URL-encodes a list of job titles."""
    return [quote(title) for title in titles]

# --- Browser Automation Controller Actions ---
controller = Controller()

@controller.action('Load and paste domains')
async def load_and_paste_domains(browser: Browser) -> ActionResult:
    """
    Implements the first part of the 11-step process:
    1. Navigate to Apollo people search
    2. Click on "Companies and Lookalikes"
    3. Click on "Include / exclude list of companies"
    4. Click on the text area under "Include list of companies"
    5. Type/paste domain list into text area
    """
    try:
        # Load domains from CSV
        if not DOMAINS_CSV.exists():
            return ActionResult(
                extracted_content="❌ Domains CSV file not found",
                include_in_memory=False
            )
        
        domains_df = pd.read_csv(DOMAINS_CSV)
        domains_list = domains_df["domain"].tolist()
        domains_string = "\n".join(domains_list)
        
        # Get current page
        page = await browser.get_current_page()
        
        # Step 1: Navigate to Apollo people search URL
        apollo_url = "https://app.apollo.io/#/people?personTitles[]=CEO&sortByField=%5Bnone%5D&sortAscending=false"
        await page.goto(apollo_url)
        await page.wait_for_load_state("networkidle")
        
        # Step 2: Click on "Companies and Lookalikes" 
        company_selectors = [
            'text="Companies and Lookalikes"',
            'button:has-text("Companies")',
            '[data-cy*="company"]',
            'text*="Company"'
        ]
        
        company_clicked = False
        for selector in company_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                await page.click(selector)
                company_clicked = True
                break
            except:
                continue
                
        if not company_clicked:
            return ActionResult(
                extracted_content="❌ Could not find 'Companies and Lookalikes' button",
                include_in_memory=False
            )
        
        # Step 3: Click on "Include / exclude list of companies"
        include_exclude_selectors = [
            'text="Include / exclude list of companies"',
            'button:has-text("Include / exclude")',
            'text*="Include / exclude"',
            '[data-cy*="include-exclude"]'
        ]
        
        include_clicked = False
        for selector in include_exclude_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                await page.click(selector)
                include_clicked = True
                break
            except:
                continue
                
        if not include_clicked:
            return ActionResult(
                extracted_content="❌ Could not find 'Include / exclude list of companies' button",
                include_in_memory=False
            )
        
        # Step 4: Find and click the text area under "Include list of companies"
        textarea_selectors = [
            'textarea[placeholder*="one domain per line"]',
            'textarea[placeholder*="domain"]',
            'textarea:below(:text("Include list of companies"))',
            'textarea'
        ]
        
        textarea_found = False
        for selector in textarea_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                await page.click(selector)
                
                # Step 5: Type/paste the domain list
                await page.fill(selector, domains_string)
                textarea_found = True
                break
            except:
                continue
                
        if not textarea_found:
            return ActionResult(
                extracted_content="❌ Could not find textarea for domain input",
                include_in_memory=False
            )
        
        return ActionResult(
            extracted_content=f"✅ Successfully pasted {len(domains_list)} domains into textarea",
            include_in_memory=True
        )
        
    except Exception as e:
        return ActionResult(
            extracted_content=f"❌ Error in load_and_paste_domains: {str(e)}",
            include_in_memory=False
        )

@controller.action('Save the final output')
async def save_final_output(browser: Browser) -> ActionResult:
    """
    Implements the final steps of the 11-step process:
    6. Double-click the "Save and Search" button
    7. Wait for URL to update
    8. Extract qOrganizationSearchListId
    9. Add job titles to the search
    10. Apply all filters
    11. Extract final URL with search ID
    """
    try:
        # Get current page
        page = await browser.get_current_page()
        
        # Step 6: Double-click the "Save and Search" button
        save_search_selectors = [
            'button:has-text("Save and Search")',
            'text="Save and Search"',
            '[data-cy*="save-search"]',
            'button:has-text("Save")'
        ]
        
        save_clicked = False
        for selector in save_search_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                # Double-click as specified in requirements
                await page.dblclick(selector)
                save_clicked = True
                break
            except:
                continue
                
        if not save_clicked:
            return ActionResult(
                extracted_content="❌ Could not find 'Save and Search' button",
                include_in_memory=False
            )
        
        # Step 7: Wait 15 seconds for the page to fully load
        await page.wait_for_timeout(15000)
        
        # Step 8: Capture current URL and extract qOrganizationSearchListId
        current_url = page.url
        parsed_url = urlparse(current_url)
        
        # The parameter might be in the URL fragment (after #)
        search_id = None
        if parsed_url.fragment and '?' in parsed_url.fragment:
            query_string = parsed_url.fragment.split('?', 1)[1]
            params = parse_qs(query_string)
            search_id = params.get('qOrganizationSearchListId', [None])[0]
        
        if not search_id:
            return ActionResult(
                extracted_content=f"❌ Could not extract qOrganizationSearchListId from URL: {current_url}",
                include_in_memory=False
            )
        
        # Step 9: Add job titles to the search
        # Click on job titles/person titles filter
        job_title_selectors = [
            'text="Job Titles"',
            'text="Person Titles"',
            'text="Title"',
            '[data-cy*="title"]',
            'text*="Titles"'
        ]
        
        title_filter_clicked = False
        for selector in job_title_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                await page.click(selector)
                title_filter_clicked = True
                break
            except:
                continue
        
        if title_filter_clicked:
            # Add each job title
            for title in JOB_TITLES:
                try:
                    # Look for input field or search box for titles
                    title_input_selectors = [
                        'input[placeholder*="title"]',
                        'input[placeholder*="job"]',
                        'input[type="text"]:below(:text("Job Titles"))',
                        'input[type="text"]'
                    ]
                    
                    for input_selector in title_input_selectors:
                        try:
                            await page.wait_for_selector(input_selector, timeout=3000)
                            await page.fill(input_selector, title)
                            await page.press(input_selector, "Enter")
                            break
                        except:
                            continue
                            
                    # Alternative: look for checkboxes with title names
                    checkbox_selector = f'input[type="checkbox"]:near(:text("{title}"))'
                    try:
                        await page.wait_for_selector(checkbox_selector, timeout=2000)
                        await page.check(checkbox_selector)
                    except:
                        pass
                        
                except Exception as title_error:
                    print(f"⚠️ Could not add title '{title}': {title_error}")
                    continue
        
        # Step 10: Apply all filters (if there's an apply button)
        apply_selectors = [
            'button:has-text("Apply")',
            'button:has-text("Search")',
            'button:has-text("Update")'
        ]
        
        for selector in apply_selectors:
            try:
                await page.wait_for_selector(selector, timeout=3000)
                await page.click(selector)
                await page.wait_for_timeout(5000)  # Wait for filters to apply
                break
            except:
                continue
        
        # Step 11: Get final URL with all filters applied
        final_url = page.url
        
        # Construct the final Apify-ready URL
        base_url = (
            "https://app.apollo.io/#/people?"
            "page=1&sortAscending=false&sortByField=%5Bnone%5D"
            f"&qOrganizationSearchListId={search_id}"
        )
        
        # Add job titles as URL parameters
        for title in JOB_TITLES:
            encoded_title = quote(title)
            base_url += f"&personTitles[]={encoded_title}"
        
        return ActionResult(
            extracted_content=f"✅ SUCCESS! Extracted search ID: {search_id}\n"
                             f"📊 Added {len(JOB_TITLES)} job titles\n"
                             f"🔗 Final URL: {base_url}",
            include_in_memory=True
        )
        
    except Exception as e:
        return ActionResult(
            extracted_content=f"❌ Error in save_final_output: {str(e)}",
            include_in_memory=False
        )

# --- Main Application Logic ---
async def main():
    """Main function implementing the controller-based 11-step process."""
    
    print("🚀 Apollo.io Contact Extraction Pipeline (Controller Version)")
    print("=" * 60)
    print("This script implements the 11-step process using controller actions:")
    print("1-5. Load domains and paste into Apollo filter")
    print("6-11. Save search and extract organization ID")
    print("=" * 60)
    
    # Step 1: Validate domains file exists
    if not DOMAINS_CSV.exists():
        print(f"❌ Error: Domains file not found at '{DOMAINS_CSV}'. Please create it.")
        return
    
    # Step 2: Setup authentication
    session_manager = ApolloSessionManager()
    session_manager.fix_browser_issues()
    
    auth_config = session_manager._get_auth_config()
    if not auth_config:
        print("❌ No authentication found. Please run session capture first.")
        return
    
    # Step 3: Create browser profile
    profile = session_manager._create_browser_profile(auth_config, headless=False)
    
    # Step 4: Setup LLM and Agent with controller
    llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
    
    agent = Agent(
        task=(
            "You will execute a precise 11-step Apollo.io automation process using controller actions. "
            "First, use the 'Load and paste domains' action to handle steps 1-5 (navigate to Apollo, "
            "click company filters, paste domains). Then use the 'Save the final output' action "
            "for steps 6-11 (save search, wait for URL update, extract search ID, add job titles). "
            "Follow the actions exactly as implemented in the controller."
        ),
        browser_profile=profile,
        llm=llm,
        controller=controller
    )
    
    # Step 5: Execute the automation
    print("🚀 Starting controller-based automation...")
    print("📋 Executing 11-step process through controller actions...")
    
    try:
        result = await agent.run(max_steps=20)
        
        # Extract search ID from the result
        result_str = str(result)
        print(f"🔍 Agent execution result: {result_str}")
        
        # Look for search ID in the result
        search_id_match = re.search(r'search ID: ([a-f0-9]{24})', result_str)
        if not search_id_match:
            search_id_match = re.search(r'([a-f0-9]{24})', result_str)
        
        if search_id_match:
            search_id = search_id_match.group(1)
            print(f"✅ Successfully extracted search ID: {search_id}")
            
            # Step 6: Construct final Apify URL
            apollo_url = (
                "https://app.apollo.io/#/people?"
                "page=1&sortAscending=false&sortByField=%5Bnone%5D"
                f"&qOrganizationSearchListId={search_id}"
            )
            
            # Add job titles
            for title in JOB_TITLES:
                encoded_title = quote(title)
                apollo_url += f"&personTitles[]={encoded_title}"
            
            # Step 7: Display results and run Apify
            domains_count = len(pd.read_csv(DOMAINS_CSV)["domain"])
            
            print(f"\n🎉 AUTOMATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"✅ Organization Search ID: {search_id}")
            print(f"✅ Domains processed: {domains_count}")
            print(f"✅ Job titles: {', '.join(JOB_TITLES)}")
            print(f"🔗 Final Apollo URL: {apollo_url}")
            print("=" * 60)
            
            # Step 8: Run Apify scraper if token available
            if APIFY_TOKEN:
                await run_apify_scraper(apollo_url)
            else:
                print("\n📋 MANUAL APIFY INSTRUCTIONS:")
                print("1. Go to https://console.apify.com/")
                print("2. Find 'Apollo.io Scraper' actor")
                print(f"3. Use URL: {apollo_url}")
                print("4. Set totalRecords: 200")
                print("5. Run the scraper")
                
        else:
            print("❌ Failed to extract search ID from automation result")
            print(f"🔍 Full result: {result_str}")
            
    except Exception as e:
        print(f"❌ Error during automation: {str(e)}")

async def run_apify_scraper(apollo_url: str):
    """Run the Apify scraper with the constructed URL."""
    try:
        print(f"\n🕷️ Running Apify scraper...")
        
        run_input = {
            "url": apollo_url,
            "totalRecords": 200,
            "fileName": "Apollo Prospects"
        }
        
        apify_client = ApifyClient(token=APIFY_TOKEN)
        run = apify_client.actor(ACTOR_ID).call(run_input=run_input)
        
        if run["status"] == "SUCCEEDED":
            dataset_id = run["data"]["datasetId"]
            print(f"✅ Scraping completed successfully!")
            
            # Download and save results
            dataset_items = apify_client.dataset(dataset_id).list_items()
            
            if dataset_items.items:
                contacts_df = pd.DataFrame(dataset_items.items)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"apollo_contacts_controller_{timestamp}.csv"
                contacts_df.to_csv(output_file, index=False)
                
                print(f"🎉 Downloaded {len(contacts_df)} contacts")
                print(f"💾 Saved to: {output_file}")
                
                if 'organization_name' in contacts_df.columns:
                    unique_companies = contacts_df['organization_name'].nunique()
                    print(f"🏢 Companies found: {unique_companies}")
            else:
                print("⚠️ No contacts found")
                
        else:
            print(f"❌ Apify run failed: {run['status']}")
            
    except Exception as e:
        print(f"❌ Apify error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())