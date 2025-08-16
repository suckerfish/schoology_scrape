import logging
from typing import Dict, Any, Optional
from driver_standard import SchoologyDriver
from shared.config import get_config
from .error_handling import retry_with_backoff, handle_scraping_error, CircuitBreaker, RetryStrategy

class GradeScraper:
    """Handles pure data extraction from Schoology"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        self.driver: Optional[SchoologyDriver] = None
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=300)
    
    @retry_with_backoff(max_retries=2, strategy=RetryStrategy.FIXED, base_delay=2.0)
    def initialize_driver(self, download_path: str = '.') -> bool:
        """
        Initialize the Schoology driver
        
        Args:
            download_path: Path for downloads
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.driver = SchoologyDriver(download_path)
            self.logger.info("Schoology driver initialized successfully")
            return True
        except Exception as e:
            handle_scraping_error(e, {"operation": "initialize_driver", "download_path": download_path})
            return False
    
    @retry_with_backoff(max_retries=3, strategy=RetryStrategy.EXPONENTIAL, base_delay=5.0)
    def login(self) -> bool:
        """
        Login to Schoology using configured credentials
        
        Returns:
            bool: True if login successful, False otherwise
        """
        if not self.driver:
            handle_scraping_error(Exception("Driver not initialized"), {"operation": "login"})
            return False
        
        try:
            def _login():
                url = self.config.schoology.base_url
                email = self.config.schoology.google_email
                password = self.config.schoology.google_password
                
                self.logger.info("Attempting to login to Schoology")
                self.driver.login(url, email, password)
                self.logger.info("Login successful")
                return True
            
            return self.circuit_breaker.call(_login)
            
        except Exception as e:
            handle_scraping_error(e, {"operation": "login", "url": self.config.schoology.base_url})
            return False
    
    @retry_with_backoff(max_retries=2, strategy=RetryStrategy.LINEAR, base_delay=10.0)
    def scrape_grades(self) -> Optional[Dict[str, Any]]:
        """
        Scrape all courses data from Schoology
        
        Returns:
            Dict containing all courses data, or None if failed
        """
        if not self.driver:
            handle_scraping_error(Exception("Driver not initialized"), {"operation": "scrape_grades"})
            return None
        
        try:
            def _scrape():
                self.logger.info("Starting grade scraping")
                email = self.config.schoology.google_email
                all_courses_data = self.driver.get_all_courses_data(email=email)
                
                if all_courses_data:
                    self.logger.info("Grade scraping completed successfully")
                    return all_courses_data
                else:
                    raise Exception("No course data retrieved from driver")
            
            return self.circuit_breaker.call(_scrape)
                
        except Exception as e:
            handle_scraping_error(e, {"operation": "scrape_grades", "email": self.config.schoology.google_email})
            return None
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.close()
                self.logger.info("Driver closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
    
    def full_scrape_session(self, download_path: str = '.') -> Optional[Dict[str, Any]]:
        """
        Complete scraping session: initialize, login, scrape, cleanup
        
        Args:
            download_path: Path for downloads
            
        Returns:
            Dict containing all courses data, or None if failed
        """
        try:
            # Initialize driver
            if not self.initialize_driver(download_path):
                return None
            
            # Login
            if not self.login():
                return None
            
            # Scrape grades
            data = self.scrape_grades()
            
            return data
            
        except Exception as e:
            self.logger.error(f"Full scrape session failed: {e}")
            return None
        finally:
            self.cleanup()