"""
Tests for reported course, period, and category grades and grade_history.
"""
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from api.fetch_grades_v2 import APIGradeFetcherV2
from shared.grade_store import GradeStore
from shared.id_comparator import IDComparator
from shared.models import Assignment, Category, Period, Section, GradeData, format_grade


SCALE_ID = 12077308
LEVELS = [("F", 0), ("D", 60), ("C", 70), ("B-", 80), ("B", 83), ("B+", 87), ("A", 90)]


class FakeClient:
    """Serves a grades feed shaped like the real /users/{id}/grades response"""

    def __init__(self, grades):
        self.grades = grades

    def get_sections(self):
        return [{"id": "s1", "course_title": "Algebra 1", "section_title": "Section 27"}]

    def get_grades(self):
        return self.grades

    def get_assignments(self, section_id):
        return [{"id": 100, "title": "Unit 1 Test"}]

    def get_assignment_comments(self, section_id, assignment_id):
        return []

    def get_grading_categories(self, section_id):
        return [{"id": 10, "title": "Assessments", "weight": 80},
                {"id": 11, "title": "Homework", "weight": 20}]

    def get_grading_scales(self, section_id):
        return [{"id": SCALE_ID, "scale": {"level": [{"grade": g, "cutoff": c} for g, c in LEVELS]}}]


def grades_feed(course=86.84, period=86.84, assessments=87.5, scale_id=SCALE_ID):
    return {"section": [{
        "section_id": "s1",
        "period": [{
            "period_id": "p1", "period_title": "2026-2027 T1",
            "assignment": [{"assignment_id": 100, "category_id": 10, "grade": 9, "max_points": 10}],
        }],
        "final_grade": [
            {"period_id": "p1", "grade": period, "scale_id": scale_id,
             "grading_category": [{"category_id": 10, "grade": assessments},
                                  {"category_id": 11, "grade": 84.21}]},
            {"period_id": "p2", "grade": None, "scale_id": scale_id,
             "grading_category": [{"category_id": 10, "grade": None}]},
            {"period_id": "final", "grade": course, "scale_id": scale_id, "grading_category": []},
        ],
    }]}


def fetch(grades) -> GradeData:
    fetcher = APIGradeFetcherV2.__new__(APIGradeFetcherV2)
    fetcher.client = FakeClient(grades)
    fetcher.sections_cache = {}
    fetcher.categories_cache = {}
    fetcher.assignments_cache = {}
    fetcher.enrollment_id_map = {}
    fetcher.bulk_loaded = set()
    fetcher.scales_cache = {}
    return fetcher.fetch_all_grades()


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield GradeStore(db_path)
    Path(db_path).unlink(missing_ok=True)


class TestParseFinalGrade:

    def test_course_period_and_category_grades(self):
        section = fetch(grades_feed()).sections[0]
        assert section.course_grade == Decimal("86.84")
        assert section.course_letter == "B"

        assert len(section.periods) == 1  # ungraded future period is skipped
        period = section.periods[0]
        assert period.grade == Decimal("86.84")
        assert period.letter == "B"

        grades = {c.name: c.grade for c in period.categories}
        assert grades == {"Assessments": Decimal("87.5"), "Homework": Decimal("84.21")}

    def test_category_without_graded_assignments_is_added(self):
        period = fetch(grades_feed()).sections[0].periods[0]
        homework = next(c for c in period.categories if c.name == "Homework")
        assert homework.assignments == []
        assert homework.weight == Decimal("20")

    def test_scale_zero_has_no_letter(self):
        section = fetch(grades_feed(scale_id=0)).sections[0]
        assert section.course_grade == Decimal("86.84")
        assert section.course_letter is None


class TestStoreGrades:

    def test_grades_round_trip(self, temp_db):
        temp_db.save_grade_data(fetch(grades_feed()))
        section = temp_db.get_section("s1")
        assert section.course_grade == Decimal("86.84")
        assert section.course_letter == "B"
        assert section.periods[0].grade == Decimal("86.84")
        assert {c.grade for c in section.periods[0].categories} == {Decimal("87.5"), Decimal("84.21")}

    def test_history_records_first_values_then_only_changes(self, temp_db):
        temp_db.save_grade_data(fetch(grades_feed()))
        temp_db.save_grade_data(fetch(grades_feed()))
        temp_db.save_grade_data(fetch(grades_feed(course=82.5, period=82.5, assessments=81)))

        with temp_db._get_connection() as conn:
            rows = conn.execute(
                "SELECT kind, old_value, new_value FROM grade_history ORDER BY id"
            ).fetchall()
        history = [tuple(row) for row in rows]

        assert ('course', None, '86.84') in history
        assert ('assignment', None, '9 / 10') in history
        changes = [row for row in history if row[1] is not None]
        assert sorted(changes) == [
            ('category', '87.5', '81'),
            ('course', '86.84', '82.5'),
            ('period', '86.84', '82.5'),
        ]

    def test_adds_grade_columns_to_existing_database(self, temp_db):
        with temp_db._get_connection() as conn:
            conn.execute("ALTER TABLE sections DROP COLUMN course_grade")
            conn.execute("ALTER TABLE periods DROP COLUMN grade")
            conn.execute("DROP TABLE grade_history")

        GradeStore(temp_db.db_path)
        GradeStore(temp_db.db_path)  # second start must not fail

        temp_db.save_grade_data(fetch(grades_feed()))
        assert temp_db.get_section("s1").course_grade == Decimal("86.84")


class TestClassGradeChanges:

    def test_unchanged_grades_report_nothing(self, temp_db):
        comparator = IDComparator(temp_db)
        comparator.detect_changes(fetch(grades_feed()))
        report = comparator.detect_changes(fetch(grades_feed()))
        assert not report.has_changes()

    def test_course_change_hides_identical_period_change(self, temp_db):
        comparator = IDComparator(temp_db)
        comparator.detect_changes(fetch(grades_feed()))
        report = comparator.detect_changes(fetch(grades_feed(course=82.5, period=82.5)))

        assert report.has_changes()
        assert [c.scope for c in report.class_changes] == ["course"]
        assert report.class_changes[0].summary() == "Course grade: B (86.84%) -> B- (82.5%)"
        assert "Class grades" in report.format_for_notification()

    def test_period_change_reported_when_it_differs_from_course(self, temp_db):
        comparator = IDComparator(temp_db)
        comparator.detect_changes(fetch(grades_feed()))
        report = comparator.detect_changes(fetch(grades_feed(course=85, period=82.5)))
        assert [c.scope for c in report.class_changes] == ["course", "period"]

    def test_first_reported_grade_is_a_change(self, temp_db):
        comparator = IDComparator(temp_db)
        comparator.detect_changes(fetch(grades_feed(course=None, period=None)))
        report = comparator.detect_changes(fetch(grades_feed()))
        assert report.class_changes[0].summary() == "Course grade: B (86.84%)"


def test_format_grade():
    assert format_grade(Decimal("100"), "A+") == "A+ (100%)"
    assert format_grade(Decimal("84.04")) == "84.04%"
    assert format_grade(None) == "—"
