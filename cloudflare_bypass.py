"""
Cloudflare Bypass Helper
Try multiple strategies to get past Cloudflare protection
"""

import asyncio
import time
from browser_use import Agent
from browser_use.llm.openai.chat import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

async def test_cloudflare_bypass():
    """Test different approaches to bypass Cloudflare"""
    
    strategies = [
        {
            "name": "Slow Navigation",
            "args": ["--disable-blink-features=AutomationControlled", "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"],
            "wait_time": 45
        },
        {
            "name": "Real Chrome",
            "channel": "chrome", 
            "args": ["--disable-web-security", "--disable-features=VizDisplayCompositor"],
            "wait_time": 30
        },
        {
            "name": "Stealth Mode",
            "stealth": True,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
            "wait_time": 60
        }
    ]
    
    llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
    
    for i, strategy in enumerate(strategies, 1):
        print(f"\n🧪 Testing Strategy {i}: {strategy['name']}")
        print("-" * 50)
        
        try:
            from browser_use.browser.profile import BrowserProfile
            
            profile_config = {
                "headless": False,
                "wait_for_network_idle_page_load_time": strategy.get("wait_time", 30),
                "allowed_domains": ["*.apollo.io"],
                "args": strategy.get("args", []),
            }
            
            if "channel" in strategy:
                profile_config["channel"] = strategy["channel"]
            if "stealth" in strategy:
                profile_config["stealth"] = strategy["stealth"]
                
            profile = BrowserProfile(**profile_config)
            
            agent = Agent(
                task=f"Navigate to https://app.apollo.io and wait {strategy.get('wait_time', 30)} seconds. If you see the Apollo interface (not Cloudflare), return 'SUCCESS'. If you see Cloudflare, return 'BLOCKED'.",
                browser_profile=profile,
                llm=llm,
            )
            
            result = await agent.run(max_steps=3)
            
            if "SUCCESS" in str(result).upper():
                print(f"✅ Strategy {i} ({strategy['name']}) WORKED!")
                return strategy
            else:
                print(f"❌ Strategy {i} ({strategy['name']}) failed: {result}")
                
        except Exception as e:
            print(f"❌ Strategy {i} error: {e}")
            
        # Wait between attempts
        if i < len(strategies):
            print("⏳ Waiting 60 seconds before next attempt...")
            await asyncio.sleep(60)
    
    print("\n❌ All strategies failed. Consider:")
    print("1. Using VPN/different IP")
    print("2. Waiting 30+ minutes")
    print("3. Manual approach")
    return None

if __name__ == "__main__":
    asyncio.run(test_cloudflare_bypass())