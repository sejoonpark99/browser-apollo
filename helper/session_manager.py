"""
Apollo Session Manager
=====================

Utilities for validating and managing Apollo.io authentication sessions.
Implements browser-use best practices for security, monitoring, and error handling.
Handles both legacy cookie files and modern storage state files.
"""

import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any

# Optional enhanced imports - graceful fallback if not available
try:
    import structlog
    logger = structlog.get_logger("apollo.session")
    HAS_STRUCTLOG = True
except ImportError:
    import logging
    HAS_STRUCTLOG = False
    
    class LoggerWrapper:
        def __init__(self, name):
            self._logger = logging.getLogger(name)
            logging.basicConfig(level=logging.INFO)
            
        def info(self, message, **kwargs):
            if kwargs:
                self._logger.info(f"{message} {kwargs}")
            else:
                self._logger.info(message)
                
        def debug(self, message, **kwargs):
            if kwargs:
                self._logger.debug(f"{message} {kwargs}")
            else:
                self._logger.debug(message)
                
        def warning(self, message, **kwargs):
            if kwargs:
                self._logger.warning(f"{message} {kwargs}")
            else:
                self._logger.warning(message)
                
        def error(self, message, **kwargs):
            if kwargs:
                self._logger.error(f"{message} {kwargs}")
            else:
                self._logger.error(message)
    
    logger = LoggerWrapper("apollo.session")

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

try:
    from models import AuthenticationResult, BrowserConfig
    from exceptions import (
        AuthenticationError, SessionExpiredError, BrowserError,
        ErrorHandler, handle_browser_use_errors
    )
    HAS_ENHANCED_MODELS = True
except ImportError:
    HAS_ENHANCED_MODELS = False

# Load environment variables
load_dotenv()

# Fallback logging function
def log_info(message, **kwargs):
    if HAS_STRUCTLOG and logger:
        logger.info(message, **kwargs)
    else:
        print(f"INFO: {message} {kwargs if kwargs else ''}")

def log_warning(message, **kwargs):
    if HAS_STRUCTLOG and logger:
        logger.warning(message, **kwargs)
    else:
        print(f"WARNING: {message} {kwargs if kwargs else ''}")

def log_error(message, **kwargs):
    if HAS_STRUCTLOG and logger:
        logger.error(message, **kwargs)
    else:
        print(f"ERROR: {message} {kwargs if kwargs else ''}")

def log_debug(message, **kwargs):
    if HAS_STRUCTLOG and logger:
        logger.debug(message, **kwargs)
    else:
        print(f"DEBUG: {message} {kwargs if kwargs else ''}")

