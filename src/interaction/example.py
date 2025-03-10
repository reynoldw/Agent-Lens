"""
Example script demonstrating how to use the job-centric simulation system.
"""

from playwright.sync_api import sync_playwright
from src.interaction.job_definitions import JobRegistry
from src.interaction.persona_browser import PersonaBasedBrowser
from src.interaction.task_executor import TaskExecutor
from src.interaction.job_executor import TaskPlanner
from src.persona.generator import PersonaGenerator


def run_simulation(website_url: str):
    """Run a complete website simulation using the job-centric system."""
    
    # Create a persona
    persona_generator = PersonaGenerator()
    persona = persona_generator.generate()
    
    # Get available jobs
    job_registry = JobRegistry()
    available_jobs = job_registry.get_jobs_for_persona(persona.get("shopping_behavior", {}).get("type", "all"))
    
    # For this example, let's use the product discovery job
    job = job_registry.get_job("product_discovery")
    
    # Create a task planner and generate execution plan
    planner = TaskPlanner(persona, job)
    execution_plan = planner.create_execution_plan()
    
    # Set up browser automation
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        
        try:
            # Create persona-based browser
            persona_browser = PersonaBasedBrowser(
                browser_context=browser.new_context(),
                persona=persona,
                screenshots_dir="screenshots"
            )
            
            # Create task executor
            executor = TaskExecutor(persona_browser, execution_plan)
            
            # Execute the job
            results = executor.execute(website_url)
            
            # Print results
            print(f"\nSimulation Results for {website_url}")
            print(f"Overall Score: {results.overall_score:.2f}/10")
            print(f"Navigation Score: {results.navigation_score:.2f}/10")
            print(f"Design Score: {results.design_score:.2f}/10")
            print(f"Findability Score: {results.findability_score:.2f}/10")
            print(f"\nSuccessful Tasks: {len(results.successful_tasks)}")
            print(f"Failed Tasks: {len(results.failed_tasks)}")
            print(f"\nIssues Found:")
            for issue in results.issues:
                print(f"- {issue}")
            print(f"\nAccessibility Issues:")
            for issue in results.accessibility_issues:
                print(f"- {issue}")
            
            return results
            
        finally:
            browser.close()


if __name__ == "__main__":
    # Example usage with real websites
    # Using well-known e-commerce sites that can handle automated testing
    websites = [
        "https://www.amazon.com",
        "https://www.ebay.com",
        "https://www.etsy.com"
    ]
    
    # Run simulation on the first website
    # For testing multiple sites, use a loop over the websites list
    results = run_simulation(websites[0]) 