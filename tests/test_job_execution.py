"""
Tests for the job execution components.
"""

import pytest
from src.interaction.job_executor import TaskPlanner
from src.interaction.persona_browser import PersonaBasedBrowser
from src.interaction.task_executor import TaskExecutor


def test_task_planner(job_registry, sample_persona):
    """Test that the task planner can create an execution plan."""
    # Get a job
    job = job_registry.get_job("product_discovery")
    assert job is not None, "Job registry should provide a product_discovery job"
    
    # Create a task planner
    planner = TaskPlanner(sample_persona, job)
    
    # Create execution plan
    plan = planner.create_execution_plan()
    
    # Verify plan properties
    assert plan.job_id == job.job_id
    assert plan.job_name == job.name
    assert plan.persona == sample_persona
    assert len(plan.tasks) > 0, "Execution plan should include tasks"
    
    # Verify that required tasks are included
    required_tasks = [task.task_id for task in job.tasks if task.required]
    plan_tasks = [task.task_id for task in plan.tasks]
    
    for task_id in required_tasks:
        assert task_id in plan_tasks, f"Required task {task_id} should be in the plan"


def test_persona_browser_initialization(browser_context, sample_persona):
    """Test that the persona-based browser initializes correctly."""
    browser = PersonaBasedBrowser(
        browser_context=browser_context,
        persona=sample_persona,
        screenshots_dir="./tests/screenshots"
    )
    
    # Check that the browser attributes are set correctly
    assert browser.tech_proficiency == sample_persona["technical"]["proficiency"]
    assert browser.patience_level == sample_persona["e_commerce_specific"]["patience_level"]
    assert browser.page is not None, "Page should be initialized"


@pytest.mark.parametrize("url", [
    "https://example.com"  # Use a simple, reliable website for testing
])
def test_persona_browser_navigation(browser_context, sample_persona, url):
    """Test that the persona-based browser can navigate to a URL."""
    browser = PersonaBasedBrowser(
        browser_context=browser_context,
        persona=sample_persona,
        screenshots_dir="./tests/screenshots"
    )
    
    # Navigate to URL
    result = browser.navigate(url)
    
    # Check navigation result
    assert result["success"], f"Navigation to {url} should succeed"
    assert "load_time" in result, "Navigation result should include load time"
    assert "screenshot" in result, "Navigation result should include screenshot path"


@pytest.mark.parametrize("job_id", [
    "product_discovery"
])
def test_task_executor_execution(browser_context, job_registry, sample_persona, job_id):
    """Test that the task executor can execute a simple job."""
    # Get a job
    job = job_registry.get_job(job_id)
    
    # Create a task planner
    planner = TaskPlanner(sample_persona, job)
    execution_plan = planner.create_execution_plan()
    
    # Create persona-based browser
    browser = PersonaBasedBrowser(
        browser_context=browser_context,
        persona=sample_persona,
        screenshots_dir="./tests/screenshots"
    )
    
    # Create and execute task executor
    executor = TaskExecutor(browser, execution_plan)
    
    # Execute on a simple site
    results = executor.execute("https://example.com")
    
    # Check results
    assert results.job_id == job_id
    assert results.job_name == job.name
    assert results.website_url == "https://example.com"
    assert len(results.task_results) > 0, "Should have task results"
    assert results.end_time > results.start_time, "End time should be after start time"
    
    # Verify that we have scores
    assert 0 <= results.navigation_score <= 10
    assert 0 <= results.design_score <= 10
    assert 0 <= results.findability_score <= 10
    assert 0 <= results.overall_score <= 10 