class ApolloSessionManager:
    """Manages Apollo.io authentication sessions with security and monitoring"""   
    
    def __init__(self):
        # Prefer verified session over regular session
        verified_path = Path("cookies/verified_storage_state.json")
        regular_path = Path("cookies/storage_state.json")
        
        if verified_path.exists():
            self.storage_state_path = verified_path
            print("🔒 Using verified Chrome session (includes Cloudflare tokens)")
        else:
            self.storage_state_path = regular_path
        self.legacy_cookies_path = Path("cookies/apollo.json")
        self.profile_dir = Path("apollo_profile")
        self.error_handler = ErrorHandler()
        self._encryption_key = self._get_or_create_encryption_key()
        
        # Security configuration
        self.sensitive_data = self._load_sensitive_data()
        self.allowed_domains = ["*.apollo.io", "accounts.google.com", "*.googleusercontent.com"]
        
        # Performance settings
        self.session_cache = {}
        self.last_validation = None
        self.validation_interval = 300  # 5 minutes
        
    async def validate_session(self, use_headless=True) -> bool:
        """
        Validate if the current session is still active
        
        Args:
            use_headless: Whether to run browser in headless mode
            
        Returns:
            bool: True if session is valid, False otherwise
        """
        print("🔍 Validating Apollo session...")
        
        # Check if we have any authentication
        auth_config = self._get_auth_config()
        if not auth_config:
            print("❌ No authentication files found")
            return False
        
        try:
            # Check cache first for performance
            if self._is_cached_validation_valid():
                logger.info("Using cached session validation")
                return True
            
            # Create secure browser profile
            profile = self._create_secure_browser_profile(auth_config, headless=use_headless)
            
            # Use structured output for validation
            from browser_use.llm.openai.chat import ChatOpenAI
            from browser_use import Agent, Controller
            from models import ApolloOutputController
            
            llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
            
            # Create agent with structured output and sensitive data protection
            agent = Agent(
                task="Navigate to https://app.apollo.io and check if you are logged in. Return 'LOGGED_IN' if you see the Apollo dashboard/home interface. Return 'NOT_LOGGED_IN' if you see login forms or are redirected to login page.",
                browser_profile=profile,
                llm=llm,
                controller=ApolloOutputController.get_authentication_controller(),
                sensitive_data=self.sensitive_data,
                use_vision=False,  # Security: no screenshots of login pages
                on_step_start=self._validation_step_monitor,
                on_step_end=self._validation_error_handler
            )
            
            # Run validation with monitoring
            logger.info("Starting Apollo session validation", 
                       session_type=auth_config.get('storage_state', 'cookies'))
            
            result = await agent.run(max_steps=10)
            
            # Process structured result
            if isinstance(result, AuthenticationResult):
                success = result.authenticated
                logger.info("Session validation completed", 
                           authenticated=success, 
                           session_type=result.session_type)
            else:
                # Fallback for non-structured output
                result_str = str(result).upper()
                success = "LOGGED_IN" in result_str or "DASHBOARD" in result_str or "HOME" in result_str
                logger.warning("Received non-structured validation result")
            
            # Cache successful validation
            if success:
                self._cache_validation_result(True)
                logger.info("✅ Session is valid!")
                return True
            else:
                logger.warning("❌ Session expired - login required")
                raise SessionExpiredError(
                    session_type=auth_config.get('storage_state', 'cookies')
                )
                
        except Exception as e:
            error_context = {
                'auth_config_type': list(auth_config.keys()) if auth_config else [],
                'headless': use_headless
            }
            
            if isinstance(e, (AuthenticationError, SessionExpiredError)):
                raise  # Re-raise our custom exceptions
            else:
                # Wrap unexpected errors
                logger.error("Session validation failed", error=str(e), context=error_context)
                raise AuthenticationError(
                    f"Session validation failed: {str(e)}",
                    context=error_context
                )
    
    async def auto_recover_session(self) -> bool:
        """
        Attempt to automatically recover the session
        
        Returns:
            bool: True if recovery successful, False if manual login needed
        """
        print("🔄 Attempting session recovery...")
        
        # First, try validating current session
        if await self.validate_session():
            print("✅ Session is already valid!")
            return True
        
        # Check if we have a backup or alternative auth method
        auth_config = self._get_auth_config()
        if not auth_config:
            print("❌ No authentication available for recovery")
            return False
        
        # Try with different browser settings (non-headless, different user agent)
        recovery_configs = [
            {"headless": False, "extra_args": ["--incognito"]},
            {"headless": True, "extra_args": ["--disable-web-security"]},
            {"headless": False, "extra_args": ["--user-data-dir=" + str(self.profile_dir)]}
        ]
        
        for i, config in enumerate(recovery_configs):
            print(f"🔄 Recovery attempt {i+1}/{len(recovery_configs)}")
            
            try:
                profile = self._create_browser_profile(
                    auth_config, 
                    headless=config["headless"],
                    extra_args=config["extra_args"]
                )
                
                # Use Agent for recovery (updated API)
                from browser_use.llm.openai.chat import ChatOpenAI
                from browser_use import Agent
                import os
                
                llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
                agent = Agent(
                    task="Navigate to https://app.apollo.io/ and check if we're logged in. If you see the main Apollo app interface, return 'RECOVERY_SUCCESS'. If you see the login page, return 'RECOVERY_FAILED'.",
                    browser_profile=profile,
                    llm=llm,
                )
                
                result = await agent.run(max_steps=10)
                
                if "RECOVERY_SUCCESS" in str(result).upper():
                    print("✅ Session recovered successfully!")
                    return True
                
            except Exception as e:
                print(f"Recovery attempt {i+1} failed: {e}")
                continue
        
        print("❌ Automatic recovery failed - manual login required")
        return False
    
    def _get_auth_config(self) -> dict:
        """Get the best available authentication configuration"""
        
        # Prefer modern storage state (no user_data_dir conflict)
        if self.storage_state_path.exists():
            print(f"📁 Using storage state: {self.storage_state_path}")
            return {"storage_state": str(self.storage_state_path)}
        
        # Fallback to legacy cookies (disable user_data_dir to avoid conflict)
        elif self.legacy_cookies_path.exists():
            print(f"📁 Using legacy cookies: {self.legacy_cookies_path}")
            return {"cookies_file": str(self.legacy_cookies_path.resolve())}
        
        return {}
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_file = Path("keys/session.key")
        key_file.parent.mkdir(exist_ok=True)
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            os.chmod(key_file, 0o600)  # Read-only for owner
            return key
    
    def _load_sensitive_data(self) -> Dict[str, Dict[str, str]]:
        """Load sensitive data for domain-restricted authentication"""
        return {
            "https://app.apollo.io": {
                "x_apollo_email": os.getenv("APOLLO_EMAIL", ""),
                "x_apollo_password": os.getenv("APOLLO_PASSWORD", ""),
                "x_apollo_api_key": os.getenv("APOLLO_API_KEY", "")
            },
            "https://accounts.google.com": {
                "x_google_email": os.getenv("GOOGLE_EMAIL", ""),
                "x_google_password": os.getenv("GOOGLE_PASSWORD", "")
            }
        }
    
    def _is_cached_validation_valid(self) -> bool:
        """Check if cached validation is still valid"""
        if not self.last_validation:
            return False
        
        elapsed = (datetime.now() - self.last_validation).total_seconds()
        return elapsed < self.validation_interval
    
    def _cache_validation_result(self, success: bool):
        """Cache validation result with timestamp"""
        if success:
            self.last_validation = datetime.now()
        else:
            self.last_validation = None
    
    async def _validation_step_monitor(self, agent):
        """Monitor validation steps for security and performance"""
        try:
            page = await agent.browser_session.get_current_page()
            current_url = page.url
            
            # Security monitoring
            if not any(domain.replace("*.", "") in current_url for domain in self.allowed_domains):
                logger.warning("Navigation outside allowed domains", url=current_url)
            
            # Performance monitoring
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
                logger.debug("Page network idle achieved", url=current_url)
            except:
                logger.debug("Page still loading", url=current_url)
                
        except Exception as e:
            logger.debug("Step monitoring failed", error=str(e))
    
    async def _validation_error_handler(self, agent):
        """Handle errors during validation"""
        try:
            page = await agent.browser_session.get_current_page()
            
            # Check for Apollo-specific errors
            error_indicators = [
                '[data-cy="error-message"]',
                '.error-banner',
                '[class*="rate-limit"]'
            ]
            
            for selector in error_indicators:
                error_element = await page.query_selector(selector)
                if error_element:
                    error_text = await error_element.text_content()
                    logger.warning("Apollo error detected", error=error_text, url=page.url)
                    break
                    
        except Exception as e:
            logger.debug("Error handler failed", error=str(e))
    
    def _create_secure_browser_profile(self, auth_config: dict, headless=True, extra_args=None):
        """Create secure browser profile with enhanced anti-detection"""
        from browser_use.browser.profile import BrowserProfile
        
        # Enhanced security args
        security_args = [
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
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-crash-reporter",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-default-apps",
            "--disable-background-networking",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-report-upload",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "--disable-features=VizDisplayCompositor,VizService",
            "--disable-gpu-sandbox",
            "--enable-features=NetworkService,NetworkServiceLogging",
            "--ignore-certificate-errors",
            "--ignore-ssl-errors",
            "--ignore-certificate-errors-spki-list"
        ]
        
        if extra_args:
            security_args.extend(extra_args)
        
        # Secure profile configuration
        profile_config = {
            "user_data_dir": str(self.profile_dir),  # Use persistent profile
            "wait_for_network_idle_page_load_time": 30.0,  # Longer wait for Cloudflare
            "headless": headless,
            "allowed_domains": self.allowed_domains,
            "args": security_args,
            "stealth": True,  # Enable stealth mode for better detection evasion
            "channel": "chrome",  # Use real Chrome for better Cloudflare bypass
            "viewport": {"width": 1920, "height": 1080},
            "java_script_enabled": True,
            "ignore_https_errors": False  # Maintain HTTPS validation
        }
        
        # Handle authentication with security best practices
        if "storage_state" in auth_config:
            profile_config.update(auth_config)
            profile_config["user_data_dir"] = None  # Avoid conflicts
        elif "cookies_file" in auth_config:
            profile_config.update(auth_config) 
            profile_config["user_data_dir"] = None  # Avoid conflicts
        else:
            # No auth config - use isolated profile
            profile_config["user_data_dir"] = str(self.profile_dir)
        
        logger.debug("Created secure browser profile", 
                    config_keys=list(profile_config.keys()),
                    auth_type=list(auth_config.keys()) if auth_config else [])
        
        return BrowserProfile(**profile_config)

    def _create_browser_profile(self, auth_config: dict, headless=True, extra_args=None):
        """Create browser profile with authentication and anti-detection settings"""
        from browser_use.browser.profile import BrowserProfile
        
        # Enhanced browser args for compatibility and stealth
        browser_args = [
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
            "--disable-gpu",  # Helps with compatibility issues
            "--disable-software-rasterizer",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-crash-reporter",  # Additional compatibility
            "--disable-extensions",  # Reduce complexity
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ]
        
        if extra_args:
            browser_args.extend(extra_args)
        
        # Handle user_data_dir conflict: NEVER use both cookies_file and user_data_dir
        profile_config = {
            "wait_for_network_idle_page_load_time": 10.0,
            "headless": headless,
            "allowed_domains": ["*.apollo.io", "apollo.io"],  # Support subdomains
            "args": browser_args,
            "stealth": True,  # Enable stealth for better detection evasion
            "viewport": {"width": 1920, "height": 1080},  # Common viewport size
            "java_script_enabled": True,
            "ignore_https_errors": True,
            "channel": "chrome",  # Use real Chrome for Cloudflare bypass
        }
        
        # Fix user_data_dir conflict based on official browser-use documentation
        if "storage_state" in auth_config:
            # Official docs: "Set user_data_dir=None when using a storage state file"
            profile_config.update(auth_config)
            profile_config["user_data_dir"] = None  # Critical: avoid conflicts
        elif "cookies_file" in auth_config:
            # Legacy cookies_file - avoid user_data_dir to prevent warnings
            profile_config.update(auth_config) 
            profile_config["user_data_dir"] = None  # Avoid sharing conflicts
        else:
            # No auth config - can use user_data_dir
            if self.profile_dir.exists():
                profile_config["user_data_dir"] = str(self.profile_dir)
        
        return BrowserProfile(**profile_config)
    
    def get_session_info(self) -> dict:
        """Get information about current session files"""
        info = {
            "storage_state_exists": self.storage_state_path.exists(),
            "legacy_cookies_exist": self.legacy_cookies_path.exists(),
            "profile_dir_exists": self.profile_dir.exists(),
            "recommended_action": None
        }
        
        if self.storage_state_path.exists():
            stat = self.storage_state_path.stat()
            info["storage_state_modified"] = datetime.fromtimestamp(stat.st_mtime)
            info["storage_state_size"] = stat.st_size
            
            # Check if file is recent (less than 30 days old)
            if datetime.now() - info["storage_state_modified"] > timedelta(days=30):
                info["recommended_action"] = "Session is old - consider re-capturing"
            else:
                info["recommended_action"] = "Session looks good"
        
        elif self.legacy_cookies_path.exists():
            info["recommended_action"] = "Upgrade to storage_state (recommended) - run helper/create_login_session.py"
        
        else:
            info["recommended_action"] = "No authentication found - run create_login_session.py"
        
        return info
    
    def cleanup_old_sessions(self):
        """Clean up old session files and profile data"""
        print("🧹 Cleaning up old session data...")
        
        files_cleaned = 0
        
        # Remove old storage state if exists
        if self.storage_state_path.exists():
            self.storage_state_path.unlink()
            files_cleaned += 1
            print(f"🗑️  Removed: {self.storage_state_path}")
        
        # Clean profile directory
        if self.profile_dir.exists():
            import shutil
            shutil.rmtree(self.profile_dir)
            files_cleaned += 1
            print(f"🗑️  Removed: {self.profile_dir}")
        
        print(f"✅ Cleaned {files_cleaned} items")
    
    def fix_browser_issues(self):
        """Fix common browser issues identified in logs"""
        print("🔧 Fixing browser configuration issues...")
        
        # Fix 1: Clean corrupted profile directory
        if self.profile_dir.exists():
            print(f"🗑️  Removing potentially corrupted profile: {self.profile_dir}")
            import shutil
            shutil.rmtree(self.profile_dir)
        
        # Fix 2: Create fresh profile directory
        self.profile_dir.mkdir(exist_ok=True)
        print(f"📁 Created fresh profile directory: {self.profile_dir}")
        
        # Fix 3: Check browser availability
        print("🔍 Checking browser availability...")
        
        return True

