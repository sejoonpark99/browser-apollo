"""
Build Apify URL from Manual Search ID
=====================================

This script takes a search ID that you extracted manually from Apollo.io
and builds the complete URL for Apify scraping.

Usage:
    python build_apify_url.py

You'll be prompted to enter your search ID.
"""

import os
from urllib.parse import quote
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Job titles to search for
JOB_TITLES = [
    "CEO", "CTO", "CFO", "VP Sales", "VP Marketing", 
    "VP Business Development", "Head of Sales", "Head of Marketing",
    "Director of Sales", "Sales Manager"
]

def url_encode_job_titles(titles):
    """URL encode job titles for Apollo search"""
    return [quote(title) for title in titles]

def build_apify_url(search_id):
    """Build complete Apify URL from search ID"""
    
    # Validate search ID
    if not search_id or len(search_id) < 10:
        print("❌ Invalid search ID. Please check and try again.")
        return None
    
    # Base Apollo URL with search ID
    base_url = (
        "https://app.apollo.io/#/people?"
        "page=1&sortAscending=false&sortByField=%5Bnone%5D"
        f"&qOrganizationSearchListId={search_id}"
    )
    
    # Add job titles
    encoded_titles = url_encode_job_titles(JOB_TITLES)
    title_params = "".join(f"&personTitles[]={title}" for title in encoded_titles)
    
    final_url = base_url + title_params
    
    return final_url

def main():
    """Main function"""
    print("🔗 Apollo Search ID → Apify URL Builder")
    print("=" * 50)
    
    print("\n📋 Instructions:")
    print("1. Go to Apollo.io in your regular browser")
    print("2. Navigate to People search")
    print("3. Click 'Companies and Lookalikes' → 'Include / exclude list of companies'")
    print("4. Paste your domain list and click 'Save and Search'")
    print("5. Copy the qOrganizationSearchListId from the URL")
    print("6. Paste it below")
    
    print("\n" + "=" * 50)
    
    # Get search ID from user
    search_id = input("\n🔍 Enter your Apollo search ID: ").strip()
    
    if not search_id:
        print("❌ No search ID provided. Exiting.")
        return
    
    print(f"\n⚙️ Processing search ID: {search_id}")
    print(f"📊 Job titles to include: {len(JOB_TITLES)} titles")
    
    # Build the URL
    apify_url = build_apify_url(search_id)
    
    if not apify_url:
        return
    
    # Display results
    print("\n🎉 SUCCESS! Apify URL Built")
    print("=" * 60)
    print(f"✅ Search ID: {search_id}")
    print(f"✅ Job titles: {', '.join(JOB_TITLES)}")
    print(f"✅ URL length: {len(apify_url)} characters")
    
    print(f"\n📋 APIFY MANUAL INSTRUCTIONS:")
    print("-" * 40)
    print("1. Go to: https://console.apify.com/")
    print("2. Search for 'Apollo.io Scraper' or use actor ID: jljBwyyQakqrL1wae")
    print("3. Click 'Try for free' or 'Start'")
    print("4. In the input configuration, paste this URL:")
    
    print(f"\n🔗 APIFY URL:")
    print("-" * 20)
    print(apify_url)
    print("-" * 20)
    
    print(f"\n5. Set 'Total Records' to: 200")
    print("6. Set 'File Name' to: Apollo_Prospects")
    print("7. Click 'Start' to run the scraper")
    print("8. Download results when complete")
    
    # Save to file for easy copying
    with open("apify_url.txt", "w") as f:
        f.write(apify_url)
    
    print(f"\n💾 URL also saved to: apify_url.txt")
    print("🎯 Ready for Apify execution!")

if __name__ == "__main__":
    main()