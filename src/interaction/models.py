"""
Data models for the job-centric simulation system.

This module contains dataclasses and models used throughout the
simulation system to avoid circular dependencies.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


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