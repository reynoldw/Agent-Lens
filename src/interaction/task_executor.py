"""
Task Execution Engine for E-commerce Website Simulation.

This module contains the TaskExecutor class responsible for executing
planned tasks using the PersonaBasedBrowser.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import time
import copy

from src.interaction.job_definitions import JobDefinition, TaskDefinition, DecisionPoint
from src.interaction.persona_browser import PersonaBasedBrowser
from src.interaction.models import ExecutionPlan, ExecutionTask, TaskResult, JobExecutionResults


class TaskExecutor:
    """Executes planned tasks using persona-based browser automation."""
    
    def __init__(self, browser: PersonaBasedBrowser, plan: ExecutionPlan):
        self.browser = browser
        self.plan = plan
        self.decisions = {decision.decision_id: decision for decision in plan.decisions}
        self.results = JobExecutionResults(
            job_id=plan.job_id,
            job_name=plan.job_name,
            persona=plan.persona,
            website_url="",  # Will be set during execution
            start_time=time.time()
        )
        # Track tasks that have been attempted with fallbacks
        self.fallback_attempts = {}
    
    def execute(self, website_url: str) -> JobExecutionResults:
        """Execute all tasks in the plan for the given website."""
        self.results.website_url = website_url
        
        try:
            # Navigate to website
            nav_result = self.browser.navigate(website_url)
            if not nav_result["success"]:
                self.results.add_issue(f"Failed to load website: {nav_result.get('error', 'Unknown error')}")
                self.results.end_time = time.time()
                return self.results
            
            # Execute each task in sequence
            for task in self.plan.tasks:
                task_result = self._execute_task(task)
                self.results.add_task_result(task_result)
                
                # If task failed, try fallback tasks
                if not task_result.success and task.fallback_tasks:
                    fallback_success = self._execute_fallback_tasks(task)
                    if not fallback_success and task_result.is_blocking_failure():
                        self.results.add_issue(f"Blocking failure in task {task.task_id}: {task_result.error_message}")
                        break
                
                # Stop if we hit a blocking failure with no successful fallbacks
                elif task_result.is_blocking_failure():
                    self.results.add_issue(f"Blocking failure in task {task.task_id}: {task_result.error_message}")
                    break
            
            # Add behavior data from browser
            self.results.behavioral_data = {
                "frustration_indicators": self.browser.frustration_indicators,
                "events": self.browser.events,
                "navigation_history": self.browser.navigation_history
            }
            
            # Calculate final scores
            self.results.calculate_scores()
            
        except Exception as e:
            self.results.add_issue(f"Unexpected error during execution: {str(e)}")
        finally:
            self.results.end_time = time.time()
        
        return self.results
    
    def _execute_fallback_tasks(self, failed_task: ExecutionTask) -> bool:
        """Execute fallback tasks for a failed task."""
        # Track that we've attempted fallbacks for this task
        task_id = failed_task.task_id
        self.fallback_attempts[task_id] = self.fallback_attempts.get(task_id, 0) + 1
        
        # Don't attempt fallbacks more than twice
        if self.fallback_attempts[task_id] > 2:
            self.results.add_issue(f"Maximum fallback attempts reached for task {task_id}")
            return False
        
        # Try each fallback task
        for fallback_id in failed_task.fallback_tasks:
            # Create a fallback task based on the original task
            fallback_task = copy.deepcopy(failed_task)
            fallback_task.task_id = fallback_id
            
            # Execute the fallback task
            fallback_result = self._execute_task(fallback_task)
            self.results.add_task_result(fallback_result)
            
            # If fallback succeeded, we're done
            if fallback_result.success:
                return True
        
        # All fallbacks failed
        return False
    
    def _execute_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a single task and return its result."""
        start_time = time.time()
        
        try:
            # Apply decisions that might affect this task
            task = self._apply_decisions_to_task(task)
            
            # Execute task based on its type
            if task.task_id == "navigate_to_homepage":
                result = self._execute_navigation_task(task)
            elif task.task_id.startswith("search"):
                result = self._execute_search_task(task)
            elif task.task_id == "explore_categories":
                result = self._execute_category_exploration_task(task)
            elif task.task_id == "examine_product_details":
                result = self._execute_product_examination_task(task)
            elif task.task_id == "add_to_cart":
                result = self._execute_add_to_cart_task(task)
            elif task.task_id == "proceed_to_checkout":
                result = self._execute_checkout_task(task)
            elif task.task_id == "filter_products":
                result = self._execute_filter_task(task)
            elif task.task_id == "filter_search_results":
                result = self._execute_filter_task(task)
            elif task.task_id == "check_product_price":
                result = self._execute_price_check_task(task)
            elif task.task_id == "check_shipping_cost":
                result = self._execute_shipping_check_task(task)
            elif task.task_id == "read_reviews":
                result = self._execute_review_task(task)
            elif task.task_id == "check_specifications":
                result = self._execute_specifications_task(task)
            elif task.task_id == "find_account_section":
                result = self._execute_find_account_task(task)
            elif task.task_id.startswith("fill_"):
                result = self._execute_form_fill_task(task)
            else:
                result = TaskResult(
                    task_id=task.task_id,
                    success=False,
                    duration=time.time() - start_time,
                    error_message=f"Unknown task type: {task.task_id}"
                )
            
            return result
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e)
            )
    
    def _apply_decisions_to_task(self, task: ExecutionTask) -> ExecutionTask:
        """Apply relevant decisions to a task before execution."""
        # Deep copy the task to avoid modifying the original
        task_copy = copy.deepcopy(task)
        
        # Match decisions to tasks
        if task.task_id == "explore_categories" and "category_selection" in self.decisions:
            decision = self.decisions["category_selection"]
            task_copy.parameters["selection_method"] = decision.selected_option
            
        elif task.task_id == "examine_product_details" and "product_interest" in self.decisions:
            decision = self.decisions["product_interest"]
            task_copy.parameters["selection_criteria"] = decision.selected_option
            
        elif task.task_id == "search_for_product" and "search_method" in self.decisions:
            decision = self.decisions["search_method"]
            task_copy.parameters["method"] = decision.selected_option
            
        elif task.task_id == "select_product" and "product_selection" in self.decisions:
            decision = self.decisions["product_selection"]
            task_copy.parameters["selection_criteria"] = decision.selected_option
            
        elif task.task_id == "select_payment_method" and "payment_selection" in self.decisions:
            decision = self.decisions["payment_selection"]
            task_copy.parameters["selected_method"] = decision.selected_option
            
        elif task.task_id == "check_shipping_cost" and "shipping_option" in self.decisions:
            decision = self.decisions["shipping_option"]
            task_copy.parameters["preferred_option"] = decision.selected_option
        
        return task_copy
    
    def _execute_navigation_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a navigation task."""
        start_time = time.time()
        nav_result = self.browser.navigate(self.results.website_url)
        
        return TaskResult(
            task_id=task.task_id,
            success=nav_result["success"],
            duration=time.time() - start_time,
            error_message=nav_result.get("error", ""),
            metrics={"load_time": nav_result.get("load_time", 0)},
            screenshots=[nav_result.get("screenshot", "")]
        )
    
    def _execute_search_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a search task."""
        start_time = time.time()
        search_term = task.parameters.get("search_term", "product")
        search_result = self.browser.search(search_term)
        
        return TaskResult(
            task_id=task.task_id,
            success=search_result["success"],
            duration=time.time() - start_time,
            error_message=search_result.get("error", ""),
            metrics={"time_to_find": search_result.get("time_taken", 0)},
            screenshots=[search_result.get("screenshot", "")]
        )
    
    def _execute_category_exploration_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a category exploration task."""
        start_time = time.time()
        screenshots = []
        
        try:
            # Get category selectors from browser's current site config
            category_selectors = self.browser.current_site_config.get(
                "category_links", 
                self.browser.selector_config["default"]["category_links"]
            )
            
            categories_explored = 0
            min_categories = task.parameters.get("min_categories", 2)
            max_categories = task.parameters.get("max_categories", 5)
            target_categories = min(max(min_categories, 2), max_categories)
            
            # If decision specified preferred categories, adjust selectors
            selection_method = task.parameters.get("selection_method")
            if selection_method == "preferred_categories":
                # Try to find categories matching persona's preferences
                preferred_categories = self._get_nested_value(
                    self.plan.persona, 
                    "shopping_behavior.product_categories", 
                    []
                )
                if preferred_categories:
                    for category in preferred_categories:
                        # Try to find links containing the category name
                        category_selector = f'a:has-text("{category}")'
                        if self.browser.click(category_selector):
                            categories_explored += 1
                            screenshot = self.browser._take_screenshot(f"category_{category}")
                            if screenshot:
                                screenshots.append(screenshot)
                            
                            # Scroll and examine the category page
                            self.browser.scroll("medium")
                            self.browser._realistic_delay(1.0, 2.0)
                            
                            # Go back for next category
                            self.browser.navigate(self.results.website_url)
                            
                            if categories_explored >= target_categories:
                                break
            
            # If we haven't explored enough categories yet, try general selectors
            if categories_explored < min_categories:
                for selector in category_selectors:
                    if categories_explored >= target_categories:
                        break
                    
                    if self.browser.click(selector):
                        categories_explored += 1
                        screenshot = self.browser._take_screenshot(f"category_{categories_explored}")
                        if screenshot:
                            screenshots.append(screenshot)
                        
                        # Scroll and examine the category page
                        self.browser.scroll("medium")
                        self.browser._realistic_delay(1.0, 2.0)
                        
                        # Go back for next category
                        self.browser.navigate(self.results.website_url)
            
            success = categories_explored >= min_categories
            error_message = "" if success else f"Only explored {categories_explored} categories, minimum required: {min_categories}"
            
            return TaskResult(
                task_id=task.task_id,
                success=success,
                duration=time.time() - start_time,
                error_message=error_message,
                metrics={"categories_explored": categories_explored},
                screenshots=screenshots
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e),
                screenshots=screenshots
            )
    
    def _execute_product_examination_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a product examination task."""
        start_time = time.time()
        screenshots = []
        
        try:
            # Get product selectors from browser's current site config
            product_selectors = self.browser.current_site_config.get(
                "product_links", 
                self.browser.selector_config["default"]["product_links"]
            )
            
            products_examined = 0
            min_products = task.parameters.get("min_products", 2)
            max_products = task.parameters.get("max_products", 4)
            target_products = min(max(min_products, 2), max_products)
            
            # Consider selection criteria from decisions
            selection_criteria = task.parameters.get("selection_criteria", "random")
            
            for selector in product_selectors:
                if products_examined >= target_products:
                    break
                
                # Modify selector based on selection criteria
                if selection_criteria == "price_based":
                    # Look for products with price information
                    modified_selector = f"{selector}:has(.price, [class*='price'])"
                    if not self.browser.click(modified_selector):
                        # Fall back to regular selector
                        if not self.browser.click(selector):
                            continue
                elif selection_criteria == "rating_based":
                    # Look for products with ratings
                    modified_selector = f"{selector}:has(.rating, [class*='rating'], [class*='star'])"
                    if not self.browser.click(modified_selector):
                        # Fall back to regular selector
                        if not self.browser.click(selector):
                            continue
                else:
                    # Use regular selector
                    if not self.browser.click(selector):
                        continue
                
                products_examined += 1
                screenshot = self.browser._take_screenshot(f"product_{products_examined}")
                if screenshot:
                    screenshots.append(screenshot)
                
                # Scroll and examine the product page
                self.browser.scroll("long")
                self.browser._realistic_delay(2.0, 4.0)
                
                # Go back for next product
                self.browser.navigate(self.results.website_url)
            
            success = products_examined >= min_products
            error_message = "" if success else f"Only examined {products_examined} products, minimum required: {min_products}"
            
            return TaskResult(
                task_id=task.task_id,
                success=success,
                duration=time.time() - start_time,
                error_message=error_message,
                metrics={"products_examined": products_examined},
                screenshots=screenshots
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e),
                screenshots=screenshots
            )
    
    def _execute_add_to_cart_task(self, task: ExecutionTask) -> TaskResult:
        """Execute an add to cart task."""
        start_time = time.time()
        
        # First, try to find a product if needed
        product_selector = task.parameters.get("product_selector")
        if not product_selector:
            # Use a product link from the site config
            product_selectors = self.browser.current_site_config.get(
                "product_links", 
                self.browser.selector_config["default"]["product_links"]
            )
            
            # Try each selector
            for selector in product_selectors:
                if self.browser.click(selector):
                    product_selector = selector
                    break
        
        # Now add to cart
        cart_result = self.browser.add_to_cart(product_selector)
        
        return TaskResult(
            task_id=task.task_id,
            success=cart_result["success"],
            duration=time.time() - start_time,
            error_message=cart_result.get("error", ""),
            metrics={"time_to_add": cart_result.get("time_taken", 0)},
            screenshots=[cart_result.get("screenshot", "")]
        )
    
    def _execute_checkout_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a checkout task."""
        start_time = time.time()
        
        # Proceed to checkout
        checkout_result = self.browser.proceed_to_checkout()
        
        return TaskResult(
            task_id=task.task_id,
            success=checkout_result["success"],
            duration=time.time() - start_time,
            error_message=checkout_result.get("error", ""),
            metrics={"time_to_checkout": checkout_result.get("time_taken", 0)},
            screenshots=[checkout_result.get("screenshot", "")]
        )
    
    def _execute_filter_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a filter task for products or search results."""
        start_time = time.time()
        screenshots = []
        
        try:
            # Common filter selectors
            filter_selectors = [
                'input[type="checkbox"]',
                '.filter-option',
                '.facet-option',
                'select',
                '.dropdown'
            ]
            
            filters_applied = 0
            min_filters = task.parameters.get("min_filters", 1)
            max_filters = task.parameters.get("max_filters", 3)
            target_filters = min(max(min_filters, 1), max_filters)
            
            # Try to apply filters
            for selector in filter_selectors:
                if filters_applied >= target_filters:
                    break
                
                try:
                    # Try to find multiple filters
                    count = self.browser.page.locator(selector).count()
                    if count > 0:
                        # Click on a random filter
                        index = random.randint(0, min(count - 1, 5))
                        self.browser.page.locator(selector).nth(index).click()
                        filters_applied += 1
                        
                        # Take screenshot
                        screenshot = self.browser._take_screenshot(f"filter_{filters_applied}")
                        if screenshot:
                            screenshots.append(screenshot)
                        
                        # Wait for filter to apply
                        self.browser._realistic_delay(1.0, 2.0)
                except:
                    continue
            
            success = filters_applied >= min_filters
            error_message = "" if success else f"Only applied {filters_applied} filters, minimum required: {min_filters}"
            
            return TaskResult(
                task_id=task.task_id,
                success=success,
                duration=time.time() - start_time,
                error_message=error_message,
                metrics={"filters_applied": filters_applied},
                screenshots=screenshots
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e),
                screenshots=screenshots
            )
    
    def _execute_price_check_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a price check task."""
        start_time = time.time()
        screenshots = []
        
        try:
            # Common price selectors
            price_selectors = [
                '.price',
                '[class*="price"]',
                '[id*="price"]',
                '.product-price',
                '.amount'
            ]
            
            price_found = False
            price_text = ""
            
            # Try to find price
            for selector in price_selectors:
                element = self.browser.find_element(selector)
                if element:
                    try:
                        price_text = element.text_content() or ""
                        if price_text:
                            price_found = True
                            
                            # Take screenshot
                            screenshot = self.browser._take_screenshot("price_check")
                            if screenshot:
                                screenshots.append(screenshot)
                            
                            break
                    except:
                        continue
            
            error_message = "" if price_found else "Could not find price information"
            
            return TaskResult(
                task_id=task.task_id,
                success=price_found,
                duration=time.time() - start_time,
                error_message=error_message,
                metrics={"price_text": price_text},
                screenshots=screenshots
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e),
                screenshots=screenshots
            )
    
    def _execute_shipping_check_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a shipping cost check task."""
        start_time = time.time()
        screenshots = []
        
        try:
            # Common shipping selectors
            shipping_selectors = [
                '[class*="shipping"]',
                '[id*="shipping"]',
                '.delivery-info',
                '[class*="delivery"]',
                '[data-test*="shipping"]'
            ]
            
            shipping_found = False
            shipping_text = ""
            
            # Try to find shipping info
            for selector in shipping_selectors:
                element = self.browser.find_element(selector)
                if element:
                    try:
                        shipping_text = element.text_content() or ""
                        if shipping_text:
                            shipping_found = True
                            
                            # Take screenshot
                            screenshot = self.browser._take_screenshot("shipping_check")
                            if screenshot:
                                screenshots.append(screenshot)
                            
                            break
                    except:
                        continue
            
            error_message = "" if shipping_found else "Could not find shipping information"
            
            return TaskResult(
                task_id=task.task_id,
                success=shipping_found,
                duration=time.time() - start_time,
                error_message=error_message,
                metrics={"shipping_text": shipping_text},
                screenshots=screenshots
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e),
                screenshots=screenshots
            )
    
    def _execute_review_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a review reading task."""
        start_time = time.time()
        screenshots = []
        
        try:
            # Common review selectors
            review_selectors = [
                '[class*="review"]',
                '[id*="review"]',
                '.reviews-section',
                '.ratings-and-reviews',
                '[data-test*="review"]'
            ]
            
            # Review section selectors
            review_section_found = False
            reviews_read = 0
            
            min_reviews = task.parameters.get("min_reviews", 2)
            max_reviews = task.parameters.get("max_reviews", 5)
            target_reviews = min(max(min_reviews, 2), max_reviews)
            
            # Try to find review section
            for selector in review_selectors:
                element = self.browser.find_element(selector)
                if element:
                    review_section_found = True
                    
                    # Scroll to review section
                    try:
                        self.browser.page.evaluate(f"""
                            const element = document.querySelector('{selector}');
                            if (element) element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        """)
                        
                        # Take screenshot
                        screenshot = self.browser._take_screenshot("reviews_section")
                        if screenshot:
                            screenshots.append(screenshot)
                        
                        # Wait for scroll
                        self.browser._realistic_delay(1.0, 2.0)
                        
                        # Count reviews
                        reviews_read = min(
                            target_reviews,
                            self.browser.page.locator(f"{selector} > *").count()
                        )
                        
                        # Scroll through reviews
                        for i in range(min(3, reviews_read)):
                            self.browser.scroll("short")
                            self.browser._realistic_delay(1.0, 2.0)
                    except:
                        pass
                    
                    break
            
            success = review_section_found and reviews_read >= min_reviews
            error_message = ""
            if not review_section_found:
                error_message = "Could not find review section"
            elif reviews_read < min_reviews:
                error_message = f"Only found {reviews_read} reviews, minimum required: {min_reviews}"
            
            return TaskResult(
                task_id=task.task_id,
                success=success,
                duration=time.time() - start_time,
                error_message=error_message,
                metrics={"reviews_read": reviews_read},
                screenshots=screenshots
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e),
                screenshots=screenshots
            )
    
    def _execute_specifications_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a specifications check task."""
        start_time = time.time()
        screenshots = []
        
        try:
            # Common specification selectors
            spec_selectors = [
                '[class*="specification"]',
                '[class*="spec"]',
                '[id*="specification"]',
                '[id*="spec"]',
                '.product-details',
                '.technical-details',
                '.features'
            ]
            
            specs_found = False
            specs_count = 0
            
            min_specs = task.parameters.get("min_specs", 3)
            max_specs = task.parameters.get("max_specs", 8)
            target_specs = min(max(min_specs, 3), max_specs)
            
            # Try to find specifications
            for selector in spec_selectors:
                element = self.browser.find_element(selector)
                if element:
                    specs_found = True
                    
                    # Scroll to specifications section
                    try:
                        self.browser.page.evaluate(f"""
                            const element = document.querySelector('{selector}');
                            if (element) element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        """)
                        
                        # Take screenshot
                        screenshot = self.browser._take_screenshot("specifications")
                        if screenshot:
                            screenshots.append(screenshot)
                        
                        # Wait for scroll
                        self.browser._realistic_delay(1.0, 2.0)
                        
                        # Count specifications (rows/items)
                        specs_count = min(
                            target_specs,
                            max(
                                self.browser.page.locator(f"{selector} tr").count(),
                                self.browser.page.locator(f"{selector} li").count(),
                                self.browser.page.locator(f"{selector} > *").count()
                            )
                        )
                        
                        # Scroll through specifications
                        for i in range(min(3, specs_count)):
                            self.browser.scroll("short")
                            self.browser._realistic_delay(0.5, 1.5)
                    except:
                        pass
                    
                    break
            
            success = specs_found and specs_count >= min_specs
            error_message = ""
            if not specs_found:
                error_message = "Could not find specifications section"
            elif specs_count < min_specs:
                error_message = f"Only found {specs_count} specifications, minimum required: {min_specs}"
            
            return TaskResult(
                task_id=task.task_id,
                success=success,
                duration=time.time() - start_time,
                error_message=error_message,
                metrics={"specs_examined": specs_count},
                screenshots=screenshots
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e),
                screenshots=screenshots
            )
    
    def _execute_find_account_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a find account section task."""
        start_time = time.time()
        screenshots = []
        
        try:
            # Common account section selectors
            account_selectors = [
                'a[href*="account"]',
                'a[href*="login"]',
                'a[href*="profile"]',
                '[class*="account"]',
                '[class*="login"]',
                '[class*="user"]',
                'header [class*="account"]',
                'header [class*="login"]'
            ]
            
            account_section_found = False
            
            # Try to find account section
            for selector in account_selectors:
                element = self.browser.find_element(selector)
                if element:
                    account_section_found = True
                    
                    # Take screenshot
                    screenshot = self.browser._take_screenshot("account_section")
                    if screenshot:
                        screenshots.append(screenshot)
                    
                    # Click the account link to see the account page
                    if self.browser.click(selector):
                        # Wait for page to load
                        self.browser._realistic_delay(1.0, 2.0)
                        
                        # Take screenshot of account page
                        screenshot = self.browser._take_screenshot("account_page")
                        if screenshot:
                            screenshots.append(screenshot)
                        
                        # Go back to homepage
                        self.browser.navigate(self.results.website_url)
                    
                    break
            
            error_message = "" if account_section_found else "Could not find account section"
            
            return TaskResult(
                task_id=task.task_id,
                success=account_section_found,
                duration=time.time() - start_time,
                error_message=error_message,
                screenshots=screenshots
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e),
                screenshots=screenshots
            )
    
    def _execute_form_fill_task(self, task: ExecutionTask) -> TaskResult:
        """Execute a form filling task (shipping, payment, etc.)."""
        start_time = time.time()
        screenshots = []
        
        try:
            # Get form fields to fill
            form_fields = task.parameters.get("form_fields", {})
            if not form_fields:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    duration=time.time() - start_time,
                    error_message="No form fields specified",
                    screenshots=screenshots
                )
            
            fields_filled = 0
            
            # Fill each field
            for field_name, field_value in form_fields.items():
                # Common selectors for this field
                field_selectors = [
                    f'input[name="{field_name}"]',
                    f'input[id="{field_name}"]',
                    f'input[placeholder*="{field_name}" i]',
                    f'textarea[name="{field_name}"]',
                    f'select[name="{field_name}"]'
                ]
                
                for selector in field_selectors:
                    if self.browser.fill_form(selector, field_value):
                        fields_filled += 1
                        break
            
            # Take screenshot after filling form
            screenshot = self.browser._take_screenshot(f"form_fill_{task.task_id}")
            if screenshot:
                screenshots.append(screenshot)
            
            success = fields_filled > 0
            error_message = "" if success else "Could not fill any form fields"
            
            return TaskResult(
                task_id=task.task_id,
                success=success,
                duration=time.time() - start_time,
                error_message=error_message,
                metrics={"fields_filled": fields_filled},
                screenshots=screenshots
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                duration=time.time() - start_time,
                error_message=str(e),
                screenshots=screenshots
            )
    
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