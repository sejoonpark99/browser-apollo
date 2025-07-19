# Apollo.io Contact Extraction Pipeline

Automated pipeline that extracts contact information from Apollo.io using browser automation and Apify scraping.

## 🚀 Quick Start

**Choose Your Execution Method:**

### Standard Agent-Based Approach
```bash
python main.py
```

### Controller-Based Approach (Recommended)
```bash
python main_controller.py
```

Both scripts handle everything automatically:
- ✅ Authentication setup (if needed)
- ✅ Session validation and recovery  
- ✅ Browser automation
- ✅ Contact data extraction

## 📋 Execution Methods

### 1. Standard Agent (`main.py`)
- Uses AI agent with natural language task instructions
- More flexible but less predictable
- Good for exploratory automation

### 2. Controller Actions (`main_controller.py`) 
- Uses precise controller actions for each step
- Implements exact 11-step process from requirements
- More reliable and deterministic
- **Recommended for production use**

## 📋 Prerequisites

1. **Environment file** - Ensure `.env` contains:
   ```
   OPENAI_API_KEY=your_openai_key
   APIFY_TOKEN=your_apify_token
   ```

2. **Company domains** - Create `data/company_domains.csv` with:
   ```csv
   domain
   example.com
   company.org
   business.net
   ```

3. **Apollo.io account** - Valid credentials for manual login (first run only)

## 🔄 How It Works

### Automatic Authentication Flow
- **First run**: Opens browser for manual Apollo login, saves session
- **Subsequent runs**: Uses saved session automatically
- **Session expired**: Auto-recovery or fresh login as needed

### Data Extraction Process
1. Loads company domains from CSV
2. Navigates to Apollo.io with saved authentication
3. Applies domain filters to search
4. Extracts organization search ID from URL
5. Constructs Apify scraper URL with job titles
6. Runs Apify actor to extract contact data

## 📁 Project Structure

```
browser-apollo/
├── main.py                    # 🎯 Agent-based execution script
├── main_controller.py         # 🎮 Controller-based execution (recommended)
├── main_improved.py           # 🔧 Enhanced version with improvements
├── main_backup.py             # 💾 Backup version
├── config.py                  # ⚙️ Configuration settings
├── models.py                  # 📊 Data models
├── exceptions.py              # ⚠️ Custom exceptions
├── requirements.txt           # 📦 Python dependencies
├── data/
│   └── company_domains.csv    # 📊 Input domains
├── helper/
│   ├── __init__.py
│   ├── create_login_session.py  # 🔐 Manual login capture
│   ├── session_manager.py       # 🛡️ Session management
│   ├── job_titles.py            # 👔 Job title utilities
│   └── load_domains.py          # 📂 Domain loading utilities
├── cookies/                   # 🍪 Session data (gitignored)
├── keys/                      # 🔑 Sensitive keys (gitignored)
├── logs/                      # 📝 Log files (gitignored)
├── jobs/
│   └── job_titles.json        # 👔 Job titles configuration
├── testcases/                 # 🧪 Test files
└── apollo_profile/            # 🌐 Browser profile data (gitignored)
```

## 🎯 Target Data

Extracts contacts with these job titles:
- CEO, CTO, CFO
- VP Sales, VP Marketing

Each contact record includes:
- Name and email
- Phone number (when available)
- Job title and company
- LinkedIn profile
- Employment history

## 🔧 Advanced Usage

### Manual Authentication (if needed)
```bash
python helper/create_login_session.py
```

### Session Management
```bash
python helper/session_manager.py [validate|recover|info|cleanup]
```

### Utility Scripts
```bash
python build_apify_url.py          # Build Apify URLs manually
python fetch_apify_data.py          # Fetch data from existing Apify runs
python cloudflare_bypass.py         # Test Cloudflare bypass methods
python extract_chrome_session.py    # Extract Chrome session data
python monitoring.py                # Monitor automation runs
```

### Testing
```bash
python testcases/test_browser_compatibility.py
python testcases/test_browser_fixes.py
python testcases/fix_browser_issues.py
```

## ⚠️ Troubleshooting

**"No authentication found"**
- Script will automatically open browser for login
- Complete the login process manually
- Session will be saved for future runs

**"Session expired"**  
- Script attempts auto-recovery
- If failed, opens fresh login browser
- No manual intervention needed

**"Cloudflare blocking"**
- Enhanced anti-detection measures included
- Uses real browser fingerprinting
- Persistent browser profile reduces detection

## 📊 Output

Successful run provides:
- ✅ Extracted search ID (`qOrganizationSearchListId`)
- ✅ Apify dataset ID  
- ✅ CSV file with contact data (`apollo_contacts_TIMESTAMP.csv`)
- ✅ Progress tracking throughout process

### Sample Output Files
```
apollo_contacts_20250119_143022.csv        # Standard agent run
apollo_contacts_controller_20250119_143045.csv  # Controller run
```

### Contact Data Fields
Each contact record includes:
- `first_name`, `last_name` - Contact name
- `email`, `sanitized_phone` - Contact information  
- `title`, `organization_name` - Job details
- `linkedin_url` - Social profile
- `employment_history` - Work experience array

Results also available in Apify dashboard for further analysis and export options.