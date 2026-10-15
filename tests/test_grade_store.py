"""
Tests for SQLite-based grade storage.
"""
import json
import pytest
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from shared.models import Assignment, Category, Period, Section, GradeData
from shared.grade_store import GradeStore


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
def sample_assignment():
    """Create sample assignment"""
    return Assignment(
        assignment_id="100",
        title="Test Assignment",
        earned_points=Decimal("8"),
        max_points=Decimal("10"),
        exception=None,
        comment="Good work",
        due_date=datetime(2025, 1, 15, 23, 59)
    )


@pytest.fixture
def sample_grade_data(sample_assignment):
    """Create sample grade data structure"""
    category = Category(
        category_id=1,
        name="Homework",
        weight=Decimal("30"),
        assignments=[sample_assignment]
    )

    period = Period(
        period_id="sec1:T1",
        name="2024-2025 T1",
        categories=[category]
    )

    section = Section(
        section_id="sec1",
        course_title="Math 7",
        section_title="Period 1",
        periods=[period]
    )

    return GradeData(
        timestamp=datetime.now(),
        sections=[section]
    )


class TestGradeStoreInitialization:
    """Tests for database initialization"""

    def test_creates_database_file(self, temp_db):
        """Test that database file is created"""
        assert Path(temp_db.db_path).exists()

    def test_creates_required_tables(self, temp_db):
        """Test that all required tables are created"""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]

        assert 'snapshots' in tables
        assert 'sections' in tables
        assert 'periods' in tables
        assert 'categories' in tables
        assert 'assignments' in tables


class TestSaveGradeData:
    """Tests for saving grade data"""

    def test_save_creates_snapshot(self, temp_db, sample_grade_data):
        """Test that saving creates a snapshot record"""
        snapshot_id = temp_db.save_grade_data(sample_grade_data)

        assert snapshot_id == 1

        # Verify snapshot exists
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM snapshots")
            count = cursor.fetchone()[0]

        assert count == 1

    def test_save_stores_section(self, temp_db, sample_grade_data):
        """Test that sections are stored correctly"""
        temp_db.save_grade_data(sample_grade_data)

        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sections WHERE section_id = 'sec1'")
            row = cursor.fetchone()

        assert row is not None
        assert row['course_title'] == "Math 7"
        assert row['section_title'] == "Period 1"

    def test_save_stores_assignment(self, temp_db, sample_grade_data):
        """Test that assignments are stored correctly"""
        temp_db.save_grade_data(sample_grade_data)

        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assignments WHERE assignment_id = '100'")
            row = cursor.fetchone()

        assert row is not None
        assert row['title'] == "Test Assignment"
        assert row['earned_points'] == "8"
        assert row['max_points'] == "10"
        assert row['comment'] == "Good work"

    def test_save_handles_null_values(self, temp_db):
        """Test that null/None values are stored correctly"""
        assignment = Assignment(
            assignment_id="200",
            title="Ungraded",
            earned_points=None,
            max_points=None,
            exception=None,
            comment="No comment",
            due_date=None
        )

        category = Category(category_id=0, name="Default", assignments=[assignment])
        period = Period(period_id="sec1:T1", name="T1", categories=[category])
        section = Section(section_id="sec1", course_title="Test", section_title="", periods=[period])
        data = GradeData(timestamp=datetime.now(), sections=[section])

        temp_db.save_grade_data(data)

        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assignments WHERE assignment_id = '200'")
            row = cursor.fetchone()

        assert row['earned_points'] is None
        assert row['max_points'] is None
        assert row['due_date'] is None


class TestRetrieveGradeData:
    """Tests for retrieving grade data"""

    def test_get_assignment_by_id(self, temp_db, sample_grade_data):
        """Test retrieving assignment by ID"""
        temp_db.save_grade_data(sample_grade_data)

        assignment = temp_db.get_assignment("100")

        assert assignment is not None
        assert assignment.assignment_id == "100"
        assert assignment.title == "Test Assignment"
        assert assignment.earned_points == Decimal("8")
        assert assignment.max_points == Decimal("10")

    def test_get_nonexistent_assignment(self, temp_db):
        """Test retrieving non-existent assignment returns None"""
        assignment = temp_db.get_assignment("nonexistent")
        assert assignment is None

    def test_get_all_assignments(self, temp_db, sample_grade_data):
        """Test retrieving all assignments"""
        temp_db.save_grade_data(sample_grade_data)

        assignments = temp_db.get_all_assignments()

        assert len(assignments) == 1
        assert assignments[0].assignment_id == "100"

    def test_get_section_with_nested_data(self, temp_db, sample_grade_data):
        """Test retrieving complete section structure"""
        temp_db.save_grade_data(sample_grade_data)

        section = temp_db.get_section("sec1")

        assert section is not None
        assert section.course_title == "Math 7"
        assert len(section.periods) == 1
        assert section.periods[0].name == "2024-2025 T1"
        assert len(section.periods[0].categories) == 1
        assert len(section.periods[0].categories[0].assignments) == 1

    def test_get_latest_snapshot_time(self, temp_db, sample_grade_data):
        """Test getting latest snapshot timestamp"""
        # Initially no snapshots
        assert temp_db.get_latest_snapshot_time() is None

        # After save
        temp_db.save_grade_data(sample_grade_data)
        latest = temp_db.get_latest_snapshot_time()

        assert latest is not None
        assert isinstance(latest, datetime)


