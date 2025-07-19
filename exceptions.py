"""
Custom exception hierarchy for Apollo.io automation
Following browser-use best practices for structured error handling
"""

from typing import Optional, Dict, Any
import traceback
from datetime import datetime


class ApolloAutomationError(Exception):
    """Base exception for Apollo.io automation errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = None,
        context: Dict[str, Any] = None,
        recoverable: bool = False,
        retry_after: Optional[int] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for structured logging"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "recoverable": self.recoverable,
            "retry_after": self.retry_after,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback
        }
    
    def sanitize_for_logging(self) -> Dict[str, Any]:
        """Sanitized version safe for logging (removes sensitive data)"""
        safe_dict = self.to_dict()
        
        # Remove potentially sensitive information
        if 'password' in str(safe_dict['context']).lower():
            safe_dict['context'] = "[REDACTED - Contains sensitive data]"
        if 'api_key' in str(safe_dict['context']).lower():
            safe_dict['context'] = "[REDACTED - Contains sensitive data]"
        
        return safe_dict


class AuthenticationError(ApolloAutomationError):
    """Authentication-related errors"""
    
    def __init__(self, message: str, auth_method: str = None, **kwargs):
        context = kwargs.get('context', {})
        context['auth_method'] = auth_method
        kwargs['context'] = context
        kwargs['recoverable'] = True  # Auth errors are usually recoverable
        super().__init__(message, **kwargs)


class SessionExpiredError(AuthenticationError):
    """Session has expired and needs refresh"""
    
    def __init__(self, session_type: str = None, **kwargs):
        message = f"Apollo.io session expired (type: {session_type})"
        kwargs['retry_after'] = 60  # Retry after 1 minute
        super().__init__(message, auth_method=session_type, **kwargs)


class InvalidCredentialsError(AuthenticationError):
    """Invalid login credentials provided"""
    
    def __init__(self, **kwargs):
        message = "Invalid Apollo.io login credentials"
        kwargs['recoverable'] = False  # Bad credentials aren't recoverable
        super().__init__(message, **kwargs)


class BrowserError(ApolloAutomationError):
    """Browser-related errors"""
    
    def __init__(self, message: str, browser_type: str = None, **kwargs):
        context = kwargs.get('context', {})
        context['browser_type'] = browser_type
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class BrowserLaunchError(BrowserError):
    """Browser failed to launch"""
    
    def __init__(self, browser_type: str = None, **kwargs):
        message = f"Failed to launch browser (type: {browser_type})"
        kwargs['recoverable'] = True  # Can try different browser
        super().__init__(message, browser_type=browser_type, **kwargs)


class PageLoadError(BrowserError):
    """Page failed to load"""
    
    def __init__(self, url: str, timeout: float = None, **kwargs):
        message = f"Page failed to load: {url}"
        context = kwargs.get('context', {})
        context.update({'url': url, 'timeout': timeout})
        kwargs['context'] = context
        kwargs['recoverable'] = True
        kwargs['retry_after'] = 30
        super().__init__(message, **kwargs)


class ElementNotFoundError(BrowserError):
    """Required page element not found"""
    
    def __init__(self, selector: str, page_url: str = None, **kwargs):
        message = f"Element not found: {selector}"
        context = kwargs.get('context', {})
        context.update({'selector': selector, 'page_url': page_url})
        kwargs['context'] = context
        kwargs['recoverable'] = True
        super().__init__(message, **kwargs)


class ApolloServiceError(ApolloAutomationError):
    """Apollo.io service-related errors"""
    pass


class RateLimitError(ApolloServiceError):
    """Apollo.io rate limiting detected"""
    
    def __init__(self, retry_after: int = 300, **kwargs):
        message = f"Apollo.io rate limit exceeded. Retry after {retry_after} seconds"
        kwargs['recoverable'] = True
        kwargs['retry_after'] = retry_after
        super().__init__(message, **kwargs)


class CloudflareError(ApolloServiceError):
    """Cloudflare protection detected"""
    
    def __init__(self, **kwargs):
        message = "Cloudflare protection detected. Consider using stealth mode"
        kwargs['recoverable'] = True
        kwargs['retry_after'] = 60
        super().__init__(message, **kwargs)


class ApolloUIChangeError(ApolloServiceError):
    """Apollo.io UI has changed and selectors are outdated"""
    
    def __init__(self, outdated_selector: str, **kwargs):
        message = f"Apollo.io UI changed. Selector may be outdated: {outdated_selector}"
        context = kwargs.get('context', {})
        context['outdated_selector'] = outdated_selector
        kwargs['context'] = context
        kwargs['recoverable'] = False  # Needs code update
        super().__init__(message, **kwargs)


class DataExtractionError(ApolloAutomationError):
    """Data extraction and processing errors"""
    pass


class SearchIDExtractionError(DataExtractionError):
    """Failed to extract qOrganizationSearchListId"""
    
    def __init__(self, current_url: str, **kwargs):
        message = f"Failed to extract search ID from URL: {current_url}"
        context = kwargs.get('context', {})
        context['current_url'] = current_url
        kwargs['context'] = context
        kwargs['recoverable'] = True
        super().__init__(message, **kwargs)


class DomainFilterError(DataExtractionError):
    """Failed to apply domain filters"""
    
    def __init__(self, domains: list, **kwargs):
        message = f"Failed to apply domain filters for {len(domains)} domains"
        context = kwargs.get('context', {})
        context['domains_count'] = len(domains)
        context['domains'] = domains[:5]  # Only log first 5 for brevity
        kwargs['context'] = context
        kwargs['recoverable'] = True
        super().__init__(message, **kwargs)


class ApifyError(ApolloAutomationError):
    """Apify scraper-related errors"""
    pass


class ApifyConfigError(ApifyError):
    """Apify configuration error"""
    
    def __init__(self, config_issue: str, **kwargs):
        message = f"Apify configuration error: {config_issue}"
        kwargs['recoverable'] = False  # Config errors need manual fix
        super().__init__(message, **kwargs)


class ApifyScrapingError(ApifyError):
    """Apify scraping operation failed"""
    
    def __init__(self, dataset_id: str = None, run_id: str = None, **kwargs):
        message = "Apify scraping operation failed"
        context = kwargs.get('context', {})
        context.update({'dataset_id': dataset_id, 'run_id': run_id})
        kwargs['context'] = context
        kwargs['recoverable'] = True
        kwargs['retry_after'] = 120
        super().__init__(message, **kwargs)


class ConfigurationError(ApolloAutomationError):
    """Configuration and setup errors"""
    
    def __init__(self, config_type: str, issue: str, **kwargs):
        message = f"Configuration error in {config_type}: {issue}"
        context = kwargs.get('context', {})
        context['config_type'] = config_type
        kwargs['context'] = context
        kwargs['recoverable'] = False
        super().__init__(message, **kwargs)


class EnvironmentError(ConfigurationError):
    """Environment setup errors"""
    
    def __init__(self, missing_var: str, **kwargs):
        message = f"Missing required environment variable: {missing_var}"
        context = kwargs.get('context', {})
        context['missing_variable'] = missing_var
        kwargs['context'] = context
        super().__init__("environment", message, **kwargs)


# Error handling utilities
class ErrorHandler:
    """Centralized error handling with retry logic"""
    
    def __init__(self):
        self.error_counts = {}
        self.max_retries = 3
    
    def should_retry(self, error: ApolloAutomationError) -> bool:
        """Determine if error should trigger a retry"""
        if not error.recoverable:
            return False
        
        error_key = f"{error.__class__.__name__}:{error.error_code}"
        current_count = self.error_counts.get(error_key, 0)
        
        if current_count >= self.max_retries:
            return False
        
        self.error_counts[error_key] = current_count + 1
        return True
    
    def get_retry_delay(self, error: ApolloAutomationError) -> int:
        """Get appropriate delay before retry"""
        if error.retry_after:
            return error.retry_after
        
        # Default exponential backoff
        error_key = f"{error.__class__.__name__}:{error.error_code}"
        attempt = self.error_counts.get(error_key, 1)
        return min(60, 2 ** attempt)  # Max 60 seconds
    
    def reset_error_count(self, error_class: type):
        """Reset error count for successful operations"""
        for key in list(self.error_counts.keys()):
            if key.startswith(error_class.__name__):
                del self.error_counts[key]


def handle_browser_use_errors(func):
    """Decorator to convert browser-use errors to Apollo automation errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_message = str(e).lower()
            
            # Map common browser-use errors to our exception hierarchy
            if "rate limit" in error_message:
                raise RateLimitError(context={'original_error': str(e)})
            elif "cloudflare" in error_message:
                raise CloudflareError(context={'original_error': str(e)})
            elif "timeout" in error_message or "navigation" in error_message:
                raise PageLoadError("unknown", context={'original_error': str(e)})
            elif "element" in error_message and "not found" in error_message:
                raise ElementNotFoundError("unknown", context={'original_error': str(e)})
            elif "authentication" in error_message or "login" in error_message:
                raise AuthenticationError(str(e), context={'original_error': str(e)})
            else:
                # Generic automation error for unmapped exceptions
                raise ApolloAutomationError(
                    f"Unexpected error: {str(e)}", 
                    context={'original_error': str(e), 'original_type': type(e).__name__}
                )
    
    return wrapper