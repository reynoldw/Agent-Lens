"""
Job Execution Engine for E-commerce Website Simulation.

This module contains the components for planning and executing
job-based simulations on e-commerce websites.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import time
import random
import os
from playwright.sync_api import Page, BrowserContext, ElementHandle

from src.interaction.job_definitions import JobDefinition, TaskDefinition, DecisionPoint
from src.persona.generator import Persona
from src.interaction.models import ExecutionTask, ExecutionDecision, ExecutionPlan

# Basic structure for the job executor components 

@dataclass
class ExecutionTask:
    """A task prepared for execution with persona-specific parameters."""
    task_id: str
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    fallback_tasks: List[str] = field(default_factory=list)


@dataclass
class ExecutionDecision:
    """A decision point prepared with a selected option based on persona."""
    decision_id: str
    name: str
    description: str
    selected_option: str
    rationale: str = ""


@dataclass
class ExecutionPlan:
    """A personalized plan for executing a job."""
    job_id: str
    job_name: str
    persona: Dict[str, Any]
    tasks: List[ExecutionTask] = field(default_factory=list)
    decisions: List[ExecutionDecision] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    estimated_duration: Dict[str, float] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    duration: float  # Time taken in seconds
    error_message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    
    def is_blocking_failure(self) -> bool:
        """Return True if this failure should block further execution."""
        # Critical tasks that would block the entire job if they fail
        blocking_task_ids = [
            "navigate_to_homepage", 
            "search_for_product",
            "add_to_cart",
            "proceed_to_checkout"
        ]
        return not self.success and self.task_id in blocking_task_ids


@dataclass
class JobExecutionResults:
    """Complete results of a job execution."""
    job_id: str
    job_name: str
    persona: Dict[str, Any]
    website_url: str
    start_time: float
    end_time: float = 0.0
    task_results: List[TaskResult] = field(default_factory=list)
    success: bool = False
    overall_score: float = 0.0
    navigation_score: float = 0.0
    design_score: float = 0.0
    findability_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    accessibility_issues: List[str] = field(default_factory=list)
    behavioral_data: Dict[str, Any] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    
    @property
    def total_duration(self) -> float:
        """Get the total duration of the job execution in seconds."""
        return self.end_time - self.start_time
    
    @property
    def successful_tasks(self) -> List[TaskResult]:
        """Get all successful task results."""
        return [task for task in self.task_results if task.success]
    
    @property
    def failed_tasks(self) -> List[TaskResult]:
        """Get all failed task results."""
        return [task for task in self.task_results if not task.success]
    
    def add_task_result(self, result: TaskResult) -> None:
        """Add a task result to the job results."""
        self.task_results.append(result)
    
    def add_issue(self, issue: str) -> None:
        """Add an issue to the job results."""
        self.issues.append(issue)
    
    def add_accessibility_issue(self, issue: str) -> None:
        """Add an accessibility issue to the job results."""
        self.accessibility_issues.append(issue)
    
    def calculate_scores(self) -> None:
        """Calculate overall and specific scores based on task results."""
        # Calculate success rate
        if not self.task_results:
            self.success = False
            self.overall_score = 0.0
            return
        
        # Calculate success based on critical tasks
        critical_tasks = ["navigate_to_homepage", "search_for_product"]
        critical_success = all(
            any(task.task_id == critical_id and task.success for task in self.task_results)
            for critical_id in critical_tasks
        )
        
        # Calculate success percentage
        success_percentage = len(self.successful_tasks) / len(self.task_results)
        
        # Task is successful if critical tasks succeeded and at least 60% of all tasks succeeded
        self.success = critical_success and success_percentage >= 0.6
        
        # Calculate scores
        self.navigation_score = self._calculate_navigation_score()
        self.design_score = self._calculate_design_score()
        self.findability_score = self._calculate_findability_score()
        
        # Overall score is weighted average
        self.overall_score = (self.navigation_score * 0.4 + 
                             self.design_score * 0.3 + 
                             self.findability_score * 0.3)
    
    def _calculate_navigation_score(self) -> float:
        """Calculate the navigation score based on task results."""
        # Navigation-related tasks
        nav_tasks = ["navigate_to_homepage", "explore_categories", "proceed_to_checkout", "find_account_section"]
        nav_results = [task for task in self.task_results if task.task_id in nav_tasks]
        
        if not nav_results:
            return 5.0  # Default score
        
        # Calculate success rate for navigation tasks
        nav_success_rate = sum(1 for task in nav_results if task.success) / len(nav_results)
        
        # Check load times if available
        nav_load_times = [task.metrics.get("load_time", 0) for task in nav_results if "load_time" in task.metrics]
        avg_load_time = sum(nav_load_times) / len(nav_load_times) if nav_load_times else 0
        
        # Determine load time factor (faster = better score)
        load_time_factor = max(0, min(1, 1 - (avg_load_time / 5)))  # Scale: 0s=1.0, 5s+=0.0
        
        # Combine factors (70% success rate, 30% load time)
        return min(10, max(0, (nav_success_rate * 7 + load_time_factor * 3) * 10 / 10))
    
    def _calculate_design_score(self) -> float:
        """Calculate the design score based on task results and issues."""
        # Base design score on issues and accessibility issues
        design_penalty = min(5, len(self.issues) * 0.5 + len(self.accessibility_issues) * 0.7)
        
        # Start with max score and apply penalties
        design_score = 10 - design_penalty
        
        # Adjust based on behavioral data if available
        if "frustration_indicators" in self.behavioral_data:
            frustration = self.behavioral_data["frustration_indicators"]
            design_score -= min(2, frustration * 0.2)
        
        return max(0, min(10, design_score))
    
    def _calculate_findability_score(self) -> float:
        """Calculate the findability score based on task results."""
        # Findability-related tasks
        find_tasks = ["search_for_product", "search_for_product_category", "filter_products", "filter_search_results"]
        find_results = [task for task in self.task_results if task.task_id in find_tasks]
        
        if not find_results:
            return 5.0  # Default score
        
        # Calculate success rate for findability tasks
        find_success_rate = sum(1 for task in find_results if task.success) / len(find_results)
        
        # Check time to find if available
        find_times = [task.metrics.get("time_to_find", 0) for task in find_results if "time_to_find" in task.metrics]
        avg_find_time = sum(find_times) / len(find_times) if find_times else 0
        
        # Determine find time factor (faster = better score)
        find_time_factor = max(0, min(1, 1 - (avg_find_time / 10)))  # Scale: 0s=1.0, 10s+=0.0
        
        # Combine factors (80% success rate, 20% find time)
        return min(10, max(0, (find_success_rate * 8 + find_time_factor * 2) * 10 / 10))


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
        
        # Initialize the page
        self._initialize_page()
    
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
    
    def _setup_behavioral_tracking(self):
        """Set up tracking for user behavior simulation."""
        # Track mouse movements
        self.page.on("mouse", lambda: self._track_event("mouse_movement"))
        
        # Track navigation events
        self.page.on("framenavigated", lambda frame: 
                    self._track_event("navigation", {"url": frame.url}) if frame.is_main_frame else None)
    
    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL with persona-specific behavior."""
        try:
            # Record start time
            start_time = time.time()
            
            # Add some randomized delay based on tech proficiency
            self._realistic_delay(0.5, 1.5)
            
            # Perform the navigation
            response = self.page.goto(url, wait_until="networkidle", timeout=60000)
            
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
    
    def find_element(self, selector: str, timeout: int = None) -> Optional[ElementHandle]:
        """Find an element with persona-specific behavior."""
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
        try:
            # Record start time
            start_time = time.time()
            
            # Common search input selectors
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="search" i]',
                'input[placeholder*="find" i]',
                'input[name*="search" i]',
                'input[id*="search" i]',
                'input[class*="search" i]',
                '.search-input',
                '#search'
            ]
            
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
            
            # Find and click search button if present
            search_button_selectors = [
                'button[type="submit"]',
                'button.search-button',
                'button[aria-label*="search" i]',
                'input[type="submit"]'
            ]
            
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
    
    def scroll(self, distance: str = "medium", direction: str = "down") -> bool:
        """Scroll the page with persona-specific behavior."""
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


