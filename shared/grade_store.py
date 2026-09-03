"""
SQLite-based grade data storage for efficient ID-based change detection.

This module provides a simple database layer for storing the current state
of grades, replacing the old file-based snapshot comparison approach.
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager
from .models import Assignment, Category, Period, Section, GradeData
from decimal import Decimal


class GradeStore:
    """
    SQLite-based storage for grade data with ID-based lookups.

    Schema:
        - snapshots: Metadata about grade data snapshots
        - sections: Course sections
        - periods: Grading periods within sections
        - categories: Grading categories within periods
        - assignments: Individual assignments with grades
    """

    def __init__(self, db_path: str = "data/grades.db"):
        """
        Initialize grade store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # SQLite ignores the schema's ON DELETE CASCADE unless this is set,
        # and it must be set on every connection.
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Snapshots table (metadata about when data was captured)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sections (
                    section_id TEXT PRIMARY KEY,
                    course_title TEXT NOT NULL,
                    section_title TEXT,
                    last_updated TEXT NOT NULL
                )
            """)

            # Periods table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS periods (
                    period_id TEXT PRIMARY KEY,
                    section_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE
                )
            """)

            # Categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    category_id INTEGER,
                    period_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    weight TEXT,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (category_id, period_id),
                    FOREIGN KEY (period_id) REFERENCES periods(period_id) ON DELETE CASCADE
                )
            """)

            # Assignments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignments (
                    assignment_id TEXT PRIMARY KEY,
                    category_id INTEGER,
                    period_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    earned_points TEXT,
                    max_points TEXT,
                    exception TEXT,
                    comment TEXT,
                    due_date TEXT,
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY (category_id, period_id) REFERENCES categories(category_id, period_id) ON DELETE CASCADE
                )
            """)

            # Indexes for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_periods_section
                ON periods(section_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_categories_period
                ON categories(period_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_assignments_category
                ON assignments(category_id, period_id)
            """)

            self.logger.info(f"Database initialized at {self.db_path}")

    def save_grade_data(self, grade_data: GradeData) -> int:
        """
        Save complete grade data snapshot to database.

        Args:
            grade_data: Complete grade data to save

        Returns:
            Snapshot ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create snapshot record
            cursor.execute(
                "INSERT INTO snapshots (timestamp) VALUES (?)",
                (grade_data.timestamp.isoformat(),)
            )
            snapshot_id = cursor.lastrowid

            # Save all sections, periods, categories, and assignments
            for section in grade_data.sections:
                self._save_section(cursor, section, grade_data.timestamp)

            self.logger.info(f"Saved snapshot {snapshot_id} with {len(grade_data.sections)} sections")

            self._prune_stale_sections(cursor, grade_data)
            self._prune_snapshots(cursor)

            return snapshot_id

    def _prune_stale_sections(self, cursor: sqlite3.Cursor, grade_data: GradeData):
        """
        Delete sections the API no longer reports, and their nested rows.

        Courses from previous school years otherwise accumulate forever. An
        empty feed is treated as a fetch problem, not as "everything ended".
        """
        if not grade_data.sections:
            self.logger.warning("Feed reported no sections; skipping section pruning")
            return

        current_ids = [section.section_id for section in grade_data.sections]
        placeholders = ",".join("?" * len(current_ids))

        cursor.execute(
            f"SELECT section_id, course_title FROM sections WHERE section_id NOT IN ({placeholders})",
            current_ids
        )
        stale = cursor.fetchall()
        if not stale:
            return

        cursor.execute(
            f"DELETE FROM sections WHERE section_id NOT IN ({placeholders})",
            current_ids
        )
        titles = ", ".join(f"{row['course_title']} ({row['section_id']})" for row in stale)
        self.logger.info(f"Pruned {len(stale)} section(s) no longer reported: {titles}")

    def _prune_snapshots(self, cursor: sqlite3.Cursor, keep: int = 100):
        """Cap the snapshots table; only the most recent row is ever read."""
        cursor.execute(
            "DELETE FROM snapshots WHERE id NOT IN "
            "(SELECT id FROM snapshots ORDER BY id DESC LIMIT ?)",
            (keep,)
        )
        if cursor.rowcount > 0:
            self.logger.info(f"Pruned {cursor.rowcount} old snapshot row(s)")

    def _save_section(self, cursor: sqlite3.Cursor, section: Section, timestamp: datetime):
        """Save section and its nested data"""
        cursor.execute(
            """
            INSERT INTO sections
            (section_id, course_title, section_title, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(section_id) DO UPDATE SET
                course_title = excluded.course_title,
                section_title = excluded.section_title,
                last_updated = excluded.last_updated
            """,
            (section.section_id, section.course_title, section.section_title, timestamp.isoformat())
        )

        for period in section.periods:
            self._save_period(cursor, period, section.section_id, timestamp)

    def _save_period(self, cursor: sqlite3.Cursor, period: Period, section_id: str, timestamp: datetime):
        """Save period and its nested data"""
        cursor.execute(
            """
            INSERT INTO periods
            (period_id, section_id, name, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(period_id) DO UPDATE SET
                section_id = excluded.section_id,
                name = excluded.name,
                last_updated = excluded.last_updated
            """,
            (period.period_id, section_id, period.name, timestamp.isoformat())
        )

        for category in period.categories:
            self._save_category(cursor, category, period.period_id, timestamp)

    def _save_category(self, cursor: sqlite3.Cursor, category: Category, period_id: str, timestamp: datetime):
        """Save category and its nested data"""
        weight_str = str(category.weight) if category.weight else None

        cursor.execute(
            """
            INSERT INTO categories
            (category_id, period_id, name, weight, last_updated)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(category_id, period_id) DO UPDATE SET
                name = excluded.name,
                weight = excluded.weight,
                last_updated = excluded.last_updated
            """,
            (category.category_id, period_id, category.name, weight_str, timestamp.isoformat())
        )

        for assignment in category.assignments:
            self._save_assignment(cursor, assignment, category.category_id, period_id, timestamp)

    def _save_assignment(self, cursor: sqlite3.Cursor, assignment: Assignment, category_id: int,
                        period_id: str, timestamp: datetime):
        """Save assignment"""
        earned_str = str(assignment.earned_points) if assignment.earned_points is not None else None
        max_str = str(assignment.max_points) if assignment.max_points is not None else None
        due_str = assignment.due_date.isoformat() if assignment.due_date else None

        cursor.execute(
            """
            INSERT INTO assignments
            (assignment_id, category_id, period_id, title, earned_points, max_points,
             exception, comment, due_date, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET
                category_id = excluded.category_id,
                period_id = excluded.period_id,
                title = excluded.title,
                earned_points = excluded.earned_points,
                max_points = excluded.max_points,
                exception = excluded.exception,
                comment = excluded.comment,
                due_date = excluded.due_date,
                last_updated = excluded.last_updated
            """,
            (assignment.assignment_id, category_id, period_id, assignment.title,
             earned_str, max_str, assignment.exception, assignment.comment, due_str, timestamp.isoformat())
        )

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """
        Get assignment by ID.

        Args:
            assignment_id: Unique assignment identifier

        Returns:
            Assignment if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM assignments WHERE assignment_id = ?",
                (assignment_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_assignment(row)

    def get_all_assignments(self) -> list[Assignment]:
        """Get all assignments from database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assignments ORDER BY assignment_id")
            rows = cursor.fetchall()
            return [self._row_to_assignment(row) for row in rows]

    def get_section(self, section_id: str) -> Optional[Section]:
        """
        Get complete section with all nested data.

        Args:
            section_id: Unique section identifier

        Returns:
            Section if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get section
            cursor.execute("SELECT * FROM sections WHERE section_id = ?", (section_id,))
            section_row = cursor.fetchone()
            if not section_row:
                return None

            section = Section(
                section_id=section_row['section_id'],
                course_title=section_row['course_title'],
                section_title=section_row['section_title'] or ""
            )

            # Get periods
            cursor.execute("SELECT * FROM periods WHERE section_id = ?", (section_id,))
            for period_row in cursor.fetchall():
                period = self._load_period(cursor, period_row)
                section.periods.append(period)

            return section

    def _load_period(self, cursor: sqlite3.Cursor, period_row: sqlite3.Row) -> Period:
        """Load period with nested categories and assignments"""
        period = Period(
            period_id=period_row['period_id'],
            name=period_row['name']
        )

        # Get categories for this period
        cursor.execute(
            "SELECT * FROM categories WHERE period_id = ?",
            (period.period_id,)
        )
        for category_row in cursor.fetchall():
            category = self._load_category(cursor, category_row)
            period.categories.append(category)

        return period

    def _load_category(self, cursor: sqlite3.Cursor, category_row: sqlite3.Row) -> Category:
        """Load category with assignments"""
        weight_str = category_row['weight']
        weight = Decimal(weight_str) if weight_str else None

        category = Category(
            category_id=category_row['category_id'],
            name=category_row['name'],
            weight=weight
        )

        # Get assignments for this category
        cursor.execute(
            "SELECT * FROM assignments WHERE category_id = ? AND period_id = ?",
            (category.category_id, category_row['period_id'])
        )
        for assignment_row in cursor.fetchall():
            assignment = self._row_to_assignment(assignment_row)
            category.assignments.append(assignment)

        return category

    def _row_to_assignment(self, row: sqlite3.Row) -> Assignment:
        """Convert database row to Assignment model"""
        earned = Decimal(row['earned_points']) if row['earned_points'] else None
        max_pts = Decimal(row['max_points']) if row['max_points'] else None
        due = datetime.fromisoformat(row['due_date']) if row['due_date'] else None

        return Assignment(
            assignment_id=row['assignment_id'],
            title=row['title'],
            earned_points=earned,
            max_points=max_pts,
            exception=row['exception'],
            comment=row['comment'] or "No comment",
            due_date=due
        )

    def get_latest_snapshot_time(self) -> Optional[datetime]:
        """Get timestamp of most recent snapshot"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp FROM snapshots ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return datetime.fromisoformat(row['timestamp'])
            return None

    def clear_all_data(self):
        """Clear all data from database (for testing)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM assignments")
            cursor.execute("DELETE FROM categories")
            cursor.execute("DELETE FROM periods")
            cursor.execute("DELETE FROM sections")
            cursor.execute("DELETE FROM snapshots")
            self.logger.info("Cleared all data from database")
