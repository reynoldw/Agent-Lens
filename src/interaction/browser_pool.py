"""
Browser Pool Manager for Website Simulation System.

This module manages a pool of browser instances for efficient resource utilization.
"""

import time
import threading
import logging
from typing import Dict, List, Any, Optional, Set
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BrowserInstance:
    """Represents a managed browser instance with reference counting."""
    
    def __init__(self, browser: Browser, playwright: Playwright):
        """Initialize a browser instance."""
        self.browser = browser
        self.playwright = playwright
        self.contexts: List[BrowserContext] = []
        self.in_use = True
        self.last_used = time.time()
        self.creation_time = time.time()
    
    def create_context(self, **kwargs) -> BrowserContext:
        """Create and track a new browser context."""
        context = self.browser.new_context(**kwargs)
        self.contexts.append(context)
        return context
    
    def release_context(self, context: BrowserContext):
        """Release a browser context when done."""
        if context in self.contexts:
            try:
                context.close()
            except Exception as e:
                logger.warning(f"Error closing browser context: {e}")
            self.contexts.remove(context)
        self.last_used = time.time()
    
    def is_healthy(self) -> bool:
        """Check if the browser instance is healthy."""
        try:
            # Try a simple operation on the browser to check if it's responsive
            self.browser.contexts
            return True
        except Exception:
            return False
    
    def close(self):
        """Close all contexts and the browser."""
        # Close all contexts
        for context in list(self.contexts):
            try:
                context.close()
            except Exception as e:
                logger.warning(f"Error closing context during browser shutdown: {e}")
        self.contexts.clear()
        
        # Close browser
        try:
            self.browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")


