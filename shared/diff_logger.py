"""
Dedicated logging module for grade change diffs and notifications.
Provides structured logging for change tracking and analysis.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from .config import Config


class DiffLogger:
    """Handles structured logging of grade changes and raw diffs."""

    def __init__(self, config: Config):
        self.config = config
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Initialize loggers
        self.change_logger = self._setup_change_logger()
        self.raw_diff_logger = self._setup_raw_diff_logger()

    def _setup_change_logger(self) -> Optional[logging.Logger]:
        """Set up the structured change logger."""
        if not self.config.logging.enable_change_logging:
            return None

        logger = logging.getLogger('grade_changes')
        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers if logger already configured
        if logger.handlers:
            return logger

        # Create file handler
        log_file = self.logs_dir / 'grade_changes.log'
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)

        # JSON formatter for structured data
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False  # Don't propagate to root logger

        return logger

    def _setup_raw_diff_logger(self) -> Optional[logging.Logger]:
        """Set up the raw diff logger for debug purposes."""
        if not self.config.logging.enable_raw_diff_logging:
            return None

        logger = logging.getLogger('raw_diffs')
        logger.setLevel(logging.DEBUG)

        # Avoid duplicate handlers if logger already configured
        if logger.handlers:
            return logger

        # Create file handler
        log_file = self.logs_dir / 'raw_diffs.log'
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.DEBUG)

        # JSON formatter for structured data
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False  # Don't propagate to root logger

        return logger

    def log_grade_changes(
        self,
        changes: Dict[str, Any],
        formatted_message: str,
        notification_results: Dict[str, bool],
        comparison_files: Optional[List[str]] = None
    ) -> None:
        """
        Log structured grade change information.

        Args:
            changes: Change information from comparator
            formatted_message: Human-readable notification message
            notification_results: Results from notification providers
            comparison_files: List of files that were compared
        """
        if not self.change_logger:
            return

        # Build structured log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "change_type": changes.get('type', 'unknown'),
            "summary": changes.get('summary', ''),
            "formatted_message": formatted_message,
            "notification_results": notification_results,
            "change_count": len(changes.get('detailed_changes', [])),
            "priority": self._determine_priority(changes),
            "comparison_files": comparison_files or [],
            "metadata": {
                "has_grade_changes": self._has_grade_changes(changes),
                "has_new_assignments": self._has_new_assignments(changes),
                "has_removed_items": self._has_removed_items(changes)
            }
        }

        # Log as JSON for easy parsing
        self.change_logger.info(json.dumps(log_entry, indent=None))

    def log_raw_diff(
        self,
        raw_diff: Dict[str, Any],
        detailed_changes: List[Dict[str, Any]],
        comparison_files: Optional[List[str]] = None,
        old_data_summary: Optional[Dict[str, Any]] = None,
        new_data_summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log raw diff data for debugging purposes.

        Args:
            raw_diff: Raw DeepDiff output
            detailed_changes: Processed changes array
            comparison_files: List of files that were compared
            old_data_summary: Summary of old data (for context)
            new_data_summary: Summary of new data (for context)
        """
        if not self.raw_diff_logger:
            return

        # Build debug log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "comparison_files": comparison_files or [],
            "old_data_summary": old_data_summary,
            "new_data_summary": new_data_summary,
            "raw_diff": self._serialize_diff(raw_diff),
            "detailed_changes": detailed_changes,
            "diff_stats": {
                "values_changed": len(raw_diff.get('values_changed', {})),
                "dictionary_item_added": len(raw_diff.get('dictionary_item_added', {})),
                "dictionary_item_removed": len(raw_diff.get('dictionary_item_removed', {})),
                "iterable_item_added": len(raw_diff.get('iterable_item_added', {})),
                "iterable_item_removed": len(raw_diff.get('iterable_item_removed', {}))
            }
        }

        # Log as JSON for easy parsing
        self.raw_diff_logger.debug(json.dumps(log_entry, indent=None))

    def _serialize_diff(self, diff: Any) -> Dict[str, Any]:
        """Convert DeepDiff object to JSON-serializable format."""
        try:
            # Convert to dict if it's a DeepDiff object
            if hasattr(diff, 'to_dict'):
                return diff.to_dict()
            elif isinstance(diff, dict):
                return diff
            else:
                return {"raw_diff": str(diff)}
        except Exception as e:
            return {"serialization_error": str(e), "diff_type": str(type(diff))}

    def _determine_priority(self, changes: Dict[str, Any]) -> str:
        """Determine priority level based on changes."""
        if changes.get('type') == 'initial':
            return 'low'

        detailed_changes = changes.get('detailed_changes', [])
        change_count = len(detailed_changes)

        # Check for grade-related changes
        grade_related_changes = 0
        for change in detailed_changes:
            path = change.get('path', '')
            if any(keyword in path.lower() for keyword in ['grade', 'score', 'points']):
                grade_related_changes += 1

        # Determine priority
        if grade_related_changes > 5:
            return 'high'
        elif grade_related_changes > 0:
            return 'normal'
        elif change_count > 10:
            return 'normal'
        else:
            return 'low'

    def _has_grade_changes(self, changes: Dict[str, Any]) -> bool:
        """Check if changes include actual grade modifications."""
        detailed_changes = changes.get('detailed_changes', [])
        for change in detailed_changes:
            path = change.get('path', '').lower()
            if 'grade' in path and change.get('type') == 'value_changed':
                return True
        return False

    def _has_new_assignments(self, changes: Dict[str, Any]) -> bool:
        """Check if changes include new assignments."""
        detailed_changes = changes.get('detailed_changes', [])
        for change in detailed_changes:
            if change.get('type') == 'item_added' and 'assignments' in change.get('path', ''):
                return True
        return False

    def _has_removed_items(self, changes: Dict[str, Any]) -> bool:
        """Check if changes include removed items."""
        detailed_changes = changes.get('detailed_changes', [])
        for change in detailed_changes:
            if change.get('type') == 'item_removed':
                return True
        return False

    def cleanup_old_logs(self) -> None:
        """Clean up old log files based on retention settings."""
        current_time = datetime.now()

        # Clean up change logs
        if self.config.logging.change_log_retention_days > 0:
            change_cutoff = current_time - timedelta(days=self.config.logging.change_log_retention_days)
            self._cleanup_log_file(self.logs_dir / 'grade_changes.log', change_cutoff)

        # Clean up raw diff logs
        if self.config.logging.raw_diff_log_retention_days > 0:
            diff_cutoff = current_time - timedelta(days=self.config.logging.raw_diff_log_retention_days)
            self._cleanup_log_file(self.logs_dir / 'raw_diffs.log', diff_cutoff)

    def _cleanup_log_file(self, log_file: Path, cutoff_date: datetime) -> None:
        """Clean up entries older than cutoff date from a log file."""
        if not log_file.exists():
            return

        try:
            temp_file = log_file.with_suffix('.tmp')
            entries_kept = 0
            entries_removed = 0

            with open(log_file, 'r') as infile, open(temp_file, 'w') as outfile:
                for line in infile:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry.get('timestamp', ''))

                        if entry_time >= cutoff_date:
                            outfile.write(line)
                            entries_kept += 1
                        else:
                            entries_removed += 1
                    except (json.JSONDecodeError, ValueError):
                        # Keep malformed entries to avoid data loss
                        outfile.write(line)
                        entries_kept += 1

            # Replace original file with cleaned version
            temp_file.replace(log_file)

            if entries_removed > 0:
                logger = logging.getLogger(__name__)
                logger.info(f"Cleaned up {log_file.name}: removed {entries_removed} old entries, kept {entries_kept}")

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error cleaning up {log_file}: {e}")
            # Remove temp file if it exists
            if temp_file.exists():
                temp_file.unlink()

    def get_recent_changes(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recent change entries for analysis.

        Args:
            days: Number of days to look back

        Returns:
            List of change entries
        """
        change_log = self.logs_dir / 'grade_changes.log'
        if not change_log.exists():
            return []

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_changes = []

        try:
            with open(change_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry.get('timestamp', ''))

                        if entry_time >= cutoff_date:
                            recent_changes.append(entry)
                    except (json.JSONDecodeError, ValueError):
                        continue
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error reading recent changes: {e}")

        return recent_changes