"""
Simple JSON logger for grade change reports.

Writes structured JSON logs of ChangeReport objects to logs/grade_changes.log.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .id_comparator import ChangeReport
    from .config import Config


class ChangeLogger:
    """Logs grade change reports as JSON for history and analysis."""

    def __init__(self, config: 'Config'):
        self.config = config
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        self.log_file = self.logs_dir / "grade_changes.log"
        self.logger = logging.getLogger(__name__)

    def log_change_report(
        self,
        report: 'ChangeReport',
        notification_sent: bool = False,
        notification_results: Optional[Dict[str, bool]] = None
    ) -> None:
        """
        Log a change report as JSON.

        Args:
            report: The ChangeReport from ID-based comparison
            notification_sent: Whether notifications were sent
            notification_results: Results from each notification provider
        """
        if not self.config.logging.enable_change_logging:
            return

        entry = {
            "timestamp": report.timestamp.isoformat(),
            "is_initial": report.is_initial,
            "has_changes": report.has_changes(),
            "summary": report.summary(),
            "counts": {
                "new_assignments": report.new_assignments_count,
                "grade_updates": report.grade_updates_count,
                "comment_updates": report.comment_updates_count,
                "total": len(report.changes)
            },
            "changes": [
                {
                    "assignment_id": c.assignment_id,
                    "assignment_title": c.assignment_title,
                    "section": c.section_name,
                    "period": c.period_name,
                    "category": c.category_name,
                    "change_type": c.change_type,
                    "old_grade": c.old_grade,
                    "new_grade": c.new_grade,
                    "old_comment": c.old_comment if c.old_comment != c.new_comment else None,
                    "new_comment": c.new_comment if c.old_comment != c.new_comment else None
                }
                for c in report.changes
            ],
            "notification": {
                "sent": notification_sent,
                "results": notification_results or {}
            }
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write change log: {e}")

    def cleanup_old_logs(self) -> None:
        """Remove log entries older than retention period."""
        retention_days = self.config.logging.change_log_retention_days
        if retention_days <= 0 or not self.log_file.exists():
            return

        cutoff = datetime.now() - timedelta(days=retention_days)
        temp_file = self.log_file.with_suffix(".tmp")

        try:
            kept = 0
            removed = 0

            with open(self.log_file, "r") as infile, open(temp_file, "w") as outfile:
                for line in infile:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry["timestamp"])
                        if entry_time >= cutoff:
                            outfile.write(line)
                            kept += 1
                        else:
                            removed += 1
                    except (json.JSONDecodeError, KeyError, ValueError):
                        outfile.write(line)  # Keep malformed entries
                        kept += 1

            temp_file.replace(self.log_file)

            if removed > 0:
                self.logger.info(f"Log cleanup: removed {removed} old entries, kept {kept}")

        except Exception as e:
            self.logger.error(f"Failed to cleanup logs: {e}")
            if temp_file.exists():
                temp_file.unlink()
