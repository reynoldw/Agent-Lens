from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright
from dataclasses import dataclass
from src.persona.generator import Persona
import time
import random
from urllib.parse import urlparse
import re

@dataclass
class SimulationResult:
    """Stores results from a website interaction simulation."""
    website_url: str
    navigation_score: float
    design_score: float
    findability_score: float
    load_times: Dict[str, float]
    issues: List[str]
    successful_actions: List[str]
    failed_actions: List[str]
    accessibility_issues: List[str]

class WebsiteSimulator:
    """Simulates user interactions with e-commerce websites."""
    
    def __init__(self):
        """Initialize the simulator."""
        self.results = []
    
    def simulate(self, url: str, persona) -> Dict:
        """Run a full simulation of user interactions based on persona."""
        # Convert persona to dictionary if it's not already
        if not isinstance(persona, dict):
            persona = vars(persona)
            
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Create browser context with appropriate settings
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            # Extract persona attributes for simulation customization
            demographics = persona.get('demographics', {})
            tech_profile = persona.get('technical', {})
            shopping = persona.get('shopping_behavior', {})
            accessibility = persona.get('accessibility_needs', [])
            goals = persona.get('goals', {})
            
            # Extract key attributes with defaults
            name = demographics.get('name', 'Unknown User')
            age = demographics.get('age', 35)
            tech_proficiency = tech_profile.get('proficiency', 5)
            patience_level = persona.get('e_commerce_specific', {}).get('patience_level', 5)
            preferred_categories = shopping.get('product_categories', [])
            if not preferred_categories and 'preferred_categories' in persona:
                preferred_categories = persona['preferred_categories']
            
            # Determine device based on persona's device preferences
            devices = tech_profile.get('devices', {})
            if devices:
                # Find the device with highest percentage
                primary_device = max(devices.items(), key=lambda x: x[1])[0] if devices else 'desktop'
            else:
                primary_device = 'desktop'
                
            # Adjust viewport based on primary device
            if primary_device == 'mobile':
                context.close()
                context = browser.new_context(
                    viewport={'width': 375, 'height': 667},
                    user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
                )
            elif primary_device == 'tablet':
                context.close()
                context = browser.new_context(
                    viewport={'width': 768, 'height': 1024},
                    user_agent='Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
                )
                
            page = context.new_page()
            # Set default timeout for all operations
            page.set_default_timeout(60000)
            
            # Initialize tracking variables
            load_times = {}
            successful_actions = []
            failed_actions = []
            issues = []
            accessibility_issues = []
            
            # Initialize behavioral data tracking
            behavioral_data = {
                'mouse_movements': [],
                'scroll_patterns': [],
                'time_spent': {},
                'clicks': [],
                'hover_events': [],
                'form_interactions': [],
                'page_visibility': []
            }
            
            # Set up event listeners for behavioral data
            self._setup_behavioral_tracking(page, behavioral_data)
            
            try:
                # Record initial page load time
                print(f"Loading website {url} for {name} with tech proficiency {tech_proficiency}")
                start_time = time.time()
                
                # Set a longer timeout for initial page load
                try:
                    page.goto(url, wait_until='networkidle', timeout=60000)
                    load_time = time.time() - start_time
                    load_times['initial_load'] = load_time
                    successful_actions.append("Initial page load")
                    
                    # Record time spent on homepage
                    behavioral_data['time_spent']['homepage'] = {
                        'start_time': start_time,
                        'end_time': time.time(),
                        'duration': load_time
                    }
                    
                    # Check if load time is too slow based on patience level
                    if load_time > (11 - patience_level):
                        issues.append(f"Page load time ({load_time:.2f}s) exceeds persona's patience threshold")
                except Exception as e:
                    failed_actions.append("Initial page load failed")
                    issues.append(f"Failed to load page: {str(e)}")
                    # Return early if we can't even load the page
                    return {
                        'website_url': url,
                        'navigation_score': 0,
                        'design_score': 0,
                        'findability_score': 0,
                        'load_times': {'initial_load_failed': time.time() - start_time},
                        'issues': [f"Critical error: Failed to load page - {str(e)}"],
                        'successful_actions': [],
                        'failed_actions': ["Initial page load failed"],
                        'accessibility_issues': [],
                        'behavioral_data': behavioral_data,
                        'interaction_data': {
                            'error': str(e),
                            'tech_proficiency': tech_proficiency,
                            'primary_device': primary_device
                        }
                    }
                
                # Analyze website type and structure
                website_type = self._analyze_website_type(page, url)
                print(f"Detected website type: {website_type}")
                
                # Take screenshot for analysis
                screenshot_path = f"screenshot_{len(self.results)}.png"
                page.screenshot(path=screenshot_path)
                
                # Analyze page structure
                page_title = page.title()
                if not page_title:
                    issues.append("Missing page title")
                
                # Simulate initial browsing behavior
                self._simulate_browsing_behavior(page, tech_proficiency, patience_level, behavioral_data)
                
                # Check for mobile-friendliness if on mobile
                if primary_device == 'mobile':
                    viewport_width = page.viewport_size['width']
                    content_width = page.evaluate('document.documentElement.scrollWidth')
                    if content_width > viewport_width * 1.1:  # 10% tolerance
                        issues.append("Page not properly optimized for mobile - horizontal scrolling required")
                
                # Simulate navigation based on tech proficiency and patience
                navigation_results = self._simulate_navigation(
                    page, 
                    tech_proficiency=tech_proficiency,
                    patience_level=patience_level,
                    website_type=website_type,
                    load_times=load_times, 
                    successful_actions=successful_actions, 
                    failed_actions=failed_actions,
                    behavioral_data=behavioral_data
                )
                
                # Add any navigation issues
                issues.extend(navigation_results.get('issues', []))
                
                # Simulate search based on preferred categories and tech proficiency
                if preferred_categories:
                    # Use website type to determine search terms
                    search_terms = self._generate_search_terms(preferred_categories, website_type)
                    
                    search_results = self._simulate_search(
                        page, 
                        search_terms=search_terms,
                        tech_proficiency=tech_proficiency, 
                        website_type=website_type,
                        load_times=load_times, 
                        successful_actions=successful_actions, 
                        failed_actions=failed_actions,
                        behavioral_data=behavioral_data
                    )
                    
                    # Add any search issues
                    issues.extend(search_results.get('issues', []))
                
                # Simulate product interaction based on persona's goals and preferences
                interaction_results = self._simulate_product_interaction(
                    page, 
                    tech_proficiency=tech_proficiency,
                    patience_level=patience_level,
                    website_type=website_type,
                    price_sensitivity=shopping.get('price_sensitivity', 'Mid-range'),
                    successful_actions=successful_actions, 
                    failed_actions=failed_actions,
                    behavioral_data=behavioral_data
                )
                
                # Add any interaction issues
                issues.extend(interaction_results.get('issues', []))
                
                # Check for accessibility issues based on persona needs
                if any('visual' in need.lower() for need in accessibility):
                    visual_issues = self._check_visual_accessibility(page)
                    accessibility_issues.extend(visual_issues)
                    if visual_issues:
                        issues.append(f"Visual accessibility issues detected: {len(visual_issues)} issues")
                
                if any('motor' in need.lower() for need in accessibility):
                    motor_issues = self._check_motor_accessibility(page)
                    accessibility_issues.extend(motor_issues)
                    if motor_issues:
                        issues.append(f"Motor accessibility issues detected: {len(motor_issues)} issues")
                
                # Calculate scores based on persona characteristics
                navigation_score = self._calculate_navigation_score(
                    successful_actions, 
                    failed_actions,
                    tech_proficiency=tech_proficiency
                )
                
                design_score = self._calculate_design_score(
                    page, 
                    age=age,
                    tech_proficiency=tech_proficiency,
                    device=primary_device
                )
                
                findability_score = self._calculate_findability_score(
                    successful_actions, 
                    failed_actions,
                    preferred_categories=preferred_categories
                )
                
                # Generate behavioral insights
                behavioral_insights = self._analyze_behavioral_data(behavioral_data, persona)
                
                # Create result object with persona-specific insights
                result = {
                    'website_url': url,
                    'navigation_score': navigation_score,
                    'design_score': design_score,
                    'findability_score': findability_score,
                    'load_times': load_times,
                    'issues': issues,
                    'successful_actions': successful_actions,
                    'failed_actions': failed_actions,
                    'accessibility_issues': accessibility_issues,
                    'behavioral_data': behavioral_data,
                    'behavioral_insights': behavioral_insights,
                    'interaction_data': {
                        'pages_visited': len(successful_actions),
                        'errors_encountered': len(failed_actions),
                        'tech_proficiency': tech_proficiency,
                        'primary_device': primary_device,
                        'preferred_categories': preferred_categories,
                        'patience_level': patience_level,
                        'age': age,
                        'name': name,
                        'website_type': website_type
                    }
                }
                
                self.results.append(result)
                return result
                
            except Exception as e:
                issues.append(f"Simulation error: {str(e)}")
                return {
                    'website_url': url,
                    'navigation_score': 0,
                    'design_score': 0,
                    'findability_score': 0,
                    'load_times': load_times,
                    'issues': issues,
                    'successful_actions': successful_actions,
                    'failed_actions': failed_actions,
                    'accessibility_issues': accessibility_issues,
                    'behavioral_data': behavioral_data,
                    'interaction_data': {
                        'error': str(e),
                        'tech_proficiency': tech_proficiency,
                        'primary_device': primary_device,
                        'name': name
                    }
                }
            finally:
                browser.close()
    
    def _simulate_navigation(self, page, tech_proficiency: int, patience_level: int, 
                           website_type: str, load_times: Dict[str, float], successful_actions: List[str], 
                           failed_actions: List[str], behavioral_data: Dict):
        """Simulate basic navigation interactions based on persona characteristics and website type."""
        issues = []
        try:
            # Find and interact with main navigation elements
            nav_elements = page.query_selector_all('nav a, .nav a, .menu a, .navigation a, header a, .navbar a, .header a, .top-menu a')
            
            # If no navigation elements found through common selectors, try more generic approach
            if not nav_elements or len(nav_elements) < 2:
                nav_elements = page.query_selector_all('a[href]:not([href^="#"]):not([href^="javascript"])')
            
            # Filter to likely navigation elements (short text, near top of page)
            nav_links = []
            for el in nav_elements:
                try:
                    text = el.inner_text().strip()
                    if text and len(text) < 30:  # Likely a navigation link
                        nav_links.append((el, text))
                except:
                    continue
            
            # Prioritize navigation links based on website type
            priority_links = []
            if website_type.startswith("ecommerce"):
                priority_terms = ['shop', 'product', 'category', 'collection', 'catalog', 'store']
                for el, text in nav_links:
                    if any(term.lower() in text.lower() for term in priority_terms):
                        priority_links.append((el, text))
            
            # If we found priority links, use those first
            if priority_links:
                nav_links_to_click = priority_links[:3]  # Limit to 3 priority links
                nav_links_to_click.extend([(el, text) for el, text in nav_links if (el, text) not in priority_links][:2])  # Add 2 more regular links
            else:
                # Limit based on tech proficiency (less tech-savvy users explore less)
                max_links = max(1, min(5, int(tech_proficiency / 2)))
                nav_links_to_click = nav_links[:max_links] if nav_links else []
            
            if not nav_links_to_click:
                failed_actions.append("Could not find navigation elements")
                issues.append("Navigation elements not easily identifiable")
            else:
                successful_actions.append(f"Found {len(nav_links_to_click)} navigation elements")
                
                # Click on navigation links based on tech proficiency and patience
                for i, (link, link_text) in enumerate(nav_links_to_click):
                    try:
                        # Simulate click with appropriate timeout based on patience
                        timeout = max(10000, 30000 - (patience_level * 2000))
                        start_time = time.time()
                        
                        # Check if link is visible and clickable
                        is_visible = link.is_visible()
                        if not is_visible:
                            failed_actions.append(f"Navigation element '{link_text}' is not visible")
                            continue
                        
                        # Try to navigate in the same page first
                        try:
                            # Get the href attribute
                            href = link.get_attribute('href')
                            if not href:
                                failed_actions.append(f"Navigation element '{link_text}' has no href")
                                continue
                                
                            # Navigate to the URL directly instead of clicking
                            page.goto(href, timeout=timeout)
                            load_time = time.time() - start_time
                            load_times[f'nav_{i}'] = load_time
                            successful_actions.append(f"Navigated to {link_text}")
                            
                            # Check load time against patience
                            if load_time > (11 - patience_level):
                                issues.append(f"Navigation to {link_text} took {load_time:.2f}s, exceeding patience threshold")
                                
                            # Go back to the main page
                            page.go_back()
                            
                        except Exception as e:
                            print(f"Navigation error for {link_text}: {e}")
                            failed_actions.append(f"Failed to navigate to {link_text}")
                            issues.append(f"Navigation error: {str(e)}")
                    except Exception as e:
                        failed_actions.append(f"Failed to interact with '{link_text if 'link_text' in locals() else 'navigation element'}'")
                        issues.append(f"Navigation interaction error: {str(e)}")
        except Exception as e:
            failed_actions.append(f'navigation_error: {str(e)}')
            issues.append(f"General navigation error: {str(e)}")
        
        return {
            'issues': issues,
            'successful_actions': successful_actions,
            'failed_actions': failed_actions
        }
    
    def _simulate_search(self, page, search_terms: List[str], 
                        tech_proficiency: int, website_type: str,
                        load_times: Dict[str, float], 
                        successful_actions: List[str], failed_actions: List[str],
                        behavioral_data: Dict):
        """Simulate search functionality based on persona preferences and website type."""
        issues = []
        try:
            # Find search input using multiple strategies
            search_input = None
            
            # Strategy 1: Common search selectors
            search_selectors = [
                'input[type="search"]', 
                'input[name="search"]', 
                'input[name="q"]',
                'input[placeholder*="search" i]', 
                'input[aria-label*="search" i]', 
                '.search input',
                'form.search input',
                '#search input',
                'input#search',
                '.searchbox input',
                'input.searchbox',
                'input[name*="search" i]'
            ]
            
            for selector in search_selectors:
                search_input = page.query_selector(selector)
                if search_input:
                    print(f"Found search input with selector: {selector}")
                    break
            
            # Strategy 2: Look for search icons and click them to reveal search input
            if not search_input:
                search_icons = page.query_selector_all('i.fa-search, i.search-icon, .search-icon, button[aria-label*="search" i]')
                for icon in search_icons:
                    try:
                        if icon.is_visible():
                            icon.click()
                            # Wait a moment for search to appear
                            page.wait_for_timeout(1000)
                            # Try selectors again
                            for selector in search_selectors:
                                search_input = page.query_selector(selector)
                                if search_input:
                                    print(f"Found search input after clicking icon, with selector: {selector}")
                                    break
                            if search_input:
                                break
                    except:
                        continue
            
            # Strategy 3: Try more generic selectors if specific ones fail
            if not search_input:
                generic_selectors = [
                    'form input[type="text"]',
                    'header input',
                    'input[type]'
                ]
                for selector in generic_selectors:
                    inputs = page.query_selector_all(selector)
                    for input in inputs:
                        try:
                            # Check if this looks like a search box
                            placeholder = input.get_attribute('placeholder') or ''
                            name = input.get_attribute('name') or ''
                            id = input.get_attribute('id') or ''
                            
                            if ('search' in placeholder.lower() or 
                                'search' in name.lower() or 
                                'search' in id.lower() or
                                'find' in placeholder.lower()):
                                search_input = input
                                print(f"Found search input with generic selector: {selector}")
                                break
                        except:
                            continue
                    if search_input:
                        break
            
            if search_input:
                successful_actions.append("Found search functionality")
                
                # Choose search term based on website type and search terms
                search_term = None
                if search_terms:
                    # Use a category as search term
                    search_term = random.choice(search_terms)
                else:
                    # Generic search terms for e-commerce
                    search_term = random.choice(['product', 'sale', 'new', 'best'])
                
                # Type with varying speed based on tech proficiency
                delay = max(50, 200 - (tech_proficiency * 15))  # ms between keystrokes
                search_input.type(search_term, delay=delay)
                successful_actions.append(f"Searched for '{search_term}'")
                
                # Find and click search button
                search_button = None
                search_button_selectors = [
                    'button[type="submit"]', 
                    'input[type="submit"]', 
                    'button.search-button', 
                    '.search-submit',
                    'button[aria-label*="search" i]',
                    'form button',
                    'button.search',
                    'button i.fa-search'
                ]
                
                for selector in search_button_selectors:
                    search_button = page.query_selector(selector)
                    if search_button and search_button.is_visible():
                        break
                
                if search_button:
                    # Record search results page load time
                    start_time = time.time()
                    try:
                        search_button.click(timeout=30000)
                        page.wait_for_load_state('networkidle', timeout=30000)
                        load_times['search_results'] = time.time() - start_time
                        successful_actions.append("Submitted search")
                    except Exception as e:
                        failed_actions.append(f"Search button click failed: {str(e)}")
                        issues.append(f"Error clicking search button: {str(e)}")
                        # Try pressing Enter instead as fallback
                        try:
                            search_input.press('Enter')
                            page.wait_for_load_state('networkidle', timeout=30000)
                            load_times['search_results'] = time.time() - start_time
                            successful_actions.append("Submitted search with Enter key")
                        except Exception as e2:
                            failed_actions.append(f"Search submission failed: {str(e2)}")
                            issues.append(f"Error submitting search: {str(e2)}")
                            return {
                                'issues': issues,
                                'successful_actions': successful_actions,
                                'failed_actions': failed_actions
                            }
                else:
                    # Try pressing Enter instead
                    start_time = time.time()
                    try:
                        search_input.press('Enter')
                        page.wait_for_load_state('networkidle', timeout=30000)
                        load_times['search_results'] = time.time() - start_time
                        successful_actions.append("Submitted search with Enter key")
                    except Exception as e:
                        failed_actions.append(f"Search submission failed: {str(e)}")
                        issues.append(f"Error submitting search: {str(e)}")
                        return {
                            'issues': issues,
                            'successful_actions': successful_actions,
                            'failed_actions': failed_actions
                        }
                
                # Check search results using multiple strategies
                results_found = False
                
                # Strategy 1: Look for common product selectors
                product_selectors = [
                    '.product', '.product-item', '.item', 'article', '.search-result',
                    '.product-card', '.product-container', '.product-box', '.product-grid',
                    '[data-product-id]', '[data-product]', '.card', '.product-listing'
                ]
                
                for selector in product_selectors:
                    results = page.query_selector_all(selector)
                    if results and len(results) > 0:
                        successful_actions.append(f"Found {len(results)} search results with selector {selector}")
                        results_found = True
                        break
                
                # Strategy 2: Check if search term appears in the page
                if not results_found:
                    page_text = page.inner_text().lower()
                    if search_term.lower() in page_text:
                        # Look for elements that might contain the search term
                        elements_with_term = page.query_selector_all(f'*:text-matches("{search_term}", "i")')
                        if elements_with_term and len(elements_with_term) > 0:
                            successful_actions.append(f"Found {len(elements_with_term)} elements containing search term '{search_term}'")
                            results_found = True
                
                # Strategy 3: Check for "no results" messages
                if not results_found:
                    no_results_indicators = [
                        'no results', 'no products', 'no matches', 'nothing found',
                        'no search results', 'couldn\'t find', 'no items', '0 results'
                    ]
                    page_text = page.inner_text().lower()
                    if any(indicator in page_text for indicator in no_results_indicators):
                        failed_actions.append(f"Search for '{search_term}' returned no results")
                        issues.append(f"Search for '{search_term}' returned no results")
                    else:
                        # If we don't see "no results" message, assume some results were found
                        successful_actions.append(f"Search results page loaded for term '{search_term}'")
                        results_found = True
                
                if not results_found:
                    failed_actions.append("No search results found")
                    issues.append("Search functionality returned no results")
            else:
                failed_actions.append("Could not find search functionality")
                issues.append("Search functionality not easily accessible")
        except Exception as e:
            failed_actions.append(f'search_error: {str(e)}')
            issues.append(f"Search functionality error: {str(e)}")
        
        return {
            'issues': issues,
            'successful_actions': successful_actions,
            'failed_actions': failed_actions
        }
    
    def _simulate_product_interaction(self, page, tech_proficiency: int, patience_level: int, 
                                    website_type: str, price_sensitivity: str, successful_actions: List[str], 
                                    failed_actions: List[str], behavioral_data: Dict):
        """Simulate interaction with product pages based on persona characteristics."""
        issues = []
        try:
            # Find product links
            product_links = page.query_selector_all('.product a, .product-item a, .item a, article a, a.product, a[href*="product"]')
            
            if not product_links:
                # Try more generic approach
                all_links = page.query_selector_all('a[href]:not([href^="#"]):not([href^="javascript"])')
                product_links = [link for link in all_links if self._looks_like_product_link(link)]
            
            if product_links:
                # Choose a product based on price sensitivity
                selected_product = None
                
                if price_sensitivity.lower() == 'budget':
                    # Look for products with sale or discount indicators
                    for link in product_links:
                        if self._has_sale_indicator(link):
                            selected_product = link
                            break
                elif price_sensitivity.lower() == 'luxury':
                    # Try to find premium products (might have certain keywords)
                    for link in product_links:
                        if self._looks_premium(link):
                            selected_product = link
                            break
                
                # If no matching product found, just pick one
                if not selected_product and product_links:
                    selected_product = random.choice(product_links)
                
                if selected_product:
                    # Click on product with appropriate timeout based on patience
                    timeout = max(5000, 15000 - (patience_level * 1000))
                    try:
                        product_text = selected_product.inner_text().strip()
                        selected_product.click()
                        page.wait_for_load_state('networkidle', timeout=timeout)
                        successful_actions.append(f"Viewed product: {product_text[:30]}")
                        
                        # Check product page elements
                        product_elements = {
                            'title': page.query_selector('h1, .product-title, .product-name'),
                            'price': page.query_selector('.price, .product-price'),
                            'description': page.query_selector('.description, .product-description'),
                            'add_to_cart': page.query_selector('button[name*="add" i], button[id*="add" i], button.add-to-cart, .add-to-cart button')
                        }
                        
                        # Record found elements
                        for element_name, element in product_elements.items():
                            if element:
                                successful_actions.append(f"Found product {element_name}")
                            else:
                                failed_actions.append(f"Could not find product {element_name}")
                                issues.append(f"Product {element_name} not easily identifiable")
                        
                        # Try to add to cart based on tech proficiency
                        if product_elements['add_to_cart'] and tech_proficiency > 3:
                            product_elements['add_to_cart'].click()
                            page.wait_for_load_state('networkidle')
                            successful_actions.append("Added product to cart")
                            
                            # Check for cart confirmation
                            cart_confirmation = page.query_selector('.cart-confirmation, .added-to-cart, .cart-success')
                            if cart_confirmation:
                                successful_actions.append("Received cart confirmation")
                            else:
                                issues.append("No clear confirmation after adding to cart")
                    except Exception as e:
                        failed_actions.append(f"Product interaction failed")
                        issues.append(f"Error interacting with product: {str(e)}")
                else:
                    failed_actions.append("Could not select a product")
                    issues.append("No suitable products found based on price preference")
            else:
                failed_actions.append("Could not find product listings")
                issues.append("Product listings not easily identifiable")
        except Exception as e:
            failed_actions.append(f'product_interaction_error: {str(e)}')
            issues.append(f"General product interaction error: {str(e)}")
        
        return {
            'issues': issues,
            'successful_actions': successful_actions,
            'failed_actions': failed_actions
        }
    
    def _looks_like_product_link(self, link) -> bool:
        """Determine if a link is likely a product link."""
        try:
            # Check link text
            text = link.inner_text().strip()
            if not text:
                return False
                
            # Check for image child
            has_image = link.query_selector('img') is not None
            
            # Check for price indicator
            has_price = '$' in text or '€' in text or '£' in text or 'price' in text.lower()
            
            # Check URL pattern
            href = link.get_attribute('href')
            url_product_indicators = ['product', 'item', 'detail', 'p=', 'pid=']
            url_has_product = href and any(indicator in href.lower() for indicator in url_product_indicators)
            
            return has_image or has_price or url_has_product
        except:
            return False
    
    def _has_sale_indicator(self, element) -> bool:
        """Check if an element has sale or discount indicators."""
        try:
            text = element.inner_text().lower()
            sale_indicators = ['sale', 'discount', 'off', 'save', 'deal', 'clearance', 'reduced']
            return any(indicator in text for indicator in sale_indicators)
        except:
            return False
    
    def _looks_premium(self, element) -> bool:
        """Check if an element appears to be a premium product."""
        try:
            text = element.inner_text().lower()
            premium_indicators = ['premium', 'luxury', 'exclusive', 'limited', 'special', 'professional']
            return any(indicator in text for indicator in premium_indicators)
        except:
            return False
    
    def _check_visual_accessibility(self, page) -> List[str]:
        """Check for common visual accessibility issues."""
        issues = []
        
        # Check for alt text on images
        images = page.query_selector_all('img')
        for img in images:
            if not img.get_attribute('alt'):
                issues.append('missing_alt_text')
                break
        
        # Check for sufficient color contrast (simplified)
        dark_text = page.query_selector_all('.text-gray-700, .text-black, [style*="color: #000"]')
        if not dark_text:
            issues.append('potential_contrast_issues')
        
        return issues
    
    def _check_motor_accessibility(self, page) -> List[str]:
        """Check for motor accessibility issues."""
        issues = []
        
        # Check for small click targets
        small_buttons = page.query_selector_all('button[style*="width: 20"], a[style*="width: 20"]')
        if small_buttons:
            issues.append('small_click_targets')
        
        # Check for keyboard navigation
        try:
            page.keyboard.press('Tab')
            if not page.query_selector(':focus'):
                issues.append('no_keyboard_navigation')
        except:
            issues.append('keyboard_navigation_error')
        
        return issues
    
    def _calculate_navigation_score(self, successful_actions: List[str], 
                                  failed_actions: List[str], tech_proficiency: int) -> float:
        """Calculate a score for navigation usability based on persona characteristics."""
        # Base calculation
        total_actions = len(successful_actions) + len(failed_actions)
        if total_actions == 0:
            return 5.0  # Default middle score if no actions
            
        # Calculate raw success rate
        raw_score = (len(successful_actions) / total_actions) * 10
        
        # Adjust based on tech proficiency
        # Less tech-savvy users are more affected by navigation issues
        if tech_proficiency < 5:
            # Amplify negative experiences for less tech-savvy users
            if raw_score < 7:
                raw_score = raw_score * 0.8  # Make bad experiences worse
        elif tech_proficiency > 7:
            # Tech-savvy users are more forgiving of minor issues
            if raw_score < 7:
                raw_score = raw_score * 1.2  # Make bad experiences less severe
                raw_score = min(raw_score, 7.0)  # But still not great
        
        # Check for specific navigation successes
        nav_successes = sum(1 for action in successful_actions if "navigation" in action.lower() or "navigated" in action.lower())
        if nav_successes >= 3:
            raw_score += 1  # Bonus for good navigation
        
        # Ensure score is within bounds
        return max(1.0, min(raw_score, 10.0))
    
    def _calculate_design_score(self, page, age: int, tech_proficiency: int, device: str) -> float:
        """Calculate a score for website design based on persona characteristics."""
        # Start with a base score
        score = 5.0
        
        # Check for basic design elements
        try:
            # Check for responsive design
            viewport_meta = page.query_selector('meta[name="viewport"]')
            if viewport_meta:
                score += 1
            
            # Check for consistent styling
            style_elements = page.query_selector_all('link[rel="stylesheet"], style')
            if style_elements:
                score += 0.5
            
            # Check for modern design elements
            modern_elements = page.query_selector_all('.container, .row, .col, .grid, .flex')
            if modern_elements:
                score += 0.5
            
            # Check for images
            images = page.query_selector_all('img')
            if images and len(images) > 5:
                score += 0.5
            
            # Check for proper heading structure
            headings = page.query_selector_all('h1, h2, h3')
            if headings and len(headings) > 3:
                score += 0.5
            
            # Check for footer
            footer = page.query_selector('footer')
            if footer:
                score += 0.5
            
            # Check for proper spacing
            spacing_check = page.evaluate('''() => {
                const paragraphs = document.querySelectorAll('p');
                let hasGoodSpacing = true;
                for (let i = 0; i < Math.min(paragraphs.length, 5); i++) {
                    const style = window.getComputedStyle(paragraphs[i]);
                    if (parseFloat(style.marginBottom) < 10 || parseFloat(style.lineHeight) < 1.2) {
                        hasGoodSpacing = false;
                        break;
                    }
                }
                return hasGoodSpacing;
            }''')
            
            if spacing_check:
                score += 0.5
        except:
            # If evaluation fails, use a neutral score
            pass
        
        # Adjust based on persona characteristics
        
        # Age adjustments
        if age > 60:
            # Older users may prefer clearer, simpler designs
            font_size_check = page.evaluate('''() => {
                const bodyStyle = window.getComputedStyle(document.body);
                return parseFloat(bodyStyle.fontSize) >= 16;
            }''')
            
            if not font_size_check:
                score -= 1.5  # Significant penalty for small text with older users
            
            # Check for high contrast
            contrast_check = page.evaluate('''() => {
                const bodyStyle = window.getComputedStyle(document.body);
                const bgColor = bodyStyle.backgroundColor;
                const textColor = bodyStyle.color;
                // Simple check - not a full WCAG contrast check
                return bgColor.includes('255') && textColor.includes('0') || 
                       bgColor.includes('0') && textColor.includes('255');
            }''')
            
            if not contrast_check:
                score -= 1  # Penalty for low contrast with older users
        
        # Tech proficiency adjustments
        if tech_proficiency < 5:
            # Less tech-savvy users prefer simpler designs
            complex_layout_check = page.evaluate('''() => {
                return document.querySelectorAll('.container, .row, .col, .grid, .flex').length > 10;
            }''')
            
            if complex_layout_check:
                score -= 1  # Penalty for complex layouts with less tech-savvy users
        
        # Device adjustments
        if device == 'mobile':
            # Check for mobile-specific issues
            mobile_friendly = page.evaluate('''() => {
                // Check if content fits viewport width
                return document.documentElement.scrollWidth <= window.innerWidth * 1.1;
            }''')
            
            if not mobile_friendly:
                score -= 2  # Major penalty for non-mobile-friendly sites on mobile
            
            # Check for touch-friendly targets
            touch_friendly = page.evaluate('''() => {
                const links = document.querySelectorAll('a, button');
                let smallTargets = 0;
                for (let i = 0; i < Math.min(links.length, 10); i++) {
                    const rect = links[i].getBoundingClientRect();
                    if (rect.width < 44 || rect.height < 44) {
                        smallTargets++;
                    }
                }
                return smallTargets <= 3; // Allow a few small targets
            }''')
            
            if not touch_friendly:
                score -= 1.5  # Penalty for small touch targets on mobile
        
        # Ensure score is within bounds
        return max(1.0, min(score, 10.0))
    
    def _calculate_findability_score(self, successful_actions: List[str], 
                                   failed_actions: List[str], preferred_categories: List[str]) -> float:
        """Calculate a score for how easily users can find products based on their preferences."""
        # Start with base score
        score = 5.0
        
        # Count findability-related actions
        findability_successes = sum(1 for action in successful_actions if any(term in action.lower() 
                                   for term in ['search', 'found', 'product', 'result', 'category', 'filter']))
        
        findability_failures = sum(1 for action in failed_actions if any(term in action.lower() 
                                  for term in ['search', 'found', 'product', 'result', 'category', 'filter', 'not found']))
        
        # Calculate success rate for findability actions
        total_findability_actions = findability_successes + findability_failures
        if total_findability_actions > 0:
            findability_rate = findability_successes / total_findability_actions
            score = findability_rate * 10
        
        # Bonus for finding preferred categories
        if preferred_categories:
            category_matches = sum(1 for action in successful_actions 
                                  if any(category.lower() in action.lower() for category in preferred_categories))
            
            if category_matches > 0:
                category_bonus = min(2.0, category_matches * 0.5)  # Up to 2 point bonus
                score += category_bonus
        
        # Bonus for search functionality
        if any('search' in action.lower() for action in successful_actions):
            score += 1
        
        # Penalty for missing search
        if any('search' in action.lower() and 'not' in action.lower() for action in failed_actions):
            score -= 2
        
        # Ensure score is within bounds
        return max(1.0, min(score, 10.0))
    
    def _analyze_website_type(self, page, url: str) -> str:
        """Analyze the website to determine its type and structure."""
        try:
            # Extract domain for analysis
            domain = urlparse(url).netloc.lower()
            
            # Check page content
            page_content = page.content().lower()
            page_text = page.inner_text().lower()
            
            # Check for common e-commerce indicators
            ecommerce_indicators = [
                'cart', 'shop', 'product', 'buy', 'price', 'checkout', 'shipping', 
                'order', 'payment', 'add to cart', 'purchase', 'store'
            ]
            
            ecommerce_score = sum(1 for indicator in ecommerce_indicators if indicator in page_text)
            
            # Check for specific types of e-commerce sites
            fashion_indicators = ['clothing', 'fashion', 'apparel', 'wear', 'shoes', 'accessories', 'style']
            electronics_indicators = ['electronics', 'computer', 'phone', 'gadget', 'tech', 'device']
            food_indicators = ['food', 'grocery', 'meal', 'recipe', 'ingredient', 'restaurant', 'dish']
            home_indicators = ['furniture', 'home', 'decor', 'kitchen', 'garden', 'interior']
            beauty_indicators = ['beauty', 'cosmetic', 'makeup', 'skin', 'hair', 'fragrance']
            
            # Calculate scores for each type
            fashion_score = sum(1 for indicator in fashion_indicators if indicator in page_text)
            electronics_score = sum(1 for indicator in electronics_indicators if indicator in page_text)
            food_score = sum(1 for indicator in food_indicators if indicator in page_text)
            home_score = sum(1 for indicator in home_indicators if indicator in page_text)
            beauty_score = sum(1 for indicator in beauty_indicators if indicator in page_text)
            
            # Determine the most likely type
            type_scores = {
                'fashion': fashion_score,
                'electronics': electronics_score,
                'food': food_score,
                'home': home_score,
                'beauty': beauty_score
            }
            
            # Default to general e-commerce if no clear type is detected
            if ecommerce_score > 2:
                if max(type_scores.values()) > 1:
                    # Get the type with the highest score
                    website_type = max(type_scores.items(), key=lambda x: x[1])[0]
                    return f"ecommerce-{website_type}"
                else:
                    return "ecommerce-general"
            
            # Check for other common website types
            if any(term in domain for term in ['blog', 'article', 'news']):
                return "content-blog"
            
            if any(term in domain for term in ['portfolio', 'gallery']):
                return "portfolio"
                
            # Default to general website
            return "general"
            
        except Exception as e:
            print(f"Error analyzing website type: {e}")
            return "unknown"
    
    def _generate_search_terms(self, preferred_categories: List[str], website_type: str) -> List[str]:
        """Generate search terms based on preferred categories and website type."""
        search_terms = []
        
        # Add preferred categories as search terms
        search_terms.extend(preferred_categories)
        
        # Add website-type specific search terms
        if website_type == "ecommerce-fashion":
            search_terms.extend(['shirt', 'dress', 'jeans', 'shoes', 'jacket', 'accessories'])
        elif website_type == "ecommerce-electronics":
            search_terms.extend(['phone', 'laptop', 'headphones', 'camera', 'tv', 'speaker'])
        elif website_type == "ecommerce-food":
            search_terms.extend(['meal', 'recipe', 'organic', 'fresh', 'snack', 'drink'])
        elif website_type == "ecommerce-home":
            search_terms.extend(['chair', 'table', 'sofa', 'bed', 'lamp', 'kitchen'])
        elif website_type == "ecommerce-beauty":
            search_terms.extend(['makeup', 'skincare', 'hair', 'fragrance', 'cream', 'lotion'])
        elif website_type.startswith("ecommerce"):
            search_terms.extend(['new', 'popular', 'sale', 'discount', 'best seller'])
        
        # Ensure we have at least some search terms
        if not search_terms:
            search_terms = ['product', 'new', 'popular', 'best']
            
        return search_terms 

    def _setup_behavioral_tracking(self, page, behavioral_data: Dict):
        """Set up event listeners to track user behavior on the page."""
        # Track mouse movements
        page.evaluate("""() => {
            window._mousePositions = [];
            document.addEventListener('mousemove', (e) => {
                if (window._mousePositions.length > 0) {
                    const lastPos = window._mousePositions[window._mousePositions.length - 1];
                    // Only record if moved more than 5 pixels to avoid excessive data
                    const distance = Math.sqrt(Math.pow(e.clientX - lastPos.x, 2) + Math.pow(e.clientY - lastPos.y, 2));
                    if (distance < 5) return;
                }
                window._mousePositions.push({
                    x: e.clientX,
                    y: e.clientY,
                    timestamp: Date.now()
                });
            });
        }""")
        
        # Track scrolling behavior
        page.evaluate("""() => {
            window._scrollEvents = [];
            document.addEventListener('scroll', (e) => {
                window._scrollEvents.push({
                    scrollX: window.scrollX,
                    scrollY: window.scrollY,
                    timestamp: Date.now()
                });
            });
        }""")
        
        # Track clicks
        page.evaluate("""() => {
            window._clickEvents = [];
            document.addEventListener('click', (e) => {
                let elementInfo = {
                    tagName: e.target.tagName,
                    className: e.target.className,
                    id: e.target.id,
                    text: e.target.innerText ? e.target.innerText.substring(0, 50) : '',
                    href: e.target.href || '',
                    isButton: e.target.tagName === 'BUTTON' || 
                              e.target.role === 'button' || 
                              e.target.className.includes('btn') ||
                              e.target.className.includes('button')
                };
                
                window._clickEvents.push({
                    x: e.clientX,
                    y: e.clientY,
                    timestamp: Date.now(),
                    element: elementInfo
                });
            });
        }""")
        
        # Track hover events
        page.evaluate("""() => {
            window._hoverEvents = [];
            document.addEventListener('mouseover', (e) => {
                // Only track significant elements
                if (['A', 'BUTTON', 'INPUT', 'SELECT', 'IMG', 'LI'].includes(e.target.tagName)) {
                    let elementInfo = {
                        tagName: e.target.tagName,
                        className: e.target.className,
                        id: e.target.id,
                        text: e.target.innerText ? e.target.innerText.substring(0, 50) : '',
                        href: e.target.href || ''
                    };
                    
                    window._hoverEvents.push({
                        timestamp: Date.now(),
                        element: elementInfo,
                        duration: 0  // Will be updated on mouseout
                    });
                }
            });
            
            document.addEventListener('mouseout', (e) => {
                if (window._hoverEvents.length > 0 && 
                    ['A', 'BUTTON', 'INPUT', 'SELECT', 'IMG', 'LI'].includes(e.target.tagName)) {
                    const lastEvent = window._hoverEvents[window._hoverEvents.length - 1];
                    lastEvent.duration = Date.now() - lastEvent.timestamp;
                }
            });
        }""")
        
        # Track form interactions
        page.evaluate("""() => {
            window._formInteractions = [];
            
            // Track input field interactions
            document.addEventListener('focus', (e) => {
                if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
                    window._formInteractions.push({
                        type: 'focus',
                        element: {
                            tagName: e.target.tagName,
                            type: e.target.type || '',
                            id: e.target.id,
                            name: e.target.name,
                            placeholder: e.target.placeholder || ''
                        },
                        timestamp: Date.now(),
                        duration: 0  // Will be updated on blur
                    });
                }
            }, true);
            
            document.addEventListener('blur', (e) => {
                if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName) && 
                    window._formInteractions.length > 0) {
                    const lastEvent = window._formInteractions[window._formInteractions.length - 1];
                    if (lastEvent.type === 'focus') {
                        lastEvent.duration = Date.now() - lastEvent.timestamp;
                        lastEvent.valueLength = e.target.value ? e.target.value.length : 0;
                    }
                }
            }, true);
            
            // Track form submissions
            document.addEventListener('submit', (e) => {
                window._formInteractions.push({
                    type: 'submit',
                    formId: e.target.id,
                    formAction: e.target.action || '',
                    timestamp: Date.now()
                });
            });
        }""")
        
        # Track page visibility
        page.evaluate("""() => {
            window._visibilityEvents = [];
            document.addEventListener('visibilitychange', () => {
                window._visibilityEvents.push({
                    visible: !document.hidden,
                    timestamp: Date.now()
                });
            });
        }""")

    def _simulate_browsing_behavior(self, page, tech_proficiency: int, patience_level: int, behavioral_data: Dict):
        """Simulate realistic browsing behavior based on persona characteristics."""
        # Simulate initial page scanning
        self._simulate_page_scan(page, tech_proficiency)
        
        # Simulate scrolling behavior based on tech proficiency and patience
        self._simulate_scrolling(page, tech_proficiency, patience_level, behavioral_data)
        
        # Record the simulated behavior
        behavioral_data['mouse_movements'].extend(page.evaluate("window._mousePositions || []"))
        behavioral_data['scroll_patterns'].extend(page.evaluate("window._scrollEvents || []"))
        behavioral_data['clicks'].extend(page.evaluate("window._clickEvents || []"))
        behavioral_data['hover_events'].extend(page.evaluate("window._hoverEvents || []"))
        behavioral_data['form_interactions'].extend(page.evaluate("window._formInteractions || []"))
        behavioral_data['page_visibility'].extend(page.evaluate("window._visibilityEvents || []"))

    def _simulate_page_scan(self, page, tech_proficiency: int):
        """Simulate how a user initially scans a page based on tech proficiency."""
        # Higher tech proficiency users scan more methodically
        if tech_proficiency > 7:
            # Methodical scan from top to bottom
            page.mouse.move(100, 100)
            time.sleep(0.5)
            page.mouse.move(300, 200)
            time.sleep(0.3)
            page.mouse.move(500, 300)
            time.sleep(0.3)
            page.mouse.move(700, 400)
        elif tech_proficiency > 4:
            # Average scan pattern - F-pattern
            page.mouse.move(100, 100)
            time.sleep(0.3)
            page.mouse.move(500, 100)
            time.sleep(0.3)
            page.mouse.move(100, 300)
            time.sleep(0.3)
            page.mouse.move(400, 300)
            time.sleep(0.3)
            page.mouse.move(100, 500)
        else:
            # Less methodical, more random scanning
            page.mouse.move(300, 200)
            time.sleep(0.2)
            page.mouse.move(100, 400)
            time.sleep(0.2)
            page.mouse.move(500, 100)
            time.sleep(0.2)
            page.mouse.move(200, 300)

    def _simulate_scrolling(self, page, tech_proficiency: int, patience_level: int, behavioral_data: Dict):
        """Simulate scrolling behavior based on persona characteristics."""
        # Get page height
        page_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        
        # Record start time for this activity
        start_time = time.time()
        
        # Determine scrolling speed and pattern based on tech proficiency and patience
        if tech_proficiency > 7:
            # Methodical, steady scrolling
            scroll_steps = min(int(page_height / 200), 10)  # Limit to 10 steps
            for i in range(1, scroll_steps + 1):
                scroll_position = (i / scroll_steps) * (page_height - viewport_height)
                page.evaluate(f"window.scrollTo(0, {scroll_position})")
                # Higher patience means more time spent reading
                time.sleep(0.5 + (patience_level / 10))
        elif tech_proficiency > 4:
            # Average scrolling - some skimming
            scroll_steps = min(int(page_height / 300), 7)  # Limit to 7 steps
            for i in range(1, scroll_steps + 1):
                scroll_position = (i / scroll_steps) * (page_height - viewport_height)
                page.evaluate(f"window.scrollTo(0, {scroll_position})")
                time.sleep(0.3 + (patience_level / 15))
        else:
            # Impatient, quick scrolling
            scroll_steps = min(int(page_height / 500), 4)  # Limit to 4 steps
            for i in range(1, scroll_steps + 1):
                scroll_position = (i / scroll_steps) * (page_height - viewport_height)
                page.evaluate(f"window.scrollTo(0, {scroll_position})")
                time.sleep(0.2 + (patience_level / 20))
        
        # Record time spent scrolling
        behavioral_data['time_spent']['initial_scrolling'] = {
            'start_time': start_time,
            'end_time': time.time(),
            'duration': time.time() - start_time
        }
        
        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.5)

    def _analyze_behavioral_data(self, behavioral_data: Dict, persona: Dict) -> Dict:
        """Analyze behavioral data to extract insights about user experience."""
        insights = {
            'engagement_level': 'medium',  # Default value
            'pain_points': [],
            'areas_of_interest': [],
            'navigation_patterns': [],
            'attention_hotspots': [],
            'form_completion_issues': [],
            'overall_experience': 'neutral'  # Default value
        }
        
        # Extract persona attributes for context
        tech_proficiency = persona.get('technical', {}).get('proficiency', 5)
        patience_level = persona.get('e_commerce_specific', {}).get('patience_level', 5)
        
        # Analyze mouse movements for engagement
        mouse_movements = behavioral_data.get('mouse_movements', [])
        if len(mouse_movements) > 100:
            insights['engagement_level'] = 'high'
        elif len(mouse_movements) < 20:
            insights['engagement_level'] = 'low'
            insights['pain_points'].append('Limited interaction with the page')
        
        # Analyze scrolling patterns
        scroll_events = behavioral_data.get('scroll_patterns', [])
        if scroll_events:
            # Check for rapid scrolling (potential frustration)
            rapid_scrolls = 0
            for i in range(1, len(scroll_events)):
                if i > 0:
                    time_diff = scroll_events[i]['timestamp'] - scroll_events[i-1]['timestamp']
                    scroll_diff = abs(scroll_events[i]['scrollY'] - scroll_events[i-1]['scrollY'])
                    if time_diff < 300 and scroll_diff > 500:  # Fast scroll
                        rapid_scrolls += 1
            
            if rapid_scrolls > 3:
                insights['pain_points'].append('Rapid scrolling detected - possible content scanning or frustration')
                if patience_level < 5:
                    insights['overall_experience'] = 'negative'
            
            # Check for careful reading (slow scrolling)
            slow_scrolls = 0
            for i in range(1, len(scroll_events)):
                if i > 0:
                    time_diff = scroll_events[i]['timestamp'] - scroll_events[i-1]['timestamp']
                    scroll_diff = abs(scroll_events[i]['scrollY'] - scroll_events[i-1]['scrollY'])
                    if time_diff > 1000 and scroll_diff < 200:  # Slow scroll
                        slow_scrolls += 1
            
            if slow_scrolls > 5:
                insights['areas_of_interest'].append('Careful reading detected - content appears engaging')
                insights['overall_experience'] = 'positive'
        
        # Analyze clicks
        clicks = behavioral_data.get('clicks', [])
        if clicks:
            # Identify repeated clicks on the same element (potential frustration)
            click_targets = {}
            for click in clicks:
                element_id = f"{click['element']['tagName']}#{click['element']['id']}.{click['element']['className']}"
                click_targets[element_id] = click_targets.get(element_id, 0) + 1
            
            repeated_clicks = [target for target, count in click_targets.items() if count > 2]
            if repeated_clicks:
                insights['pain_points'].append(f'Repeated clicks on {len(repeated_clicks)} elements - possible confusion or non-responsive elements')
            
            # Identify navigation patterns
            nav_clicks = [click for click in clicks if click['element']['tagName'] == 'A' or click['element']['isButton']]
            if len(nav_clicks) > 5:
                insights['navigation_patterns'].append('Extensive navigation - exploring multiple sections')
            elif len(nav_clicks) < 2:
                insights['navigation_patterns'].append('Limited navigation - possibly found content quickly or gave up')
        
        # Analyze hover events to identify areas of interest
        hover_events = behavioral_data.get('hover_events', [])
        if hover_events:
            # Find elements with long hover times
            long_hovers = [hover for hover in hover_events if hover.get('duration', 0) > 1000]
            if long_hovers:
                hover_elements = [f"{hover['element']['tagName']}: {hover['element']['text'][:20]}" 
                                 for hover in long_hovers if hover['element'].get('text')]
                if hover_elements:
                    insights['areas_of_interest'].extend(hover_elements[:3])  # Top 3 elements
                    insights['attention_hotspots'].extend(hover_elements[:3])
        
        # Analyze form interactions
        form_interactions = behavioral_data.get('form_interactions', [])
        if form_interactions:
            # Check for abandoned form fields
            focus_events = [event for event in form_interactions if event['type'] == 'focus']
            abandoned_fields = [event for event in focus_events 
                               if event.get('duration', 0) < 500 and event.get('valueLength', 0) == 0]
            
            if abandoned_fields:
                insights['form_completion_issues'].append(f'{len(abandoned_fields)} form fields abandoned - possible usability issues')
            
            # Check for form submissions
            submissions = [event for event in form_interactions if event['type'] == 'submit']
            if submissions and tech_proficiency < 5:
                insights['overall_experience'] = 'positive'  # Successfully submitted form despite low tech proficiency
        
        # Analyze time spent on different sections
        time_spent = behavioral_data.get('time_spent', {})
        total_time = sum(section.get('duration', 0) for section in time_spent.values())
        
        if total_time > 120:  # More than 2 minutes
            if patience_level < 5:
                insights['overall_experience'] = 'negative'  # Long time for impatient user
                insights['pain_points'].append('Session duration exceeds patience threshold')
            else:
                insights['overall_experience'] = 'positive'  # Engaged session for patient user
                insights['areas_of_interest'].append('Extended session duration indicates engagement')
        
        return insights

    def generate_ai_review(self, simulation_result: Dict, persona: Dict) -> Dict:
        """Generate an AI-powered review based on simulation results and persona context."""
        import openai
        import os
        
        # Check if OpenAI API key is available
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return {
                'review': "AI review generation requires an OpenAI API key set as OPENAI_API_KEY environment variable.",
                'rating': self._calculate_overall_rating(simulation_result),
                'summary': "Unable to generate AI review."
            }
        
        openai.api_key = api_key
        
        # Extract key information for the review
        website_url = simulation_result.get('website_url', '')
        navigation_score = simulation_result.get('navigation_score', 0)
        design_score = simulation_result.get('design_score', 0)
        findability_score = simulation_result.get('findability_score', 0)
        issues = simulation_result.get('issues', [])
        successful_actions = simulation_result.get('successful_actions', [])
        failed_actions = simulation_result.get('failed_actions', [])
        accessibility_issues = simulation_result.get('accessibility_issues', [])
        behavioral_insights = simulation_result.get('behavioral_insights', {})
        
        # Extract persona information
        demographics = persona.get('demographics', {})
        tech_profile = persona.get('technical', {})
        shopping = persona.get('shopping_behavior', {})
        accessibility_needs = persona.get('accessibility_needs', [])
        goals = persona.get('goals', {})
        
        name = demographics.get('name', 'Anonymous User')
        age = demographics.get('age', 35)
        tech_proficiency = tech_profile.get('proficiency', 5)
        patience_level = persona.get('e_commerce_specific', {}).get('patience_level', 5)
        
        # Prepare prompt for OpenAI
        prompt = f"""
        You are {name}, a {age}-year-old online shopper with {tech_proficiency}/10 technical proficiency 
        and {patience_level}/10 patience level. Write a detailed review of your experience shopping on {website_url}.
        
        Your shopping preferences: {', '.join(shopping.get('product_categories', ['various products']))}
        Your accessibility needs: {', '.join(accessibility_needs) if accessibility_needs else 'None'}
        
        During your visit:
        - Navigation experience (Score: {navigation_score}/10): {', '.join(successful_actions[:3])}
        - Design experience (Score: {design_score}/10)
        - Finding products (Score: {findability_score}/10)
        
        Issues encountered: {', '.join(issues[:3]) if issues else 'None significant'}
        Failed actions: {', '.join(failed_actions[:3]) if failed_actions else 'None'}
        Accessibility issues: {', '.join(accessibility_issues[:3]) if accessibility_issues else 'None'}
        
        Behavioral insights:
        - Engagement level: {behavioral_insights.get('engagement_level', 'medium')}
        - Areas of interest: {', '.join(behavioral_insights.get('areas_of_interest', ['None specific']))}
        - Pain points: {', '.join(behavioral_insights.get('pain_points', ['None significant']))}
        
        Write a first-person review (300-400 words) that sounds authentic to your persona. 
        Include specific details about your experience, what you liked and disliked, 
        and whether you would shop on this site again. Rate the site from 1-5 stars.
        
        Format your response as:
        
        RATING: [1-5]
        SUMMARY: [One sentence summary of your experience]
        REVIEW: [Your detailed review]
        """
        
        try:
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI that generates authentic e-commerce website reviews from the perspective of specific user personas."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            # Parse the response
            review_text = response.choices[0].message.content.strip()
            
            # Extract rating, summary and review
            rating_match = re.search(r'RATING:\s*(\d+)', review_text)
            summary_match = re.search(r'SUMMARY:\s*(.+?)(?=\nREVIEW:|$)', review_text, re.DOTALL)
            review_match = re.search(r'REVIEW:\s*(.+)', review_text, re.DOTALL)
            
            rating = int(rating_match.group(1)) if rating_match else self._calculate_overall_rating(simulation_result)
            summary = summary_match.group(1).strip() if summary_match else "No summary provided."
            review = review_match.group(1).strip() if review_match else review_text
            
            return {
                'rating': rating,
                'summary': summary,
                'review': review,
                'persona_name': name,
                'persona_age': age,
                'tech_proficiency': tech_proficiency,
                'patience_level': patience_level
            }
            
        except Exception as e:
            # Fallback if API call fails
            return {
                'rating': self._calculate_overall_rating(simulation_result),
                'summary': f"Review from the perspective of {name}, {age}",
                'review': f"As {name}, I found this website to be {self._get_experience_description(simulation_result)}. " +
                         f"The navigation was {self._get_score_description(navigation_score)}, " +
                         f"design was {self._get_score_description(design_score)}, and " +
                         f"finding products was {self._get_score_description(findability_score)}. " +
                         (f"I encountered issues with: {', '.join(issues[:3])}. " if issues else "") +
                         (f"The site didn't work well for my accessibility needs: {', '.join(accessibility_issues[:3])}. " if accessibility_issues else "") +
                         f"Overall, I would {'recommend' if self._calculate_overall_rating(simulation_result) >= 3 else 'not recommend'} this site.",
                'error': str(e)
            }

    def _calculate_overall_rating(self, simulation_result: Dict) -> int:
        """Calculate an overall star rating (1-5) based on simulation scores."""
        navigation_score = simulation_result.get('navigation_score', 0)
        design_score = simulation_result.get('design_score', 0)
        findability_score = simulation_result.get('findability_score', 0)
        
        # Calculate average score and convert to 1-5 scale
        avg_score = (navigation_score + design_score + findability_score) / 3
        rating = round(avg_score / 2)  # Convert from 0-10 to 0-5
        
        # Ensure rating is between 1-5
        return max(1, min(5, rating))

    def _get_score_description(self, score: float) -> str:
        """Convert a numeric score to a descriptive term."""
        if score >= 9:
            return "excellent"
        elif score >= 7:
            return "good"
        elif score >= 5:
            return "average"
        elif score >= 3:
            return "poor"
        else:
            return "very poor"

    def _get_experience_description(self, simulation_result: Dict) -> str:
        """Generate an overall experience description based on simulation results."""
        overall_rating = self._calculate_overall_rating(simulation_result)
        issues = simulation_result.get('issues', [])
        failed_actions = simulation_result.get('failed_actions', [])
        
        if overall_rating >= 4 and len(issues) < 3 and len(failed_actions) < 2:
            return "a pleasure to use"
        elif overall_rating >= 3 and len(issues) < 5:
            return "generally satisfactory"
        elif overall_rating >= 2:
            return "somewhat frustrating"
        else:
            return "difficult and frustrating" 