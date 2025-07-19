"""
Fetch Data from Apify Actor Run
===============================

This script fetches and processes data from a completed Apify actor run.
Use this after you've run the Apollo scraper in Apify dashboard.

Usage:
    python fetch_apify_data.py

You'll be prompted to enter your Apify run ID or dataset ID.
"""

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load environment variables
load_dotenv()

def setup_apify_client():
    """Setup Apify client with token"""
    token = os.getenv("APIFY_TOKEN")
    
    if not token:
        print("❌ APIFY_TOKEN not found in .env file")
        print("💡 Get your token from: https://console.apify.com/account/integrations")
        return None
    
    return ApifyClient(token)

def fetch_by_run_id(client, run_id):
    """Fetch data using run ID"""
    try:
        print(f"🔍 Fetching run details for: {run_id}")
        
        # Get run details
        run_client = client.run(run_id)
        run_info = run_client.get()
        
        print(f"📊 Run status: {run_info.get('status', 'Unknown')}")
        print(f"📅 Started: {run_info.get('startedAt', 'Unknown')}")
        print(f"📅 Finished: {run_info.get('finishedAt', 'Unknown')}")
        
        # Get dataset ID from run
        dataset_id = run_info.get('defaultDatasetId')
        
        if not dataset_id:
            print("❌ No dataset found for this run")
            return None
        
        print(f"📦 Dataset ID: {dataset_id}")
        
        # Fetch dataset items
        dataset_client = client.dataset(dataset_id)
        items = list(dataset_client.iterate_items())
        
        return items, dataset_id
        
    except Exception as e:
        print(f"❌ Error fetching run data: {e}")
        return None, None

def fetch_by_dataset_id(client, dataset_id):
    """Fetch data using dataset ID"""
    try:
        print(f"📦 Fetching dataset: {dataset_id}")
        
        dataset_client = client.dataset(dataset_id)
        items = list(dataset_client.iterate_items())
        
        return items, dataset_id
        
    except Exception as e:
        print(f"❌ Error fetching dataset: {e}")
        return None, None

def process_contacts(items):
    """Process and clean contact data"""
    if not items:
        print("❌ No items to process")
        return None
    
    print(f"📊 Processing {len(items)} contacts...")
    
    # Convert to DataFrame for easier processing
    df = pd.DataFrame(items)
    
    # Display basic stats
    print(f"✅ Total contacts: {len(df)}")
    
    if not df.empty:
        print(f"📊 Columns: {', '.join(df.columns)}")
        
        # Check for key fields
        key_fields = ['first_name', 'last_name', 'email', 'title', 'organization_name']
        available_fields = [field for field in key_fields if field in df.columns]
        print(f"🔑 Key fields available: {', '.join(available_fields)}")
        
        # Check email availability
        if 'email' in df.columns:
            emails_available = df['email'].notna().sum()
            print(f"📧 Contacts with emails: {emails_available}/{len(df)}")
    
    return df

def save_data(df, dataset_id):
    """Save processed data to files"""
    if df is None or df.empty:
        print("❌ No data to save")
        return
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"apollo_contacts_{timestamp}"
    
    # Save as CSV
    csv_file = output_dir / f"{base_filename}.csv"
    df.to_csv(csv_file, index=False)
    print(f"💾 CSV saved: {csv_file}")
    
    # Save as JSON
    json_file = output_dir / f"{base_filename}.json"
    df.to_json(json_file, orient='records', indent=2)
    print(f"💾 JSON saved: {json_file}")
    
    # Save metadata
    metadata = {
        "dataset_id": dataset_id,
        "extraction_date": datetime.now().isoformat(),
        "total_contacts": len(df),
        "columns": list(df.columns),
        "contacts_with_email": df['email'].notna().sum() if 'email' in df.columns else 0
    }
    
    metadata_file = output_dir / f"{base_filename}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"📋 Metadata saved: {metadata_file}")

def main():
    """Main function"""
    print("📥 Apify Data Fetcher")
    print("=" * 30)
    
    # Setup client
    client = setup_apify_client()
    if not client:
        return
    
    print("\n📋 Options:")
    print("1. Fetch by Run ID (recommended)")
    print("2. Fetch by Dataset ID")
    
    choice = input("\nSelect option (1 or 2): ").strip()
    
    if choice == "1":
        run_id = input("\n🆔 Enter Apify Run ID: ").strip()
        if not run_id:
            print("❌ No run ID provided")
            return
        
        items, dataset_id = fetch_by_run_id(client, run_id)
        
    elif choice == "2":
        dataset_id = input("\n📦 Enter Dataset ID: ").strip()
        if not dataset_id:
            print("❌ No dataset ID provided")
            return
        
        items, dataset_id = fetch_by_dataset_id(client, dataset_id)
        
    else:
        print("❌ Invalid option")
        return
    
    if items is None:
        print("❌ Failed to fetch data")
        return
    
    # Process the data
    df = process_contacts(items)
    
    # Save results
    save_data(df, dataset_id)
    
    print(f"\n🎉 Data processing complete!")
    print("📁 Check the 'output' folder for your files")

if __name__ == "__main__":
    main()