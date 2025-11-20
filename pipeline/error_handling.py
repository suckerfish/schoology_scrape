import logging
import time
import functools
from typing import Callable, Any, Optional
from enum import Enum

class RetryStrategy(Enum):
    """Retry strategy types"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"

class PipelineError(Exception):
    """Base exception for pipeline errors"""
    pass

class ScrapingError(PipelineError):
    """Scraping-specific errors"""
    pass

class ComparisonError(PipelineError):
    """Change detection errors"""
    pass

class NotificationError(PipelineError):
    """Notification delivery errors"""
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