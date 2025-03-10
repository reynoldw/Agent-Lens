"""
Job Definitions for E-commerce Website Simulation.

This module defines the various "jobs to be done" that can be simulated
on e-commerce websites, representing complete user journeys.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class TaskDefinition:
    """Definition of a single task within a job."""
    task_id: str
    name: str
    description: str
    required: bool = True
    fallback_tasks: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionPoint:
    """A point in the job where the persona must make a decision."""
    decision_id: str
    name: str
    description: str
    options: List[str]
    persona_factors: List[str]  # Factors from persona that influence this decision


@dataclass
class JobDefinition:
    """Definition of a complete job to be done."""
    job_id: str
    name: str
    description: str
    tasks: List[TaskDefinition]
    decision_points: List[DecisionPoint] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    applicable_personas: List[str] = field(default_factory=list)  # Persona types this job applies to
    estimated_duration: Dict[str, float] = field(default_factory=dict)  # Min, max, avg duration in seconds


class JobRegistry:
    """Registry of all available job definitions."""
    
    def __init__(self):
        """Initialize the job registry with predefined jobs."""
        self.jobs = {}
        self._initialize_jobs()
    
    def _initialize_jobs(self):
        """Create and register all predefined jobs."""
        # Register all predefined jobs
        self._register_product_discovery_job()
        self._register_price_check_job()
        self._register_purchase_completion_job()
        self._register_research_comparison_job()
        self._register_account_management_job()
    
    def _register_product_discovery_job(self):
        """Register the product discovery job."""
        tasks = [
            TaskDefinition(
                task_id="navigate_to_homepage",
                name="Navigate to Homepage",
                description="Navigate to the website's homepage",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="explore_categories",
                name="Explore Product Categories",
                description="Browse through available product categories",
                required=True,
                parameters={"min_categories": 2, "max_categories": 5}
            ),
            TaskDefinition(
                task_id="browse_featured_products",
                name="Browse Featured Products",
                description="Look at featured or recommended products",
                required=False,
                parameters={"min_products": 1, "max_products": 3}
            ),
            TaskDefinition(
                task_id="examine_product_details",
                name="Examine Product Details",
                description="View detailed information about specific products",
                required=True,
                parameters={"min_products": 2, "max_products": 4}
            ),
            TaskDefinition(
                task_id="filter_products",
                name="Filter Products",
                description="Apply filters to narrow down product selection",
                required=False,
                parameters={"min_filters": 1, "max_filters": 3}
            )
        ]
        
        decision_points = [
            DecisionPoint(
                decision_id="category_selection",
                name="Category Selection",
                description="Which product categories to explore",
                options=["preferred_categories", "featured_categories", "random_categories"],
                persona_factors=["shopping_behavior.product_categories", "goals.primary"]
            ),
            DecisionPoint(
                decision_id="product_interest",
                name="Product Interest",
                description="Which products to examine in detail",
                options=["price_based", "rating_based", "feature_based", "random"],
                persona_factors=["shopping_behavior.price_sensitivity", "e_commerce_specific.importance_of_reviews"]
            )
        ]
        
        success_criteria = [
            "At least 2 product categories explored",
            "At least 2 product detail pages viewed",
            "Spent minimum of 30 seconds on product pages"
        ]
        
        job = JobDefinition(
            job_id="product_discovery",
            name="Product Discovery",
            description="Browse the website to discover products of interest",
            tasks=tasks,
            decision_points=decision_points,
            success_criteria=success_criteria,
            applicable_personas=["all"],
            estimated_duration={"min": 60, "max": 300, "avg": 180}
        )
        
        self.jobs["product_discovery"] = job
    
    def _register_price_check_job(self):
        """Register the price check job."""
        tasks = [
            TaskDefinition(
                task_id="navigate_to_homepage",
                name="Navigate to Homepage",
                description="Navigate to the website's homepage",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="search_for_product",
                name="Search for Product",
                description="Search for a specific product by name",
                required=True,
                parameters={"search_term": ""}
            ),
            TaskDefinition(
                task_id="filter_search_results",
                name="Filter Search Results",
                description="Apply filters to narrow down search results",
                required=False,
                parameters={"min_filters": 0, "max_filters": 2}
            ),
            TaskDefinition(
                task_id="check_product_price",
                name="Check Product Price",
                description="View the price of the product",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="check_shipping_cost",
                name="Check Shipping Cost",
                description="View the shipping cost for the product",
                required=False,
                parameters={}
            )
        ]
        
        decision_points = [
            DecisionPoint(
                decision_id="search_method",
                name="Search Method",
                description="How to search for the product",
                options=["search_bar", "category_navigation", "featured_products"],
                persona_factors=["technical.proficiency", "e_commerce_specific.previous_online_shopping_experience"]
            ),
            DecisionPoint(
                decision_id="price_evaluation",
                name="Price Evaluation",
                description="How to evaluate the product price",
                options=["compare_options", "check_single_price", "look_for_discounts"],
                persona_factors=["shopping_behavior.price_sensitivity", "shopping_behavior.research_behavior"]
            )
        ]
        
        success_criteria = [
            "Product successfully found",
            "Price information viewed",
            "Price information understood"
        ]
        
        job = JobDefinition(
            job_id="price_check",
            name="Price Check",
            description="Search for a specific product to check its price",
            tasks=tasks,
            decision_points=decision_points,
            success_criteria=success_criteria,
            applicable_personas=["all"],
            estimated_duration={"min": 30, "max": 180, "avg": 90}
        )
        
        self.jobs["price_check"] = job
    
    def _register_purchase_completion_job(self):
        """Register the purchase completion job."""
        tasks = [
            TaskDefinition(
                task_id="navigate_to_homepage",
                name="Navigate to Homepage",
                description="Navigate to the website's homepage",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="search_for_product",
                name="Search for Product",
                description="Search for a specific product by name",
                required=True,
                parameters={"search_term": ""}
            ),
            TaskDefinition(
                task_id="select_product",
                name="Select Product",
                description="Select a product from search results",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="add_to_cart",
                name="Add to Cart",
                description="Add the selected product to the shopping cart",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="proceed_to_checkout",
                name="Proceed to Checkout",
                description="Navigate to the checkout page",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="fill_shipping_info",
                name="Fill Shipping Information",
                description="Enter shipping address and contact information",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="select_payment_method",
                name="Select Payment Method",
                description="Choose a payment method",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="complete_order",
                name="Complete Order",
                description="Finalize the purchase",
                required=True,
                parameters={}
            )
        ]
        
        decision_points = [
            DecisionPoint(
                decision_id="product_selection",
                name="Product Selection",
                description="Which product to select from search results",
                options=["first_result", "best_rated", "lowest_price", "specific_brand"],
                persona_factors=["shopping_behavior.price_sensitivity", "shopping_behavior.brand_loyalty"]
            ),
            DecisionPoint(
                decision_id="payment_selection",
                name="Payment Selection",
                description="Which payment method to use",
                options=["credit_card", "paypal", "apple_pay", "google_pay"],
                persona_factors=["technical.payment_methods", "technical.proficiency"]
            ),
            DecisionPoint(
                decision_id="shipping_option",
                name="Shipping Option",
                description="Which shipping option to select",
                options=["standard", "express", "cheapest", "fastest"],
                persona_factors=["e_commerce_specific.importance_of_shipping_speed", "shopping_behavior.price_sensitivity"]
            )
        ]
        
        success_criteria = [
            "Product successfully added to cart",
            "Shipping information entered correctly",
            "Payment method selected",
            "Order confirmation page reached"
        ]
        
        job = JobDefinition(
            job_id="purchase_completion",
            name="Purchase Completion",
            description="Search for a product, add to cart, and complete checkout",
            tasks=tasks,
            decision_points=decision_points,
            success_criteria=success_criteria,
            applicable_personas=["all"],
            estimated_duration={"min": 120, "max": 600, "avg": 300}
        )
        
        self.jobs["purchase_completion"] = job
    
    def _register_research_comparison_job(self):
        """Register the research and comparison job."""
        tasks = [
            TaskDefinition(
                task_id="navigate_to_homepage",
                name="Navigate to Homepage",
                description="Navigate to the website's homepage",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="search_for_product_category",
                name="Search for Product Category",
                description="Search for a category of products",
                required=True,
                parameters={"category": ""}
            ),
            TaskDefinition(
                task_id="filter_products",
                name="Filter Products",
                description="Apply filters to narrow down product selection",
                required=True,
                parameters={"min_filters": 1, "max_filters": 4}
            ),
            TaskDefinition(
                task_id="compare_products",
                name="Compare Products",
                description="Compare multiple products side by side",
                required=True,
                parameters={"min_products": 2, "max_products": 5}
            ),
            TaskDefinition(
                task_id="read_reviews",
                name="Read Reviews",
                description="Read customer reviews for products",
                required=False,
                parameters={"min_reviews": 2, "max_reviews": 5}
            ),
            TaskDefinition(
                task_id="check_specifications",
                name="Check Specifications",
                description="Review detailed specifications for products",
                required=True,
                parameters={"min_specs": 3, "max_specs": 8}
            )
        ]
        
        decision_points = [
            DecisionPoint(
                decision_id="comparison_factors",
                name="Comparison Factors",
                description="Which factors to prioritize when comparing products",
                options=["price", "features", "reviews", "brand", "availability"],
                persona_factors=["shopping_behavior.price_sensitivity", "shopping_behavior.brand_loyalty", "e_commerce_specific.importance_of_reviews"]
            ),
            DecisionPoint(
                decision_id="research_depth",
                name="Research Depth",
                description="How deeply to research each product",
                options=["quick_overview", "detailed_research", "exhaustive_comparison"],
                persona_factors=["shopping_behavior.research_behavior", "e_commerce_specific.patience_level"]
            )
        ]
        
        success_criteria = [
            "At least 2 products compared",
            "Key specifications reviewed",
            "Price comparison completed",
            "Minimum of 3 minutes spent on research"
        ]
        
        job = JobDefinition(
            job_id="research_comparison",
            name="Research & Comparison",
            description="Research multiple products to compare features and prices",
            tasks=tasks,
            decision_points=decision_points,
            success_criteria=success_criteria,
            applicable_personas=["researcher", "value_seeker", "quality_focused"],
            estimated_duration={"min": 180, "max": 900, "avg": 420}
        )
        
        self.jobs["research_comparison"] = job
    
    def _register_account_management_job(self):
        """Register the account management job."""
        tasks = [
            TaskDefinition(
                task_id="navigate_to_homepage",
                name="Navigate to Homepage",
                description="Navigate to the website's homepage",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="find_account_section",
                name="Find Account Section",
                description="Locate the account or profile section",
                required=True,
                parameters={}
            ),
            TaskDefinition(
                task_id="create_account",
                name="Create Account",
                description="Create a new user account",
                required=False,
                parameters={}
            ),
            TaskDefinition(
                task_id="login_to_account",
                name="Login to Account",
                description="Log in to an existing account",
                required=False,
                parameters={}
            ),
            TaskDefinition(
                task_id="update_profile",
                name="Update Profile",
                description="Update profile information",
                required=False,
                parameters={}
            ),
            TaskDefinition(
                task_id="check_order_history",
                name="Check Order History",
                description="View order history and status",
                required=False,
                parameters={}
            ),
            TaskDefinition(
                task_id="manage_payment_methods",
                name="Manage Payment Methods",
                description="Add or update payment methods",
                required=False,
                parameters={}
            ),
            TaskDefinition(
                task_id="manage_addresses",
                name="Manage Addresses",
                description="Add or update shipping addresses",
                required=False,
                parameters={}
            )
        ]
        
        decision_points = [
            DecisionPoint(
                decision_id="account_action",
                name="Account Action",
                description="What account management action to perform",
                options=["create_new", "login_existing", "update_profile", "check_orders"],
                persona_factors=["e_commerce_specific.previous_online_shopping_experience", "technical.proficiency"]
            ),
            DecisionPoint(
                decision_id="information_sharing",
                name="Information Sharing",
                description="How much personal information to provide",
                options=["minimal", "standard", "detailed"],
                persona_factors=["demographics.age", "technical.proficiency"]
            )
        ]
        
        success_criteria = [
            "Account section successfully located",
            "Primary account action completed",
            "Navigation through account settings completed"
        ]
        
        job = JobDefinition(
            job_id="account_management",
            name="Account Management",
            description="Create an account, manage profile, or check order history",
            tasks=tasks,
            decision_points=decision_points,
            success_criteria=success_criteria,
            applicable_personas=["all"],
            estimated_duration={"min": 60, "max": 300, "avg": 180}
        )
        
        self.jobs["account_management"] = job
    
    def get_job(self, job_id: str) -> Optional[JobDefinition]:
        """Get a job definition by ID."""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[JobDefinition]:
        """Get all registered job definitions."""
        return list(self.jobs.values())
    
    def get_jobs_for_persona(self, persona_type: str) -> List[JobDefinition]:
        """Get all jobs applicable to a specific persona type."""
        return [job for job in self.jobs.values() 
                if "all" in job.applicable_personas or persona_type in job.applicable_personas] 