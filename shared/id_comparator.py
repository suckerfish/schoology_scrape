"""
ID-based grade comparator - efficient replacement for DeepDiff.

This module compares grade data using stable unique identifiers instead of
deep dictionary comparison, making change detection fast and reliable.
"""
import logging
from collections import defaultdict
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from .models import Assignment, GradeData, Section, Period, Category
from .grade_store import GradeStore


@dataclass
class GradeChange:
    """
    Represents a single grade change.

    Attributes:
        assignment_id: Unique assignment identifier
        assignment_title: Assignment title
        section_name: Full course/section name
        period_name: Grading period name
        category_name: Category name
        old_grade: Previous grade string
        new_grade: New grade string
        old_comment: Previous comment
        new_comment: New comment
        change_type: Type of change (new_assignment, grade_updated, comment_updated)
    """
    assignment_id: str
    assignment_title: str
    section_name: str
    period_name: str
    category_name: str
    old_grade: Optional[str]
    new_grade: str
    old_comment: Optional[str]
    new_comment: str
    change_type: str  # "new_assignment", "grade_updated", "comment_updated"
    new_earned: Optional[Decimal] = None
    new_max: Optional[Decimal] = None
    old_earned: Optional[Decimal] = None
    old_max: Optional[Decimal] = None

    def percentage(self) -> Optional[float]:
        """Compute percentage from new earned/max points"""
        if self.new_earned is not None and self.new_max and self.new_max > 0:
            return float(self.new_earned / self.new_max * 100)
        return None

    def old_percentage(self) -> Optional[float]:
        """Compute percentage from old earned/max points"""
        if self.old_earned is not None and self.old_max and self.old_max > 0:
            return float(self.old_earned / self.old_max * 100)
        return None

    @staticmethod
    def letter_grade(pct: Optional[float]) -> Optional[str]:
        """Convert percentage to letter grade on plus/minus scale"""
        if pct is None:
            return None
        thresholds = [
            (97, "A+"), (93, "A"), (90, "A-"),
            (87, "B+"), (83, "B"), (80, "B-"),
            (77, "C+"), (73, "C"), (70, "C-"),
            (67, "D+"), (63, "D"), (60, "D-"),
        ]
        for cutoff, grade in thresholds:
            if pct >= cutoff:
                return grade
        return "F"

    def _format_grade_with_pct(self, grade_str: str, pct: Optional[float]) -> str:
        """Append percentage and letter grade to a grade string"""
        if pct is not None:
            letter = self.letter_grade(pct)
            return f"{grade_str} ({pct:.0f}% {letter})"
        return grade_str

    def summary(self) -> str:
        """Generate human-readable summary of this change"""
        if self.change_type == "new_assignment":
            grade = self._format_grade_with_pct(self.new_grade, self.percentage())
            return f"New: {self.assignment_title} = {grade}"
        elif self.change_type == "grade_updated":
            old = self._format_grade_with_pct(self.old_grade, self.old_percentage())
            new = self._format_grade_with_pct(self.new_grade, self.percentage())
            return f"{self.assignment_title}: {old} -> {new}"
        elif self.change_type == "comment_updated":
            return f"{self.assignment_title}: Comment updated"
        return f"{self.assignment_title}: Changed"