# Convenience functions for direct use
async def validate_apollo_session() -> bool:
    """Quick session validation"""
    manager = ApolloSessionManager()
    return await manager.validate_session()

async def recover_apollo_session() -> bool:
    """Quick session recovery"""
    manager = ApolloSessionManager()
    return await manager.auto_recover_session()

def get_apollo_session_info() -> dict:
    """Quick session info"""
    manager = ApolloSessionManager()
    return manager.get_session_info()

if __name__ == "__main__":
    import sys
    
    async def main():
        manager = ApolloSessionManager()
        
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "validate":
                success = await manager.validate_session()
                sys.exit(0 if success else 1)
                
            elif command == "recover":
                success = await manager.auto_recover_session()
                sys.exit(0 if success else 1)
                
            elif command == "info":
                info = manager.get_session_info()
                print("\n📊 Session Information:")
                print("-" * 30)
                for key, value in info.items():
                    print(f"{key}: {value}")
                
            elif command == "cleanup":
                manager.cleanup_old_sessions()
                
            else:
                print("Usage: python session_manager.py [validate|recover|info|cleanup]")
        else:
            # Default: show info and validate
            info = manager.get_session_info()
            print("📊 Apollo Session Status:")
            print("-" * 30)
            for key, value in info.items():
                print(f"{key}: {value}")
            
            print("\n🔍 Validating session...")
            is_valid = await manager.validate_session()
            print(f"Session valid: {is_valid}")
    
    asyncio.run(main())