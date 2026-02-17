"""
Tests for ID-based grade comparison system.
"""
import pytest
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from shared.models import Assignment, Category, Period, Section, GradeData
from shared.grade_store import GradeStore
from shared.id_comparator import IDComparator, GradeChange, ChangeReport


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    store = GradeStore(db_path)
    yield store

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_grade_data():
    """Create sample grade data for testing"""
    assignment1 = Assignment(
        assignment_id="100",
        title="Test Assignment 1",
        earned_points=Decimal("5"),
        max_points=Decimal("5"),
        comment="Good work"
    )

    assignment2 = Assignment(
        assignment_id="101",
        title="Test Assignment 2",
        earned_points=Decimal("8"),
        max_points=Decimal("10"),
        comment="No comment"
    )

    category = Category(
        category_id=1,
        name="Homework",
        weight=Decimal("50"),
        assignments=[assignment1, assignment2]
    )

    period = Period(
        period_id="section1:T1",
        name="T1 2024-2025",
        categories=[category]
    )

    section = Section(
        section_id="section1",
        course_title="Math 7",
        section_title="Section 1",
        periods=[period]
    )

    return GradeData(
        timestamp=datetime.now(),
        sections=[section]
    )


def test_initial_data_capture(temp_db, sample_grade_data):
    """Test that initial data capture is detected correctly"""
    comparator = IDComparator(temp_db)

    report = comparator.detect_changes(sample_grade_data)

    assert report.is_initial is True
    assert report.has_changes() is False
    assert "Initial" in report.summary()


def test_no_changes_detected(temp_db, sample_grade_data):
    """Test that no changes are detected when data is identical"""
    comparator = IDComparator(temp_db)

    # First run - initial capture
    comparator.detect_changes(sample_grade_data)

    # Second run - should detect no changes
    report = comparator.detect_changes(sample_grade_data)

    assert report.is_initial is False
    assert report.has_changes() is False
    assert "No changes" in report.summary()


def test_grade_change_detected(temp_db, sample_grade_data):
    """Test that grade changes are detected"""
    comparator = IDComparator(temp_db)

    # Initial capture
    comparator.detect_changes(sample_grade_data)

    # Modify grade
    modified_data = GradeData(
        timestamp=datetime.now(),
        sections=sample_grade_data.sections
    )
    modified_data.sections[0].periods[0].categories[0].assignments[0].earned_points = Decimal("4")

    # Should detect change
    report = comparator.detect_changes(modified_data)

    assert report.has_changes() is True
    assert report.grade_updates_count == 1
    assert len(report.changes) == 1

    change = report.changes[0]
    assert change.change_type == "grade_updated"
    assert change.old_grade == "5 / 5"
    assert change.new_grade == "4 / 5"


def test_new_assignment_detected(temp_db, sample_grade_data):
    """Test that new assignments are detected"""
    comparator = IDComparator(temp_db)

    # Initial capture
    comparator.detect_changes(sample_grade_data)

    # Add new assignment
    new_assignment = Assignment(
        assignment_id="102",
        title="New Assignment",
        earned_points=Decimal("10"),
        max_points=Decimal("10"),
        comment="No comment"
    )

    modified_data = GradeData(
        timestamp=datetime.now(),
        sections=sample_grade_data.sections
    )
    modified_data.sections[0].periods[0].categories[0].assignments.append(new_assignment)

    # Should detect new assignment
    report = comparator.detect_changes(modified_data)

    assert report.has_changes() is True
    assert report.new_assignments_count == 1
    assert len(report.changes) == 1

    change = report.changes[0]
    assert change.change_type == "new_assignment"
    assert change.assignment_id == "102"
    assert change.new_grade == "10 / 10"


def test_comment_change_detected(temp_db, sample_grade_data):
    """Test that comment changes are detected"""
    comparator = IDComparator(temp_db)

    # Initial capture
    comparator.detect_changes(sample_grade_data)

    # Modify comment
    modified_data = GradeData(
        timestamp=datetime.now(),
        sections=sample_grade_data.sections
    )
    modified_data.sections[0].periods[0].categories[0].assignments[0].comment = "Excellent work!"

    # Should detect change
    report = comparator.detect_changes(modified_data)

    assert report.has_changes() is True
    assert report.comment_updates_count == 1

    change = report.changes[0]
    assert change.change_type == "comment_updated"
    assert change.old_comment == "Good work"
    assert change.new_comment == "Excellent work!"


