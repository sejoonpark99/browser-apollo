"""
Comprehensive monitoring and lifecycle hooks for Apollo.io automation
Following browser-use best practices for observability and debugging
"""

import asyncio
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog
from urllib.parse import urlparse

from browser_use import Agent
from exceptions import RateLimitError, CloudflareError, AuthenticationError

# Setup structured logging
try:
    import structlog
    logger = structlog.get_logger("apollo.monitoring")
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
    
    logger = LoggerWrapper("apollo.monitoring")


class ApolloMonitoringSystem:
    """
    Comprehensive monitoring system for Apollo.io automation
    Implements all browser-use lifecycle hooks with Apollo-specific intelligence
    """
    
    def __init__(self):
        self.metrics = {
            "session_start": datetime.now(),
            "steps_executed": 0,
            "pages_visited": set(),
            "errors_detected": 0,
            "apollo_states_encountered": {},
            "performance_data": [],
            "security_alerts": [],
            "navigation_history": []
        }
        
        self.apollo_state_map = {
            "/login": "authentication_page",
            "/people": "people_search",
            "/contacts": "contacts_page", 
            "/companies": "companies_page",
            "/sequences": "sequences_page",
            "qOrganizationSearchListId": "filtered_search"
        }
        
        # Create monitoring directories
        self.setup_monitoring_directories()
    
    def setup_monitoring_directories(self):
        """Create directories for monitoring outputs"""
        dirs = ["logs/monitoring", "screenshots/debug", "reports/performance"]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    async def step_start_monitor(self, agent: Agent) -> None:
        """
        Comprehensive step start monitoring
        Tracks navigation, performance, and security
        """
        try:
            step_start_time = time.time()
            self.metrics["steps_executed"] += 1
            
            page = await agent.browser_session.get_current_page()
            current_url = page.url
            
            # Navigation tracking
            self.metrics["pages_visited"].add(current_url)
            self.metrics["navigation_history"].append({
                "step": self.metrics["steps_executed"],
                "url": current_url,
                "timestamp": datetime.now().isoformat(),
                "action": "step_start"
            })
            
            # Apollo state detection
            apollo_state = self._detect_apollo_state(current_url)
            if apollo_state:
                state_count = self.metrics["apollo_states_encountered"].get(apollo_state, 0)
                self.metrics["apollo_states_encountered"][apollo_state] = state_count + 1
                
                logger.info("Apollo state detected", 
                           state=apollo_state, 
                           step=self.metrics["steps_executed"],
                           url=current_url)
            
            # Performance monitoring
            try:
                # Check if page is still loading
                loading_state = await page.evaluate("document.readyState")
                network_requests = await page.evaluate("""
                    () => performance.getEntriesByType('navigation')[0] || {}
                """)
                
                perf_data = {
                    "step": self.metrics["steps_executed"],
                    "url": current_url,
                    "loading_state": loading_state,
                    "timestamp": step_start_time,
                    "dom_ready": network_requests.get("domContentLoadedEventEnd", 0),
                    "load_complete": network_requests.get("loadEventEnd", 0)
                }
                
                self.metrics["performance_data"].append(perf_data)
                
            except Exception as perf_error:
                logger.debug("Performance monitoring failed", error=str(perf_error))
            
            # Security monitoring
            await self._security_monitor(page, current_url)
            
            # Domain validation
            if not self._is_allowed_domain(current_url):
                security_alert = {
                    "type": "unauthorized_navigation",
                    "url": current_url,
                    "step": self.metrics["steps_executed"],
                    "timestamp": datetime.now().isoformat()
                }
                self.metrics["security_alerts"].append(security_alert)
                
                logger.warning("Navigation to unauthorized domain", 
                              url=current_url, 
                              step=self.metrics["steps_executed"])
            
            logger.info("Step monitoring completed", 
                       step=self.metrics["steps_executed"],
                       apollo_state=apollo_state,
                       url=current_url)
                       
        except Exception as e:
            logger.error("Step start monitoring failed", error=str(e))
    
    async def step_end_monitor(self, agent: Agent) -> None:
        """
        Comprehensive step end monitoring
        Handles errors, takes screenshots, validates results
        """
        try:
            page = await agent.browser_session.get_current_page()
            current_url = page.url
            
            # Error detection and handling
            await self._detect_and_handle_errors(page, agent)
            
            # State transition validation
            await self._validate_state_transitions(page)
            
            # Conditional screenshot capture
            await self._conditional_screenshot(page, agent)
            
            # Performance analysis
            await self._analyze_step_performance(page)
            
            # Memory usage monitoring (if available)
            await self._monitor_memory_usage(page)
            
            logger.debug("Step end monitoring completed", 
                        step=self.metrics["steps_executed"],
                        url=current_url)
                        
        except Exception as e:
            logger.error("Step end monitoring failed", error=str(e))
    
    def _detect_apollo_state(self, url: str) -> Optional[str]:
        """Detect current Apollo.io application state"""
        for pattern, state in self.apollo_state_map.items():
            if pattern in url:
                return state
        return None
    
    def _is_allowed_domain(self, url: str) -> bool:
        """Check if URL is in allowed domains"""
        allowed_domains = ["apollo.io", "google.com", "googleusercontent.com"]
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        return any(allowed in domain for allowed in allowed_domains)
    
    async def _security_monitor(self, page, url: str) -> None:
        """Monitor for security threats and suspicious activity"""
        try:
            # Check for Cloudflare protection
            cloudflare_indicators = [
                '[class*="cf-"]',
                '[id*="cf-"]',
                'text=Cloudflare',
                'text=Please wait while we check your browser'
            ]
            
            for indicator in cloudflare_indicators:
                if await page.query_selector(indicator):
                    security_alert = {
                        "type": "cloudflare_detected",
                        "url": url,
                        "indicator": indicator,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.metrics["security_alerts"].append(security_alert)
                    logger.warning("Cloudflare protection detected", indicator=indicator)
                    break
            
            # Check for rate limiting
            rate_limit_indicators = [
                '[class*="rate-limit"]',
                '[class*="Rate-limit"]', 
                'text=rate limit',
                'text=too many requests'
            ]
            
            for indicator in rate_limit_indicators:
                if await page.query_selector(indicator):
                    security_alert = {
                        "type": "rate_limit_detected",
                        "url": url,
                        "indicator": indicator,
                        "timestamp": datetime.now().isoformat()
                    }
                    self.metrics["security_alerts"].append(security_alert)
                    logger.warning("Rate limiting detected", indicator=indicator)
                    break
            
            # Check for authentication challenges
            auth_indicators = [
                'input[type="password"]',
                'text=Sign in',
                'text=Log in',
                '[data-cy="login"]'
            ]
            
            for indicator in auth_indicators:
                if await page.query_selector(indicator):
                    logger.info("Authentication page detected", indicator=indicator)
                    break
                    
        except Exception as e:
            logger.debug("Security monitoring failed", error=str(e))
    
    async def _detect_and_handle_errors(self, page, agent: Agent) -> None:
        """Detect and categorize Apollo.io errors"""
        try:
            # Apollo-specific error selectors
            error_selectors = [
                '[data-cy="error-message"]',
                '.error-banner',
                '.alert-danger',
                '[class*="error"]',
                '[role="alert"]'
            ]
            
            for selector in error_selectors:
                error_elements = await page.query_selector_all(selector)
                if error_elements:
                    for element in error_elements:
                        error_text = await element.text_content()
                        if error_text and error_text.strip():
                            self.metrics["errors_detected"] += 1
                            
                            logger.error("Apollo error detected", 
                                       error_text=error_text.strip(),
                                       selector=selector,
                                       url=page.url)
                            
                            # Take error screenshot
                            await self._capture_error_screenshot(page, error_text)
                            break
            
            # Check for JavaScript errors in console
            console_errors = await page.evaluate("""
                () => {
                    const errors = [];
                    const originalError = console.error;
                    console.error = function(...args) {
                        errors.push(args.join(' '));
                        originalError.apply(console, args);
                    };
                    return errors;
                }
            """)
            
            if console_errors:
                logger.warning("JavaScript console errors detected", 
                             errors=console_errors[:5])  # Limit to first 5
                             
        except Exception as e:
            logger.debug("Error detection failed", error=str(e))
    
    async def _validate_state_transitions(self, page) -> None:
        """Validate expected Apollo.io state transitions"""
        try:
            current_url = page.url
            current_state = self._detect_apollo_state(current_url)
            
            if not current_state:
                return
            
            # Check for successful transitions
            if current_state == "filtered_search":
                # Validate that search filters are applied
                filter_indicators = [
                    '[data-cy*="filter"]',
                    '.filter-applied',
                    '[class*="active-filter"]'
                ]
                
                has_filters = False
                for indicator in filter_indicators:
                    if await page.query_selector(indicator):
                        has_filters = True
                        break
                
                if has_filters:
                    logger.info("Search filters successfully applied")
                else:
                    logger.warning("In filtered search state but no filter indicators found")
            
            elif current_state == "people_search":
                # Validate search interface is loaded
                search_indicators = [
                    '[data-cy="search-results"]',
                    '.search-results',
                    '[class*="prospect"]'
                ]
                
                has_search_ui = False
                for indicator in search_indicators:
                    if await page.query_selector(indicator):
                        has_search_ui = True
                        break
                
                if not has_search_ui:
                    logger.warning("In people search state but search UI not detected")
                    
        except Exception as e:
            logger.debug("State transition validation failed", error=str(e))
    
    async def _conditional_screenshot(self, page, agent: Agent) -> None:
        """Take screenshots based on conditions"""
        try:
            current_url = page.url
            should_screenshot = False
            screenshot_reason = ""
            
            # Screenshot on errors
            if self.metrics["errors_detected"] > 0:
                should_screenshot = True
                screenshot_reason = "error_detected"
            
            # Screenshot on important state transitions
            apollo_state = self._detect_apollo_state(current_url)
            if apollo_state in ["filtered_search", "authentication_page"]:
                should_screenshot = True
                screenshot_reason = f"state_{apollo_state}"
            
            # Screenshot on security alerts
            if len(self.metrics["security_alerts"]) > 0:
                should_screenshot = True
                screenshot_reason = "security_alert"
            
            if should_screenshot:
                timestamp = int(time.time())
                filename = f"apollo_{screenshot_reason}_{timestamp}.png"
                screenshot_path = Path(f"screenshots/debug/{filename}")
                
                await page.screenshot(path=str(screenshot_path))
                logger.info("Debug screenshot captured", 
                           path=str(screenshot_path), 
                           reason=screenshot_reason)
                           
        except Exception as e:
            logger.debug("Screenshot capture failed", error=str(e))
    
    async def _capture_error_screenshot(self, page, error_text: str) -> None:
        """Capture screenshot specifically for errors"""
        try:
            timestamp = int(time.time())
            # Sanitize error text for filename
            safe_error = "".join(c for c in error_text[:30] if c.isalnum() or c in "-_")
            filename = f"error_{safe_error}_{timestamp}.png"
            screenshot_path = Path(f"screenshots/debug/{filename}")
            
            await page.screenshot(path=str(screenshot_path))
            logger.info("Error screenshot captured", 
                       path=str(screenshot_path), 
                       error_preview=error_text[:50])
                       
        except Exception as e:
            logger.debug("Error screenshot failed", error=str(e))
    
    async def _analyze_step_performance(self, page) -> None:
        """Analyze performance metrics for current step"""
        try:
            # Get performance timing data
            timing_data = await page.evaluate("""
                () => {
                    const nav = performance.getEntriesByType('navigation')[0];
                    const paint = performance.getEntriesByType('paint');
                    
                    return {
                        navigation: nav ? {
                            domContentLoaded: nav.domContentLoadedEventEnd - nav.navigationStart,
                            loadComplete: nav.loadEventEnd - nav.navigationStart,
                            firstByte: nav.responseStart - nav.navigationStart
                        } : null,
                        paint: paint.reduce((acc, entry) => {
                            acc[entry.name] = entry.startTime;
                            return acc;
                        }, {})
                    };
                }
            """)
            
            if timing_data["navigation"]:
                nav_timing = timing_data["navigation"]
                
                # Log slow page loads
                if nav_timing["loadComplete"] > 10000:  # > 10 seconds
                    logger.warning("Slow page load detected", 
                                 load_time=nav_timing["loadComplete"],
                                 url=page.url)
                
                # Log performance data
                logger.debug("Performance timing", 
                           dom_ready=nav_timing["domContentLoaded"],
                           load_complete=nav_timing["loadComplete"],
                           first_byte=nav_timing["firstByte"])
                           
        except Exception as e:
            logger.debug("Performance analysis failed", error=str(e))
    
    async def _monitor_memory_usage(self, page) -> None:
        """Monitor browser memory usage if available"""
        try:
            memory_info = await page.evaluate("""
                () => {
                    if ('memory' in performance) {
                        return {
                            used: performance.memory.usedJSHeapSize,
                            total: performance.memory.totalJSHeapSize,
                            limit: performance.memory.jsHeapSizeLimit
                        };
                    }
                    return null;
                }
            """)
            
            if memory_info:
                used_mb = memory_info["used"] / 1024 / 1024
                total_mb = memory_info["total"] / 1024 / 1024
                
                # Log high memory usage
                if used_mb > 100:  # > 100MB
                    logger.warning("High memory usage detected", 
                                 used_mb=round(used_mb, 2),
                                 total_mb=round(total_mb, 2))
                
                logger.debug("Memory usage", 
                           used_mb=round(used_mb, 2),
                           total_mb=round(total_mb, 2))
                           
        except Exception as e:
            logger.debug("Memory monitoring failed", error=str(e))
    
    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        session_duration = (datetime.now() - self.metrics["session_start"]).total_seconds()
        
        report = {
            "session_summary": {
                "start_time": self.metrics["session_start"].isoformat(),
                "duration_seconds": session_duration,
                "steps_executed": self.metrics["steps_executed"],
                "pages_visited": len(self.metrics["pages_visited"]),
                "errors_detected": self.metrics["errors_detected"],
                "security_alerts": len(self.metrics["security_alerts"])
            },
            "apollo_states": self.metrics["apollo_states_encountered"],
            "navigation_summary": {
                "unique_pages": list(self.metrics["pages_visited"]),
                "navigation_history": self.metrics["navigation_history"][-10:]  # Last 10
            },
            "performance_summary": {
                "avg_steps_per_minute": self.metrics["steps_executed"] / (session_duration / 60) if session_duration > 0 else 0,
                "performance_issues": [
                    p for p in self.metrics["performance_data"] 
                    if p.get("load_complete", 0) > 10000
                ]
            },
            "security_summary": {
                "alerts": self.metrics["security_alerts"],
                "unauthorized_navigations": [
                    alert for alert in self.metrics["security_alerts"] 
                    if alert["type"] == "unauthorized_navigation"
                ]
            }
        }
        
        return report
    
    def save_monitoring_report(self) -> str:
        """Save monitoring report to file"""
        report = self.generate_monitoring_report()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(f"reports/performance/apollo_monitoring_{timestamp}.json")
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info("Monitoring report saved", path=str(report_path))
        return str(report_path)


# Factory function to create monitoring hooks
def create_apollo_monitoring_hooks():
    """Create monitoring system and return hook functions"""
    monitoring = ApolloMonitoringSystem()
    
    return {
        "step_start": monitoring.step_start_monitor,
        "step_end": monitoring.step_end_monitor,
        "monitoring_system": monitoring
    }