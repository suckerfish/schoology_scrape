import logging
import time
import functools
from typing import Callable, Any, Optional, Union, Dict, List
from enum import Enum

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RetryStrategy(Enum):
    """Retry strategy types"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"

class PipelineError(Exception):
    """Base exception for pipeline errors"""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 component: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.severity = severity
        self.component = component
        self.details = details or {}
        self.timestamp = time.time()

class ScrapingError(PipelineError):
    """Scraping-specific errors"""
    pass

class ComparisonError(PipelineError):
    """Change detection errors"""
    pass

class NotificationError(PipelineError):
    """Notification delivery errors"""
    pass

class DataServiceError(PipelineError):
    """Data service errors"""
    pass

def retry_with_backoff(
    max_retries: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
):
    """
    Decorator for retry logic with configurable backoff strategies
    
    Args:
        max_retries: Maximum number of retry attempts
        strategy: Retry strategy (fixed, exponential, linear)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exceptions to catch and retry
        logger: Logger instance for retry logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        if logger:
                            logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise e
                    
                    # Calculate delay
                    if strategy == RetryStrategy.FIXED:
                        delay = base_delay
                    elif strategy == RetryStrategy.LINEAR:
                        delay = base_delay * (attempt + 1)
                    else:  # EXPONENTIAL
                        delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    if logger:
                        logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.2f}s")
                    
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator

class ErrorHandler:
    """Centralized error handling for the pipeline"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_history: List[PipelineError] = []
    
    def handle_error(self, error: Exception, component: str, 
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    details: Optional[Dict[str, Any]] = None) -> PipelineError:
        """
        Handle an error with appropriate logging and tracking
        
        Args:
            error: The original exception
            component: Component where error occurred
            severity: Error severity level
            details: Additional error details
            
        Returns:
            PipelineError instance
        """
        # Create pipeline error
        if isinstance(error, PipelineError):
            pipeline_error = error
        else:
            pipeline_error = PipelineError(
                message=str(error),
                severity=severity,
                component=component,
                details=details
            )
        
        # Add to error history
        self.error_history.append(pipeline_error)
        
        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"[{component}] Critical error: {pipeline_error}")
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(f"[{component}] High severity error: {pipeline_error}")
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.error(f"[{component}] Error: {pipeline_error}")
        else:  # LOW
            self.logger.warning(f"[{component}] Low severity error: {pipeline_error}")
        
        return pipeline_error
    
    def should_abort_pipeline(self) -> bool:
        """
        Determine if the pipeline should abort based on error history
        
        Returns:
            bool: True if pipeline should abort
        """
        recent_errors = [e for e in self.error_history if time.time() - e.timestamp < 300]  # Last 5 minutes
        
        # Abort if any critical errors
        if any(e.severity == ErrorSeverity.CRITICAL for e in recent_errors):
            return True
        
        # Abort if too many high severity errors
        high_severity_errors = [e for e in recent_errors if e.severity == ErrorSeverity.HIGH]
        if len(high_severity_errors) >= 3:
            return True
        
        # Abort if too many total errors
        if len(recent_errors) >= 10:
            return True
        
        return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of recent errors
        
        Returns:
            Dictionary containing error summary
        """
        recent_errors = [e for e in self.error_history if time.time() - e.timestamp < 3600]  # Last hour
        
        summary = {
            'total_errors': len(recent_errors),
            'by_severity': {},
            'by_component': {},
            'recent_critical': []
        }
        
        # Count by severity
        for severity in ErrorSeverity:
            count = len([e for e in recent_errors if e.severity == severity])
            summary['by_severity'][severity.value] = count
        
        # Count by component
        for error in recent_errors:
            component = error.component or 'unknown'
            summary['by_component'][component] = summary['by_component'].get(component, 0) + 1
        
        # Recent critical errors
        critical_errors = [e for e in recent_errors if e.severity == ErrorSeverity.CRITICAL]
        summary['recent_critical'] = [
            {
                'message': str(e),
                'component': e.component,
                'timestamp': e.timestamp
            }
            for e in critical_errors[-5:]  # Last 5 critical errors
        ]
        
        return summary
    
    def clear_error_history(self):
        """Clear error history (useful for testing or manual resets)"""
        self.error_history.clear()
        self.logger.info("Error history cleared")

# Create global error handler instance
error_handler = ErrorHandler()

# Convenience functions
def handle_scraping_error(error: Exception, details: Optional[Dict[str, Any]] = None) -> ScrapingError:
    """Handle scraping-specific errors"""
    scraping_error = ScrapingError(
        message=str(error),
        severity=ErrorSeverity.HIGH,
        component="scraper",
        details=details
    )
    error_handler.handle_error(scraping_error, "scraper", ErrorSeverity.HIGH, details)
    return scraping_error

def handle_comparison_error(error: Exception, details: Optional[Dict[str, Any]] = None) -> ComparisonError:
    """Handle comparison-specific errors"""
    comparison_error = ComparisonError(
        message=str(error),
        severity=ErrorSeverity.MEDIUM,
        component="comparator",
        details=details
    )
    error_handler.handle_error(comparison_error, "comparator", ErrorSeverity.MEDIUM, details)
    return comparison_error

def handle_notification_error(error: Exception, details: Optional[Dict[str, Any]] = None) -> NotificationError:
    """Handle notification-specific errors"""
    notification_error = NotificationError(
        message=str(error),
        severity=ErrorSeverity.MEDIUM,
        component="notifier",
        details=details
    )
    error_handler.handle_error(notification_error, "notifier", ErrorSeverity.MEDIUM, details)
    return notification_error

def handle_data_service_error(error: Exception, details: Optional[Dict[str, Any]] = None) -> DataServiceError:
    """Handle data service errors"""
    data_error = DataServiceError(
        message=str(error),
        severity=ErrorSeverity.HIGH,
        component="data_service",
        details=details
    )
    error_handler.handle_error(data_error, "data_service", ErrorSeverity.HIGH, details)
    return data_error

# Circuit breaker pattern
class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker
        
        Args:
            func: Function to call
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.logger.info("Circuit breaker transitioning to CLOSED")
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"Circuit breaker transitioning to OPEN after {self.failure_count} failures")