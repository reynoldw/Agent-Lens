"""
Enhanced Browser Automation for E-commerce Website Simulation.

This module contains the PersonaBasedBrowser class that provides
persona-specific browser automation capabilities.
"""

from typing import Dict, List, Any, Optional
import time
import random
import os
from playwright.sync_api import Page, BrowserContext, ElementHandle


class PersonaBasedBrowser:
    """Enhanced browser automation based on persona characteristics."""
    
    def __init__(self, browser_context: BrowserContext, persona: Dict[str, Any], screenshots_dir: str = "screenshots"):
        """
        Initialize the persona-based browser.
        
        Args:
            browser_context: The Playwright browser context
            persona: The persona dictionary
            screenshots_dir: Directory to save screenshots
        """
        self.context = browser_context
        self.page = None
        self.persona = persona
        self.screenshots_dir = screenshots_dir
        
        # Create screenshots directory if it doesn't exist
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Extract persona characteristics for browser behavior
        self.tech_proficiency = self._get_nested_value(persona, "technical.proficiency", 5)
        self.patience_level = self._get_nested_value(persona, "e_commerce_specific.patience_level", 5)
        self.attention_span = 10 - max(1, min(10, (75 - self._get_nested_value(persona, "demographics.age", 35)) / 10))
        
        # Set up tracking
        self.events = []
        self.last_action_time = time.time()
        self.page_load_times = {}
        self.navigation_history = []
        self.frustration_indicators = 0
        
        # Current URL
        self.current_url = ""
        
        # Initialize the page
        self._initialize_page()
        
        # Configurable selectors for different site types
        self.selector_config = self._get_default_selector_config()
    
    def _get_default_selector_config(self) -> Dict[str, Dict[str, List[str]]]:
        """Get default selector configurations for different site types."""
        return {
            "default": {
                "search_inputs": [
                    'input[type="search"]',
                    'input[placeholder*="search" i]',
                    'input[placeholder*="find" i]',
                    'input[name*="search" i]',
                    'input[id*="search" i]',
                    'input[class*="search" i]',
                    '.search-input',
                    '#search'
                ],
                "search_buttons": [
                    'button[type="submit"]',
                    'button.search-button',
                    'button[aria-label*="search" i]',
                    'input[type="submit"]'
                ],
                "category_links": [
                    'a[href*="category"]',
                    'a[href*="department"]',
                    '.category-link',
                    '.department-link',
                    'nav a'
                ],
                "product_links": [
                    '.product-card',
                    '.product-link',
                    'a[href*="product"]',
                    '.item-card'
                ],
                "add_to_cart_buttons": [
                    'button[id*="add-to-cart"]',
                    'button[class*="add-to-cart"]',
                    'button:has-text("Add to Cart")',
                    'button:has-text("Buy Now")',
                    'button.buy-button'
                ],
                "checkout_buttons": [
                    'a[href*="checkout"]',
                    'button:has-text("Checkout")',
                    'button:has-text("Proceed to Checkout")',
                    '.checkout-button'
                ]
            },
            # Add site-specific configurations here as needed
            "shopify": {
                "search_inputs": [
                    'input[name="q"]',
                    'input[aria-label="Search"]'
                ],
                "add_to_cart_buttons": [
                    'button[name="add"]',
                    'button.product-form__submit'
                ]
            },
            "woocommerce": {
                "add_to_cart_buttons": [
                    'button.add_to_cart_button',
                    'button.single_add_to_cart_button'
                ],
                "checkout_buttons": [
                    'a.checkout-button',
                    '.wc-proceed-to-checkout'
                ]
            }
        }
    
    def set_selector_config_for_site(self, site_type: str):
        """Set the selector configuration for a specific site type."""
        if site_type in self.selector_config:
            # Use site-specific config but fall back to default for missing selectors
            default_config = self.selector_config["default"]
            site_config = self.selector_config[site_type]
            
            # Merge configurations
            for selector_type in default_config:
                if selector_type not in site_config:
                    site_config[selector_type] = default_config[selector_type]
                    
            self.current_site_config = site_config
        else:
            self.current_site_config = self.selector_config["default"]
    
    def _initialize_page(self):
        """Initialize the page with event listeners and settings."""
        self.page = self.context.new_page()
        
        # Set realistic viewport based on persona's primary device
        devices = self._get_nested_value(self.persona, "technical.devices", {})
        primary_device = max(devices.items(), key=lambda x: x[1])[0] if devices else "desktop"
        
        if primary_device == "mobile":
            self.page.set_viewport_size({"width": 375, "height": 667})
        elif primary_device == "tablet":
            self.page.set_viewport_size({"width": 768, "height": 1024})
        else:  # desktop
            self.page.set_viewport_size({"width": 1280, "height": 800})
        
        # Set default timeout based on patience level
        timeout = 30000 + (self.patience_level * 5000)  # 30-80 seconds
        self.page.set_default_timeout(timeout)
        
        # Track page load events
        self.page.on("load", lambda: self._track_event("page_load"))
        
        # Initialize behavioral tracking
        self._setup_behavioral_tracking()
        
        # Set up error handling
        self._setup_error_handling()
    
    def _setup_error_handling(self):
        """Set up error handling for the page."""
        # Handle page crash
        self.page.on("crash", lambda: self._track_event("page_crash", {"url": self.current_url}))
        
        # Handle page errors
        self.page.on("pageerror", lambda error: self._track_event("page_error", {"error": str(error)}))
    
    def is_page_valid(self) -> bool:
        """Check if the current page is valid and operational."""
        try:
            # Try a simple operation to see if the page is responsive
            self.page.evaluate('1 + 1')
            return True
        except Exception:
            return False
    
    def recover_page(self):
        """Recover from a crashed or invalid page."""
        try:
            # Close the existing page if possible
            if self.page:
                try:
                    self.page.close()
                except:
                    pass
                
            # Create a new page
            self._initialize_page()
            
            # Navigate back to the last known URL if available
            if self.current_url:
                self.navigate(self.current_url)
                
            return True
        except Exception as e:
            print(f"Failed to recover page: {e}")
            return False
    
    def ensure_valid_page(self) -> bool:
        """Ensure we have a valid page, attempting to recover if needed."""
        if not self.is_page_valid():
            return self.recover_page()
        return True
    
    def _setup_behavioral_tracking(self):
        """Set up tracking for user behavior simulation."""
        # Track mouse movements
        self.page.on("mouse", lambda: self._track_event("mouse_movement"))
        
        # Track navigation events
        self.page.on("framenavigated", lambda frame: 
                    self._track_event("navigation", {"url": frame.url}) if frame.parent_frame is None else None)
    
    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL with persona-specific behavior."""
        try:
            # Ensure we have a valid page
            if not self.ensure_valid_page():
                return {
                    "success": False,
                    "error": "Failed to recover page"
                }
                
            # Record start time
            start_time = time.time()
            
            # Add some randomized delay based on tech proficiency
            self._realistic_delay(0.5, 1.5)
            
            # Perform the navigation
            response = self.page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Update current URL
            self.current_url = url
            
            # Record load time
            load_time = time.time() - start_time
            self.page_load_times[url] = load_time
            
            # Track the navigation
            self.navigation_history.append({
                "url": url,
                "timestamp": start_time,
                "load_time": load_time,
                "status": response.status if response else None
            })
            
            # Capture screenshot
            screenshot_path = self._take_screenshot(f"navigate_{len(self.navigation_history)}")
            
            # Simulate realistic user behavior after page load
            self._simulate_post_navigation_behavior(load_time)
            
            # Detect site type and set appropriate selectors
            self._detect_and_set_site_type(url)
            
            return {
                "success": True,
                "load_time": load_time,
                "status": response.status if response else None,
                "screenshot": screenshot_path
            }
        except Exception as e:
            # Record the failure
            self.frustration_indicators += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    def _detect_and_set_site_type(self, url: str):
        """Detect the site type and set appropriate selectors."""
        try:
            # Check for common platform signatures
            html = self.page.content()
            
            if "Shopify.theme" in html or "cdn.shopify.com" in html:
                self.set_selector_config_for_site("shopify")
            elif "woocommerce" in html or "wp-content" in html:
                self.set_selector_config_for_site("woocommerce")
            else:
                # Default
                self.set_selector_config_for_site("default")
        except:
            # Fall back to default if detection fails
            self.set_selector_config_for_site("default")
    
    def find_element(self, selector: str, timeout: int = None) -> Optional[ElementHandle]:
        """Find an element with persona-specific behavior."""
        # Ensure we have a valid page
        if not self.ensure_valid_page():
            return None
            
        if timeout is None:
            # Adjust timeout based on patience level
            timeout = 1000 + (self.patience_level * 1000)  # 1-11 seconds
        
        try:
            # Add realistic delay before searching
            self._realistic_delay(0.2, 0.8)
            
            # Try different strategies based on tech proficiency
            if self.tech_proficiency > 7:
                # Tech-savvy users are more precise
                return self.page.wait_for_selector(selector, timeout=timeout)
            else:
                # Less tech-savvy users might do more visual scanning
                self._simulate_visual_scan()
                return self.page.wait_for_selector(selector, timeout=timeout)
        except Exception:
            # Increment frustration counter
            self.frustration_indicators += 1
            return None
    
    def click(self, selector: str, force: bool = False) -> bool:
        """Click an element with persona-specific behavior."""
        # Ensure we have a valid page
        if not self.ensure_valid_page():
            return False
            
        try:
            # Find the element
            element = self.find_element(selector)
            if not element:
                return False
            
            # Add realistic delay before clicking
            self._realistic_delay(0.3, 1.0)
            
            # Simulate mouse movement to element
            self._simulate_mouse_movement(element)
            
            # Perform the click
            if force:
                element.click(force=True)
            else:
                element.click()
            
            # Track the click
            self._track_event("click", {"selector": selector})
            
            return True
        except Exception:
            # Increment frustration counter
            self.frustration_indicators += 1
            return False
    
    def fill_form(self, selector: str, value: str) -> bool:
        """Fill a form field with persona-specific behavior."""
        # Ensure we have a valid page
        if not self.ensure_valid_page():
            return False
            
        try:
            # Find the element
            element = self.find_element(selector)
            if not element:
                return False
            
            # Add realistic delay before filling
            self._realistic_delay(0.3, 0.8)
            
            # Clear the field first
            element.click()
            
            # Add realistic typing delay
            typing_speed = self._calculate_typing_speed()
            
            # Type the value (simplified simulation)
            element.fill(value)
            
            # For more realistic typing simulation:
            # for char in value:
            #     element.type(char)
            #     time.sleep(typing_speed)
            
            # Track the form interaction
            self._track_event("form_fill", {
                "selector": selector,
                "length": len(value)
            })
            
            return True
        except Exception:
            # Increment frustration counter
            self.frustration_indicators += 1
            return False
    
    def search(self, query: str) -> Dict[str, Any]:
        """Perform a search with persona-specific behavior."""
        # Ensure we have a valid page
        if not self.ensure_valid_page():
            return {
                "success": False,
                "error": "Invalid page"
            }
            
        try:
            # Record start time
            start_time = time.time()
            
            # Get search input selectors based on current site config
            search_selectors = self.current_site_config.get(
                "search_inputs", 
                self.selector_config["default"]["search_inputs"]
            )
            
            # Find search input
            search_input = None
            for selector in search_selectors:
                search_input = self.find_element(selector, timeout=2000)
                if search_input:
                    break
            
            if not search_input:
                return {
                    "success": False,
                    "error": "Could not find search input"
                }
            
            # Fill the search input
            self.fill_form(search_selectors[search_selectors.index(selector)], query)
            
            # Get search button selectors based on current site config
            search_button_selectors = self.current_site_config.get(
                "search_buttons", 
                self.selector_config["default"]["search_buttons"]
            )
            
            # Find and click search button if present
            search_button = None
            for selector in search_button_selectors:
                search_button = self.find_element(selector, timeout=2000)
                if search_button:
                    self.click(selector)
                    break
            
            # If no search button found, press Enter
            if not search_button:
                self.page.keyboard.press("Enter")
            
            # Wait for search results to load
            self._realistic_delay(1.0, 3.0)
            
            # Calculate search time
            search_time = time.time() - start_time
            
            # Take screenshot
            screenshot_path = self._take_screenshot(f"search_{query.replace(' ', '_')}")
            
            return {
                "success": True,
                "search_term": query,
                "time_taken": search_time,
                "screenshot": screenshot_path
            }
        except Exception as e:
            # Increment frustration counter
            self.frustration_indicators += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_to_cart(self, product_selector: str = None) -> Dict[str, Any]:
        """Add a product to the cart with persona-specific behavior."""
        # Ensure we have a valid page
        if not self.ensure_valid_page():
            return {
                "success": False,
                "error": "Invalid page"
            }
            
        try:
            # Record start time
            start_time = time.time()
            
            # If product selector provided, click it first
            if product_selector:
                if not self.click(product_selector):
                    return {
                        "success": False,
                        "error": "Could not click product"
                    }
                # Wait for product page to load
                self._realistic_delay(1.0, 3.0)
            
            # Get add to cart button selectors
            add_to_cart_selectors = self.current_site_config.get(
                "add_to_cart_buttons", 
                self.selector_config["default"]["add_to_cart_buttons"]
            )
            
            # Try each selector
            for selector in add_to_cart_selectors:
                if self.click(selector):
                    # Wait for cart update
                    self._realistic_delay(1.0, 2.0)
                    
                    # Take screenshot
                    screenshot_path = self._take_screenshot("add_to_cart")
                    
                    return {
                        "success": True,
                        "time_taken": time.time() - start_time,
                        "screenshot": screenshot_path
                    }
            
            # If we get here, no button worked
            return {
                "success": False,
                "error": "Could not find add to cart button"
            }
        except Exception as e:
            # Increment frustration counter
            self.frustration_indicators += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    def proceed_to_checkout(self) -> Dict[str, Any]:
        """Proceed to checkout with persona-specific behavior."""
        # Ensure we have a valid page
        if not self.ensure_valid_page():
            return {
                "success": False,
                "error": "Invalid page"
            }
            
        try:
            # Record start time
            start_time = time.time()
            
            # Get checkout button selectors
            checkout_selectors = self.current_site_config.get(
                "checkout_buttons", 
                self.selector_config["default"]["checkout_buttons"]
            )
            
            # Try each selector
            for selector in checkout_selectors:
                if self.click(selector):
                    # Wait for checkout page to load
                    self._realistic_delay(1.0, 3.0)
                    
                    # Take screenshot
                    screenshot_path = self._take_screenshot("checkout")
                    
                    return {
                        "success": True,
                        "time_taken": time.time() - start_time,
                        "screenshot": screenshot_path
                    }
            
            # If we get here, no button worked
            return {
                "success": False,
                "error": "Could not find checkout button"
            }
        except Exception as e:
            # Increment frustration counter
            self.frustration_indicators += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    def scroll(self, distance: str = "medium", direction: str = "down") -> bool:
        """Scroll the page with persona-specific behavior."""
        # Ensure we have a valid page
        if not self.ensure_valid_page():
            return False
            
        try:
            # Determine scroll distance based on the parameter
            if distance == "short":
                pixels = random.randint(200, 400)
            elif distance == "medium":
                pixels = random.randint(400, 800)
            elif distance == "long":
                pixels = random.randint(800, 1500)
            else:
                pixels = int(distance) if str(distance).isdigit() else 500
            
            # Adjust direction
            if direction == "up":
                pixels = -pixels
            
            # Add realistic delay before scrolling
            self._realistic_delay(0.2, 0.5)
            
            # Perform the scroll
            self.page.evaluate(f"window.scrollBy(0, {pixels})")
            
            # Track the scroll
            self._track_event("scroll", {
                "distance": pixels,
                "direction": direction
            })
            
            # Add post-scroll delay based on attention span
            self._realistic_delay(0.5, self.attention_span * 0.5)
            
            return True
        except Exception:
            return False
    
    def _realistic_delay(self, min_seconds: float, max_seconds: float):
        """Add a realistic delay based on persona characteristics."""
        # Adjust delay based on persona's patience and tech proficiency
        patience_factor = max(0.5, min(1.5, self.patience_level / 5))
        tech_factor = max(0.7, min(1.3, 10 / self.tech_proficiency))
        
        # Calculate delay
        delay = random.uniform(min_seconds * patience_factor * tech_factor, 
                              max_seconds * patience_factor * tech_factor)
        
        # Sleep
        time.sleep(delay)
    
    def _simulate_mouse_movement(self, target_element: ElementHandle = None):
        """Simulate realistic mouse movement."""
        # Simplified simulation
        if target_element:
            try:
                # Get element position
                bounding_box = target_element.bounding_box()
                if bounding_box:
                    # Move to element center
                    self.page.mouse.move(
                        bounding_box["x"] + bounding_box["width"] / 2,
                        bounding_box["y"] + bounding_box["height"] / 2
                    )
            except:
                pass  # Ignore errors in mouse movement simulation
    
    def _simulate_visual_scan(self):
        """Simulate user visually scanning the page."""
        # Simplified visual scanning behavior
        try:
            # Get page dimensions
            dimensions = self.page.evaluate("""
                () => {
                    return {
                        width: document.documentElement.clientWidth,
                        height: document.documentElement.clientHeight
                    }
                }
            """)
            
            # Random points to look at
            scan_points = 2 + int(self.attention_span / 2)  # 2-7 points based on attention span
            
            # Simulate eye movements by moving mouse to different points
            for _ in range(scan_points):
                x = random.randint(0, dimensions["width"])
                y = random.randint(0, dimensions["height"])
                
                # Move mouse to simulate eye movement
                self.page.mouse.move(x, y)
                
                # Short delay
                time.sleep(random.uniform(0.1, 0.3) * (10 / self.tech_proficiency))
        except:
            pass  # Ignore errors in visual scan simulation
    
    def _calculate_typing_speed(self) -> float:
        """Calculate a realistic typing speed based on persona characteristics."""
        # Base typing speed (seconds per character)
        base_speed = 0.1
        
        # Adjust for tech proficiency (1-10)
        tech_adjustment = 1.5 - (self.tech_proficiency / 10)  # Tech 1=1.4x slower, Tech 10=0.5x slower
        
        # Adjust for age
        age = self._get_nested_value(self.persona, "demographics.age", 35)
        age_adjustment = 1.0
        if age < 25:
            age_adjustment = 0.8  # 20% faster
        elif age > 60:
            age_adjustment = 1.3  # 30% slower
        
        return base_speed * tech_adjustment * age_adjustment
    
    def _simulate_post_navigation_behavior(self, load_time: float):
        """Simulate behavior after navigating to a new page."""
        # Simulate frustration if page loads slowly
        if load_time > (11 - self.patience_level):
            self.frustration_indicators += 1
        
        # Scroll down a bit to scan the page
        for _ in range(min(3, max(1, int(self.attention_span / 3)))):
            self.scroll(distance="short")
            self._realistic_delay(0.5, 1.5)
    
    def _take_screenshot(self, name: str) -> str:
        """Take a screenshot and save it."""
        # Generate filename
        filename = f"{name}_{int(time.time())}.png"
        path = os.path.join(self.screenshots_dir, filename)
        
        try:
            # Take screenshot
            self.page.screenshot(path=path)
            return path
        except:
            return ""
    
    def _track_event(self, event_type: str, data: Dict[str, Any] = None):
        """Track an event during the simulation."""
        self.events.append({
            "type": event_type,
            "timestamp": time.time(),
            "time_since_last": time.time() - self.last_action_time,
            "data": data or {}
        })
        self.last_action_time = time.time()
    
    def _get_nested_value(self, data: Dict, path: str, default=None):
        """Get a value from a nested dictionary using a dot-separated path."""
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current 