def test_exception_status_detected(temp_db, sample_grade_data):
    """Test that exception status changes are detected"""
    comparator = IDComparator(temp_db)

    # Initial capture
    comparator.detect_changes(sample_grade_data)

    # Change to Missing
    modified_data = GradeData(
        timestamp=datetime.now(),
        sections=sample_grade_data.sections
    )
    modified_data.sections[0].periods[0].categories[0].assignments[0].exception = "Missing"
    modified_data.sections[0].periods[0].categories[0].assignments[0].earned_points = None
    modified_data.sections[0].periods[0].categories[0].assignments[0].max_points = None

    # Should detect change
    report = comparator.detect_changes(modified_data)

    assert report.has_changes() is True
    assert report.grade_updates_count == 1

    change = report.changes[0]
    assert change.old_grade == "5 / 5"
    assert change.new_grade == "Missing"


def test_ungraded_assignments_ignored(temp_db):
    """Test that ungraded assignments don't trigger change notifications"""
    comparator = IDComparator(temp_db)

    # Create data with ungraded assignment
    ungraded = Assignment(
        assignment_id="200",
        title="Ungraded Assignment",
        comment="No comment"
    )

    category = Category(
        category_id=1,
        name="Homework",
        assignments=[ungraded]
    )

    period = Period(
        period_id="section1:T1",
        name="T1 2024-2025",
        categories=[category]
    )

    section = Section(
        section_id="section1",
        course_title="Math 7",
        section_title="Section 1",
        periods=[period]
    )

    data = GradeData(
        timestamp=datetime.now(),
        sections=[section]
    )

    # First run - initial capture includes structure but no graded assignments reported
    report1 = comparator.detect_changes(data)
    assert report1.is_initial is True

    # Add grade to the assignment
    data.sections[0].periods[0].categories[0].assignments[0].earned_points = Decimal("10")
    data.sections[0].periods[0].categories[0].assignments[0].max_points = Decimal("10")

    # Should detect as grade change (from "Not graded" to "10 / 10")
    report2 = comparator.detect_changes(data)
    assert report2.has_changes() is True
    assert report2.grade_updates_count == 1
    change = report2.changes[0]
    assert change.old_grade == "Not graded"
    assert change.new_grade == "10 / 10"


def test_notification_formatting(sample_grade_data):
    """Test that change reports format with hierarchical grouping"""
    changes = [
        GradeChange(
            assignment_id="100",
            assignment_title="Test 1",
            section_name="Math 7: Section 1",
            period_name="T1",
            category_name="Tests",
            old_grade="5 / 5",
            new_grade="4 / 5",
            old_comment="Good",
            new_comment="Needs work",
            change_type="grade_updated",
            new_earned=Decimal("4"),
            new_max=Decimal("5"),
            old_earned=Decimal("5"),
            old_max=Decimal("5"),
        ),
        GradeChange(
            assignment_id="101",
            assignment_title="Quiz 2",
            section_name="Math 7: Section 1",
            period_name="T1",
            category_name="Tests",
            old_grade=None,
            new_grade="8 / 10",
            old_comment=None,
            new_comment="No comment",
            change_type="new_assignment",
            new_earned=Decimal("8"),
            new_max=Decimal("10"),
        ),
    ]

    report = ChangeReport(
        changes=changes,
        timestamp=datetime.now(),
        is_initial=False,
        grade_updates_count=1,
        new_assignments_count=1,
    )

    message = report.format_for_notification()

    # Should have hierarchical structure
    assert "Math 7: Section 1" in message
    assert "T1" in message
    assert "Tests" in message
    # Should contain assignment names
    assert "Test 1" in message
    assert "Quiz 2" in message
    # Should contain percentages
    assert "80%" in message
    assert "B-" in message
    # Should contain summary line
    assert "1 grade update" in message
    assert "1 new assignment" in message


def test_letter_grade_computation():
    """Test letter grade threshold boundaries"""
    assert GradeChange.letter_grade(100) == "A+"
    assert GradeChange.letter_grade(97) == "A+"
    assert GradeChange.letter_grade(96.9) == "A"
    assert GradeChange.letter_grade(93) == "A"
    assert GradeChange.letter_grade(92.9) == "A-"
    assert GradeChange.letter_grade(90) == "A-"
    assert GradeChange.letter_grade(89.9) == "B+"
    assert GradeChange.letter_grade(87) == "B+"
    assert GradeChange.letter_grade(83) == "B"
    assert GradeChange.letter_grade(80) == "B-"
    assert GradeChange.letter_grade(77) == "C+"
    assert GradeChange.letter_grade(73) == "C"
    assert GradeChange.letter_grade(70) == "C-"
    assert GradeChange.letter_grade(67) == "D+"
    assert GradeChange.letter_grade(63) == "D"
    assert GradeChange.letter_grade(60) == "D-"
    assert GradeChange.letter_grade(59.9) == "F"
    assert GradeChange.letter_grade(0) == "F"
    assert GradeChange.letter_grade(None) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