@dataclass
class ChangeReport:
    """
    Complete report of all detected changes.

    Attributes:
        changes: List of individual grade changes
        timestamp: When comparison was performed
        is_initial: Whether this is the first data capture (no previous data)
        new_assignments_count: Number of new graded assignments
        grade_updates_count: Number of grade changes
        comment_updates_count: Number of comment changes
    """
    changes: list[GradeChange]
    timestamp: datetime
    is_initial: bool = False
    new_assignments_count: int = 0
    grade_updates_count: int = 0
    comment_updates_count: int = 0

    def has_changes(self) -> bool:
        """Check if any changes were detected"""
        return len(self.changes) > 0

    def summary(self) -> str:
        """Generate human-readable summary"""
        if self.is_initial:
            return "Initial grade data captured"

        if not self.has_changes():
            return "No changes detected"

        parts = []
        if self.new_assignments_count > 0:
            parts.append(f"{self.new_assignments_count} new assignment(s)")
        if self.grade_updates_count > 0:
            parts.append(f"{self.grade_updates_count} grade update(s)")
        if self.comment_updates_count > 0:
            parts.append(f"{self.comment_updates_count} comment update(s)")

        return "Changes detected: " + ", ".join(parts)

    def format_for_notification(self) -> str:
        """Format changes for notification message with hierarchical grouping"""
        if self.is_initial:
            return self.summary()

        if not self.has_changes():
            return self.summary()

        message = f"{self.summary()}\n\n"

        # Group changes by section -> period -> category
        tree: dict[str, dict[str, dict[str, list[GradeChange]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        for change in self.changes:
            tree[change.section_name][change.period_name][change.category_name].append(change)

        for section_name, periods in tree.items():
            message += f"{section_name}\n"
            for period_name, categories in periods.items():
                message += f"  {period_name}\n"
                for category_name, changes in categories.items():
                    message += f"    {category_name}\n"
                    for change in changes:
                        message += f"      {change.summary()}\n"

        return message


class IDComparator:
    """
    ID-based grade comparator using database for state tracking.

    This comparator replaces DeepDiff with a simple, efficient approach:
    1. Load previous state from database
    2. Compare assignments by ID
    3. Detect meaningful changes (grade, comment)
    4. Save new state to database
    """

    def __init__(self, store: Optional[GradeStore] = None):
        """
        Initialize comparator.

        Args:
            store: Grade store instance (creates default if not provided)
        """
        self.logger = logging.getLogger(__name__)
        self.store = store or GradeStore()

    def detect_changes(self, new_data: GradeData, save_to_db: bool = True) -> ChangeReport:
        """
        Detect changes by comparing new data against database.

        Args:
            new_data: New grade data to compare
            save_to_db: Whether to save new data to database after comparison

        Returns:
            ChangeReport with all detected changes
        """
        # Check if this is the first run
        last_snapshot = self.store.get_latest_snapshot_time()
        is_initial = last_snapshot is None

        if is_initial:
            self.logger.info("No previous data found - treating as initial capture")
            if save_to_db:
                self.store.save_grade_data(new_data)
            return ChangeReport(
                changes=[],
                timestamp=new_data.timestamp,
                is_initial=True
            )

        # Compare against database
        self.logger.info("Comparing new data against database...")
        changes = self._compare_grade_data(new_data)

        # Save new data to database
        if save_to_db:
            self.store.save_grade_data(new_data)

        # Count change types
        new_count = sum(1 for c in changes if c.change_type == "new_assignment")
        grade_count = sum(1 for c in changes if c.change_type == "grade_updated")
        comment_count = sum(1 for c in changes if c.change_type == "comment_updated")

        report = ChangeReport(
            changes=changes,
            timestamp=new_data.timestamp,
            is_initial=False,
            new_assignments_count=new_count,
            grade_updates_count=grade_count,
            comment_updates_count=comment_count
        )

        self.logger.info(f"Comparison complete: {report.summary()}")
        return report

    def _compare_grade_data(self, new_data: GradeData) -> list[GradeChange]:
        """
        Compare new grade data against database state.

        Args:
            new_data: New grade data

        Returns:
            List of detected changes
        """
        changes = []

        # Iterate through all assignments in new data
        for section, period, category, new_assignment in new_data.get_all_assignments():
            # Only track assignments that have grades
            if not new_assignment.has_grade():
                continue

            # Look up previous state from database
            old_assignment = self.store.get_assignment(new_assignment.assignment_id)

            if old_assignment is None:
                # New graded assignment
                changes.append(GradeChange(
                    assignment_id=new_assignment.assignment_id,
                    assignment_title=new_assignment.title,
                    section_name=section.full_name,
                    period_name=period.name,
                    category_name=category.name,
                    old_grade=None,
                    new_grade=new_assignment.grade_string(),
                    old_comment=None,
                    new_comment=new_assignment.comment,
                    change_type="new_assignment",
                    new_earned=new_assignment.earned_points,
                    new_max=new_assignment.max_points,
                ))

            elif new_assignment.grade_changed(old_assignment):
                # Grade or comment changed
                change_type = "grade_updated"

                # Check if only comment changed (and it's substantive)
                if (new_assignment.earned_points == old_assignment.earned_points and
                    new_assignment.max_points == old_assignment.max_points and
                    new_assignment.exception == old_assignment.exception):
                    change_type = "comment_updated"

                changes.append(GradeChange(
                    assignment_id=new_assignment.assignment_id,
                    assignment_title=new_assignment.title,
                    section_name=section.full_name,
                    period_name=period.name,
                    category_name=category.name,
                    old_grade=old_assignment.grade_string(),
                    new_grade=new_assignment.grade_string(),
                    old_comment=old_assignment.comment,
                    new_comment=new_assignment.comment,
                    change_type=change_type,
                    new_earned=new_assignment.earned_points,
                    new_max=new_assignment.max_points,
                    old_earned=old_assignment.earned_points,
                    old_max=old_assignment.max_points,
                ))

        return changes

    def format_changes_for_notification(self, report: ChangeReport) -> str:
        """
        Format change report for notification (compatible with old interface).

        Args:
            report: Change report

        Returns:
            Formatted notification message
        """
        return report.format_for_notification()