class TaskPlanner:
    """Plans the execution of a job based on a persona."""
    
    def __init__(self, persona, job_definition: JobDefinition):
        """
        Initialize the task planner.
        
        Args:
            persona: The persona to plan for (dict or Persona object)
            job_definition: The job definition to plan
        """
        # Convert persona to dictionary if it's not already
        if not isinstance(persona, dict):
            self.persona = vars(persona)
        else:
            self.persona = persona
            
        self.job_definition = job_definition
    
    def create_execution_plan(self) -> ExecutionPlan:
        """Generate a personalized execution plan for the job."""
        # Create base execution plan
        plan = ExecutionPlan(
            job_id=self.job_definition.job_id,
            job_name=self.job_definition.name,
            persona=self.persona,
            success_criteria=self.job_definition.success_criteria,
            estimated_duration=self.job_definition.estimated_duration
        )
        
        # Process tasks based on persona characteristics
        self._plan_tasks(plan)
        
        # Process decision points based on persona characteristics
        self._plan_decisions(plan)
        
        return plan
    
    def _plan_tasks(self, plan: ExecutionPlan):
        """Plan the tasks based on persona characteristics."""
        # Get persona characteristics
        tech_proficiency = self._get_nested_value(self.persona, "technical.proficiency", 5)
        patience_level = self._get_nested_value(self.persona, "e_commerce_specific.patience_level", 5)
        shopping_frequency = self._get_nested_value(self.persona, "shopping_behavior.frequency", "Monthly")
        
        # Add all required tasks
        for task in self.job_definition.tasks:
            if task.required:
                # Create execution task
                execution_task = ExecutionTask(
                    task_id=task.task_id,
                    name=task.name,
                    description=task.description,
                    parameters=task.parameters.copy(),  # Copy to avoid modifying original
                    fallback_tasks=task.fallback_tasks.copy()  # Copy to avoid modifying original
                )
                
                # Customize task parameters based on persona
                self._customize_task_parameters(execution_task, tech_proficiency, patience_level, shopping_frequency)
                
                # Add to plan
                plan.tasks.append(execution_task)
        
        # Consider optional tasks based on persona characteristics
        for task in self.job_definition.tasks:
            if not task.required:
                # Determine if task should be included based on persona
                if self._should_include_optional_task(task, tech_proficiency, patience_level, shopping_frequency):
                    # Create execution task
                    execution_task = ExecutionTask(
                        task_id=task.task_id,
                        name=task.name,
                        description=task.description,
                        parameters=task.parameters.copy(),  # Copy to avoid modifying original
                        fallback_tasks=task.fallback_tasks.copy()  # Copy to avoid modifying original
                    )
                    
                    # Customize task parameters based on persona
                    self._customize_task_parameters(execution_task, tech_proficiency, patience_level, shopping_frequency)
                    
                    # Add to plan
                    plan.tasks.append(execution_task)
    
    def _plan_decisions(self, plan: ExecutionPlan):
        """Plan decisions based on persona characteristics."""
        for decision_point in self.job_definition.decision_points:
            # Determine the selected option based on persona factors
            selected_option, rationale = self._select_option_for_decision(decision_point)
            
            # Create execution decision
            execution_decision = ExecutionDecision(
                decision_id=decision_point.decision_id,
                name=decision_point.name,
                description=decision_point.description,
                selected_option=selected_option,
                rationale=rationale
            )
            
            # Add to plan
            plan.decisions.append(execution_decision)
    
    def _customize_task_parameters(self, task: ExecutionTask, tech_proficiency: int, patience_level: int, shopping_frequency: str):
        """Customize task parameters based on persona characteristics."""
        # Example of parameter customization based on persona
        if "min_categories" in task.parameters and "max_categories" in task.parameters:
            # More tech-savvy users explore more categories
            if tech_proficiency > 7:
                task.parameters["min_categories"] = min(task.parameters["min_categories"] + 1, task.parameters["max_categories"])
            elif tech_proficiency < 3:
                task.parameters["max_categories"] = max(task.parameters["min_categories"], task.parameters["max_categories"] - 1)
        
        if "min_products" in task.parameters and "max_products" in task.parameters:
            # More patient users examine more products
            if patience_level > 7:
                task.parameters["min_products"] = min(task.parameters["min_products"] + 1, task.parameters["max_products"])
                task.parameters["max_products"] = min(task.parameters["max_products"] + 1, 10)
            elif patience_level < 3:
                task.parameters["max_products"] = max(task.parameters["min_products"], task.parameters["max_products"] - 1)
        
        # Adjust search parameters based on shopping behavior
        if task.task_id == "search_for_product" and "search_term" in task.parameters:
            # Set a realistic search term based on preferred categories
            preferred_categories = self._get_nested_value(self.persona, "shopping_behavior.product_categories", [])
            if preferred_categories:
                category = random.choice(preferred_categories) if isinstance(preferred_categories, list) else preferred_categories
                search_terms = {
                    "Electronics": ["smartphone", "laptop", "headphones", "camera"],
                    "Fashion": ["shoes", "dress", "jacket", "jeans"],
                    "Home": ["sofa", "lamp", "kitchen", "bedding"],
                    "Books": ["novel", "cookbook", "biography", "fiction"],
                    "Sports": ["sneakers", "fitness", "bike", "yoga"],
                    "Beauty": ["skincare", "makeup", "fragrance", "haircare"],
                    "Food": ["coffee", "chocolate", "snacks", "tea"]
                }
                
                if category in search_terms:
                    task.parameters["search_term"] = random.choice(search_terms[category])
                else:
                    task.parameters["search_term"] = "product"
    
    def _should_include_optional_task(self, task: TaskDefinition, tech_proficiency: int, patience_level: int, shopping_frequency: str) -> bool:
        """Determine if an optional task should be included based on persona characteristics."""
        # Base inclusion probability
        include_probability = 0.5
        
        # Adjust based on tech proficiency
        if tech_proficiency > 7 and task.task_id in ["filter_products", "read_reviews"]:
            include_probability += 0.3
        elif tech_proficiency < 3 and task.task_id in ["filter_products", "check_specifications"]:
            include_probability -= 0.3
        
        # Adjust based on patience level
        if patience_level > 7 and task.task_id in ["read_reviews", "check_shipping_cost", "browse_featured_products"]:
            include_probability += 0.2
        elif patience_level < 3:
            include_probability -= 0.2
        
        # Adjust based on shopping frequency
        if shopping_frequency in ["Daily", "Weekly"] and task.task_id in ["check_shipping_cost", "filter_search_results"]:
            include_probability += 0.2
        
        # Random decision based on probability
        return random.random() < include_probability
    
    def _select_option_for_decision(self, decision_point: DecisionPoint) -> tuple:
        """Select an option for a decision point based on persona factors."""
        options = decision_point.options
        if not options:
            return "default", "No options available"
        
        # Default to random if no specific logic applies
        default_option = random.choice(options)
        default_rationale = "Random selection based on available options"
        
        # Factor-based option selection
        for factor in decision_point.persona_factors:
            factor_value = self._get_nested_value(self.persona, factor)
            if factor_value is not None:
                # Handle specific decision points with custom logic
                if decision_point.decision_id == "category_selection":
                    if "preferred_categories" in options and self._get_nested_value(self.persona, "shopping_behavior.product_categories"):
                        return "preferred_categories", f"Based on persona's preferred product categories: {self._get_nested_value(self.persona, 'shopping_behavior.product_categories')}"
                
                elif decision_point.decision_id == "product_selection":
                    price_sensitivity = self._get_nested_value(self.persona, "shopping_behavior.price_sensitivity", "Mid-range")
                    if price_sensitivity == "Budget" and "lowest_price" in options:
                        return "lowest_price", "Based on budget price sensitivity"
                    
                    brand_loyalty = self._get_nested_value(self.persona, "shopping_behavior.brand_loyalty", "Price-driven")
                    if brand_loyalty == "Brand loyal" and "specific_brand" in options:
                        return "specific_brand", "Based on brand loyalty"
                    
                    if "best_rated" in options and self._get_nested_value(self.persona, "e_commerce_specific.importance_of_reviews", 5) > 7:
                        return "best_rated", "Based on high importance of reviews"
                
                elif decision_point.decision_id == "payment_selection":
                    preferred_methods = self._get_nested_value(self.persona, "technical.payment_methods", [])
                    if preferred_methods:
                        for method in preferred_methods:
                            method_lower = method.lower().replace(" ", "_")
                            if method_lower in options:
                                return method_lower, f"Based on preferred payment method: {method}"
                
                elif decision_point.decision_id == "search_method":
                    if tech_proficiency := self._get_nested_value(self.persona, "technical.proficiency"):
                        if tech_proficiency > 7 and "search_bar" in options:
                            return "search_bar", "Based on high tech proficiency"
                        elif tech_proficiency < 3 and "category_navigation" in options:
                            return "category_navigation", "Based on low tech proficiency"
        
        return default_option, default_rationale
    
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