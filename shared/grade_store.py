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
        - grade_history: Append-only log of every course, period, category,
          and assignment grade change. Kept when a section is pruned.

    Course, period, and category grades are the values Schoology reports,
    stored on their own rows.
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
                    course_grade TEXT,
                    course_letter TEXT,
                    last_updated TEXT NOT NULL
                )
            """)

            # Periods table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS periods (
                    period_id TEXT PRIMARY KEY,
                    section_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    grade TEXT,
                    letter TEXT,
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
                    grade TEXT,
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
                    graded_at TEXT,
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY (category_id, period_id) REFERENCES categories(category_id, period_id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    section_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT
                )
            """)

            # Databases created by older versions lack these columns
            added_columns = {
                'sections': ['course_grade', 'course_letter'],
                'periods': ['grade', 'letter'],
                'categories': ['grade'],
                'assignments': ['graded_at'],
            }
            for table, names in added_columns.items():
                columns = {row['name'] for row in cursor.execute(f"PRAGMA table_info({table})")}
                for name in names:
                    if name not in columns:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} TEXT")

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
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_item
                ON grade_history(kind, item_id)
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

    @staticmethod
    def _grade_str(grade: Optional[Decimal]) -> Optional[str]:
        return str(grade) if grade is not None else None

    def _record_history(self, cursor: sqlite3.Cursor, timestamp: datetime, kind: str, item_id: str,
                        section_id: str, label: str, old_value: Optional[str], new_value: Optional[str]):
        """Append a grade_history row if the value changed (including first appearance)"""
        if old_value == new_value:
            return
        cursor.execute(
            """
            INSERT INTO grade_history
            (recorded_at, kind, item_id, section_id, label, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp.isoformat(), kind, item_id, section_id, label, old_value, new_value)
        )

    def _old_value(self, cursor: sqlite3.Cursor, query: str, params: tuple) -> Optional[str]:
        row = cursor.execute(query, params).fetchone()
        return row[0] if row else None

    def _save_section(self, cursor: sqlite3.Cursor, section: Section, timestamp: datetime):
        """Save section and its nested data"""
        grade_str = self._grade_str(section.course_grade)
        old_grade = self._old_value(
            cursor, "SELECT course_grade FROM sections WHERE section_id = ?", (section.section_id,)
        )
        self._record_history(cursor, timestamp, 'course', section.section_id, section.section_id,
                             section.full_name, old_grade, grade_str)

        cursor.execute(
            """
            INSERT INTO sections
            (section_id, course_title, section_title, course_grade, course_letter, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(section_id) DO UPDATE SET
                course_title = excluded.course_title,
                section_title = excluded.section_title,
                course_grade = excluded.course_grade,
                course_letter = excluded.course_letter,
                last_updated = excluded.last_updated
            """,
            (section.section_id, section.course_title, section.section_title,
             grade_str, section.course_letter, timestamp.isoformat())
        )

        for period in section.periods:
            self._save_period(cursor, period, section, timestamp)

    def _save_period(self, cursor: sqlite3.Cursor, period: Period, section: Section, timestamp: datetime):
        """Save period and its nested data"""
        grade_str = self._grade_str(period.grade)
        old_grade = self._old_value(
            cursor, "SELECT grade FROM periods WHERE period_id = ?", (period.period_id,)
        )
        self._record_history(cursor, timestamp, 'period', period.period_id, section.section_id,
                             f"{section.full_name} / {period.name}", old_grade, grade_str)

        cursor.execute(
            """
            INSERT INTO periods
            (period_id, section_id, name, grade, letter, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(period_id) DO UPDATE SET
                section_id = excluded.section_id,
                name = excluded.name,
                grade = excluded.grade,
                letter = excluded.letter,
                last_updated = excluded.last_updated
            """,
            (period.period_id, section.section_id, period.name, grade_str, period.letter,
             timestamp.isoformat())
        )

        for category in period.categories:
            self._save_category(cursor, category, period, section, timestamp)

    def _save_category(self, cursor: sqlite3.Cursor, category: Category, period: Period,
                       section: Section, timestamp: datetime):
        """Save category and its nested data"""
        period_id = period.period_id
        weight_str = str(category.weight) if category.weight else None
        grade_str = self._grade_str(category.grade)
        old_grade = self._old_value(
            cursor, "SELECT grade FROM categories WHERE category_id = ? AND period_id = ?",
            (category.category_id, period_id)
        )
        self._record_history(cursor, timestamp, 'category', f"{period_id}:{category.category_id}",
                             section.section_id, f"{section.full_name} / {period.name} / {category.name}",
                             old_grade, grade_str)

        cursor.execute(
            """
            INSERT INTO categories
            (category_id, period_id, name, weight, grade, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(category_id, period_id) DO UPDATE SET
                name = excluded.name,
                weight = excluded.weight,
                grade = excluded.grade,
                last_updated = excluded.last_updated
            """,
            (category.category_id, period_id, category.name, weight_str, grade_str,
             timestamp.isoformat())
        )

        for assignment in category.assignments:
            old_row = cursor.execute(
                "SELECT * FROM assignments WHERE assignment_id = ?", (assignment.assignment_id,)
            ).fetchone()
            old_grade = self._row_to_assignment(old_row).grade_string() if old_row else None
            self._record_history(cursor, timestamp, 'assignment', assignment.assignment_id,
                                 section.section_id, f"{section.full_name} / {assignment.title}",
                                 old_grade, assignment.grade_string())

            self._save_assignment(cursor, assignment, category.category_id, period_id, timestamp)

    def _save_assignment(self, cursor: sqlite3.Cursor, assignment: Assignment, category_id: int,
                        period_id: str, timestamp: datetime):
        """Save assignment"""
        earned_str = str(assignment.earned_points) if assignment.earned_points is not None else None
        max_str = str(assignment.max_points) if assignment.max_points is not None else None
        due_str = assignment.due_date.isoformat() if assignment.due_date else None
        graded_str = assignment.graded_at.isoformat() if assignment.graded_at else None

        cursor.execute(
            """
            INSERT INTO assignments
            (assignment_id, category_id, period_id, title, earned_points, max_points,
             exception, comment, due_date, graded_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET
                category_id = excluded.category_id,
                period_id = excluded.period_id,
                title = excluded.title,
                earned_points = excluded.earned_points,
                max_points = excluded.max_points,
                exception = excluded.exception,
                comment = excluded.comment,
                due_date = excluded.due_date,
                graded_at = excluded.graded_at,
                last_updated = excluded.last_updated
            """,
            (assignment.assignment_id, category_id, period_id, assignment.title,
             earned_str, max_str, assignment.exception, assignment.comment, due_str,
             graded_str, timestamp.isoformat())
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
                section_title=section_row['section_title'] or "",
                course_grade=section_row['course_grade'],
                course_letter=section_row['course_letter']
            )

            # Get periods
            cursor.execute("SELECT * FROM periods WHERE section_id = ? ORDER BY name", (section_id,))
            for period_row in cursor.fetchall():
                period = self._load_period(cursor, period_row)
                section.periods.append(period)

            return section

    def get_all_sections(self) -> list[Section]:
        """Get every stored section with nested data, ordered by course title"""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT section_id FROM sections ORDER BY course_title").fetchall()
        return [self.get_section(row['section_id']) for row in rows]

    def _load_period(self, cursor: sqlite3.Cursor, period_row: sqlite3.Row) -> Period:
        """Load period with nested categories and assignments"""
        period = Period(
            period_id=period_row['period_id'],
            name=period_row['name'],
            grade=period_row['grade'],
            letter=period_row['letter']
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
            weight=weight,
            grade=category_row['grade']
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
        graded = datetime.fromisoformat(row['graded_at']) if row['graded_at'] else None

        return Assignment(
            assignment_id=row['assignment_id'],
            title=row['title'],
            earned_points=earned,
            max_points=max_pts,
            exception=row['exception'],
            comment=row['comment'] or "No comment",
            due_date=due,
            graded_at=graded
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
            cursor.execute("DELETE FROM grade_history")
            self.logger.info("Cleared all data from database")
