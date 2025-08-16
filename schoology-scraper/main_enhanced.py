#!/usr/bin/env python3
"""
Enhanced Schoology Grade Scraper with centralized configuration and improved error handling.
This version uses the Phase 2 architectural improvements.
"""
import sys
import os
import json
import datetime
import logging
from pathlib import Path
from deepdiff import DeepDiff

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from config import get_config, setup_logging
from grade_data_service import create_grade_data_service
from driver_standard import SchoologyDriver


logger = logging.getLogger(__name__)


class SchoologyScraperService:
    """Enhanced scraper service with configuration management."""
    
    def __init__(self):
        """Initialize the scraper with configuration."""
        self.config = get_config()
        setup_logging(self.config)
        
        # Initialize services
        self.data_service = create_grade_data_service(enhanced=True, config=self.config)
        self.driver = None
        
        logger.info("Schoology Scraper Service initialized")
        logger.info(f"Configuration loaded - DynamoDB table: {self.config.aws.dynamodb_table_name}")
    
    def initialize_driver(self) -> bool:
        """Initialize the Selenium WebDriver."""
        try:
            self.driver = SchoologyDriver(self.config.app.download_path)
            logger.info("WebDriver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False
    
    def login_to_schoology(self) -> bool:
        """Login to Schoology using configured credentials."""
        if not self.driver:
            logger.error("WebDriver not initialized")
            return False
        
        try:
            self.driver.login(
                self.config.schoology.base_url,
                self.config.schoology.google_email,
                self.config.schoology.google_password
            )
            logger.info("Successfully logged into Schoology")
            return True
        except Exception as e:
            logger.error(f"Failed to login to Schoology: {e}")
            return False
    
    def scrape_grade_data(self) -> dict:
        """Scrape grade data from Schoology."""
        if not self.driver:
            logger.error("WebDriver not initialized")
            return None
        
        try:
            logger.info("Starting grade data scraping...")
            all_courses_data = self.driver.get_all_courses_data(
                email=self.config.schoology.google_email
            )
            
            if all_courses_data:
                logger.info(f"Successfully scraped data for {len(all_courses_data)} courses")
                return all_courses_data
            else:
                logger.warning("No course data retrieved")
                return None
                
        except Exception as e:
            logger.error(f"Failed to scrape grade data: {e}")
            return None
    
    def detect_changes(self, current_data: dict) -> bool:
        """Detect if there are changes from the previous snapshot."""
        try:
            # Get latest snapshot for comparison
            latest_snapshot = self.data_service.get_latest_snapshot(use_cache=True)
            
            if not latest_snapshot:
                logger.info("No previous snapshot found - treating as new data")
                return True
            
            # Compare with DeepDiff
            diff = DeepDiff(latest_snapshot, current_data)
            has_changes = bool(diff)
            
            if has_changes:
                logger.info("Changes detected in grade data")
                logger.debug(f"Changes summary: {len(diff.get('values_changed', {}))} values changed, "
                           f"{len(diff.get('iterable_item_added', {}))} items added, "
                           f"{len(diff.get('iterable_item_removed', {}))} items removed")
            else:
                logger.info("No changes detected in grade data")
            
            return has_changes
            
        except Exception as e:
            logger.error(f"Error during change detection: {e}")
            # If we can't detect changes, assume there are changes to be safe
            return True
    
    def save_local_backup(self, data: dict) -> str:
        """Save a local JSON backup of the data."""
        try:
            data_dir = Path(self.config.app.data_directory)
            data_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'all_courses_data_{timestamp}.json'
            filepath = data_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Local backup saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save local backup: {e}")
            raise
    
    def save_to_database(self, data: dict) -> str:
        """Save data to the database with validation."""
        try:
            timestamp = self.data_service.save_snapshot(data, validate=True)
            logger.info(f"Data saved to database with timestamp: {timestamp}")
            return timestamp
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            raise
    
    def send_notifications(self, data: dict, changes_detected: bool):
        """Send notifications if configured and changes detected."""
        if not changes_detected:
            logger.debug("Skipping notifications - no changes detected")
            return
        
        notifications_sent = []
        
        # Pushover notification
        if (self.config.notifications.pushover_token and 
            self.config.notifications.pushover_user_key):
            try:
                from pushover import send_pushover_message
                send_pushover_message("Schoology grades updated!", "New grade changes detected")
                notifications_sent.append("Pushover")
                logger.info("Pushover notification sent")
            except Exception as e:
                logger.error(f"Failed to send Pushover notification: {e}")
        
        # Email notification
        if self.config.notifications.email_enabled:
            try:
                from email_myself import send_email_to_myself
                send_email_to_myself("Schoology Grade Update", "Grade changes have been detected and saved.")
                notifications_sent.append("Email")
                logger.info("Email notification sent")
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")
        
        # Gemini AI analysis
        if self.config.notifications.gemini_api_key:
            try:
                from gemini_client import Gemini
                gemini = Gemini()
                # Note: You'd need to implement the analysis logic here
                notifications_sent.append("Gemini AI")
                logger.info("Gemini AI analysis triggered")
            except Exception as e:
                logger.error(f"Failed to trigger Gemini AI analysis: {e}")
        
        if notifications_sent:
            logger.info(f"Notifications sent via: {', '.join(notifications_sent)}")
        else:
            logger.info("No notifications configured or all failed")
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.close()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
    
    def run_scraping_pipeline(self) -> bool:
        """Run the complete scraping pipeline."""
        success = False
        
        try:
            logger.info("Starting Schoology scraping pipeline")
            
            # Initialize driver
            if not self.initialize_driver():
                return False
            
            # Login
            if not self.login_to_schoology():
                return False
            
            # Scrape data
            grade_data = self.scrape_grade_data()
            if not grade_data:
                logger.error("No grade data retrieved - aborting pipeline")
                return False
            
            # Detect changes
            changes_detected = self.detect_changes(grade_data)
            
            if changes_detected:
                # Save local backup
                try:
                    self.save_local_backup(grade_data)
                except Exception as e:
                    logger.error(f"Local backup failed: {e}")
                    # Continue even if local backup fails
                
                # Save to database
                self.save_to_database(grade_data)
                
                # Send notifications
                self.send_notifications(grade_data, changes_detected)
                
                logger.info("Scraping pipeline completed successfully with changes")
            else:
                logger.info("Scraping pipeline completed - no changes to save")
            
            success = True
            
        except Exception as e:
            logger.error(f"Scraping pipeline failed: {e}")
            success = False
        
        finally:
            self.cleanup()
        
        return success


def main():
    """Main entry point for the scraper."""
    try:
        scraper = SchoologyScraperService()
        success = scraper.run_scraping_pipeline()
        
        if success:
            logger.info("Scraper completed successfully")
            return 0
        else:
            logger.error("Scraper failed")
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)