import logging
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .api_scraper import APIGradeScraper
from .comparator import GradeComparator
from .notifier import GradeNotifier
from shared.config import get_config
from shared.diff_logger import DiffLogger

class GradePipeline:
    """Main pipeline orchestrator that coordinates scraping, comparison, storage, and notifications"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        
        # Initialize pipeline components
        self.scraper = APIGradeScraper()
        self.comparator = GradeComparator()
        self.notifier = GradeNotifier()
        self.diff_logger = DiffLogger(self.config)
        
        # Ensure data directory exists
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
    
    def run_full_pipeline(self, download_path: str = '.') -> bool:
        """
        Execute the complete grade monitoring pipeline
        
        Args:
            download_path: Path for driver downloads
            
        Returns:
            bool: True if pipeline completed successfully
        """
        pipeline_start_time = datetime.datetime.now()
        self.logger.info("Starting grade monitoring pipeline")
        
        try:
            # Step 1: Fetch grades via API
            self.logger.info("Step 1: Fetching grades from Schoology API")
            grade_data = self._scrape_grades(download_path)
            if not grade_data:
                self._handle_scraping_failure()
                return False
            
            # Step 2: Detect changes
            self.logger.info("Step 2: Detecting changes")
            changes = self._detect_changes(grade_data)
            
            # Step 3: Save data (conditionally based on changes)
            save_success = self._save_grade_data_conditional(grade_data, changes)
            if not save_success:
                self.logger.warning("Failed to save grade data, but continuing pipeline")
            
            # Step 4: Send combined status and change notifications
            pipeline_duration = datetime.datetime.now() - pipeline_start_time
            self.logger.info(f"Pipeline completed successfully in {pipeline_duration}")

            if changes:
                self.logger.info("Step 4: Sending combined notification with changes and status")
                notification_success = self._send_combined_notification(changes, pipeline_duration)
                if not notification_success:
                    self.logger.warning("Failed to send combined notification")
            else:
                self.logger.info("Step 4: Sending status notification - no changes detected")
                status_message = f"Grade monitoring completed successfully. No changes detected. Duration: {pipeline_duration}"
                self.notifier.send_status_notification(status_message, success=True)

            # Clean up old log files and snapshots periodically
            try:
                self.diff_logger.cleanup_old_logs()
            except Exception as cleanup_error:
                self.logger.warning(f"Failed to clean up old logs: {cleanup_error}")

            try:
                self._cleanup_old_snapshots()
            except Exception as cleanup_error:
                self.logger.warning(f"Failed to clean up old snapshots: {cleanup_error}")

            return True
            
        except Exception as e:
            pipeline_duration = datetime.datetime.now() - pipeline_start_time
            self.logger.error(f"Pipeline failed after {pipeline_duration}: {e}")
            
            # Send error notification
            self.notifier.send_error_notification(
                "Grade monitoring pipeline failed",
                f"Error: {str(e)}\nDuration: {pipeline_duration}"
            )
            
            return False
    
    def _scrape_grades(self, download_path: str) -> Optional[Dict[str, Any]]:
        """Fetch grades via API with error handling and retries"""
        max_retries = self.config.app.max_retries if hasattr(self.config.app, 'max_retries') else 3

        for attempt in range(max_retries):
            try:
                self.logger.info(f"API fetch attempt {attempt + 1}/{max_retries}")

                with self.scraper as scraper:
                    grade_data = scraper.full_scrape_session(download_path)

                if grade_data:
                    self.logger.info("API fetch successful")
                    return grade_data
                else:
                    self.logger.warning(f"API fetch attempt {attempt + 1} returned no data")

            except Exception as e:
                self.logger.error(f"API fetch attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    self.logger.info("Retrying API fetch...")
                    # Optional: add delay between retries
                    import time
                    time.sleep(5)

        self.logger.error("All API fetch attempts failed")
        return None
    
    def _detect_changes(self, grade_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect changes using file-based comparison"""
        try:
            # Use file-based comparison (grade changes only)
            self.logger.info("Using file-based change detection (grade changes only)")
            changes = self.comparator.detect_changes_from_file(grade_data, grade_changes_only=True)
            return changes

        except Exception as e:
            self.logger.error(f"Error in file-based change detection: {e}")

            # If comparison fails, treat as initial data
            self.logger.warning("Treating data as initial due to comparison failure")
            return {
                'type': 'initial',
                'message': 'Data saved (comparison failed)',
                'data': grade_data
            }
    
    def _save_grade_data(self, grade_data: Dict[str, Any]) -> bool:
        """Save grade data to local file"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            local_file = self.data_dir / f'all_courses_data_{timestamp}.json'

            with open(local_file, 'w') as f:
                json.dump(grade_data, f, indent=2)

            self.logger.info(f"Grade data saved to local file: {local_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save grade data to local file: {e}")
            return False
    
    def _save_grade_data_conditional(self, grade_data: Dict[str, Any], changes: Optional[Dict[str, Any]]) -> bool:
        """
        Save grade data conditionally based on change detection results and configuration
        
        Args:
            grade_data: The scraped grade data to save
            changes: Change detection results (None if no changes, dict if changes/initial)
            
        Returns:
            bool: True if save operation succeeded or was skipped appropriately
        """
        # Check configuration settings
        should_save_conditionally = self.config.storage.conditional_save
        force_save_on_error = self.config.storage.force_save_on_error
        
        # Determine whether to save based on changes and configuration
        should_save = False
        reason = ""
        
        if not should_save_conditionally:
            # Configuration disables conditional saving - always save
            should_save = True
            reason = "conditional saving disabled in configuration"
        elif changes is None:
            # No changes detected
            should_save = False
            reason = "no changes detected in grade data"
        elif changes.get('type') == 'initial':
            # Initial data capture (no previous data to compare)
            should_save = True
            reason = "initial grade data capture"
        elif changes.get('type') == 'update':
            # Changes detected
            should_save = True
            reason = f"changes detected: {changes.get('summary', 'unknown changes')}"
        else:
            # Unknown change type or change detection failed
            if force_save_on_error:
                should_save = True
                reason = "change detection returned unexpected result, saving as fail-safe"
            else:
                should_save = False
                reason = "change detection failed and fail-safe disabled"
        
        # Log the decision
        if should_save:
            self.logger.info(f"Step 3: Saving grade data - {reason}")
            return self._save_grade_data(grade_data)
        else:
            self.logger.info(f"Step 3: Skipping save - {reason}")
            return True  # Return True since skipping is the correct behavior
    
    def _send_notifications(self, changes: Dict[str, Any]) -> bool:
        """Send notifications about changes"""
        try:
            # Format changes for notification
            formatted_message = self.comparator.format_changes_for_notification(changes)

            # Send notification
            notification_success, notification_results = self.notifier.send_grade_change_notification(changes, formatted_message)

            # Log structured change information
            self.diff_logger.log_grade_changes(
                changes=changes,
                formatted_message=formatted_message,
                notification_results=notification_results,
                comparison_files=changes.get('comparison_files', [])
            )

            if notification_success:
                self.logger.info("Notifications sent successfully")
            else:
                self.logger.warning("Failed to send notifications")

            return notification_success

        except Exception as e:
            self.logger.error(f"Error sending notifications: {e}")
            return False

    def _send_combined_notification(self, changes: Dict[str, Any], pipeline_duration) -> bool:
        """
        Send combined notification including both changes and status information

        Args:
            changes: Dictionary containing grade change information
            pipeline_duration: How long the pipeline took to run

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Format the grade changes
            formatted_message = self.comparator.format_changes_for_notification(changes)

            # Create enhanced status message that includes changes
            status_info = f"Grade monitoring completed successfully. Duration: {pipeline_duration}"
            combined_message = f"{formatted_message}\n\n--- Status ---\n{status_info}"

            # Send combined notification with changes + status
            notification_success, notification_results = self.notifier.send_grade_change_notification(changes, combined_message)

            # Log structured change information
            self.diff_logger.log_grade_changes(
                changes=changes,
                formatted_message=combined_message,
                notification_results=notification_results,
                comparison_files=changes.get('comparison_files', [])
            )

            if notification_success:
                self.logger.info("Combined notification sent successfully")
            else:
                self.logger.warning("Failed to send combined notification")

            return notification_success

        except Exception as e:
            self.logger.error(f"Error sending combined notification: {e}")
            return False
    
    def _handle_scraping_failure(self):
        """Handle API fetch failure with appropriate notifications"""
        error_message = "Failed to fetch grade data from Schoology API"
        self.logger.error(error_message)

        # Send error notification
        self.notifier.send_error_notification(
            error_message,
            "All API fetch attempts failed. Please check API credentials and network connectivity."
        )

    def _cleanup_old_snapshots(self, keep_count: int = 30):
        """
        Clean up old JSON snapshots, keeping only the most recent ones

        Args:
            keep_count: Number of recent snapshots to keep (default: 30)
        """
        try:
            # Get all snapshot files sorted by modification time (newest first)
            snapshot_files = sorted(
                self.data_dir.glob('all_courses_data_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            if len(snapshot_files) <= keep_count:
                self.logger.debug(f"Found {len(snapshot_files)} snapshots, no cleanup needed (keeping {keep_count})")
                return

            # Delete old snapshots beyond the keep count
            files_to_delete = snapshot_files[keep_count:]
            deleted_count = 0

            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.debug(f"Deleted old snapshot: {file_path.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete snapshot {file_path.name}: {e}")

            self.logger.info(f"Cleaned up {deleted_count} old snapshots (kept {keep_count} most recent)")

        except Exception as e:
            self.logger.error(f"Error during snapshot cleanup: {e}")
