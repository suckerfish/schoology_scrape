"""
Grade pipeline orchestrator using ID-based change detection.

This module coordinates scraping, comparison, storage, and notifications
using the new ID-based approach with database storage.
"""
import logging
import datetime
from pathlib import Path
from typing import Optional
from api.fetch_grades_v2 import APIGradeFetcherV2
from shared.models import GradeData
from shared.grade_store import GradeStore
from shared.id_comparator import IDComparator, ChangeReport
from pipeline.notifier import GradeNotifier
from shared.config import get_config
from shared.change_logger import ChangeLogger


class GradePipelineV2:
    """
    Main pipeline orchestrator using ID-based change detection.

    This replaces the old DeepDiff-based comparator with an efficient
    ID-based approach using SQLite for state tracking.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = get_config()

        # Initialize pipeline components
        self.fetcher = APIGradeFetcherV2()
        self.store = GradeStore()
        self.comparator = IDComparator(self.store)
        self.notifier = GradeNotifier()
        self.change_logger = ChangeLogger(self.config)

        # Ensure data directory exists
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)

    def run_full_pipeline(self, download_path: str = '.') -> bool:
        """
        Execute the complete grade monitoring pipeline.

        Args:
            download_path: Path for driver downloads (unused, kept for compatibility)

        Returns:
            bool: True if pipeline completed successfully
        """
        pipeline_start_time = datetime.datetime.now()
        self.logger.info("Starting grade monitoring pipeline (ID-based)")

        try:
            # Step 1: Fetch grades via API
            self.logger.info("Step 1: Fetching grades from Schoology API")
            grade_data = self._fetch_grades()
            if not grade_data:
                self._handle_fetch_failure()
                return False

            # Step 2: Detect changes using ID-based comparison
            self.logger.info("Step 2: Detecting changes (ID-based comparison)")
            report = self._detect_changes(grade_data)

            # Step 3: Send notifications if changes detected
            pipeline_duration = datetime.datetime.now() - pipeline_start_time
            self.logger.info(f"Pipeline completed successfully in {pipeline_duration}")

            notification_results = {}
            if report.has_changes():
                self.logger.info("Step 3: Sending change notification")
                notification_success, notification_results = self._send_change_notification(report, pipeline_duration)
                if not notification_success:
                    self.logger.warning("Failed to send change notification")
            else:
                self.logger.info("Step 3: Sending status notification - no changes detected")
                status_message = f"Grade monitoring completed successfully. {report.summary()}. Duration: {pipeline_duration}"
                self.notifier.send_status_notification(status_message, success=True)

            # Log change report to JSON history
            self.change_logger.log_change_report(
                report,
                notification_sent=report.has_changes(),
                notification_results=notification_results
            )

            # Periodic cleanup of old logs
            try:
                self.change_logger.cleanup_old_logs()
            except Exception as e:
                self.logger.warning(f"Log cleanup failed: {e}")

            return True

        except Exception as e:
            pipeline_duration = datetime.datetime.now() - pipeline_start_time
            self.logger.error(f"Pipeline failed after {pipeline_duration}: {e}", exc_info=True)

            # Send error notification
            self.notifier.send_error_notification(
                "Grade monitoring pipeline failed",
                f"Error: {str(e)}\nDuration: {pipeline_duration}"
            )

            return False

    def _fetch_grades(self) -> Optional[GradeData]:
        """Fetch grades via API with error handling and retries"""
        max_retries = self.config.app.max_retries if hasattr(self.config.app, 'max_retries') else 3

        for attempt in range(max_retries):
            try:
                self.logger.info(f"API fetch attempt {attempt + 1}/{max_retries}")
                grade_data = self.fetcher.fetch_all_grades()

                if grade_data:
                    total_assignments = len(grade_data.get_all_assignments())
                    self.logger.info(f"API fetch successful: {len(grade_data.sections)} sections, {total_assignments} assignments")
                    return grade_data
                else:
                    self.logger.warning(f"API fetch attempt {attempt + 1} returned no data")

            except Exception as e:
                self.logger.error(f"API fetch attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    self.logger.info("Retrying API fetch...")
                    import time
                    time.sleep(5)

        self.logger.error("All API fetch attempts failed")
        return None

    def _detect_changes(self, grade_data: GradeData) -> ChangeReport:
        """Detect changes using ID-based comparison"""
        try:
            report = self.comparator.detect_changes(grade_data, save_to_db=True)
            self.logger.info(f"Change detection complete: {report.summary()}")
            return report

        except Exception as e:
            self.logger.error(f"Error in change detection: {e}", exc_info=True)
            # Return empty report indicating initial capture
            return ChangeReport(
                changes=[],
                timestamp=grade_data.timestamp,
                is_initial=True
            )

    def _send_change_notification(self, report: ChangeReport, pipeline_duration) -> tuple[bool, dict]:
        """
        Send notification about detected changes.

        Args:
            report: Change report
            pipeline_duration: How long the pipeline took to run

        Returns:
            Tuple of (success, notification_results dict)
        """
        try:
            # Format the changes for notification
            formatted_message = report.format_for_notification()

            # Create enhanced status message that includes changes
            status_info = f"Grade monitoring completed successfully. Duration: {pipeline_duration}"
            combined_message = f"{formatted_message}\n\n--- Status ---\n{status_info}"

            # Send notification
            # Note: We need to adapt the old notification interface
            # For now, create a compatible structure
            changes_dict = {
                'type': 'update',
                'summary': report.summary(),
                'detailed_changes': [
                    {
                        'type': 'grade_change',
                        'assignment_id': change.assignment_id,
                        'assignment_title': change.assignment_title,
                        'old_grade': change.old_grade,
                        'new_grade': change.new_grade,
                        'change_type': change.change_type
                    }
                    for change in report.changes
                ]
            }

            notification_success, notification_results = self.notifier.send_grade_change_notification(
                changes_dict,
                combined_message
            )

            if notification_success:
                self.logger.info("Change notification sent successfully")
            else:
                self.logger.warning("Failed to send change notification")

            return notification_success, notification_results

        except Exception as e:
            self.logger.error(f"Error sending change notification: {e}", exc_info=True)
            return False, {}

    def _handle_fetch_failure(self):
        """Handle API fetch failure with appropriate notifications"""
        error_message = "Failed to fetch grade data from Schoology API"
        self.logger.error(error_message)

        # Send error notification
        self.notifier.send_error_notification(
            error_message,
            "All API fetch attempts failed. Please check API credentials and network connectivity."
        )
