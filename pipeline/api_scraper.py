"""
API-based grade scraper that replaces Selenium scraping with Schoology API calls
Maintains the same interface as GradeScraper for drop-in compatibility
"""
import logging
from typing import Dict, Any, Optional
from api.fetch_grades import APIGradeFetcher


class APIGradeScraper:
    """
    API-based scraper that fetches grade data from Schoology API
    Drop-in replacement for GradeScraper with matching interface
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fetcher = APIGradeFetcher()
        self._initialized = False

    def __enter__(self):
        """Context manager entry - mimics GradeScraper interface"""
        self._initialized = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - mimics GradeScraper interface"""
        self.cleanup()

    def initialize_driver(self) -> bool:
        """
        Initialize API client (mimics GradeScraper.initialize_driver)

        Returns:
            bool: True if initialization successful
        """
        try:
            # Test API connection by fetching user ID
            user_id = self.fetcher.client.get_user_id()
            self.logger.info(f"API client initialized successfully for user: {user_id}")
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize API client: {e}")
            return False

    def full_scrape_session(self, download_path: str = '.') -> Optional[Dict[str, Any]]:
        """
        Fetch all grade data from API (mimics GradeScraper.full_scrape_session)

        Args:
            download_path: Unused, kept for interface compatibility

        Returns:
            Dict containing all grade data in scraper-compatible format
        """
        try:
            self.logger.info("Starting API grade fetch...")
            grade_data = self.fetcher.fetch_all_grades()

            if grade_data:
                # Log summary
                total_courses = len(grade_data)
                total_assignments = sum(
                    len(cat['assignments'])
                    for course in grade_data.values()
                    for period in course.get('periods', {}).values()
                    for cat in period.get('categories', {}).values()
                )
                self.logger.info(f"API fetch completed: {total_courses} courses, {total_assignments} assignments")
                return grade_data
            else:
                self.logger.warning("API fetch returned no data")
                return None

        except Exception as e:
            self.logger.error(f"API fetch failed: {e}", exc_info=True)
            return None

    def cleanup(self):
        """Cleanup resources (mimics GradeScraper.cleanup)"""
        self._initialized = False
        self.logger.debug("API scraper cleanup completed")
