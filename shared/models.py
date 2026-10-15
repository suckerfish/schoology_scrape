"""
Pydantic models for normalized grade data with unique identifiers.

This module defines the data structures for ID-based change detection,
replacing the old string-key-based nested dictionaries with proper models
that preserve unique identifiers from the Schoology API.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from decimal import Decimal


# Marks that stand in for a score; other marks (Collected, Late) keep the points
SCORE_REPLACING_MARKS = {"Excused", "Incomplete", "Missing"}


class Assignment(BaseModel):
    """
    Normalized assignment model with stable unique identifier.

    Attributes:
        assignment_id: Unique identifier from Schoology API
        title: Assignment title
        earned_points: Points earned (None if not graded)
        max_points: Maximum points possible (None if not graded)
        exception: Grade mark. Missing, Excused, and Incomplete replace the
            score; any other mark (Collected, Late) sits beside it.
        comment: Teacher comment
        due_date: Due date as datetime (None if no due date)
        graded_at: When the grade was entered (None if unknown). Kept apart
            from due_date, and not compared for change detection.
    """
    assignment_id: str
    title: str
    earned_points: Optional[Decimal] = None
    max_points: Optional[Decimal] = None
    exception: Optional[str] = None  # "Missing", "Excused", "Incomplete", "Collected", "Late"
    comment: str = "No comment"
    due_date: Optional[datetime] = None
    graded_at: Optional[datetime] = None

    @field_validator('earned_points', 'max_points', mode='before')
    @classmethod
    def parse_decimal(cls, v):
        """Convert various numeric formats to Decimal"""
        if v is None or v == '':
            return None
        try:
            return Decimal(str(v))
        except:
            return None

    @field_validator('due_date', mode='before')
    @classmethod
    def parse_due_date(cls, v):
        """Parse various date formats to datetime"""
        if v is None or v == '':
            return None

        if isinstance(v, datetime):
            return v

        # Try parsing common formats
        formats = [
            '%m/%d/%y %I:%M%p',  # 08/15/25 03:00pm
            '%Y-%m-%d %H:%M:%S',  # 2025-08-15 15:00:00
            '%Y-%m-%dT%H:%M:%S',  # 2025-08-15T15:00:00
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(v), fmt)
            except:
                continue

        return None

    def has_grade(self) -> bool:
        """Check if assignment has a grade"""
        return (self.exception is not None) or (self.earned_points is not None)

    def grade_string(self) -> str:
        """Format grade as human-readable string"""
        if self.exception in SCORE_REPLACING_MARKS:
            return self.exception

        if self.earned_points is None:
            return self.exception or "Not graded"

        if self.max_points:
            score = f"{self.earned_points} / {self.max_points}"
        else:
            score = str(self.earned_points)

        return f"{score} ({self.exception})" if self.exception else score

    def grade_changed(self, other: 'Assignment') -> bool:
        """
        Check if grade has changed compared to another assignment.

        Only compares semantically meaningful fields:
        - earned_points
        - max_points
        - exception
        - comment (if substantive)
        """
        if self.exception != other.exception:
            return True

        if self.earned_points != other.earned_points:
            return True

        if self.max_points != other.max_points:
            return True

        # Only consider comment changes if they're substantive (not "No comment")
        if self.comment != "No comment" or other.comment != "No comment":
            if self.comment != other.comment:
                return True

        return False


def _to_decimal(v):
    """Convert a numeric API value to Decimal, or None if it is blank or invalid"""
    if v is None or v == '':
        return None
    try:
        return Decimal(str(v))
    except:
        return None


def format_grade(grade: Optional[Decimal], letter: Optional[str] = None) -> str:
    """Format a reported percentage grade the way the Schoology GUI does"""
    if grade is None:
        return "—"
    pct = f"{grade.normalize():f}%"
    return f"{letter} ({pct})" if letter else pct


class Category(BaseModel):
    """
    Grading category with assignments.

    Attributes:
        category_id: Unique identifier from Schoology (0 for uncategorized)
        name: Category name
        weight: Category weight as percentage (None if not weighted)
        grade: Category grade for this period, as reported by Schoology
        assignments: List of assignments in this category
    """
    # The fetcher sets grades after construction; validate those too
    model_config = ConfigDict(validate_assignment=True)

    category_id: int
    name: str
    weight: Optional[Decimal] = None
    grade: Optional[Decimal] = None
    assignments: list[Assignment] = Field(default_factory=list)

    @field_validator('grade', mode='before')
    @classmethod
    def parse_grade(cls, v):
        return _to_decimal(v)

    @field_validator('weight', mode='before')
    @classmethod
    def parse_weight(cls, v):
        """Convert weight to Decimal"""
        if v is None or v == '':
            return None
        try:
            return Decimal(str(v))
        except:
            return None


class Period(BaseModel):
    """
    Grading period with categories.

    Attributes:
        period_id: Unique identifier (constructed from period title)
        name: Period name (e.g., "2025-2026 T1")
        grade: Period grade as reported by Schoology (None until graded)
        letter: Letter grade from the section's grading scale (None if no scale)
        categories: List of grading categories
    """
    # The fetcher sets grades after construction; validate those too
    model_config = ConfigDict(validate_assignment=True)

    period_id: str
    name: str
    grade: Optional[Decimal] = None
    letter: Optional[str] = None
    categories: list[Category] = Field(default_factory=list)

    @field_validator('grade', mode='before')
    @classmethod
    def parse_grade(cls, v):
        return _to_decimal(v)


class Section(BaseModel):
    """
    Course section with periods.

    Attributes:
        section_id: Unique identifier from Schoology API
        course_title: Course title
        section_title: Section title
        course_grade: Overall course grade as reported by Schoology. The GUI
            sometimes hides it, but the API still returns it.
        course_letter: Letter grade from the section's grading scale
        periods: List of grading periods
    """
    # The fetcher sets grades after construction; validate those too
    model_config = ConfigDict(validate_assignment=True)

    section_id: str
    course_title: str
    section_title: str
    course_grade: Optional[Decimal] = None
    course_letter: Optional[str] = None
    periods: list[Period] = Field(default_factory=list)

    @field_validator('course_grade', mode='before')
    @classmethod
    def parse_grade(cls, v):
        return _to_decimal(v)

    @property
    def full_name(self) -> str:
        """Get full course name"""
        if self.section_title:
            return f"{self.course_title}: {self.section_title}"
        return self.course_title


class GradeData(BaseModel):
    """
    Complete grade data snapshot.

    Attributes:
        timestamp: When this snapshot was taken
        sections: List of all course sections
    """
    timestamp: datetime
    sections: list[Section] = Field(default_factory=list)

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """Find assignment by ID across all sections/periods/categories"""
        for section in self.sections:
            for period in section.periods:
                for category in period.categories:
                    for assignment in category.assignments:
                        if assignment.assignment_id == assignment_id:
                            return assignment
        return None

    def get_all_assignments(self) -> list[tuple[Section, Period, Category, Assignment]]:
        """Get all assignments with their context (section, period, category)"""
        result = []
        for section in self.sections:
            for period in section.periods:
                for category in period.categories:
                    for assignment in category.assignments:
                        result.append((section, period, category, assignment))
        return result
