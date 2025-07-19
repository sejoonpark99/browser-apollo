"""
Comprehensive configuration management for Apollo.io automation
Following browser-use best practices for security and maintainability
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
import structlog

from exceptions import ConfigurationError, EnvironmentError

# Load environment variables
load_dotenv()
try:
    import structlog
    logger = structlog.get_logger("apollo.config")
except ImportError:
    import logging
    
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
    
    logger = LoggerWrapper("apollo.config")


@dataclass
class BrowserConfiguration:
    """Browser-specific configuration with security defaults"""
    headless: bool = False
    stealth: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    wait_for_network_idle: float = 10.0
    page_load_timeout: int = 30000
    
    # Security settings
    allowed_domains: List[str] = field(default_factory=lambda: [
        "*.apollo.io", 
        "accounts.google.com", 
        "*.googleusercontent.com"
    ])
    
    # Performance settings
    disable_images: bool = False
    disable_css: bool = False
    disable_fonts: bool = False
    
    # Anti-detection settings
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    
    def get_browser_args(self) -> List[str]:
        """Get comprehensive browser arguments for anti-detection"""
        args = [
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
            f"--user-agent={self.user_agent}"
        ]
        
        # Performance optimizations
        if self.disable_images:
            args.append("--blink-settings=imagesEnabled=false")
        if self.disable_css:
            args.append("--disable-css-inspector")
        if self.disable_fonts:
            args.append("--disable-font-loading")
            
        return args


@dataclass
class ApolloConfiguration:
    """Apollo.io specific configuration"""
    max_contacts: int = 200
    job_titles: List[str] = field(default_factory=lambda: [
        "CEO", "CTO", "CFO", "VP Sales", "VP Marketing"
    ])
    
    # Rate limiting
    request_delay: float = 2.0
    max_requests_per_minute: int = 30
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 5.0
    exponential_backoff: bool = True
    
    # Data extraction settings
    extraction_timeout: int = 30
    domain_filter_timeout: int = 15
    search_id_timeout: int = 30


@dataclass
class ApifyConfiguration:
    """Apify scraper configuration"""
    actor_id: str = "jljBwyyQakqrL1wae"
    timeout: int = 300  # 5 minutes
    memory_mb: int = 1024
    
    # Output settings
    dataset_name: str = "Apollo Prospects"
    output_format: str = "json"
    
    # Scraping limits
    max_records: int = 200
    max_pages: int = 10


@dataclass
class SecurityConfiguration:
    """Security and privacy configuration"""
    enable_encryption: bool = True
    store_credentials: bool = False
    log_sensitive_data: bool = False
    
    # Session management
    session_timeout_minutes: int = 30
    auto_cleanup_sessions: bool = True
    
    # Monitoring
    capture_screenshots: bool = True
    log_navigation: bool = True
    monitor_memory: bool = True


@dataclass
class LoggingConfiguration:
    """Logging and monitoring configuration"""
    log_level: str = "INFO"
    log_format: str = "structured"
    
    # File logging
    enable_file_logging: bool = True
    log_directory: str = "logs"
    max_log_size_mb: int = 100
    backup_count: int = 5
    
    # Monitoring
    enable_performance_logging: bool = True
    enable_error_screenshots: bool = True
    enable_step_monitoring: bool = True


class ApolloConfigManager:
    """Centralized configuration management with validation"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file) if config_file else Path("config/apollo_config.json")
        self.config_file.parent.mkdir(exist_ok=True)
        
        # Load configurations
        self.browser = BrowserConfiguration()
        self.apollo = ApolloConfiguration()
        self.apify = ApifyConfiguration()
        self.security = SecurityConfiguration()
        self.logging = LoggingConfiguration()
        
        # Load from file if exists
        if self.config_file.exists():
            self.load_from_file()
        
        # Override with environment variables
        self.load_from_environment()
        
        # Validate configuration
        self.validate_configuration()
    
    def load_from_file(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update configurations from file
            if "browser" in config_data:
                for key, value in config_data["browser"].items():
                    if hasattr(self.browser, key):
                        setattr(self.browser, key, value)
            
            if "apollo" in config_data:
                for key, value in config_data["apollo"].items():
                    if hasattr(self.apollo, key):
                        setattr(self.apollo, key, value)
            
            if "apify" in config_data:
                for key, value in config_data["apify"].items():
                    if hasattr(self.apify, key):
                        setattr(self.apify, key, value)
            
            if "security" in config_data:
                for key, value in config_data["security"].items():
                    if hasattr(self.security, key):
                        setattr(self.security, key, value)
            
            if "logging" in config_data:
                for key, value in config_data["logging"].items():
                    if hasattr(self.logging, key):
                        setattr(self.logging, key, value)
            
            logger.info("Configuration loaded from file", file=str(self.config_file))
            
        except Exception as e:
            logger.warning("Failed to load configuration file", 
                         file=str(self.config_file), 
                         error=str(e))
    
    def load_from_environment(self):
        """Load configuration from environment variables"""
        env_mappings = {
            # Browser configuration
            "APOLLO_HEADLESS": ("browser", "headless", bool),
            "APOLLO_STEALTH": ("browser", "stealth", bool),
            "APOLLO_VIEWPORT_WIDTH": ("browser", "viewport_width", int),
            "APOLLO_VIEWPORT_HEIGHT": ("browser", "viewport_height", int),
            
            # Apollo configuration
            "APOLLO_MAX_CONTACTS": ("apollo", "max_contacts", int),
            "APOLLO_REQUEST_DELAY": ("apollo", "request_delay", float),
            "APOLLO_MAX_RETRIES": ("apollo", "max_retries", int),
            
            # Apify configuration
            "APIFY_ACTOR_ID": ("apify", "actor_id", str),
            "APIFY_TIMEOUT": ("apify", "timeout", int),
            "APIFY_MEMORY_MB": ("apify", "memory_mb", int),
            
            # Security configuration
            "APOLLO_ENABLE_ENCRYPTION": ("security", "enable_encryption", bool),
            "APOLLO_SESSION_TIMEOUT": ("security", "session_timeout_minutes", int),
            
            # Logging configuration
            "APOLLO_LOG_LEVEL": ("logging", "log_level", str),
            "APOLLO_LOG_DIRECTORY": ("logging", "log_directory", str),
        }
        
        for env_var, (section, key, value_type) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Convert to appropriate type
                    if value_type == bool:
                        converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        converted_value = int(env_value)
                    elif value_type == float:
                        converted_value = float(env_value)
                    else:
                        converted_value = env_value
                    
                    # Set the value
                    config_section = getattr(self, section)
                    setattr(config_section, key, converted_value)
                    
                    logger.debug("Environment variable loaded", 
                               var=env_var, 
                               section=section, 
                               key=key, 
                               value=converted_value)
                    
                except (ValueError, TypeError) as e:
                    logger.warning("Failed to parse environment variable", 
                                 var=env_var, 
                                 value=env_value, 
                                 error=str(e))
    
    def validate_configuration(self):
        """Validate configuration values"""
        errors = []
        
        # Validate required environment variables
        required_env_vars = [
            "OPENAI_API_KEY",
            "APIFY_TOKEN"
        ]
        
        for var in required_env_vars:
            if not os.getenv(var):
                errors.append(f"Missing required environment variable: {var}")
        
        # Validate browser configuration
        if self.browser.viewport_width < 800 or self.browser.viewport_width > 3840:
            errors.append("Browser viewport width must be between 800 and 3840")
        
        if self.browser.viewport_height < 600 or self.browser.viewport_height > 2160:
            errors.append("Browser viewport height must be between 600 and 2160")
        
        if self.browser.wait_for_network_idle < 1.0 or self.browser.wait_for_network_idle > 60.0:
            errors.append("Network idle timeout must be between 1.0 and 60.0 seconds")
        
        # Validate Apollo configuration
        if self.apollo.max_contacts < 1 or self.apollo.max_contacts > 1000:
            errors.append("Max contacts must be between 1 and 1000")
        
        if self.apollo.max_retries < 0 or self.apollo.max_retries > 10:
            errors.append("Max retries must be between 0 and 10")
        
        if not self.apollo.job_titles:
            errors.append("At least one job title must be specified")
        
        # Validate Apify configuration
        if self.apify.timeout < 60 or self.apify.timeout > 3600:
            errors.append("Apify timeout must be between 60 and 3600 seconds")
        
        if self.apify.memory_mb < 512 or self.apify.memory_mb > 8192:
            errors.append("Apify memory must be between 512 and 8192 MB")
        
        # Validate paths
        if self.logging.enable_file_logging:
            log_dir = Path(self.logging.log_directory)
            try:
                log_dir.mkdir(exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create log directory {log_dir}: {e}")
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            raise ConfigurationError(
                "configuration", 
                error_message,
                context={"errors": errors}
            )
        
        logger.info("Configuration validation passed")
    
    def save_to_file(self):
        """Save current configuration to file"""
        config_data = {
            "browser": {
                "headless": self.browser.headless,
                "stealth": self.browser.stealth,
                "viewport_width": self.browser.viewport_width,
                "viewport_height": self.browser.viewport_height,
                "wait_for_network_idle": self.browser.wait_for_network_idle,
                "allowed_domains": self.browser.allowed_domains,
                "disable_images": self.browser.disable_images,
                "disable_css": self.browser.disable_css,
                "disable_fonts": self.browser.disable_fonts
            },
            "apollo": {
                "max_contacts": self.apollo.max_contacts,
                "job_titles": self.apollo.job_titles,
                "request_delay": self.apollo.request_delay,
                "max_requests_per_minute": self.apollo.max_requests_per_minute,
                "max_retries": self.apollo.max_retries,
                "retry_delay": self.apollo.retry_delay,
                "exponential_backoff": self.apollo.exponential_backoff
            },
            "apify": {
                "actor_id": self.apify.actor_id,
                "timeout": self.apify.timeout,
                "memory_mb": self.apify.memory_mb,
                "max_records": self.apify.max_records,
                "max_pages": self.apify.max_pages
            },
            "security": {
                "enable_encryption": self.security.enable_encryption,
                "store_credentials": self.security.store_credentials,
                "log_sensitive_data": self.security.log_sensitive_data,
                "session_timeout_minutes": self.security.session_timeout_minutes,
                "auto_cleanup_sessions": self.security.auto_cleanup_sessions
            },
            "logging": {
                "log_level": self.logging.log_level,
                "log_format": self.logging.log_format,
                "enable_file_logging": self.logging.enable_file_logging,
                "log_directory": self.logging.log_directory,
                "enable_performance_logging": self.logging.enable_performance_logging,
                "enable_error_screenshots": self.logging.enable_error_screenshots
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info("Configuration saved to file", file=str(self.config_file))
    
    def get_browser_profile_config(self) -> Dict[str, Any]:
        """Get browser profile configuration for browser-use"""
        return {
            "headless": self.browser.headless,
            "stealth": self.browser.stealth,
            "viewport": {
                "width": self.browser.viewport_width,
                "height": self.browser.viewport_height
            },
            "wait_for_network_idle_page_load_time": self.browser.wait_for_network_idle,
            "allowed_domains": self.browser.allowed_domains,
            "args": self.browser.get_browser_args(),
            "java_script_enabled": True,
            "ignore_https_errors": False,
            "channel": "chromium"
        }
    
    def get_sensitive_data_config(self) -> Dict[str, Dict[str, str]]:
        """Get sensitive data configuration for browser-use"""
        if not self.security.store_credentials:
            return {}
        
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
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging"""
        return {
            "browser": {
                "headless": self.browser.headless,
                "stealth": self.browser.stealth,
                "viewport": f"{self.browser.viewport_width}x{self.browser.viewport_height}",
                "domains": len(self.browser.allowed_domains)
            },
            "apollo": {
                "max_contacts": self.apollo.max_contacts,
                "job_titles": len(self.apollo.job_titles),
                "max_retries": self.apollo.max_retries
            },
            "apify": {
                "actor_id": self.apify.actor_id,
                "timeout": self.apify.timeout,
                "memory_mb": self.apify.memory_mb
            },
            "security": {
                "encryption": self.security.enable_encryption,
                "session_timeout": self.security.session_timeout_minutes
            }
        }


# Global configuration instance
config_manager = ApolloConfigManager()

# Convenience functions
def get_config() -> ApolloConfigManager:
    """Get the global configuration manager instance"""
    return config_manager

def reload_config():
    """Reload configuration from files and environment"""
    global config_manager
    config_manager = ApolloConfigManager()
    logger.info("Configuration reloaded")

def save_config():
    """Save current configuration to file"""
    config_manager.save_to_file()