class BrowserPool:
    """Manages a pool of browser instances for efficient resource utilization."""
    
    def __init__(self, max_browsers: int = 5, idle_timeout: int = 300, 
                 browser_type: str = "chromium", headless: bool = True):
        """
        Initialize the browser pool.
        
        Args:
            max_browsers: Maximum number of browsers to keep in the pool
            idle_timeout: Time in seconds after which to close idle browsers
            browser_type: Browser type ('chromium', 'firefox', 'webkit')
            headless: Whether to run browsers in headless mode
        """
        self.max_browsers = max_browsers
        self.idle_timeout = idle_timeout
        self.browser_type = browser_type
        self.headless = headless
        
        self.browsers: Dict[str, BrowserInstance] = {}
        self.available_browsers: Set[str] = set()
        self.lock = threading.RLock()
        
        self.maintenance_thread = threading.Thread(target=self._maintenance_worker, daemon=True)
        self.maintenance_thread.start()
        
        self._playwright = None
        logger.info(f"Browser pool initialized (max: {max_browsers}, timeout: {idle_timeout}s)")
    
    def _get_playwright(self) -> Playwright:
        """Get or initialize the playwright instance."""
        if self._playwright is None:
            self._playwright = sync_playwright().start()
        return self._playwright
    
    def get_browser_context(self, **kwargs) -> (BrowserContext, str):
        """
        Get a browser context from the pool.
        
        Args:
            **kwargs: Arguments to pass to browser.new_context()
            
        Returns:
            Tuple of (BrowserContext, browser_id)
        """
        with self.lock:
            # Try to get an available browser
            browser_id = None
            if self.available_browsers:
                # Get the most recently used browser
                browser_id = next(iter(self.available_browsers))
                self.available_browsers.remove(browser_id)
                browser_instance = self.browsers[browser_id]
                
                # Check if it's healthy
                if not browser_instance.is_healthy():
                    logger.warning(f"Browser {browser_id} is unhealthy, closing it")
                    self._close_browser(browser_id)
                    browser_id = None
            
            # Create a new browser if needed
            if browser_id is None:
                browser_id = self._create_new_browser()
            
            # Mark the browser as in use
            browser_instance = self.browsers[browser_id]
            browser_instance.in_use = True
            browser_instance.last_used = time.time()
            
            # Create and return a new context
            context = browser_instance.create_context(**kwargs)
            return context, browser_id
    
    def _create_new_browser(self) -> str:
        """Create a new browser instance."""
        # Check if we're at capacity
        if len(self.browsers) >= self.max_browsers:
            # Try to find the oldest idle browser to replace
            oldest_id = None
            oldest_time = float('inf')
            
            for bid, browser in self.browsers.items():
                if not browser.in_use and bid in self.available_browsers:
                    if browser.last_used < oldest_time:
                        oldest_id = bid
                        oldest_time = browser.last_used
            
            # Close the oldest browser if found
            if oldest_id:
                self._close_browser(oldest_id)
            else:
                # If all browsers are in use, we need to wait or raise an error
                raise RuntimeError("All browsers are in use and at maximum capacity")
        
        # Create a new browser instance
        playwright = self._get_playwright()
        browser_method = getattr(playwright, self.browser_type)
        browser = browser_method.launch(headless=self.headless)
        
        # Generate a unique ID
        browser_id = f"browser_{int(time.time())}_{id(browser)}"
        
        # Store the browser
        self.browsers[browser_id] = BrowserInstance(browser, playwright)
        logger.info(f"Created new browser: {browser_id}")
        
        return browser_id
    
    def release_browser_context(self, context: BrowserContext, browser_id: str):
        """
        Release a browser context back to the pool.
        
        Args:
            context: The browser context to release
            browser_id: The ID of the browser that created this context
        """
        with self.lock:
            if browser_id in self.browsers:
                browser = self.browsers[browser_id]
                # Release the context
                browser.release_context(context)
                # Mark the browser as available
                browser.in_use = False
                self.available_browsers.add(browser_id)
                logger.debug(f"Released browser context for {browser_id}")
            else:
                # Browser was already closed
                try:
                    context.close()
                except:
                    pass
                logger.warning(f"Attempted to release context for unknown browser: {browser_id}")
    
    def _close_browser(self, browser_id: str):
        """Close a specific browser instance."""
        with self.lock:
            if browser_id in self.browsers:
                browser = self.browsers[browser_id]
                browser.close()
                del self.browsers[browser_id]
                self.available_browsers.discard(browser_id)
                logger.info(f"Closed browser: {browser_id}")
    
    def _maintenance_worker(self):
        """Background worker to close idle browsers."""
        while True:
            try:
                # Sleep first to allow initialization
                time.sleep(30)
                
                with self.lock:
                    current_time = time.time()
                    browsers_to_close = []
                    
                    # Identify browsers to close
                    for browser_id, browser in self.browsers.items():
                        # Close browsers that have been idle for too long
                        if not browser.in_use and current_time - browser.last_used > self.idle_timeout:
                            browsers_to_close.append(browser_id)
                            logger.info(f"Marking idle browser for closure: {browser_id} (idle for {current_time - browser.last_used:.1f}s)")
                    
                    # Close identified browsers
                    for browser_id in browsers_to_close:
                        self._close_browser(browser_id)
                    
                    # Log current pool status
                    active = len(self.browsers) - len(self.available_browsers)
                    logger.debug(f"Browser pool status: {active} active, {len(self.available_browsers)} available, {len(self.browsers)} total")
            
            except Exception as e:
                logger.error(f"Error in browser pool maintenance: {e}")
    
    def shutdown(self):
        """Shut down the browser pool and release all resources."""
        with self.lock:
            logger.info("Shutting down browser pool")
            # Close all browsers
            for browser_id in list(self.browsers.keys()):
                self._close_browser(browser_id)
            
            # Stop playwright
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception as e:
                    logger.error(f"Error stopping playwright: {e}")
                self._playwright = None


# Global browser pool instance
_browser_pool = None

def get_browser_pool(max_browsers: int = 5, idle_timeout: int = 300, 
                    browser_type: str = "chromium", headless: bool = True) -> BrowserPool:
    """Get or create the global browser pool instance."""
    global _browser_pool
    if _browser_pool is None:
        _browser_pool = BrowserPool(
            max_browsers=max_browsers,
            idle_timeout=idle_timeout,
            browser_type=browser_type,
            headless=headless
        )
    return _browser_pool 