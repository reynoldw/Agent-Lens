"""
Simulator Bridge for E-Commerce Website Evaluator.

This module provides a compatibility layer between the old action-based simulator
and the new job-centric simulation approach, allowing for gradual migration.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import asdict
import re

from src.interaction.simulator import WebsiteSimulator
from src.interaction.job_definitions import JobRegistry
from src.interaction.job_executor import TaskPlanner
from src.interaction.task_executor import TaskExecutor
from src.interaction.persona_browser import PersonaBasedBrowser
from src.interaction.models import JobExecutionResults
from src.utils.error_handling import SimulationError, capture_exceptions
from src.utils.config import get_config

# Configure logging
logger = logging.getLogger(__name__)


class SimulatorBridge:
    """
    Bridge between old simulator and new job-centric approach.
    
    This class maintains the same interface as the old WebsiteSimulator
    but internally uses the new job-centric approach.
    """
    
    def __init__(self, use_legacy: bool = False, browser_pool=None):
        """
        Initialize the simulator bridge.
        
        Args:
            use_legacy: Whether to use the legacy simulator (for fallback)
            browser_pool: Optional browser pool instance to use (if None, will be imported from app)
        """
        self.use_legacy = use_legacy
        self.config = get_config()
        
        # Initialize components based on mode
        if use_legacy:
            self.legacy_simulator = WebsiteSimulator()
        else:
            self.job_registry = JobRegistry()
            # Use provided browser pool or import from app
            if browser_pool is not None:
                self.browser_pool = browser_pool
            else:
                from src.app import browser_pool as app_browser_pool
                self.browser_pool = app_browser_pool
        
        self.results = []
    
    @capture_exceptions(SimulationError)
    def simulate(self, url: str, persona: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate user interactions with a website based on persona.
        
        Args:
            url: The website URL to simulate
            persona: The persona to use for simulation
            
        Returns:
            Simulation results in the old format
        """
        try:
            # Clean URL
            url = self._clean_url(url)
            
            if self.use_legacy:
                # Use the legacy simulator
                result = self.legacy_simulator.simulate(url, persona)
                self.results.append(result)
                return result
            else:
                # Use the new job-centric approach
                return self._simulate_with_jobs(url, persona)
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            # Return a default result with the error
            return self._create_error_result(url, str(e))
    
    def _simulate_with_jobs(self, url: str, persona: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate with the new job-centric approach."""
        # Select a job based on persona goals
        job = self._select_job_for_persona(persona)
        
        # Create a task planner
        planner = TaskPlanner(persona, job)
        execution_plan = planner.create_execution_plan()
        
        # Get browser context from pool
        browser_context, browser_id = self.browser_pool.get_browser_context()
        
        try:
            # Create persona-based browser
            screenshots_dir = self.config.get("app.screenshots_dir", "./screenshots")
            persona_browser = PersonaBasedBrowser(
                browser_context=browser_context,
                persona=persona,
                screenshots_dir=screenshots_dir
            )
            
            # Create and execute task executor
            executor = TaskExecutor(persona_browser, execution_plan)
            job_results = executor.execute(url)
            
            # Store results
            self.results.append(job_results)
            
            # Convert to old format
            return self._convert_to_old_format(job_results)
        finally:
            # Release browser context back to pool
            self.browser_pool.release_browser_context(browser_context, browser_id)
    
    def _select_job_for_persona(self, persona: Dict[str, Any]) -> Any:
        """Select the most appropriate job for a persona."""
        # Default job
        default_job_id = self.config.get("simulation.jobs.default_job", "product_discovery")
        
        # Try to find a more specific job based on persona goals
        goals = persona.get("goals", {})
        primary_goal = goals.get("primary", "").lower() if goals else ""
        
        # Map goals to job IDs
        goal_to_job = {
            "find a specific product": "product_discovery",
            "browse for deals": "product_discovery",
            "research options": "research_comparison",
            "make a purchase": "purchase_completion",
            "check prices": "price_check",
            "compare prices": "research_comparison",
            "create an account": "account_management",
            "check order status": "account_management",
            "find contact information": "account_management"
        }
        
        # Find the best matching goal
        best_job_id = default_job_id
        best_match_score = 0
        
        for goal_text, job_id in goal_to_job.items():
            # Simple text matching score (can be improved with semantic matching)
            if goal_text in primary_goal:
                score = len(goal_text)
                if score > best_match_score:
                    best_match_score = score
                    best_job_id = job_id
        
        # Get the job definition
        job = self.job_registry.get_job(best_job_id)
        if not job:
            # Fallback to default
            job = self.job_registry.get_job(default_job_id)
            if not job:
                # Last resort fallback
                jobs = self.job_registry.get_all_jobs()
                if jobs:
                    job = jobs[0]
                else:
                    raise ValueError("No job definitions available")
        
        return job
    
    def _convert_to_old_format(self, job_results: JobExecutionResults) -> Dict[str, Any]:
        """Convert job execution results to the old simulator result format."""
        # Extract metrics from task results
        load_times = {}
        successful_actions = []
        failed_actions = []
        
        for task in job_results.task_results:
            # Track successful/failed actions
            action_name = f"{task.task_id}: {task.metrics.get('description', '')}"
            if task.success:
                successful_actions.append(action_name)
            else:
                failed_actions.append(f"{action_name} - {task.error_message}")
            
            # Track load times
            if "load_time" in task.metrics:
                load_times[task.task_id] = task.metrics["load_time"]
        
        # Construct the old format result
        return {
            "website_url": job_results.website_url,
            "navigation_score": job_results.navigation_score,
            "design_score": job_results.design_score,
            "findability_score": job_results.findability_score,
            "load_times": load_times,
            "issues": job_results.issues,
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "accessibility_issues": job_results.accessibility_issues,
            "behavioral_data": job_results.behavioral_data,
            "interaction_data": {
                # Keep these fields for compatibility
                "tech_proficiency": job_results.persona.get('technical', {}).get('proficiency', 5),
                "primary_device": self._get_primary_device(job_results.persona)
            }
        }
    
    def _create_error_result(self, url: str, error_message: str) -> Dict[str, Any]:
        """Create a default result for simulation errors."""
        return {
            "website_url": url,
            "navigation_score": 0,
            "design_score": 0,
            "findability_score": 0,
            "load_times": {"initial_load_failed": 0},
            "issues": [f"Simulation error: {error_message}"],
            "successful_actions": [],
            "failed_actions": ["Simulation failed"],
            "accessibility_issues": [],
            "behavioral_data": {},
            "interaction_data": {
                "error": error_message,
                "tech_proficiency": 5,
                "primary_device": "desktop"
            }
        }
    
    def _get_primary_device(self, persona: Dict[str, Any]) -> str:
        """Determine the primary device from persona."""
        devices = persona.get('technical', {}).get('devices', {})
        if devices:
            # Find the device with highest percentage
            return max(devices.items(), key=lambda x: x[1])[0] if devices else 'desktop'
        return 'desktop'
    
    def _clean_url(self, url: str) -> str:
        """Clean and normalize a URL."""
        # Ensure URL has scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Remove trailing slash
        url = re.sub(r'/$', '', url)
        
        return url
    
    def shutdown(self):
        """Release resources."""
        # Do not shut down the browser pool here as it's shared
        pass 