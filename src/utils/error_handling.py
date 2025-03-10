"""
Error Handling Utilities for the E-Commerce Website Evaluator.

This module provides standardized error handling functions and classes
to ensure consistent error management throughout the application.
"""

import logging
import traceback
import sys
import json
from typing import Dict, Any, Optional, Callable, TypeVar, List
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('evaluation_errors.log')
    ]
)

logger = logging.getLogger(__name__)

# Type variable for generic function
T = TypeVar('T')


class EvaluationError(Exception):
    """Base exception class for all evaluation-related errors."""
    
    def __init__(self, message: str, error_code: str = "GENERAL_ERROR", 
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize an evaluation error.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details and context
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary representation."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }
    
    def log(self, level: int = logging.ERROR):
        """Log the error with appropriate level."""
        log_message = f"{self.error_code}: {self.message}"
        if self.details:
            log_message += f" - Details: {json.dumps(self.details)}"
        logger.log(level, log_message)


class ConfigurationError(EvaluationError):
    """Error related to application configuration."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)


class APIError(EvaluationError):
    """Error related to external API calls."""
    
    def __init__(self, message: str, api_name: str, status_code: Optional[int] = None, 
                 response: Optional[str] = None):
        details = {
            "api_name": api_name,
            "status_code": status_code,
            "response": response
        }
        super().__init__(message, "API_ERROR", details)


class SimulationError(EvaluationError):
    """Error during website simulation."""
    
    def __init__(self, message: str, website_url: str, 
                 browser_info: Optional[Dict[str, Any]] = None,
                 task_id: Optional[str] = None):
        details = {
            "website_url": website_url,
            "browser_info": browser_info or {},
            "task_id": task_id
        }
        super().__init__(message, "SIMULATION_ERROR", details)


class ValidationError(EvaluationError):
    """Error during input validation."""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, constraints: Optional[Dict[str, Any]] = None):
        details = {
            "field": field,
            "value": str(value) if value is not None else None,
            "constraints": constraints or {}
        }
        super().__init__(message, "VALIDATION_ERROR", details)


class AnalysisError(EvaluationError):
    """Error during data analysis."""
    
    def __init__(self, message: str, analysis_type: str, 
                 data_info: Optional[Dict[str, Any]] = None):
        details = {
            "analysis_type": analysis_type,
            "data_info": data_info or {}
        }
        super().__init__(message, "ANALYSIS_ERROR", details)


class ResourceExhaustionError(EvaluationError):
    """Error when system resources are exhausted."""
    
    def __init__(self, message: str, resource_type: str, 
                 current_usage: Optional[Any] = None, limit: Optional[Any] = None):
        details = {
            "resource_type": resource_type,
            "current_usage": current_usage,
            "limit": limit
        }
        super().__init__(message, "RESOURCE_EXHAUSTION", details)


def capture_exceptions(error_type: type = EvaluationError, default_return: Any = None) -> Callable:
    """
    Decorator to capture exceptions and convert them to standardized error types.
    
    Args:
        error_type: Type of error to wrap exceptions in
        default_return: Default value to return on error
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except EvaluationError as e:
                # Already a standard error, just log it
                e.log()
                return default_return
            except Exception as e:
                # Convert to standard error
                error = error_type(
                    message=str(e),
                    details={"traceback": traceback.format_exc()}
                )
                error.log()
                return default_return
        return wrapper
    return decorator


def validate_inputs(validation_func: Callable[[Dict[str, Any]], List[str]]) -> Callable:
    """
    Decorator to validate function inputs.
    
    Args:
        validation_func: Function that takes kwargs dict and returns list of error messages
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Validate inputs
            errors = validation_func(kwargs)
            if errors:
                raise ValidationError(
                    message="; ".join(errors),
                    field="input_parameters",
                    value=kwargs,
                    constraints={"errors": errors}
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def with_retry(max_attempts: int = 3, retry_exceptions: tuple = (Exception,), 
               backoff_factor: float = 1.5) -> Callable:
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        retry_exceptions: Exceptions to retry on
        backoff_factor: Factor to multiply delay by after each failure
        
    Returns:
        Decorated function
    """
    import time
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            last_exception = None
            delay = 1.0  # Initial delay in seconds
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}. "
                            f"Retrying in {delay:.1f}s. Error: {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}. "
                            f"Last error: {e}"
                        )
            
            # All attempts failed
            if isinstance(last_exception, EvaluationError):
                raise last_exception
            else:
                # Convert to standard error
                raise EvaluationError(
                    message=f"Failed after {max_attempts} attempts: {str(last_exception)}",
                    error_code="RETRY_EXHAUSTED",
                    details={"function": func.__name__, "last_error": str(last_exception)}
                )
        
        return wrapper
    
    return decorator


def log_execution_time(logger_instance=None, level=logging.DEBUG) -> Callable:
    """
    Decorator to log the execution time of a function.
    
    Args:
        logger_instance: Logger to use (defaults to module logger)
        level: Logging level to use
        
    Returns:
        Decorated function
    """
    import time
    log = logger_instance or logger
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            log.log(level, f"{func.__name__} executed in {execution_time:.2f} seconds")
            return result
        return wrapper
    return decorator


def format_error_response(error: Exception) -> Dict[str, Any]:
    """
    Format an exception for API response.
    
    Args:
        error: The exception to format
        
    Returns:
        Formatted error response
    """
    if isinstance(error, EvaluationError):
        return {
            "success": False,
            "error": error.to_dict()
        }
    else:
        # Convert to standard format
        return {
            "success": False,
            "error": {
                "error_code": "UNHANDLED_ERROR",
                "message": str(error),
                "details": {
                    "type": error.__class__.__name__,
                    "traceback": traceback.format_exc()
                }
            }
        }


# Global error handler for unhandled exceptions
def setup_global_exception_handler():
    """Set up a global exception handler to catch unhandled exceptions."""
    def global_exception_handler(exctype, value, tb):
        # Log the exception
        logger.critical(
            f"Unhandled {exctype.__name__}: {value}\n"
            f"{''.join(traceback.format_tb(tb))}"
        )
        # Call the default exception handler
        sys.__excepthook__(exctype, value, tb)
    
    # Set the exception handler
    sys.excepthook = global_exception_handler 