class TestClearData:
    """Tests for clearing data"""

    def test_clear_removes_all_data(self, temp_db, sample_grade_data):
        """Test that clear removes all data"""
        temp_db.save_grade_data(sample_grade_data)

        # Verify data exists
        assert len(temp_db.get_all_assignments()) == 1

        temp_db.clear_all_data()

        # Verify data is gone
        assert len(temp_db.get_all_assignments()) == 0
        assert temp_db.get_latest_snapshot_time() is None


class TestUpdateBehavior:
    """Tests for update/replace behavior"""

    def test_assignment_update_replaces_existing(self, temp_db, sample_grade_data):
        """Test that saving again updates existing records"""
        temp_db.save_grade_data(sample_grade_data)

        # Modify and save again
        sample_grade_data.sections[0].periods[0].categories[0].assignments[0].earned_points = Decimal("9")
        temp_db.save_grade_data(sample_grade_data)

        # Should have updated value
        assignment = temp_db.get_assignment("100")
        assert assignment.earned_points == Decimal("9")

        # Should still only have 1 assignment
        assert len(temp_db.get_all_assignments()) == 1


class TestGradedAt:
    """Tests for the graded_at column"""

    def test_graded_at_round_trips_separately_from_due_date(self, temp_db, sample_grade_data):
        """graded_at is stored in its own column and due_date stays as-is"""
        assignment = sample_grade_data.sections[0].periods[0].categories[0].assignments[0]
        assignment.graded_at = datetime(2025, 1, 20, 9, 30)
        temp_db.save_grade_data(sample_grade_data)

        stored = temp_db.get_assignment("100")
        assert stored.due_date == datetime(2025, 1, 15, 23, 59)
        assert stored.graded_at == datetime(2025, 1, 20, 9, 30)

    def test_undated_assignment_keeps_null_due_date(self, temp_db, sample_grade_data):
        """A grade column with no due date gets graded_at only"""
        assignment = sample_grade_data.sections[0].periods[0].categories[0].assignments[0]
        assignment.due_date = None
        assignment.graded_at = datetime(2025, 1, 20, 9, 30)
        temp_db.save_grade_data(sample_grade_data)

        with temp_db._get_connection() as conn:
            row = conn.execute(
                "SELECT due_date, graded_at FROM assignments WHERE assignment_id = '100'"
            ).fetchone()
        assert row['due_date'] is None
        assert row['graded_at'] == "2025-01-20T09:30:00"

    def test_adds_column_to_existing_database(self, temp_db):
        """A database created before graded_at gains the column on startup"""
        with temp_db._get_connection() as conn:
            conn.execute("ALTER TABLE assignments DROP COLUMN graded_at")

        GradeStore(temp_db.db_path)
        GradeStore(temp_db.db_path)  # second start must not fail

        with temp_db._get_connection() as conn:
            columns = {row['name'] for row in conn.execute("PRAGMA table_info(assignments)")}
        assert 'graded_at' in columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


def test_backfill_history_copies_older_log_changes_once(temp_db, tmp_path):
    """Change-log entries older than grade_history are copied, and only once"""
    log = tmp_path / "grade_changes.log"
    entries = [
        {"timestamp": "2026-09-01T12:00:00", "changes": [
            {"change_type": "new_assignment", "assignment_id": "a1", "section": "Science 8: Section 52",
             "assignment_title": "Lab", "old_grade": None, "new_grade": "Missing"}]},
        {"timestamp": "2026-09-05T12:00:00", "changes": [
            {"change_type": "grade_updated", "assignment_id": "a1", "section": "Science 8: Section 52",
             "assignment_title": "Lab", "old_grade": "Missing", "new_grade": "8 / 10"},
            {"change_type": "comment_updated", "assignment_id": "a1", "section": "Science 8: Section 52",
             "assignment_title": "Lab", "old_grade": "8 / 10", "new_grade": "8 / 10"}]},
        {"timestamp": "2026-10-20T12:00:00", "changes": [
            {"change_type": "grade_updated", "assignment_id": "a1", "section": "Science 8: Section 52",
             "assignment_title": "Lab", "old_grade": "8 / 10", "new_grade": "10 / 10"}]},
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\nnot json\n")

    # A live run already recorded history from 2026-10-20 onward
    with temp_db._get_connection() as conn:
        conn.execute(
            "INSERT INTO grade_history (recorded_at, kind, item_id, section_id, label, old_value, new_value) "
            "VALUES ('2026-10-20T12:00:00', 'assignment', 'a1', '', 'x', '8 / 10', '10 / 10')"
        )

    assert temp_db.backfill_history(log) == 2
    assert temp_db.backfill_history(log) == 0

    with temp_db._get_connection() as conn:
        rows = conn.execute(
            "SELECT recorded_at, old_value, new_value, label FROM grade_history "
            "WHERE kind = 'assignment' ORDER BY recorded_at"
        ).fetchall()
    assert [(r[1], r[2]) for r in rows] == [(None, "Missing"), ("Missing", "8 / 10"), ("8 / 10", "10 / 10")]
    assert rows[0][3] == "Science 8: Section 52 / Lab"
