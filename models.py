"""
Pydantic models for structured output in Apollo.io automation
Following browser-use best practices for type-safe data extraction
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re


class Contact(BaseModel):
    """Individual contact information extracted from Apollo.io"""
    first_name: str = Field(description="Contact's first name")
    last_name: str = Field(description="Contact's last name")
    email: Optional[str] = Field(description="Contact's email address")
    sanitized_phone: Optional[str] = Field(description="Contact's phone number")
    title: str = Field(description="Job title")
    organization_name: str = Field(description="Company name")
    linkedin_url: Optional[str] = Field(description="LinkedIn profile URL")
    employment_history: Optional[List[Dict[str, Any]]] = Field(
        default=[], description="Array of work experiences"
    )
    
    @validator('email')
    def validate_email(cls, v):
        if v and not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('linkedin_url')
    def validate_linkedin_url(cls, v):
        if v and not v.startswith(('https://linkedin.com', 'https://www.linkedin.com')):
            raise ValueError('Invalid LinkedIn URL format')
        return v


class ContactList(BaseModel):
    """Collection of contacts with metadata"""
    contacts: List[Contact] = Field(description="List of extracted contacts")
    search_id: str = Field(description="Apollo qOrganizationSearchListId")
    total_found: int = Field(description="Total number of contacts found")
    domains_filtered: List[str] = Field(description="Company domains used in filter")
    job_titles_searched: List[str] = Field(description="Job titles included in search")
    extraction_timestamp: datetime = Field(default_factory=datetime.now)
    
    @validator('search_id')
    def validate_search_id(cls, v):
        if not v or len(v) < 10:
            raise ValueError('Invalid search ID format')
        return v


class SearchResult(BaseModel):
    """Apollo.io search operation result"""
    success: bool = Field(description="Whether the search was successful")
    search_id: Optional[str] = Field(description="Extracted qOrganizationSearchListId")
    url: str = Field(description="Final Apollo URL with search parameters")
    domains_applied: List[str] = Field(description="Domains successfully applied to filter")
    job_titles_applied: List[str] = Field(description="Job titles applied to search")
    error_message: Optional[str] = Field(description="Error details if search failed")
    execution_time_seconds: float = Field(description="Time taken for search operation")


class AuthenticationResult(BaseModel):
    """Apollo.io authentication validation result"""
    authenticated: bool = Field(description="Whether user is logged in")
    session_type: str = Field(description="Type of session (storage_state, cookies, manual)")
    session_file_path: Optional[str] = Field(description="Path to session file")
    auth_domains: List[str] = Field(description="Domains with authentication")
    expires_at: Optional[datetime] = Field(description="Session expiration time")
    validation_timestamp: datetime = Field(default_factory=datetime.now)
    
    @validator('session_type')
    def validate_session_type(cls, v):
        valid_types = ['storage_state', 'cookies_file', 'manual_login', 'unknown']
        if v not in valid_types:
            raise ValueError(f'Invalid session type. Must be one of: {valid_types}')
        return v


class BrowserConfig(BaseModel):
    """Browser configuration for Apollo.io automation"""
    headless: bool = Field(default=False, description="Run browser in headless mode")
    stealth: bool = Field(default=True, description="Enable stealth mode")
    allowed_domains: List[str] = Field(description="Domains allowed for navigation")
    user_data_dir: Optional[str] = Field(description="Browser profile directory")
    storage_state: Optional[str] = Field(description="Path to storage state file")
    wait_for_network_idle: float = Field(default=10.0, description="Network idle timeout")
    viewport_width: int = Field(default=1920, description="Browser viewport width")
    viewport_height: int = Field(default=1080, description="Browser viewport height")


class PipelineResult(BaseModel):
    """Complete Apollo.io extraction pipeline result"""
    success: bool = Field(description="Overall pipeline success")
    authentication: Optional[AuthenticationResult] = Field(default=None, description="Authentication validation result")
    search: Optional[SearchResult] = Field(default=None, description="Search operation result")
    contacts: Optional[ContactList] = Field(default=None, description="Extracted contacts data")
    apify_dataset_id: Optional[str] = Field(default=None, description="Apify dataset ID")
    apify_url: Optional[str] = Field(default=None, description="Constructed Apify scraper URL")
    execution_statistics: Dict[str, Any] = Field(description="Pipeline execution metrics")
    errors: List[str] = Field(default=[], description="List of errors encountered")
    warnings: List[str] = Field(default=[], description="List of warnings")
    pipeline_duration_seconds: float = Field(description="Total execution time")
    
    def add_error(self, error: str):
        """Add error to the pipeline result"""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")
        self.success = False
    
    def add_warning(self, warning: str):
        """Add warning to the pipeline result"""
        self.warnings.append(f"{datetime.now().isoformat()}: {warning}")


class DomainFilterResult(BaseModel):
    """Result of applying domain filters in Apollo.io"""
    success: bool = Field(description="Whether domain filtering was successful")
    domains_requested: List[str] = Field(description="Domains requested to filter")
    domains_applied: List[str] = Field(description="Domains successfully applied")
    domains_failed: List[str] = Field(default=[], description="Domains that failed to apply")
    filter_text: str = Field(description="Actual text pasted into filter")
    apollo_response_time: float = Field(description="Time for Apollo to process filter")
    url_after_filter: str = Field(description="Apollo URL after applying filter")


class ApifyScrapingResult(BaseModel):
    """Result from Apify scraping operation"""
    success: bool = Field(description="Whether scraping completed successfully")
    dataset_id: Optional[str] = Field(description="Apify dataset ID")
    total_records: int = Field(description="Total number of records scraped")
    url_scraped: str = Field(description="Apollo URL that was scraped")
    scraping_duration_seconds: float = Field(description="Time taken to scrape")
    apify_run_id: Optional[str] = Field(description="Apify run ID for tracking")
    cost_credits: Optional[float] = Field(description="Apify credits consumed")
    error_details: Optional[str] = Field(description="Error details if scraping failed")


# Output format controllers for browser-use agents
class ApolloOutputController:
    """Controller for structured output in Apollo automation"""
    
    @staticmethod
    def get_search_controller():
        """Returns controller configured for search result output"""
        from browser_use import Controller
        return Controller(output_model=SearchResult)
    
    @staticmethod
    def get_authentication_controller():
        """Returns controller configured for authentication result output"""
        from browser_use import Controller
        return Controller(output_model=AuthenticationResult)
    
    @staticmethod
    def get_domain_filter_controller():
        """Returns controller configured for domain filtering result output"""
        from browser_use import Controller
        return Controller(output_model=DomainFilterResult)