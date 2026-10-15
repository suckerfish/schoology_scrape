"""
Tests for grade marks: codes that replace the score and codes that sit beside it.
"""
from decimal import Decimal

import pytest

from api.fetch_grades_v2 import APIGradeFetcherV2
from shared.models import Assignment


@pytest.fixture
def fetcher():
    # _parse_grade needs no API client
    return APIGradeFetcherV2.__new__(APIGradeFetcherV2)


@pytest.mark.parametrize("code, grade, expected", [
    (0, "8", (Decimal("8"), Decimal("10"), None)),
    (3, "0", (None, None, "Missing")),
    ("2", "", (None, None, "Incomplete")),
    (4, "10", (Decimal("10"), Decimal("10"), "Collected")),
    ("6", "4", (Decimal("4"), Decimal("10"), "Late")),
    (9, "7", (Decimal("7"), Decimal("10"), "Mark 9")),
    (None, "5", (Decimal("5"), Decimal("10"), None)),
])
def test_parse_grade_marks(fetcher, code, grade, expected):
    assert fetcher._parse_grade({"grade": grade, "max_points": "10", "exception": code}) == expected


@pytest.mark.parametrize("earned, exception, expected", [
    (None, "Missing", "Missing"),
    ("4", "Late", "4 / 10 (Late)"),
    ("10", "Collected", "10 / 10 (Collected)"),
    (None, "Collected", "Collected"),
    ("8", None, "8 / 10"),
    (None, None, "Not graded"),
])
def test_grade_string_marks(earned, exception, expected):
    a = Assignment(assignment_id="1", title="t", earned_points=earned, max_points="10", exception=exception)
    assert a.grade_string() == expected
