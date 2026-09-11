"""
SQLite-based grade data storage for efficient ID-based change detection.

This module provides a simple database layer for storing the current state
of grades, replacing the old file-based snapshot comparison approach.
"""
import sqlite3
import logging
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager
from .models import Assignment, Category, Period, Section, GradeData
from decimal import Decimal


@dataclass
class HistoryPoint:
    """
    One assignment's grade as of one snapshot.

    Labels come from assignment_meta, so they survive section pruning and are
    present even for courses the API no longer reports.
    """
    snapshot_id: int
    assignment_id: str
    recorded_at: datetime
    earned_points: Optional[Decimal] = None
    max_points: Optional[Decimal] = None
    exception: Optional[str] = None
    title: Optional[str] = None
    section_id: Optional[str] = None
    section_name: Optional[str] = None
    period_id: Optional[str] = None
    period_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None

    def percentage(self) -> Optional[float]:
        """Score as a percentage, or None if ungraded or unscored"""
        if self.earned_points is None or not self.max_points or self.max_points <= 0:
            return None
        return float(self.earned_points / self.max_points * 100)


class GradeStore:
    """
    SQLite-based storage for grade data with ID-based lookups.

    Schema:
        - snapshots: Metadata about grade data snapshots
        - sections: Course sections
        - periods: Grading periods within sections
        - categories: Grading categories within periods
        - assignments: Individual assignments with grades (current state only)
        - assignment_history: Append-only point-in-time grades, keyed by snapshot
        - assignment_meta: Stable labels for history rows, kept after pruning
    """

    def __init__(
        self,
        db_path: str = "data/grades.db",
        history_enabled: bool = True,
        snapshot_retention: int = 0,
    ):
        """
        Initialize grade store.

        Args:
            db_path: Path to SQLite database file
            history_enabled: Record a point-in-time row per assignment per run
            snapshot_retention: Snapshots to keep (0 = unlimited). Pruning a
                snapshot cascades to its history rows, so this is the real
                history retention knob.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_enabled = history_enabled
        self.snapshot_retention = snapshot_retention
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

            # Append-only grade history: one row per assignment per snapshot.
            # Deliberately NOT tied to sections/categories, so pruning a course
            # that ended does not erase the history a dashboard wants to scrub.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignment_history (
                    snapshot_id INTEGER NOT NULL,
                    assignment_id TEXT NOT NULL,
                    earned_points TEXT,
                    max_points TEXT,
                    exception TEXT,
                    recorded_at TEXT NOT NULL,
                    PRIMARY KEY (snapshot_id, assignment_id),
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
                )
            """)

            # Labels for history rows. One row per assignment ever seen, never
            # pruned, so a time series keeps its course/category names even
            # after the section disappears from the feed.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignment_meta (
                    assignment_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    section_id TEXT,
                    section_name TEXT,
                    period_id TEXT,
                    period_name TEXT,
                    category_id INTEGER,
                    category_name TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_assignment
                ON assignment_history(assignment_id, recorded_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_recorded_at
                ON assignment_history(recorded_at)
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
                self._save_section(cursor, section, grade_data.timestamp, snapshot_id)

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

    def _prune_snapshots(self, cursor: sqlite3.Cursor):
        """
        Cap the snapshots table.

        Deleting a snapshot cascades to its assignment_history rows, so this
        is the retention policy for grade history, not just for metadata.
        A retention of 0 keeps everything.
        """
        keep = self.snapshot_retention
        if keep <= 0:
            return

        cursor.execute(
            "DELETE FROM snapshots WHERE id NOT IN "
            "(SELECT id FROM snapshots ORDER BY timestamp DESC, id DESC LIMIT ?)",
            (keep,)
        )
        if cursor.rowcount > 0:
            self.logger.info(f"Pruned {cursor.rowcount} old snapshot row(s)")

    def _save_section(self, cursor: sqlite3.Cursor, section: Section, timestamp: datetime,
                      snapshot_id: Optional[int] = None):
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
            self._save_period(cursor, period, section, timestamp, snapshot_id)

    def _save_period(self, cursor: sqlite3.Cursor, period: Period, section: Section, timestamp: datetime,
                     snapshot_id: Optional[int] = None):
        """Save period and its nested data"""
        section_id = section.section_id
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
            self._save_category(cursor, category, section, period, timestamp, snapshot_id)

    def _save_category(self, cursor: sqlite3.Cursor, category: Category, section: Section, period: Period,
                       timestamp: datetime, snapshot_id: Optional[int] = None):
        """Save category and its nested data"""
        period_id = period.period_id
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
            self._save_assignment(cursor, assignment, section, period, category, timestamp, snapshot_id)

    def _save_assignment(self, cursor: sqlite3.Cursor, assignment: Assignment, section: Section,
                         period: Period, category: Category, timestamp: datetime,
                         snapshot_id: Optional[int] = None):
        """Save assignment current state, and its history row for this snapshot"""
        category_id = category.category_id
        period_id = period.period_id
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

        if self.history_enabled and snapshot_id is not None:
            self._record_history(
                cursor,
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                assignment_id=assignment.assignment_id,
                earned=earned_str,
                max_points=max_str,
                exception=assignment.exception,
                title=assignment.title,
                section_id=section.section_id,
                section_name=section.full_name,
                period_id=period.period_id,
                period_name=period.name,
                category_id=category.category_id,
                category_name=category.name,
            )

    def _record_history(self, cursor: sqlite3.Cursor, snapshot_id: int, timestamp: datetime,
                        assignment_id: str, earned: Optional[str], max_points: Optional[str],
                        exception: Optional[str], title: str,
                        section_id: Optional[str], section_name: Optional[str],
                        period_id: Optional[str], period_name: Optional[str],
                        category_id: Optional[int], category_name: Optional[str]) -> None:
        """
        Write one point-in-time row plus its labels.

        The history row is an upsert on (snapshot_id, assignment_id) so a
        re-run against the same snapshot corrects rather than duplicates.
        """
        recorded_at = timestamp.isoformat()

        cursor.execute(
            """
            INSERT INTO assignment_history
            (snapshot_id, assignment_id, earned_points, max_points, exception, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_id, assignment_id) DO UPDATE SET
                earned_points = excluded.earned_points,
                max_points = excluded.max_points,
                exception = excluded.exception,
                recorded_at = excluded.recorded_at
            """,
            (snapshot_id, assignment_id, earned, max_points, exception, recorded_at)
        )

        cursor.execute(
            """
            INSERT INTO assignment_meta
            (assignment_id, title, section_id, section_name, period_id, period_name,
             category_id, category_name, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET
                title = excluded.title,
                section_id = COALESCE(excluded.section_id, assignment_meta.section_id),
                section_name = COALESCE(excluded.section_name, assignment_meta.section_name),
                period_id = COALESCE(excluded.period_id, assignment_meta.period_id),
                period_name = COALESCE(excluded.period_name, assignment_meta.period_name),
                category_id = COALESCE(excluded.category_id, assignment_meta.category_id),
                category_name = COALESCE(excluded.category_name, assignment_meta.category_name),
                first_seen = MIN(excluded.first_seen, assignment_meta.first_seen),
                last_seen = MAX(excluded.last_seen, assignment_meta.last_seen)
            """,
            (assignment_id, title, section_id, section_name, period_id, period_name,
             category_id, category_name, recorded_at, recorded_at)
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
                "SELECT timestamp FROM snapshots ORDER BY timestamp DESC, id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return datetime.fromisoformat(row['timestamp'])
            return None

    def get_snapshot_times(self) -> list[tuple[int, datetime]]:
        """
        Get every retained snapshot as (id, timestamp), oldest first.

        This is the time axis for a scrubbing dashboard.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY timestamp, id")
            return [(row['id'], datetime.fromisoformat(row['timestamp'])) for row in cursor.fetchall()]

    def get_assignment_history(self, assignment_id: str, since: Optional[datetime] = None,
                               until: Optional[datetime] = None) -> list[HistoryPoint]:
        """
        Get one assignment's full time series, oldest first.

        Args:
            assignment_id: Assignment to trace
            since: Optional inclusive lower bound on recorded_at
            until: Optional inclusive upper bound on recorded_at
        """
        sql = (
            "SELECT h.*, m.title, m.section_id, m.section_name, m.period_id, "
            "       m.period_name, m.category_id, m.category_name "
            "FROM assignment_history h "
            "LEFT JOIN assignment_meta m ON m.assignment_id = h.assignment_id "
            "WHERE h.assignment_id = ?"
        )
        params: list = [assignment_id]

        if since is not None:
            sql += " AND h.recorded_at >= ?"
            params.append(since.isoformat())
        if until is not None:
            sql += " AND h.recorded_at <= ?"
            params.append(until.isoformat())

        sql += " ORDER BY h.recorded_at, h.snapshot_id"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [self._row_to_history_point(row) for row in cursor.fetchall()]

    def get_history_at(self, timestamp: datetime) -> list[HistoryPoint]:
        """
        Get every assignment's most recent value at or before a point in time.

        This is the query a scrubber runs per tick: it carries the last known
        value forward, so assignments that did not change still report.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM (
                    SELECT h.*, m.title, m.section_id, m.section_name, m.period_id,
                           m.period_name, m.category_id, m.category_name,
                           ROW_NUMBER() OVER (
                               PARTITION BY h.assignment_id
                               ORDER BY h.recorded_at DESC, h.snapshot_id DESC
                           ) AS rn
                    FROM assignment_history h
                    LEFT JOIN assignment_meta m ON m.assignment_id = h.assignment_id
                    WHERE h.recorded_at <= ?
                )
                WHERE rn = 1
                ORDER BY section_name, period_name, category_name, title
                """,
                (timestamp.isoformat(),)
            )
            return [self._row_to_history_point(row) for row in cursor.fetchall()]

    def _row_to_history_point(self, row: sqlite3.Row) -> HistoryPoint:
        """Convert a joined history row to a HistoryPoint"""
        return HistoryPoint(
            snapshot_id=row['snapshot_id'],
            assignment_id=row['assignment_id'],
            recorded_at=datetime.fromisoformat(row['recorded_at']),
            earned_points=Decimal(row['earned_points']) if row['earned_points'] else None,
            max_points=Decimal(row['max_points']) if row['max_points'] else None,
            exception=row['exception'],
            title=row['title'],
            section_id=row['section_id'],
            section_name=row['section_name'],
            period_id=row['period_id'],
            period_name=row['period_name'],
            category_id=row['category_id'],
            category_name=row['category_name'],
        )

    def append_history_snapshot(self, timestamp: datetime, records: list[dict]) -> Optional[int]:
        """
        Append a synthetic snapshot of history rows without touching current state.

        Used by the backfill script to replay historical change-log entries.
        Reuses an existing snapshot if one already carries this timestamp, so
        re-running a backfill corrects rows instead of duplicating snapshots.

        Args:
            timestamp: When these values were observed
            records: Dicts with an ``assignment_id`` plus any of ``earned_points``,
                ``max_points``, ``exception``, ``title``, ``section_name``,
                ``period_name``, ``category_name``

        Returns:
            The snapshot ID written to, or None if records was empty
        """
        if not records:
            return None

        iso = timestamp.isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM snapshots WHERE timestamp = ?", (iso,))
            row = cursor.fetchone()
            if row:
                snapshot_id = row['id']
            else:
                cursor.execute("INSERT INTO snapshots (timestamp) VALUES (?)", (iso,))
                snapshot_id = cursor.lastrowid

            for record in records:
                earned = record.get('earned_points')
                max_points = record.get('max_points')
                self._record_history(
                    cursor,
                    snapshot_id=snapshot_id,
                    timestamp=timestamp,
                    assignment_id=record['assignment_id'],
                    earned=str(earned) if earned is not None else None,
                    max_points=str(max_points) if max_points is not None else None,
                    exception=record.get('exception'),
                    title=record.get('title') or record['assignment_id'],
                    section_id=record.get('section_id'),
                    section_name=record.get('section_name'),
                    period_id=record.get('period_id'),
                    period_name=record.get('period_name'),
                    category_id=record.get('category_id'),
                    category_name=record.get('category_name'),
                )

            return snapshot_id

    def clear_all_data(self):
        """Clear all data from database (for testing)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM assignment_history")
            cursor.execute("DELETE FROM assignment_meta")
            cursor.execute("DELETE FROM assignments")
            cursor.execute("DELETE FROM categories")
            cursor.execute("DELETE FROM periods")
            cursor.execute("DELETE FROM sections")
            cursor.execute("DELETE FROM snapshots")
            self.logger.info("Cleared all data from database")
